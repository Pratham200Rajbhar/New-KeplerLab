"""Router — selects and executes tools with chaining and conditional execution.

Supports:
- Conditional skip: step with "conditional": "if_previous_empty" is skipped
  if the previous tool returned non-empty successful output.
- Tool chaining: step with "uses_previous_output": True gets the previous
  tool's output injected as previous_context/previous_metadata kwargs.
- Step-by-step SSE streaming: emits step/step_done events for each tool.
- Data profiler and file generator dispatch.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

from app.services.agent.state import AgentState, ToolResult, compress_tool_result
from app.services.agent.tools_registry import get_tool, list_tools

logger = logging.getLogger(__name__)

# Step label mapping for SSE events
_STEP_LABELS = {
    "rag_tool": "🔍 Searching your materials",
    "research_tool": "🌐 Researching online",
    "python_tool": "🐍 Writing & running Python code",
    "quiz_tool": "📝 Generating quiz",
    "flashcard_tool": "🃏 Creating flashcards",
    "ppt_tool": "📊 Building presentation",
    "data_profiler": "🧠 Analyzing dataset structure",
    "file_generator": "📄 Generating file",
}


async def route_and_execute(state: AgentState) -> AgentState:
    """Tool routing and execution node with chaining support.

    Steps:
      1. Read the current plan step.
      2. Check conditional execution (skip if previous had results).
      3. Handle special tools (data_profiler, file_generator) directly.
      4. Build kwargs — inject previous tool output if chaining enabled.
      5. Execute the tool.
      6. Record step_log entry and append the ToolResult.
      7. Advance the step counter.
    """
    plan = state.get("plan", [])
    current_step = state.get("current_step", 0)
    iterations = state.get("iterations", 0)
    tool_results = list(state.get("tool_results", []))
    step_log = list(state.get("step_log", []))
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
    step_label = _STEP_LABELS.get(tool_name, f"⚙️ Running {tool_name}")

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

    step_start = time.time()

    logger.info(
        "[router] Executing | intent=%s | step=%d/%d | tool=%s | iter=%d | desc=%r",
        intent,
        current_step + 1,
        len(plan),
        tool_name,
        iterations,
        step_desc,
    )

    # -- Handle special tools directly ----------------------------------------

    # Data profiler: runs directly, not through tool registry
    if tool_name == "data_profiler":
        try:
            from app.services.agent.tools.data_profiler import profile_dataset
            updated_state = await profile_dataset(state)
            step_time = time.time() - step_start

            result = ToolResult(
                tool_name="data_profiler",
                success=True,
                output=f"Dataset profiled: {updated_state.get('analysis_context', {}).get('shape', 'unknown')}",
                metadata=updated_state.get("analysis_context", {}),
                tokens_used=0,
            )
            tool_results.append(compress_tool_result(result))

            step_log.append({
                "tool": tool_name,
                "label": step_label,
                "status": "success",
                "time_taken": round(step_time, 2),
            })

            return {
                **updated_state,
                "tool_results": tool_results,
                "selected_tool": tool_name,
                "current_step": current_step + 1,
                "step_retries": 0,
                "step_log": step_log,
                "total_tool_calls": state.get("total_tool_calls", 0) + 1,
            }
        except Exception as exc:
            logger.exception("[router] data_profiler failed: %s", exc)
            step_time = time.time() - step_start
            result = ToolResult(
                tool_name="data_profiler",
                success=False,
                output="Dataset profiling failed.",
                metadata={},
                error=str(exc),
                tokens_used=0,
            )
            tool_results.append(compress_tool_result(result))
            step_log.append({
                "tool": tool_name,
                "label": step_label,
                "status": "error",
                "time_taken": round(step_time, 2),
                "stderr": str(exc),
            })
            return {
                **state,
                "tool_results": tool_results,
                "selected_tool": tool_name,
                "current_step": current_step + 1,
                "step_retries": 0,
                "step_log": step_log,
                "total_tool_calls": state.get("total_tool_calls", 0) + 1,
            }

    # File generator: runs directly, not through tool registry
    if tool_name == "file_generator":
        try:
            from app.services.agent.tools.file_generator import generate_file
            # Get code from the plan step or from the last tool result
            code = step.get("code", "")
            if not code and tool_results:
                last = tool_results[-1]
                code = last.get("metadata", {}).get("generated_code", "")

            result = await generate_file(state, code)
            step_time = time.time() - step_start

            # Update generated_files in state
            new_files = result.get("metadata", {}).get("generated_files", [])
            generated_files = list(state.get("generated_files", []))
            generated_files.extend(new_files)

            step_log_entry = {
                "tool": tool_name,
                "label": step_label,
                "status": "success" if result.get("success") else "error",
                "time_taken": round(step_time, 2),
                "code": code,
                "stdout": result.get("metadata", {}).get("stdout", ""),
                "stderr": result.get("metadata", {}).get("stderr", ""),
            }
            step_log.append(step_log_entry)
            tool_results.append(compress_tool_result(result))

            return {
                **state,
                "tool_results": tool_results,
                "selected_tool": tool_name,
                "current_step": current_step + 1,
                "step_retries": 0,
                "step_log": step_log,
                "generated_files": generated_files,
                "last_stdout": result.get("metadata", {}).get("stdout", ""),
                "last_stderr": result.get("metadata", {}).get("stderr", ""),
                "total_tool_calls": state.get("total_tool_calls", 0) + 1,
            }
        except Exception as exc:
            logger.exception("[router] file_generator failed: %s", exc)
            step_time = time.time() - step_start
            result = ToolResult(
                tool_name="file_generator",
                success=False,
                output=f"File generation failed: {str(exc)}",
                metadata={},
                error=str(exc),
                tokens_used=0,
            )
            tool_results.append(compress_tool_result(result))
            step_log.append({
                "tool": tool_name,
                "label": step_label,
                "status": "error",
                "time_taken": round(step_time, 2),
                "stderr": str(exc),
            })
            return {
                **state,
                "tool_results": tool_results,
                "selected_tool": tool_name,
                "current_step": current_step + 1,
                "step_retries": 0,
                "step_log": step_log,
                "total_tool_calls": state.get("total_tool_calls", 0) + 1,
            }

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

    step_time = time.time() - step_start
    tokens_used = result.get("tokens_used", 0)
    tool_results.append(compress_tool_result(result))

    # -- Record step log entry ---------------------------------------------------
    step_log_entry = {
        "tool": tool_name,
        "label": step_label,
        "status": "success" if success else "error",
        "time_taken": round(step_time, 2),
    }
    # Include code/stdout/stderr for code execution tools
    if tool_name in ("python_tool", "code_executor"):
        meta_block = result.get("metadata", {}) or {}
        # python_tool stores the generated source under "generated_code";
        # code_executor uses "code". Accept both so code-repair can find it.
        step_log_entry["code"] = (
            meta_block.get("generated_code") or meta_block.get("code") or ""
        )
        step_log_entry["stdout"] = meta_block.get("stdout", result.get("output", ""))
        step_log_entry["stderr"] = meta_block.get("stderr", result.get("error", ""))
    step_log.append(step_log_entry)

    # -- Update stdout/stderr in state for reflection ----------------------------
    last_stdout = result.get("metadata", {}).get("stdout", "") if result.get("metadata") else ""
    last_stderr = result.get("metadata", {}).get("stderr", result.get("error", "")) if not success else ""

    return {
        **state,
        "tool_results": tool_results,
        "selected_tool": tool_name,
        "current_step": current_step + 1,
        "step_retries": 0,
        "step_log": step_log,
        "last_stdout": last_stdout,
        "last_stderr": last_stderr,
        "total_tool_calls": state.get("total_tool_calls", 0) + 1,
        "total_tokens": state.get("total_tokens", 0) + tokens_used,
    }
