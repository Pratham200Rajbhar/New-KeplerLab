"""Reflection — evaluates tool output quality and enforces safety limits.

Decides whether to retry the current step, execute the next plan step,
add dynamic fallback steps, or finalize the response.

Includes self-healing code repair: when code execution fails,
the repair loop re-generates code and retries up to MAX_CODE_REPAIR_ATTEMPTS.

Quality evaluation checks:
    - Tool success/failure status
    - Output length and content quality
    - Dynamic fallback injection (e.g. research_tool when RAG returns empty)
    - Code repair for failed code_executor / file_generator / python_tool

Safety limits (from state.py):
    MAX_AGENT_ITERATIONS = 7    -- hard stop on total loop iterations
    MAX_TOOL_CALLS       = 10   -- hard stop on total tool calls
    TOKEN_BUDGET         = 12000 -- hard stop on token consumption

Per-step retry budget:
    Up to 2 retries per individual plan step (tracked via step_retries).
    After 2 retries the step is abandoned and the agent proceeds.
"""

from __future__ import annotations

import logging

from app.core.config import settings
from app.services.agent.state import (
    AgentState,
    MAX_AGENT_ITERATIONS,
    MAX_TOOL_CALLS,
    TOKEN_BUDGET,
)

logger = logging.getLogger(__name__)

_MAX_STEP_RETRIES = 2   # max retries for a single failing plan step
_MIN_USEFUL_OUTPUT_LEN = 50  # chars — below this, output is considered empty

# Tools that support self-healing code repair
_CODE_TOOLS = {"code_executor", "file_generator", "python_tool"}


async def reflect(state: AgentState) -> AgentState:
    """Reflection node — checks tool output quality and enforces safety limits.

    Decision tree:
    1. Increment iteration counter.
    2. Enforce hard safety limits (iterations, tool calls, tokens).
    3. Self-healing code repair: if last tool was code-related and failed,
       attempt LLM-based repair up to MAX_CODE_REPAIR_ATTEMPTS.
    4. If last tool failed AND we have retries left: go back one step.
    5. If output is near-empty for QUESTION intent AND no research fallback
       was attempted yet: inject research_tool as dynamic fallback.
    6. If more plan steps remain: continue to next step.
    7. All steps done (or retries exhausted): proceed to response generation.
    """
    iterations = state.get("iterations", 0) + 1
    total_tool_calls = state.get("total_tool_calls", 0)
    total_tokens = state.get("total_tokens", 0)
    tool_results = state.get("tool_results", [])
    plan = list(state.get("plan", []))
    current_step = state.get("current_step", 0)
    step_retries = state.get("step_retries", 0)
    intent = state.get("intent", "UNKNOWN")
    selected_tool = state.get("selected_tool", "unknown")
    repair_attempts = state.get("repair_attempts", 0)

    logger.info(
        "[reflect] iter=%d | tool=%s | intent=%s | steps=%d/%d | retries=%d | repairs=%d | tokens=%d",
        iterations,
        selected_tool,
        intent,
        current_step,
        len(plan),
        step_retries,
        repair_attempts,
        total_tokens,
    )

    # -- 1. Hard safety limits ---------------------------------------------------
    if iterations >= MAX_AGENT_ITERATIONS:
        logger.warning("[reflect] STOP: max iterations reached (%d)", MAX_AGENT_ITERATIONS)
        return {**state, "iterations": iterations, "needs_retry": False,
                "stopped_reason": "max_iterations"}

    if total_tool_calls >= MAX_TOOL_CALLS:
        logger.warning("[reflect] STOP: max tool calls reached (%d)", MAX_TOOL_CALLS)
        return {**state, "iterations": iterations, "needs_retry": False,
                "stopped_reason": "max_tool_calls"}

    if total_tokens >= TOKEN_BUDGET:
        logger.warning("[reflect] STOP: token budget exhausted (%d)", TOKEN_BUDGET)
        return {**state, "iterations": iterations, "needs_retry": False,
                "stopped_reason": "token_budget"}

    # -- 2. Check last tool result quality ---------------------------------------
    if tool_results:
        last_result = tool_results[-1]
        last_success = last_result.get("success", False)
        last_output = (last_result.get("output") or "").strip()
        last_tool = last_result.get("tool_name", "?")

        # -- 2a. Self-healing code repair for code execution tools ------
        if not last_success and last_tool in _CODE_TOOLS:
            last_stderr = state.get("last_stderr", "") or last_result.get("error", "")
            max_repairs = settings.MAX_CODE_REPAIR_ATTEMPTS

            if last_stderr and repair_attempts < max_repairs:
                # Attempt code repair via LLM
                logger.info(
                    "[reflect] Code error detected — repair attempt %d/%d for tool=%s",
                    repair_attempts + 1,
                    max_repairs,
                    last_tool,
                )
                try:
                    from app.services.agent.tools.code_repair import repair_code
                    from app.services.llm_service.llm import get_llm

                    # Get broken code from step_log or tool metadata
                    step_log = state.get("step_log", [])
                    broken_code = ""
                    if step_log:
                        broken_code = step_log[-1].get("code", "")
                    if not broken_code:
                        broken_code = last_result.get("metadata", {}).get("code", "")

                    if broken_code:
                        llm = get_llm(temperature=0.0, max_tokens=4000)
                        fixed_code = await repair_code(broken_code, last_stderr, llm)

                        # Update the plan step's code with the fixed version
                        prev_step_idx = max(0, current_step - 1)
                        if prev_step_idx < len(plan):
                            plan[prev_step_idx]["code"] = fixed_code

                        return {
                            **state,
                            "iterations": iterations,
                            "plan": plan,
                            "repair_attempts": repair_attempts + 1,
                            "needs_retry": True,
                            "current_step": prev_step_idx,  # go back to re-execute
                            "step_retries": step_retries,
                        }
                except Exception as exc:
                    logger.warning("[reflect] Code repair failed: %s", exc)

            elif repair_attempts >= max_repairs:
                logger.warning(
                    "[reflect] Code repair exhausted (%d attempts) — moving on",
                    max_repairs,
                )
                # Reset repair attempts and fall through
                return {
                    **state,
                    "iterations": iterations,
                    "repair_attempts": 0,
                    "needs_retry": False,
                    "stopped_reason": "code_repair_exhausted",
                }

        # -- 2b. Tool failed (non-code) — retry if budget allows ---
        if not last_success and last_tool not in _CODE_TOOLS:
            new_retries = step_retries + 1
            if new_retries <= _MAX_STEP_RETRIES:
                logger.info(
                    "[reflect] Tool failed — retry #%d for step %d (tool=%s)",
                    new_retries, current_step, last_tool,
                )
                return {
                    **state,
                    "iterations": iterations,
                    "step_retries": new_retries,
                    "needs_retry": True,
                    "current_step": max(0, current_step - 1),
                }
            else:
                logger.warning(
                    "[reflect] Tool '%s' failed after %d retries — moving on",
                    last_tool, _MAX_STEP_RETRIES,
                )
                # Fall through to step-advance logic below

        # -- 2c. Reset repair_attempts on success ---
        if last_success and repair_attempts > 0:
            logger.info("[reflect] Code repair succeeded after %d attempts", repair_attempts)
            state = {**state, "repair_attempts": 0}

        # -- 2d. Output too short for QUESTION intent → inject research fallback --
        if last_success and len(last_output) < _MIN_USEFUL_OUTPUT_LEN and intent == "QUESTION":
            already_researched = any(
                r.get("tool_name") == "research_tool" for r in tool_results
            )
            if not already_researched:
                logger.info(
                    "[reflect] RAG output too short (%d chars) — injecting research fallback",
                    len(last_output),
                )
                plan.append({
                    "tool": "research_tool",
                    "description": "Fallback web search (RAG returned insufficient results)",
                })
                return {
                    **state,
                    "iterations": iterations,
                    "plan": plan,
                    "needs_retry": True,
                    "step_retries": 0,
                }

    # -- 3. More plan steps remaining? -------------------------------------------
    if current_step < len(plan):
        logger.info(
            "[reflect] CONTINUE: next step %d/%d", current_step + 1, len(plan)
        )
        return {**state, "iterations": iterations, "needs_retry": True, "step_retries": 0}

    # -- 4. All steps complete ---------------------------------------------------
    logger.info("[reflect] RESPOND: all %d plan step(s) complete", len(plan))
    return {**state, "iterations": iterations, "needs_retry": False,
            "stopped_reason": "plan_complete"}


def should_continue(state: AgentState) -> str:
    """Conditional edge: decide whether to loop back or finish.

    Returns:
        'continue' -> route back to tool_router
        'retry'    -> route back to tool_router (after code repair)
        'respond'  -> proceed to response_generator
    """
    iterations = state.get("iterations", 0)
    total_tokens = state.get("total_tokens", 0)

    if iterations >= MAX_AGENT_ITERATIONS:
        logger.warning("[reflect] Edge: FORCE STOP due to iteration limit")
        return "respond"

    if total_tokens >= TOKEN_BUDGET:
        logger.warning("[reflect] Edge: FORCE STOP due to token budget")
        return "respond"

    if state.get("needs_retry", False):
        # Check if this is a code repair retry
        if state.get("repair_attempts", 0) > 0:
            logger.debug("[reflect] Edge decision: retry (code repair)")
            return "retry"
        logger.debug("[reflect] Edge decision: continue")
        return "continue"

    logger.debug("[reflect] Edge decision: respond")
    return "respond"
