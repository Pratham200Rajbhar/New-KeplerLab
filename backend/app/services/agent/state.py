"""Agent state schema for LangGraph.

Defines the TypedDict that flows through every node in the agent graph.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ToolResult(TypedDict, total=False):
    """Result from a single tool execution.

    Required contract — every tool MUST set these three fields:
        success  : bool  – whether the tool call succeeded
        output   : str   – human-readable response string (may be empty on failure)
        metadata : Dict  – structured data for downstream consumers (may be {})

    Optional fields:
        tool_name     : str  – name of the tool (set by each handler)
        error         : str  – error message on failure
        tokens_used   : int  – rough token consumption estimate
        output_summary: str  – truncated version for LLM context (set by compress_tool_result)
    """
    tool_name: str
    success: bool
    output: str        # canonical plain-text response — always set
    metadata: Dict     # structured payload (quiz questions, chart b64, etc.)
    error: Optional[str]
    tokens_used: int
    output_summary: str  # truncated — used in LLM planning context


_SUMMARY_MAX_CHARS = 500


def compress_tool_result(result: ToolResult) -> ToolResult:
    """Add a truncated ``output_summary`` to keep state lean.

    The full ``output`` is preserved for the response_generator; only
    ``output_summary`` should be passed into subsequent LLM calls (planner,
    reflection) to save tokens.
    """
    full = result.get("output", "")
    summary = (full[:_SUMMARY_MAX_CHARS] + "…") if len(full) > _SUMMARY_MAX_CHARS else full
    return {**result, "output_summary": summary}


class AgentState(TypedDict, total=False):
    """Full state flowing through the LangGraph agent pipeline.

    Every node reads/writes fields from this dict.
    """
    # ── Input ─────────────────────────────────────────────
    user_message: str
    notebook_id: str
    user_id: str
    material_ids: List[str]
    session_id: str

    # ── Intent Detection ──────────────────────────────────
    intent: str                    # QUESTION, DATA_ANALYSIS, RESEARCH, CODE_EXECUTION, CONTENT_GENERATION
    intent_confidence: float       # 0.0 – 1.0
    # requires_planning is intentionally removed — planner always runs

    # ── Planning ──────────────────────────────────────────
    plan: List[Dict[str, Any]]     # Ordered list of planned tool calls
    current_step: int              # Index into plan

    # ── Tool Execution ────────────────────────────────────
    selected_tool: str             # Tool to execute next
    tool_input: Dict[str, Any]     # Input for the tool
    tool_results: List[ToolResult] # Accumulated results from tool executions

    # ── Reflection & Safety ───────────────────────────────
    needs_retry: bool              # Whether the reflector decided to retry
    iterations: int                # Current iteration count
    step_retries: int              # Retry count for the *current* plan step
    total_tokens: int              # Running token budget counter
    total_tool_calls: int          # Running tool call counter

    # ── Response ──────────────────────────────────────────
    response: str                  # Final response to user
    agent_metadata: Dict[str, Any] # Metadata for frontend (intent, tools, steps, tokens)

    # ── Context ───────────────────────────────────────────
    rag_context: str               # Retrieved context from RAG
    chat_history: str              # Formatted previous conversation

    # ── Workspace & Generated Files ───────────────────────
    workspace_files: List[Dict]    # [{id, filename, real_path, text_path, ext, type}]
    generated_files: List[Dict]    # [{filename, path, download_url, size, type}]

    # ── Code Execution Context ────────────────────────────
    last_stdout: str               # stdout from last code execution
    last_stderr: str               # stderr from last code execution
    analysis_context: Dict         # dataset shape, columns, dtypes after profiling
    code_vars: Dict[str, str]      # variable name → type from last execution

    # ── Edit & Step Tracking ──────────────────────────────
    edit_history: List[Dict]       # log of append/replace/delete ops
    step_log: List[Dict]           # each step: {tool, label, status, time_taken, code, stdout, stderr}
    repair_attempts: int           # current repair loop counter, default 0


# ── Safety Limits ─────────────────────────────────────────
MAX_AGENT_ITERATIONS = 7
MAX_TOOL_CALLS = 10
TOKEN_BUDGET = 12_000
INTENT_MIN_CONFIDENCE = 0.6
