"""Agent graph — LangGraph state machine wiring all agent nodes.

Builds a compiled StateGraph:
  intent_detection → planner → tool_router → reflection ─┐
                                     ↑                       │
                                     └── (continue) ────────┘
                                                    │
                                               (respond) → response_generator
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, AsyncIterator, Dict

from app.services.agent.state import AgentState, MAX_AGENT_ITERATIONS, TOKEN_BUDGET
from app.services.agent.intent import detect_intent
from app.services.agent.planner import plan_execution
from app.services.agent.router import route_and_execute
from app.services.agent.reflection import reflect, should_continue

logger = logging.getLogger(__name__)


# ── Combined Intent + Plan Node ───────────────────────────────


async def intent_and_plan(state: AgentState) -> AgentState:
    """Merged intent detection + planning in a single graph node.

    Saves one graph transition. When keyword intent confidence >= 0.85,
    planning is purely static and no LLM call is made at all.
    """
    state = await detect_intent(state)
    state = await plan_execution(state)
    return state


# ── Response Generator Node ───────────────────────────────────


def _format_tool_output(raw_output: str, tool_name: str, intent: str) -> str:
    """Return the tool output for inclusion in the agent response.

    - data_profiler: always empty — it is an intermediate step consumed by python_tool
    - python_tool DATA_ANALYSIS JSON: passed through as-is so the frontend's
      tryParseDataAnalysis parser can render the chart, explanation, and stdout
      correctly via ChartRenderer (data: URIs are blocked by react-markdown when
      embedded as markdown image syntax, so we never convert them here)
    - Everything else: pass through unchanged
    """
    if tool_name == "data_profiler":
        return ""

    return raw_output


async def generate_response(state: AgentState) -> AgentState:
    """Final node — synthesizes ALL successful tool results, not just the last one."""
    tool_results = state.get("tool_results", [])
    intent = state.get("intent", "QUESTION")

    iterations = state.get("iterations", 0)
    total_tokens = state.get("total_tokens", 0)
    stopped_reason = state.get("stopped_reason", "completed")

    # ── Enforce Hard Limits Fallback ─────────────────────────
    if iterations >= MAX_AGENT_ITERATIONS:
        response = "I'm sorry, I couldn't complete your request within the allowed number of steps. Please try simplifying your request."
        stopped_reason = "max_iterations"
    elif total_tokens >= TOKEN_BUDGET:
        response = "I'm sorry, your request requires too much processing power. Please try narrowing your question or breaking it into smaller parts."
        stopped_reason = "token_budget"
    elif state.get("plan_error") == "no_completed_materials":
        response = (
            "I wasn't able to find relevant information to answer this. "
            "Please check that your materials are fully processed and try again."
        )
        stopped_reason = "no_completed_materials"
    else:
        # Collect successful results
        successful = [r for r in tool_results if r.get("success")]
        failed = [r for r in tool_results if not r.get("success")]

        if not successful and failed:
            # All tools failed
            error_msgs = [r.get("error", "Unknown error") for r in failed]
            response = (
                "I'm sorry, I encountered an error while processing your request. "
                f"Error: {'; '.join(error_msgs)}"
            )
        elif successful:
            if len(successful) == 1:
                raw_output = (successful[0].get("output") or "").strip()
                tool_name = successful[0].get("tool_name", "")
                # If the single output is a DATA_ANALYSIS JSON blob, extract
                # the explanation and keep the structured data in metadata.
                response = _format_tool_output(raw_output, tool_name, intent)
            else:
                # Multi-tool synthesis: format each output individually
                context_parts = []
                for i, result in enumerate(successful):
                    tool_name = result.get("tool_name", "unknown")
                    raw_output = (result.get("output") or "").strip()
                    if not raw_output:
                        continue
                    formatted = _format_tool_output(raw_output, tool_name, intent)
                    if formatted:
                        context_parts.append(formatted)
                response = "\n\n".join(context_parts) if context_parts else ""

            if not response:
                response = "Your request has been completed successfully."
        else:
            response = "I'm sorry, I couldn't process your request. Please try again."

    # Build agent metadata for frontend — no null fields allowed
    metadata = {
        "intent": str(intent or "UNKNOWN"),
        "confidence": float(state.get("intent_confidence") or 0.0),
        "tools_used": [str(r.get("tool_name") or "unknown") for r in tool_results] if tool_results else [],
        "iterations": int(iterations or 0),
        "total_tokens": int(total_tokens or 0),
        "stopped_reason": stopped_reason,
        "step_log": state.get("step_log", []),
        "generated_files": state.get("generated_files", []),
        "repair_attempts": state.get("repair_attempts", 0),
    }

    return {
        **state,
        "response": response,
        "agent_metadata": metadata,
    }


# ── Graph Builder ─────────────────────────────────────────────


def build_agent_graph():
    """Build and compile the LangGraph agent graph.

    Returns a compiled graph that can be invoked or streamed.
    """
    try:
        from langgraph.graph import StateGraph, END
    except ImportError:
        logger.error(
            "langgraph is not installed. Install with: pip install langgraph"
        )
        raise ImportError(
            "langgraph is required for the agent. "
            "Install: pip install langgraph"
        )

    # Ensure tools are registered before building the graph
    from app.services.agent.tools_registry import ensure_tools_initialized
    ensure_tools_initialized()

    # Create graph
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("intent_and_plan", intent_and_plan)
    graph.add_node("tool_router", route_and_execute)
    graph.add_node("reflection", reflect)
    graph.add_node("response_generator", generate_response)

    # Set entry point
    graph.set_entry_point("intent_and_plan")

    # Add edges
    graph.add_edge("intent_and_plan", "tool_router")
    graph.add_edge("tool_router", "reflection")

    # Conditional edge: reflection decides whether to loop or respond
    graph.add_conditional_edges(
        "reflection",
        should_continue,
        {
            "continue": "tool_router",
            "retry": "tool_router",
            "respond": "response_generator",
        },
    )

    # Response generator goes to END
    graph.add_edge("response_generator", END)

    # Compile
    compiled = graph.compile()
    logger.info("Agent graph compiled successfully")

    return compiled


# ── Cached Graph Instance ─────────────────────────────────────

import threading

_agent_graph = None
_graph_lock = threading.Lock()


def get_agent_graph():
    """Get or create the singleton agent graph (thread-safe)."""
    global _agent_graph
    if _agent_graph is None:
        with _graph_lock:
            if _agent_graph is None:
                _agent_graph = build_agent_graph()
    return _agent_graph


# ── Agent Runner ──────────────────────────────────────────────


async def run_agent(
    state: AgentState,
) -> Dict[str, Any]:
    """Run the agent graph and return the final result.

    Args:
        user_message: The user's message
        user_id: Current user ID
        notebook_id: Current notebook ID
        material_ids: List of material IDs to use
        session_id: Chat session ID

    Returns:
        Dict with 'response' and 'agent_metadata'
    """
    graph = get_agent_graph()

    start = time.time()

    try:
        result = await graph.ainvoke(state)
        elapsed = time.time() - start

        logger.info(
            f"Agent completed in {elapsed:.2f}s | "
            f"Intent: {result.get('intent')} | "
            f"Tools: {result.get('total_tool_calls', 0)} | "
            f"Tokens: {result.get('total_tokens', 0)}"
        )

        return {
            "response": result.get("response", ""),
            "agent_metadata": result.get("agent_metadata", {}),
        }

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Agent failed after {elapsed:.2f}s: {e}")
        return {
            "response": f"I'm sorry, an error occurred: {str(e)}",
            "agent_metadata": {
                "intent": "ERROR",
                "confidence": 0.0,
                "tools_used": [],
                "iterations": 0,
                "total_tokens": 0,
            },
        }


async def run_agent_stream(
    state: AgentState,
) -> AsyncIterator[str]:
    """Run the agent graph with unified SSE streaming and unique session isolation.

    Yields SSE events:
    - event: start    data: {"session_id": "..."}
    - event: step     data: {"session_id": "...", "tool": "...", "status": "..."}
    - event: token    data: {"session_id": "...", "content": "..."}
    - event: code_stdout data: {"session_id": "...", "line": "..."}
    - event: meta     data: {"session_id": "...", "intent": "...", ...}
    - event: done     data: {"session_id": "...", "elapsed": S}
    """
    graph = get_agent_graph()
    start_time = time.time()
    session_id = state.get("session_id", "unknown")

    yield f"event: start\ndata: {json.dumps({'session_id': session_id})}\n\n"

    _emitted_done = False
    _prev_step_count = 0
    _prev_repair_attempts = 0
    _streamed_tokens = False  # Track if rag_token events already sent content
    _step_running_tool = None  # Dedup guard: tracks which tool has an active "running" step
    try:
        async for event in graph.astream_events(state, version="v2"):
            kind = event["event"]

            # 1) Chain start for tool_router — emit "step running" event
            if kind == "on_chain_start" and event.get("name") == "tool_router":
                # Extract which tool is about to run from the plan
                input_data = event.get("data", {}).get("input")
                tool_name = "unknown"
                if isinstance(input_data, dict):
                    plan = input_data.get("plan", [])
                    current_step = input_data.get("current_step", 0)
                    if plan and current_step < len(plan):
                        tool_name = plan[current_step].get("tool", "unknown")
                _step_running_tool = tool_name
                step_data = json.dumps({
                    "session_id": session_id,
                    "tool": tool_name,
                    "status": "running"
                })
                yield f"event: step\ndata: {step_data}\n\n"

            # 1a) LangChain tool start events (fallback — skip if already emitted via 1)
            elif kind == "on_tool_start":
                tool_name = event.get("name", "unknown")
                if _step_running_tool == tool_name:
                    pass  # Already emitted by on_chain_start for tool_router
                else:
                    _step_running_tool = tool_name
                    step_data = json.dumps({
                        "session_id": session_id,
                        "tool": tool_name,
                        "status": "running"
                    })
                    yield f"event: step\ndata: {step_data}\n\n"

            # 1b) Chain end for tool_router — emit step_done + step log
            elif kind == "on_chain_end" and event.get("name") == "tool_router":
                _step_running_tool = None  # Reset dedup guard
                output = event["data"].get("output")
                if isinstance(output, dict):
                    step_log = output.get("step_log", [])
                    selected_tool = output.get("selected_tool", "unknown")

                    # Emit step_done
                    if len(step_log) > _prev_step_count:
                        latest_step = step_log[-1]
                        yield f"event: step_done\ndata: {json.dumps({'session_id': session_id, 'tool': selected_tool, 'status': latest_step.get('status', 'success'), 'step': latest_step})}\n\n"
                        _prev_step_count = len(step_log)

                        # Emit code_written if step has code
                        if latest_step.get("code"):
                            yield f"event: code_written\ndata: {json.dumps({'session_id': session_id, 'code': latest_step['code']})}\n\n"

                        # Emit stdout lines
                        if latest_step.get("stdout"):
                            yield f"event: stdout\ndata: {json.dumps({'session_id': session_id, 'output': latest_step['stdout']})}\n\n"

                    # Emit file_ready events
                    generated_files = output.get("generated_files", [])
                    for f in generated_files:
                        yield f"event: file_ready\ndata: {json.dumps({'session_id': session_id, **f})}\n\n"

            # 1c) Chain end for reflection — emit repair events
            elif kind == "on_chain_end" and event.get("name") == "reflection":
                output = event["data"].get("output")
                if isinstance(output, dict):
                    current_repairs = output.get("repair_attempts", 0)
                    if current_repairs > _prev_repair_attempts:
                        yield f"event: repair_attempt\ndata: {json.dumps({'session_id': session_id, 'attempt': current_repairs, 'error_summary': (output.get('last_stderr', '') or '')[:200]})}\n\n"
                        _prev_repair_attempts = current_repairs
                    elif current_repairs == 0 and _prev_repair_attempts > 0:
                        yield f"event: repair_success\ndata: {json.dumps({'session_id': session_id, 'attempt': _prev_repair_attempts})}\n\n"
                        _prev_repair_attempts = 0

            # 2) Custom events from tools
            # NOTE: we do NOT forward on_chat_model_stream here — the rag_token
            # custom event already carries every LLM delta from inside the RAG
            # tool, so forwarding both would double every token in the client.
            elif kind == "on_custom_event":
                if event["name"] == "code_stdout":
                    line = event["data"].get("line", "")
                    yield f"event: code_stdout\ndata: {json.dumps({'session_id': session_id, 'line': line})}\n\n"
                elif event["name"] == "rag_token":
                    content = event["data"].get("content", "")
                    token_data = json.dumps({"session_id": session_id, "content": content})
                    yield f"event: token\ndata: {token_data}\n\n"
                    _streamed_tokens = True
                elif event["name"] == "code_generating":
                    # The LLM is generating code — tell the frontend
                    yield f"event: code_generating\ndata: {json.dumps({'session_id': session_id, 'status': 'generating'})}\n\n"
                elif event["name"] == "code_generated":
                    # Code has been generated, about to execute
                    code = event["data"].get("code", "")
                    yield f"event: code_written\ndata: {json.dumps({'session_id': session_id, 'code': code})}\n\n"

            # 4) Metadata from response_generator node — also emit response as tokens
            elif kind == "on_chain_end" and event.get("name") == "response_generator":
                output = event["data"].get("output")
                if isinstance(output, dict) and "agent_metadata" in output:
                    response_text = output.get("response", "")
                    metadata = output["agent_metadata"]
                    metadata["session_id"] = session_id
                    metadata["response"] = response_text

                    # Emit the final response as token events in chunks so
                    # the frontend streams it progressively.
                    # Skip cases where content was already streamed:
                    #   1. rag_token events — content sent live during RAG execution
                    #   2. Structured JSON responses (DATA_ANALYSIS base64 payloads) —
                    #      these can be several hundred KB; emitting them as 80-char
                    #      chunks causes hundreds of re-renders of partial JSON in the
                    #      UI.  The meta event already carries `response`, and the
                    #      frontend done-handler reads agentMeta.response as fallback.
                    _is_json_payload = response_text.strip().startswith('{') and response_text.strip().endswith('}')
                    if response_text and not _streamed_tokens and not _is_json_payload:
                        CHUNK_SIZE = 80
                        for i in range(0, len(response_text), CHUNK_SIZE):
                            chunk = response_text[i:i + CHUNK_SIZE]
                            token_data = json.dumps({"session_id": session_id, "content": chunk})
                            yield f"event: token\ndata: {token_data}\n\n"

                    yield f"event: meta\ndata: {json.dumps(metadata)}\n\n"

        elapsed = time.time() - start_time
        yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'elapsed': round(elapsed, 2)})}\n\n"
        _emitted_done = True

    except Exception as e:
        logger.error("Agent stream failed: %s", e)
        yield f"event: error\ndata: {json.dumps({'session_id': session_id, 'error': str(e)})}\n\n"
    finally:
        # Guarantee the stream always terminates with a done event
        if not _emitted_done:
            elapsed = time.time() - start_time
            yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'elapsed': round(elapsed, 2)})}\n\n"
