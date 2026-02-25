"""Sandbox — subprocess-based Python execution with resource limits.

Runs validated Python code in an isolated subprocess with:
- CPU time limits
- Memory limits (via ulimit)
- No network access
- Timeout enforcement
- Output capture
- Optional live stdout streaming via an async callback
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────

MAX_EXECUTION_TIME = 15    # seconds
MAX_OUTPUT_SIZE = 1_000_000  # 1MB max output
MAX_MEMORY_MB = 512         # 512MB RAM limit


@dataclass
class ExecutionResult:
    """Result from sandbox execution."""
    stdout: str = ""
    stderr: str = ""
    exit_code: int = -1
    timed_out: bool = False
    chart_base64: Optional[str] = None
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


def _create_wrapper_script(code: str, work_dir: str) -> str:
    """Create a wrapper script that sets up the execution environment.

    The wrapper:
    - Redirects matplotlib backend to Agg (non-interactive)
    - Runs the user code
    """
    wrapper = f'''
import sys
import os

# ── Matplotlib non-interactive backend ───────────
try:
    import matplotlib
    matplotlib.use("Agg")
except ImportError:
    pass

# ── Execute user code ────────────────────────────
{code}
'''
    return wrapper


async def run_in_sandbox(
    code: str,
    work_dir: Optional[str] = None,
    timeout: int = MAX_EXECUTION_TIME,
    on_stdout_line: Optional[Callable[[str], Awaitable[None]]] = None,
) -> ExecutionResult:
    """Execute Python code in a sandboxed subprocess.

    Args:
        code: Validated Python code to execute
        work_dir: Working directory (temp dir if not specified)
        timeout: Maximum execution time in seconds
        on_stdout_line: Optional async callback invoked with each decoded stdout
            line as it arrives.  Enables live streaming to WebSocket clients.
            When *not* provided the classic ``communicate()`` buffered path is used.

    Returns:
        ExecutionResult with stdout, stderr, exit_code, charts
    """
    start_time = time.time()

    # Create temp directory for execution if not provided
    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="kepler_sandbox_")

    # Write the wrapper script
    script_path = os.path.join(work_dir, "_run.py")
    wrapper_code = _create_wrapper_script(code, work_dir)
    container_name = f"kepler_sandbox_{uuid.uuid4().hex[:8]}"

    try:
        with open(script_path, "w") as f:
            f.write(wrapper_code)

        docker_cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--cpus=1.0",
            "-m", f"{MAX_MEMORY_MB}m",
            "--network", "none",
            "-v", f"{work_dir}:{work_dir}",
            "-w", work_dir,
            "python:3.11-slim",
            "python", "_run.py"
        ]

        # Run in subprocess
        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if on_stdout_line is not None:
                # ── Streaming path: read stdout line-by-line ──────────────────
                # Concurrently drain stdout (line-by-line + callback) and stderr
                # (buffered).  Both tasks must finish or be cancelled together.
                stdout_lines: list[str] = []
                stderr_buffer: list[bytes] = []

                async def _stream_stdout() -> None:
                    assert process.stdout is not None
                    async for raw_line in process.stdout:
                        line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                        stdout_lines.append(line)
                        try:
                            await on_stdout_line(line)
                        except Exception as cb_exc:
                            logger.debug("on_stdout_line callback error: %s", cb_exc)

                async def _collect_stderr() -> None:
                    assert process.stderr is not None
                    data = await process.stderr.read(MAX_OUTPUT_SIZE)
                    stderr_buffer.append(data)

                try:
                    await asyncio.wait_for(
                        asyncio.gather(_stream_stdout(), _collect_stderr()),
                        timeout=timeout,
                    )
                    await process.wait()
                except asyncio.TimeoutError:
                    try:
                        kill_proc = await asyncio.create_subprocess_exec(
                            "docker", "rm", "-f", container_name,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
                    elapsed = time.time() - start_time
                    return ExecutionResult(
                        stdout="\n".join(stdout_lines),
                        stderr=f"Execution timed out after {timeout}s",
                        exit_code=-1,
                        timed_out=True,
                        elapsed_seconds=round(elapsed, 2),
                        error=f"Timed out after {timeout}s",
                    )

                elapsed = time.time() - start_time
                stdout = "\n".join(stdout_lines)[:MAX_OUTPUT_SIZE]
                stderr = (stderr_buffer[0] if stderr_buffer else b"").decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]

        else:
                # ── Buffered path: original communicate() ─────────────────────
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout,
                    )
                except asyncio.TimeoutError:
                    try:
                        kill_proc = await asyncio.create_subprocess_exec(
                            "docker", "rm", "-f", container_name,
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL
                        )
                        await kill_proc.wait()
                        process.kill()
                        await process.wait()
                    except Exception:
                        pass
                    elapsed = time.time() - start_time
                    return ExecutionResult(
                        stdout="",
                        stderr=f"Execution timed out after {timeout}s",
                        exit_code=-1,
                        timed_out=True,
                        elapsed_seconds=round(elapsed, 2),
                        error=f"Timed out after {timeout}s",
                    )

                elapsed = time.time() - start_time
                stdout = stdout_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]
                stderr = stderr_bytes.decode("utf-8", errors="replace")[:MAX_OUTPUT_SIZE]

        # Extract chart if present
        chart_base64 = None
        if "__CHART_BASE64__" in stdout:
            import re
            match = re.search(r"__CHART_BASE64__(.+?)__END_CHART__", stdout, re.DOTALL)
            if match:
                chart_base64 = match.group(1).strip()
                # Remove the chart marker from stdout
                stdout = re.sub(r"__CHART_BASE64__.+?__END_CHART__", "", stdout, flags=re.DOTALL).strip()

        return ExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=process.returncode or 0,
            timed_out=False,
            chart_base64=chart_base64,
            elapsed_seconds=round(elapsed, 2),
        )

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error("Sandbox execution failed: %s", e)
        return ExecutionResult(
            stdout="",
            stderr=str(e),
            exit_code=-1,
            elapsed_seconds=round(elapsed, 2),
            error=str(e),
        )

    finally:
        # Always destroy the container — handles crashes, timeouts, and normal exits.
        # The --rm flag covers the normal-exit case, but explicit rm -f is the safety net.
        try:
            kill_proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(kill_proc.wait(), timeout=5.0)
        except Exception:
            pass  # Container already gone or Docker unavailable

        # Clean up script file
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass
