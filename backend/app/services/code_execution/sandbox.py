"""Sandbox — subprocess-based Python execution with resource limits.

Runs validated Python code in an isolated subprocess with:
- CPU time limits
- Memory limits (via ulimit on Linux)
- Timeout enforcement
- Output capture
- Optional live stdout streaming via an async callback

Note: Code is executed using the same Python interpreter as the server
(sys.executable) so all venv-installed packages (pandas, numpy, matplotlib,
scikit-learn, etc.) are available.  Security is handled upstream by the
code validator in security.py before this function is ever called.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────

MAX_EXECUTION_TIME = 15    # seconds
MAX_OUTPUT_SIZE = 1_000_000  # 1MB max output


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
    - Captures charts as base64 via plt.show() monkey-patch
    - Runs the user code
    """
    wrapper = f'''
import sys
import os
import base64
import io

# ── Matplotlib non-interactive backend ───────────
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as _plt_orig

    def _capture_show(*args, **kwargs):
        buf = io.BytesIO()
        _plt_orig.savefig(buf, format="png", bbox_inches="tight", dpi=72)
        buf.seek(0)
        b64 = base64.b64encode(buf.read()).decode("utf-8")
        print(f"__CHART_BASE64__{{b64}}__END_CHART__")
        _plt_orig.clf()
        _plt_orig.close("all")

    _plt_orig.show = _capture_show
    import matplotlib.pyplot as plt
    plt.show = _capture_show
except ImportError:
    pass

# ── Execute user code ────────────────────────────
{code}
'''
    return wrapper


def _preexec_limits():
    """Set process limits for the sandbox subprocess (Linux only).

    Applies:
    - RLIMIT_CPU: Hard limit on CPU time (prevents crypto-mining, infinite loops)
    - RLIMIT_FSIZE: Maximum file size the process can create
    - RLIMIT_NOFILE: Maximum open file descriptors

    Note: RLIMIT_AS (virtual address space) is intentionally NOT set —
    numpy, pandas and other scientific packages mmap many shared objects and
    easily exceed address-space limits.

    Note: RLIMIT_NPROC is intentionally NOT set — it limits threads too
    (on Linux, threads count towards NPROC), and libraries like OpenBLAS,
    NumPy, SciPy, and scikit-learn require worker threads internally.
    Fork-bomb protection is handled by the execution timeout instead.
    """
    try:
        import resource
        # CPU time: soft=30s, hard=60s
        resource.setrlimit(resource.RLIMIT_CPU, (30, 60))
        # Max file size: 50 MB
        resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
        # Max open files: 128 (numpy/pandas open many file descriptors)
        resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    except (ImportError, ValueError, OSError):
        pass  # Non-Linux or insufficient permissions — rely on timeout


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

    Returns:
        ExecutionResult with stdout, stderr, exit_code, charts
    """
    start_time = time.time()
    cleanup_work_dir = False

    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="kepler_sandbox_")
        cleanup_work_dir = True

    script_path = os.path.join(work_dir, "_run.py")
    wrapper_code = _create_wrapper_script(code, work_dir)

    try:
        with open(script_path, "w") as f:
            f.write(wrapper_code)

        cmd = [sys.executable, "_run.py"]

        # Build a sanitized environment — strip sensitive credentials
        _STRIP_ENV_KEYS = {
            "DATABASE_URL", "JWT_SECRET_KEY", "GOOGLE_API_KEY",
            "NVIDIA_API_KEY", "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        }
        sandbox_env = {
            k: v for k, v in os.environ.items()
            if k not in _STRIP_ENV_KEYS
        }
        # Control library thread counts — prevents OpenBLAS/MKL from
        # spawning excessive threads while still allowing them to work.
        sandbox_env["OPENBLAS_NUM_THREADS"] = "4"
        sandbox_env["MKL_NUM_THREADS"] = "4"
        sandbox_env["OMP_NUM_THREADS"] = "4"
        sandbox_env["NUMEXPR_MAX_THREADS"] = "4"

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env=sandbox_env,
            preexec_fn=_preexec_limits,
            limit=16 * 1024 * 1024,   # 16 MB — allows large __CHART_BASE64__ lines
        )

        if on_stdout_line is not None:
            # ── Streaming path: read stdout line-by-line ──────────────────
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
            # ── Buffered path: communicate() ──────────────────────────────
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                try:
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
        try:
            if os.path.exists(script_path):
                os.remove(script_path)
        except Exception:
            pass
        if cleanup_work_dir:
            try:
                import shutil
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass
