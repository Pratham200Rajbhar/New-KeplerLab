"""Workspace builder — constructs Python header code for AI-generated scripts.

Generates variable definitions for uploaded files and standard imports,
so the AI's generated code can reference workspace files by variable name.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List

from app.core.config import settings
from app.services.agent.state import AgentState


def _safe_varname(filename: str) -> str:
    """Convert a filename into a valid Python variable name."""
    name = os.path.splitext(filename)[0]
    # Replace non-alphanumeric chars with underscore
    name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    # Remove leading digits
    name = re.sub(r"^[0-9]+", "", name)
    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")
    return name.lower() or "file"


def build_workspace_header(state: AgentState) -> str:
    """Build a Python code header with imports and file path variables.

    Args:
        state: Agent state containing workspace_files, user_id, session_id.

    Returns:
        Multi-line Python string to prepend to generated code.
    """
    user_id = state.get("user_id", "default")
    session_id = state.get("session_id", "default")

    # Sanitize path components to prevent directory traversal
    safe_user_id = os.path.basename(user_id)
    safe_session_id = os.path.basename(session_id)

    # Use ABSOLUTE path so FILE_SAVED markers resolve correctly
    # and file writes go to the correct location regardless of cwd.
    output_dir = os.path.join(
        settings.GENERATED_OUTPUT_DIR, safe_user_id, safe_session_id
    )

    lines: List[str] = [
        "# ── Auto-generated workspace header ──",
        "import os",
        "import pandas as pd",
        "import numpy as np",
        "import matplotlib",
        "matplotlib.use('Agg')",
        "import matplotlib.pyplot as plt",
        "import json, csv",
        "",
        "# Output directory (absolute path — pre-created by runtime)",
        f'OUTPUT_DIR = "{output_dir}"',
        "",
    ]

    workspace_files: List[Dict] = state.get("workspace_files", [])

    if workspace_files:
        lines.append("# ── Uploaded file paths ──")
        seen_vars: Dict[str, int] = {}

        for f in workspace_files:
            filename = f.get("filename", "unknown")
            real_path = f.get("real_path", "")
            text_path = f.get("text_path", "")
            ext = f.get("ext", "").lower()

            base_var = _safe_varname(filename)
            # Handle duplicate variable names
            if base_var in seen_vars:
                seen_vars[base_var] += 1
                base_var = f"{base_var}_{seen_vars[base_var]}"
            else:
                seen_vars[base_var] = 0

            if ext in (".csv", ".xlsx", ".xls"):
                load_hint = "pd.read_csv()" if ext == ".csv" else "pd.read_excel()"
                lines.append(f'{base_var}_path = "{real_path}"  # load with {load_hint}')
            elif ext in (".pdf", ".docx", ".txt", ".md"):
                lines.append(f'{base_var}_text_path = "{text_path}"  # load with open().read()')
            else:
                # Generic file reference
                if real_path:
                    lines.append(f'{base_var}_path = "{real_path}"')
                if text_path:
                    lines.append(f'{base_var}_text_path = "{text_path}"')

        lines.append("")

    return "\n".join(lines)
