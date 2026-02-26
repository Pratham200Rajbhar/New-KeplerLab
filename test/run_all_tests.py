#!/usr/bin/env python3
"""
run_all_tests.py — Master test runner for KeplerLab-AI-Notebook.

Usage:
    python test/run_all_tests.py              # run all tests
    python test/run_all_tests.py --unit       # run only unit tests
    python test/run_all_tests.py --integration
    python test/run_all_tests.py --api
    python test/run_all_tests.py --e2e
    python test/run_all_tests.py --fast       # skip slow e2e tests

Output:
    ✅ PASS  test/unit/test_auth_security.py
    ❌ FAIL  test/unit/test_token_counter.py

    ============================================================
    SUMMARY: 23 passed, 1 failed, 0 skipped
    ============================================================

Reports are saved to: output/test_report_<timestamp>.txt
Per-test logs are saved to: output/logs/<test_name>.log
"""

import argparse
import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent

# ── Resolve Python interpreter ─────────────────────────────────────────────────
# Prefer the project's virtualenv, then the interpreter running this script.
_VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"
PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable
OUTPUT_DIR = PROJECT_ROOT / "output"
LOGS_DIR = OUTPUT_DIR / "logs"

# Ensure output directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

# ── Test discovery ─────────────────────────────────────────────────────────────
SUITES = {
    "unit": HERE / "unit",
    "integration": HERE / "integration",
    "api": HERE / "api",
    "e2e": HERE / "e2e",
}


def discover_tests(suites: list[str]) -> list[Path]:
    """Return sorted list of test file paths for the requested suites."""
    files: list[Path] = []
    for suite in suites:
        suite_dir = SUITES.get(suite)
        if suite_dir and suite_dir.exists():
            found = sorted(suite_dir.glob("test_*.py"))
            files.extend(found)
    return files


# ── Runner ────────────────────────────────────────────────────────────────────

def run_test_file(test_path: Path, verbose: bool = False) -> tuple[bool, str, float]:
    """Run a single pytest test file.

    Returns: (passed: bool, output: str, elapsed_seconds: float)
    """
    # Resolve relative path for display
    try:
        display_path = str(test_path.relative_to(PROJECT_ROOT))
    except ValueError:
        display_path = str(test_path)

    cmd = [
        PYTHON, "-m", "pytest",
        str(test_path),
        "-v" if verbose else "-q",
        "--tb=short",
        "--no-header",
        "--timeout=60",          # per-test timeout requires pytest-timeout
        "--asyncio-mode=auto",   # requires pytest-asyncio
    ]

    # Set minimal environment variables so Pydantic Settings validates
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
    env.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        elapsed = time.perf_counter() - start
        combined = result.stdout + result.stderr
        passed = result.returncode == 0
    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start
        combined = "ERROR: test file timed out after 120 seconds\n"
        passed = False

    # Save per-file log
    log_name = display_path.replace("/", "__").replace("\\", "__") + ".log"
    log_path = LOGS_DIR / log_name
    log_path.write_text(combined, encoding="utf-8")

    return passed, combined, elapsed


# ── Report formatting ─────────────────────────────────────────────────────────

def format_badge(passed: bool) -> str:
    if passed:
        return f"{GREEN}{BOLD}✅ PASS{RESET}"
    return f"{RED}{BOLD}❌ FAIL{RESET}"


def format_line(passed: bool, display: str, elapsed: float) -> str:
    badge = format_badge(passed)
    return f"  {badge}  {display:<60}  ({elapsed:.1f}s)"


def build_report(results: list[dict], elapsed_total: float) -> str:
    """Build a full plain-text report (no ANSI codes)."""
    lines = [
        "=" * 70,
        "KeplerLab-AI-Notebook — Test Report",
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
        "",
    ]

    for r in results:
        status = "PASS" if r["passed"] else "FAIL"
        lines.append(f"  [{status}]  {r['display']:<60}  ({r['elapsed']:.1f}s)")
        if not r["passed"]:
            # Include a condensed failure excerpt
            excerpt = "\n".join(r["output"].splitlines()[-30:])
            lines.append("")
            lines.append("    --- Failure output (last 30 lines) ---")
            for line in excerpt.splitlines():
                lines.append("    " + line)
            lines.append("")

    n_pass = sum(1 for r in results if r["passed"])
    n_fail = len(results) - n_pass

    lines += [
        "",
        "=" * 70,
        f"SUMMARY: {n_pass} passed, {n_fail} failed  |  total time: {elapsed_total:.1f}s",
        "=" * 70,
    ]
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the KeplerLab-AI-Notebook test suite"
    )
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")
    parser.add_argument("--api", action="store_true", help="Run API tests only")
    parser.add_argument("--e2e", action="store_true", help="Run E2E tests only")
    parser.add_argument("--fast", action="store_true", help="Skip slow E2E tests (run unit+integration+api)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Pass -v to pytest")
    args = parser.parse_args()

    # Determine which suites to run
    if args.fast:
        active_suites = ["unit", "integration", "api"]
    elif args.unit:
        active_suites = ["unit"]
    elif args.integration:
        active_suites = ["integration"]
    elif args.api:
        active_suites = ["api"]
    elif args.e2e:
        active_suites = ["e2e"]
    else:
        active_suites = ["unit", "integration", "api", "e2e"]

    test_files = discover_tests(active_suites)

    if not test_files:
        print(f"{YELLOW}No test files found for suites: {active_suites}{RESET}")
        return 0

    # Header
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{BOLD}{CYAN}{'=' * 62}{RESET}")
    print(f"{BOLD}{CYAN}  KeplerLab-AI-Notebook Test Suite  —  {timestamp}{RESET}")
    print(f"{BOLD}{CYAN}  Suites: {', '.join(active_suites)}{RESET}")
    print(f"{BOLD}{CYAN}  Files:  {len(test_files)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 62}{RESET}\n")

    # Run each test file
    results: list[dict] = []
    total_start = time.perf_counter()

    for test_path in test_files:
        try:
            display = str(test_path.relative_to(PROJECT_ROOT))
        except ValueError:
            display = str(test_path)

        passed, output, elapsed = run_test_file(test_path, verbose=args.verbose)
        results.append({
            "passed": passed,
            "display": display,
            "output": output,
            "elapsed": elapsed,
        })
        print(format_line(passed, display, elapsed))

        # Print failure details immediately for quick feedback
        if not passed:
            # Show last 20 lines of output to highlight the error
            excerpt_lines = output.splitlines()[-20:]
            print(f"\n    {YELLOW}--- Failure excerpt ---{RESET}")
            for line in excerpt_lines:
                print(f"    {line}")
            print()

    total_elapsed = time.perf_counter() - total_start

    # Summary
    n_pass = sum(1 for r in results if r["passed"])
    n_fail = len(results) - n_pass

    print(f"\n{BOLD}{'=' * 62}{RESET}")
    if n_fail == 0:
        print(f"{GREEN}{BOLD}  ALL TESTS PASSED  ✅  {n_pass}/{len(results)}{RESET}"
              f"  |  {total_elapsed:.1f}s")
    else:
        print(f"{RED}{BOLD}  {n_fail} FAILED / {n_pass} PASSED{RESET}"
              f"  |  {total_elapsed:.1f}s")
    print(f"{BOLD}{'=' * 62}{RESET}\n")

    # Save report
    report_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = OUTPUT_DIR / f"test_report_{report_ts}.txt"
    report_content = build_report(results, total_elapsed)
    report_file.write_text(report_content, encoding="utf-8")

    print(f"  Report saved: {report_file}")
    print(f"  Logs saved:   {LOGS_DIR}/\n")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
