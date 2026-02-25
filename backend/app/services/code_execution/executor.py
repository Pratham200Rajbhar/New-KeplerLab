"""Executor — orchestrates code validation, execution, and result formatting.

Ties together security validation → code sanitization → sandbox execution → result parsing.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Awaitable, Callable, Dict, List, Optional

from app.services.code_execution.security import validate_code, sanitize_code
from app.services.code_execution.sandbox import run_in_sandbox, ExecutionResult

logger = logging.getLogger(__name__)


async def execute_code(
    code: str,
    work_dir: Optional[str] = None,
    timeout: int = 15,
    on_stdout_line: Optional[Callable[[str], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """Execute Python code safely.

    Pipeline:
    1. Validate code against security rules
    2. Sanitize code (strip whitespace, inject chart capture)
    3. Run in subprocess sandbox
    4. Parse and format results

    Args:
        code: Python source to execute.
        work_dir: Optional working directory path.
        timeout: Execution timeout in seconds.
        on_stdout_line: Optional callback invoked with each output line.

    Returns:
        Dict with keys: success, stdout, stderr, exit_code, chart_base64,
        elapsed, error, violations, warnings, job_id
    """
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"[{job_id}] Executing code ({len(code)} chars)")

    # Step 1: Validate
    validation = validate_code(code)

    if not validation.is_safe:
        logger.warning(f"[{job_id}] Code validation failed: {validation.violations}")
        return {
            "success": False,
            "stdout": "",
            "stderr": "Code validation failed",
            "exit_code": -1,
            "chart_base64": None,
            "elapsed": 0.0,
            "error": "Security violation",
            "violations": validation.violations,
            "warnings": validation.warnings,
            "job_id": job_id,
        }

    # Step 2: Sanitize
    sanitized = sanitize_code(code)

    # Step 3 is skipped since on_stdout_line is passed directly
    # Step 4: Execute in sandbox
    result: ExecutionResult = await run_in_sandbox(
        code=sanitized,
        work_dir=work_dir,
        timeout=timeout,
        on_stdout_line=on_stdout_line,
    )

    # Step 5: Format result
    success = result.exit_code == 0 and not result.timed_out and result.error is None

    logger.info(
        f"[{job_id}] Execution complete: "
        f"exit={result.exit_code}, "
        f"timeout={result.timed_out}, "
        f"elapsed={result.elapsed_seconds}s, "
        f"chart={'yes' if result.chart_base64 else 'no'}"
    )

    return {
        "success": success,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "chart_base64": result.chart_base64,
        "elapsed": result.elapsed_seconds,
        "error": result.error,
        "violations": [],
        "warnings": validation.warnings,
        "job_id": job_id,
        "timed_out": result.timed_out,
    }


async def generate_and_execute(
    user_query: str,
    csv_files: Optional[List[Dict[str, Any]]] = None,
    parquet_files: Optional[List[Dict[str, str]]] = None,
    timeout: int = 15,
    on_stdout_line: Optional[Callable[[str], Awaitable[None]]] = None,
    additional_context: str = "",
) -> Dict[str, Any]:
    """Generate Python code from a natural language query, then execute it.

    This is the high-level entry point for data analysis requests.

    Args:
        user_query: Natural language description of the analysis
        csv_files: List of dicts with 'filename' and 'content' for CSV context
        parquet_files: List of dicts with 'name' and 'path' for pre-built parquet files
        timeout: Execution timeout
        on_stdout_line: Optional callback for live stdout streaming.
    """
    from app.services.llm_service.llm import get_llm
    import tempfile
    import os
    import shutil

    # ── Build data context for the LLM prompt ──────────────────
    data_context = ""

    # Parquet files (preferred — fast pd.read_parquet)
    if parquet_files:
        data_context += "Available Parquet files in your working directory (use pd.read_parquet):\n"
        for pf in parquet_files:
            # Read a small preview
            try:
                import pandas as pd
                df_preview = pd.read_parquet(pf["path"]).head(5)
                cols = list(df_preview.columns)
                dtypes = {str(c): str(df_preview[c].dtype) for c in cols}
                data_context += (
                    f"- {pf['name']}\n"
                    f"  Columns: {cols}\n"
                    f"  Dtypes: {dtypes}\n"
                    f"  Sample rows:\n{df_preview.to_string(index=False, max_cols=10)}\n\n"
                )
            except Exception:
                data_context += f"- {pf['name']} (schema preview unavailable)\n\n"

    # Legacy CSV text context
    if csv_files:
        data_context += "Available CSV files in your working directory:\n"
        for f in csv_files:
            preview = f.get('content', '')[:500] + ('...' if len(f.get('content', '')) > 500 else '')
            data_context += f"- {f['filename']}\n  First few characters:\n  {preview}\n\n"

    # Append RAG context from previous tool if available (tool chaining)
    if additional_context:
        data_context += f"\nAdditional context from document search:\n{additional_context[:2000]}\n"

    # Generate code via LLM
    prompt = f"""You are a Python data analysis expert. Generate ONLY executable Python code.

User request: {user_query}

{data_context}

Rules:
- Use pandas for data manipulation
- Use matplotlib.pyplot for charts (call plt.show() at the end)
- Print results clearly with print()
- Do NOT use interactive features
- Do NOT access the filesystem except reading the provided data files
- Keep code concise and correct
- If creating a chart, always call plt.show() so the chart is captured
- For parquet files use pd.read_parquet("filename.parquet")
- For CSV files use pd.read_csv("filename.csv")

Respond with ONLY the Python code, no markdown, no explanations:"""

    try:
        llm = get_llm(mode="code")
        response = await llm.ainvoke(prompt)
        generated_code = getattr(response, "content", str(response)).strip()

        # Clean markdown code blocks if present
        if generated_code.startswith("```"):
            lines = generated_code.split("\n")
            # Remove first and last lines (```python and ```)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            generated_code = "\n".join(lines)

        logger.info(f"Generated {len(generated_code)} chars of code")

        # Create temporary working directory and mount data files
        work_dir = None
        if csv_files or parquet_files:
            work_dir = tempfile.mkdtemp(prefix="kepler_analysis_")
            # Mount CSV files (write content)
            if csv_files:
                for f in csv_files:
                    file_path = os.path.join(work_dir, f["filename"])
                    with open(file_path, "w", encoding="utf-8") as out_f:
                        out_f.write(f["content"])
                logger.info(f"Mounted {len(csv_files)} CSV file(s) into {work_dir}")
            # Mount parquet files (copy from source)
            if parquet_files:
                for pf in parquet_files:
                    dst = os.path.join(work_dir, pf["name"])
                    try:
                        shutil.copy2(pf["path"], dst)
                    except Exception as exc:
                        logger.warning("Failed to copy parquet %s: %s", pf["path"], exc)
                logger.info(f"Mounted {len(parquet_files)} parquet file(s) into {work_dir}")

        # Execute the generated code
        # Note: run_in_sandbox creates a temp dir if work_dir=None, but we provide it if csv_files are present.
        result = await execute_code(generated_code, work_dir=work_dir, timeout=timeout, on_stdout_line=on_stdout_line)
        result["generated_code"] = generated_code

        # Cleanup work dir
        if work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

        return result

    except Exception as e:
        logger.error(f"Code generation failed: {e}")
        return {
            "success": False,
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "chart_base64": None,
            "elapsed": 0.0,
            "error": f"Code generation failed: {str(e)}",
            "violations": [],
            "warnings": [],
            "job_id": str(uuid.uuid4())[:8],
            "generated_code": "",
        }
