"""Router — selects and executes tools with chaining and conditional execution.

Supports:
- Conditional skip: step with "conditional": "if_previous_empty" is skipped
  if the previous tool returned non-empty successful output.
- Tool chaining: step with "uses_previous_output": True gets the previous
  tool's output injected as previous_context/previous_metadata kwargs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.services.agent.state import AgentState, ToolResult, compress_tool_result
from app.services.agent.tools_registry import get_tool, list_tools

logger = logging.getLogger(__name__)


async def route_and_execute(state: AgentState) -> AgentState:
    """Tool routing and execution node with chaining support.

    Steps:
      1. Read the current plan step.
      2. Check conditional execution (skip if previous had results).
      3. Build kwargs — inject previous tool output if chaining enabled.
      4. Execute the tool.
      5. Append the ToolResult and advance the step counter.
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    iterations = state.get("iterations", 0)
    tool_results = list(state.get("tool_results", []))
    intent = state.get("intent", "UNKNOWN")

    if current_step >= len(plan):
        logger.warning(
            "[router] No more steps in plan | step=%d plan_len=%d",
            current_step, len(plan),
        )
        return state

    step = plan[current_step]
    tool_name: str = step.get("tool", "")
    step_desc: str = step.get("description", "")

    # -- Check conditional execution ------------------------------------------
    if step.get("conditional") == "if_previous_empty":
        last_result = tool_results[-1] if tool_results else None
        if last_result and last_result.get("success") and (last_result.get("output") or "").strip():
            logger.info(
                "[router] Skipping conditional step '%s' — previous tool had results",
                tool_name,
            )
            return {
                **state,
                "current_step": current_step + 1,
            }

    logger.info(
        "[router] Executing | intent=%s | step=%d/%d | tool=%s | iter=%d | desc=%r",
        intent,
        current_step + 1,
        len(plan),
        tool_name,
        iterations,
        step_desc,
    )

    # -- Look up tool (NO silent fallback) ----------------------------------------
    tool_entry = get_tool(tool_name)
    if tool_entry is None:
        logger.error(
            "[router] Tool '%s' not registered. Available tools: %s",
            tool_name,
            list_tools(),
        )
        error_result = ToolResult(
            tool_name=tool_name,
            success=False,
            output=f"Tool '{tool_name}' is not available.",
            metadata={},
            error=f"Tool '{tool_name}' is not registered in the tool registry.",
            tokens_used=0,
        )
        tool_results.append(error_result)
        return {
            **state,
            "tool_results": tool_results,
            "selected_tool": tool_name,
            "current_step": current_step + 1,
            "step_retries": 0,
            "total_tool_calls": state.get("total_tool_calls", 0) + 1,
        }

    # -- Build kwargs from state --------------------------------------------------
    user_message: str = state.get("user_message", "")
    tool_kwargs: Dict[str, Any] = {
        "user_id": state.get("user_id", ""),
        "query": user_message,
        "material_ids": state.get("material_ids", []),
        "notebook_id": state.get("notebook_id", ""),
        "session_id": state.get("session_id", ""),
        "intent": intent,
        # Pass the full user message as `topic` for content-generation tools
        "topic": user_message,
    }

    # -- Inject previous tool output for chaining ---------------------------------
    if step.get("uses_previous_output") and tool_results:
        prev = tool_results[-1]
        tool_kwargs["previous_context"] = prev.get("output", "")
        tool_kwargs["previous_metadata"] = prev.get("metadata", {})
        logger.info(
            "[router] Chaining: injecting %d chars from previous tool '%s'",
            len(tool_kwargs["previous_context"]),
            prev.get("tool_name", "unknown"),
        )

    # -- Execute tool -------------------------------------------------------------
    try:
        handler = tool_entry["handler"]
        result: ToolResult = await handler(**tool_kwargs)
    except Exception as exc:
        logger.exception(
            "[router] Unhandled exception from tool '%s': %s", tool_name, exc
        )
        result = ToolResult(
            tool_name=tool_name,
            success=False,
            output=f"Tool '{tool_name}' raised an unexpected exception.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )

    # -- Log outcome --------------------------------------------------------------
    success = result.get("success", False)
    output_preview = (result.get("output") or "")[:120]
    logger.info(
        "[router] Result | tool=%s | success=%s | output=%r | iter=%d",
        tool_name,
        success,
        output_preview,
        iterations,
    )
    if not success:
        logger.warning(
            "[router] Tool failure | tool=%s | error=%r",
            tool_name,
            result.get("error", "unknown"),
        )

    tokens_used = result.get("tokens_used", 0)
    tool_results.append(compress_tool_result(result))

    return {
        **state,
        "tool_results": tool_results,
        "selected_tool": tool_name,
        "current_step": current_step + 1,
        "step_retries": 0,
        "total_tool_calls": state.get("total_tool_calls", 0) + 1,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }
