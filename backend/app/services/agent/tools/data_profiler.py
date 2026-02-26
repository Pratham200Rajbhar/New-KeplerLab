"""Data profiler — automatically profiles CSV/XLSX/TSV datasets.

Loads the first data file from workspace_files, runs pandas profiling,
and stores the results in analysis_context for LLM use.

Safety: limits rows loaded to prevent OOM on large files.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.services.agent.state import AgentState

logger = logging.getLogger(__name__)

_MAX_PROFILE_ROWS = 50_000  # Safety cap for large files


def _find_data_file(workspace_files: List[Dict]) -> Optional[Dict]:
    """Find the first CSV, TSV, or XLSX file in workspace_files."""
    for f in workspace_files:
        ext = f.get("ext", "").lower()
        if ext in (".csv", ".tsv", ".xlsx", ".xls"):
            return f
    return None


def _profile_sync(file_path: str, ext: str) -> Dict[str, Any]:
    """Synchronous pandas profiling (runs in thread pool).
    
    Caps rows at _MAX_PROFILE_ROWS to prevent OOM on large files.
    """
    import pandas as pd

    if ext == ".csv":
        df = pd.read_csv(file_path, nrows=_MAX_PROFILE_ROWS)
    elif ext == ".tsv":
        df = pd.read_csv(file_path, sep="\t", nrows=_MAX_PROFILE_ROWS)
    else:
        df = pd.read_excel(file_path, nrows=_MAX_PROFILE_ROWS)
    
    truncated = len(df) >= _MAX_PROFILE_ROWS

    profile = {
        "shape": list(df.shape),
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "describe": df.describe(include="all").to_dict(),
        "null_counts": df.isnull().sum().to_dict(),
        "sample_rows": df.head(3).to_dict(orient="records"),
    }
    if truncated:
        profile["truncated"] = True
        profile["max_rows_loaded"] = _MAX_PROFILE_ROWS
    
    return profile


async def profile_dataset(state: AgentState) -> AgentState:
    """Profile the first CSV/XLSX file in workspace_files.

    Stores profiling results in state["analysis_context"].

    Args:
        state: Agent state with workspace_files populated.

    Returns:
        Updated state with analysis_context filled.
    """
    workspace_files = state.get("workspace_files", [])
    data_file = _find_data_file(workspace_files)

    if data_file is None:
        logger.warning("[data_profiler] No CSV/XLSX file found in workspace_files")
        return {
            **state,
            "analysis_context": {
                "error": "No data file found in uploaded materials",
            },
        }

    file_path = data_file.get("real_path", "")
    ext = data_file.get("ext", ".csv").lower()
    filename = data_file.get("filename", "unknown")

    logger.info("[data_profiler] Profiling %s (%s)", filename, file_path)

    try:
        profile = await asyncio.to_thread(_profile_sync, file_path, ext)
        profile["filename"] = filename
        profile["file_path"] = file_path

        logger.info(
            "[data_profiler] Profile complete: %d rows × %d cols",
            profile["shape"][0],
            profile["shape"][1],
        )

        return {
            **state,
            "analysis_context": profile,
        }

    except Exception as exc:
        logger.error("[data_profiler] Profiling failed: %s", exc)
        return {
            **state,
            "analysis_context": {
                "error": f"Failed to profile {filename}: {str(exc)}",
                "filename": filename,
            },
        }
