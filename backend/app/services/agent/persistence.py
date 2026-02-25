"""Agent persistence — DB write operations for agent-layer route handlers.

Centralises all Prisma writes that originate from agent-related endpoints
so that route files remain DB-free.

Functions:
    log_code_execution  — record a code sandbox run (CodeExecutionSession)
"""

from __future__ import annotations

import logging

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


async def log_code_execution(
    user_id: str,
    notebook_id: str,
    code: str,
    stdout: str,
    stderr: str,
    exit_code: int,
    has_chart: bool,
    elapsed: float,
) -> None:
    """Write a CodeExecutionSession row.  Best-effort — never raises."""
    try:
        await prisma.codeexecutionsession.create(
            data={
                "userId": user_id,
                "notebookId": notebook_id,
                "code": code[:5000],
                "stdout": stdout[:10000],
                "stderr": stderr[:5000],
                "exitCode": exit_code,
                "hasChart": has_chart,
                "elapsedTime": elapsed,
            }
        )
    except Exception as exc:
        logger.error("log_code_execution failed: %s", exc)
