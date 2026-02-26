"""File generator — executes AI-generated code to produce files.

Orchestrates workspace header injection, code execution in sandbox,
and detection of FILE_SAVED: markers to track generated files.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.services.agent.state import AgentState, ToolResult
from app.services.agent.tools.workspace_builder import build_workspace_header
from app.core.config import settings

logger = logging.getLogger(__name__)


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def _detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    ext = os.path.splitext(filename)[1].lower()
    type_map = {
        ".csv": "spreadsheet",
        ".xlsx": "spreadsheet",
        ".xls": "spreadsheet",
        ".docx": "document",
        ".doc": "document",
        ".pdf": "document",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".svg": "image",
        ".html": "web",
        ".json": "data",
        ".txt": "text",
    }
    return type_map.get(ext, "file")


async def generate_file(
    state: AgentState,
    code: str,
    stream_cb: Optional[Callable[[str, Any], Coroutine]] = None,
) -> ToolResult:
    """Execute AI-generated code to produce files.

    Args:
        state: Agent state with workspace_files and user/session info.
        code: AI-generated Python code to execute.
        stream_cb: Optional async callback(event_name, data) for SSE streaming.

    Returns:
        ToolResult with generated file info.
    """
    from app.services.code_execution.executor import execute_code

    # Build workspace header and prepend to code
    header = build_workspace_header(state)
    full_code = header + "\n" + code

    user_id = state.get("user_id", "default")
    session_id = state.get("session_id", "default")
    
    # Sanitize path components to prevent traversal attacks
    safe_user_id = os.path.basename(user_id)
    safe_session_id = os.path.basename(session_id)
    output_dir = os.path.join(settings.GENERATED_OUTPUT_DIR, safe_user_id, safe_session_id)
    os.makedirs(output_dir, exist_ok=True)

    logger.info("[file_generator] Executing code (%d chars) for file generation", len(full_code))

    # Track stdout lines for FILE_SAVED detection
    stdout_lines: List[str] = []
    generated_files: List[Dict[str, Any]] = list(state.get("generated_files", []))

    async def on_stdout_line(line: str):
        stdout_lines.append(line)

    # Execute in sandbox
    result = await execute_code(
        code=full_code,
        work_dir=output_dir,
        timeout=settings.CODE_EXECUTION_TIMEOUT,
        on_stdout_line=on_stdout_line,
    )

    # Parse FILE_SAVED: markers from stdout
    full_stdout = result.get("stdout", "")
    new_files: List[Dict[str, Any]] = []

    for line in full_stdout.split("\n"):
        line = line.strip()
        if line.startswith("FILE_SAVED:"):
            file_path = line[len("FILE_SAVED:"):].strip()
            if os.path.exists(file_path):
                filename = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_type = _detect_file_type(filename)
                download_url = f"/agent/download/{user_id}/{session_id}/{filename}"

                file_info = {
                    "filename": filename,
                    "path": file_path,
                    "download_url": download_url,
                    "size": file_size,
                    "size_human": _format_size(file_size),
                    "type": file_type,
                }
                new_files.append(file_info)
                generated_files.append(file_info)

                # Notify via stream callback
                if stream_cb:
                    try:
                        await stream_cb("file_ready", file_info)
                    except Exception as exc:
                        logger.warning("[file_generator] stream_cb failed: %s", exc)

                logger.info(
                    "[file_generator] File saved: %s (%s)",
                    filename,
                    _format_size(file_size),
                )

    success = result.get("success", False)
    stderr = result.get("stderr", "")

    if success and new_files:
        file_list = ", ".join(f["filename"] for f in new_files)
        output_msg = f"Generated {len(new_files)} file(s): {file_list}"
    elif success:
        output_msg = "Code executed successfully but no FILE_SAVED markers found."
    else:
        output_msg = f"Code execution failed: {stderr[:500]}"

    return ToolResult(
        tool_name="file_generator",
        success=success,
        output=output_msg,
        metadata={
            "generated_files": new_files,
            "stdout": full_stdout,
            "stderr": stderr,
            "exit_code": result.get("exit_code", -1),
            "code": code,
        },
        error=stderr if not success else None,
        tokens_used=0,
    )
