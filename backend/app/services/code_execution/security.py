"""Security — code validation and forbidden pattern detection.

Validates user-submitted Python code against a set of dangerous patterns
before allowing execution in the sandbox.
"""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger(__name__)


# ── Forbidden Patterns ────────────────────────────────────────

# Regex patterns that should never appear in user code
_FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    # System access — dangerous os operations (os.path is safe and allowed)
    (r'\bos\s*\.\s*(system|popen|exec[lv]?[pe]?|spawn|kill|remove|unlink|rmdir|makedirs|rename)', "OS system calls are forbidden"),
    (r'\bos\s*\.\s*(environ|getenv|putenv|unsetenv)', "Accessing environment variables is forbidden"),
    (r'\bos\s*\.\s*(chdir|fchdir|chroot)', "Changing directories is forbidden"),
    (r'\bos\s*\.\s*(listdir|scandir|walk)', "Directory listing is forbidden"),
    (r'\bos\s*\.\s*(chmod|chown|lchown|chflags)', "Changing file permissions is forbidden"),
    (r'\bos\s*\.\s*(link|symlink|readlink)', "Creating links is forbidden"),
    (r'\bos\s*\.\s*(fork|wait|waitpid|_exit)', "Process control is forbidden"),
    (r'\bsubprocess\b', "subprocess module is forbidden"),
    (r'\bshutil\b', "shutil module is forbidden"),
    (r'\bsys\s*\.\s*(exit|_exit)', "sys.exit is forbidden"),

    # Code injection
    (r'\b__import__\b', "__import__ is forbidden"),
    (r'\bexec\s*\(', "exec() is forbidden"),
    (r'\beval\s*\(', "eval() is forbidden"),
    (r'\bcompile\s*\(', "compile() is forbidden"),
    (r'\bgetattr\s*\(.*,\s*[\'"]__', "Accessing dunder attributes via getattr is forbidden"),
    (r'\bglobals\s*\(\)', "globals() is forbidden"),
    (r'\blocals\s*\(\)', "locals() is forbidden"),
    (r'\bdelattr\s*\(', "delattr() is forbidden"),
    (r'\bsetattr\s*\(.*,\s*[\'"]__', "Setting dunder attributes via setattr is forbidden"),
    (r'\b__builtins__\b', "Accessing __builtins__ is forbidden"),
    (r'\b__subclasses__\b', "Accessing __subclasses__ is forbidden"),
    (r'\b__bases__\b', "Accessing __bases__ is forbidden"),
    (r'\b__class__\s*\.\s*__mro__', "Accessing __mro__ is forbidden"),
    (r'\bbreakpoint\s*\(', "breakpoint() is forbidden"),

    # File system write
    (r'open\s*\([^)]*[\'"][wa]\+?[\'"]', "Writing files is forbidden"),
    (r'\bpathlib\b.*\.(write_text|write_bytes|mkdir|unlink|rmdir)', "File system writes via pathlib are forbidden"),
    (r'\bPath\s*\(.*\)\s*\.\s*(write_text|write_bytes|mkdir|unlink|rmdir)', "File system writes via Path are forbidden"),

    # Network access
    (r'\bsocket\b', "socket module is forbidden"),
    (r'\brequests\b', "requests module is forbidden"),
    (r'\burllib\b', "urllib module is forbidden"),
    (r'\bhttpx\b', "httpx module is forbidden"),
    (r'\baiohttp\b', "aiohttp module is forbidden"),

    # Dangerous modules
    (r'\bctypes\b', "ctypes module is forbidden"),
    (r'\bmultiprocessing\b', "multiprocessing module is forbidden"),
    (r'\bthreading\b', "threading module is forbidden"),
    (r'\bsignal\b', "signal module is forbidden"),
    (r'\bpickle\b', "pickle module is forbidden (security risk)"),
]

# Modules allowed for import
_ALLOWED_MODULES = {
    # Data science
    "pandas", "numpy", "scipy", "sklearn", "statistics",
    # Visualization
    "matplotlib", "matplotlib.pyplot", "seaborn", "plotly",
    # Standard lib (safe subset)
    "math", "random", "datetime", "collections", "itertools",
    "functools", "operator", "string", "re", "json", "csv",
    "decimal", "fractions", "textwrap", "typing",
    # IO (read-only)
    "io", "StringIO", "BytesIO",
    # os — allowed for os.path operations; dangerous os.* calls
    # are caught by regex patterns in _FORBIDDEN_PATTERNS above
    "os", "os.path",
}

# Modules explicitly blocked
_BLOCKED_MODULES = {
    "sys", "subprocess", "shutil", "socket", "requests",
    "urllib", "http", "ftplib", "smtplib", "telnetlib",
    "ctypes", "multiprocessing", "threading", "signal",
    "pickle", "shelve", "dbm", "sqlite3", "importlib",
    "code", "codeop", "compileall", "py_compile",
    "webbrowser", "antigravity",
    # Note: 'os' is NOT blocked — os.path is commonly needed.
    # Dangerous os.* calls are caught by _FORBIDDEN_PATTERNS regex.
}


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_safe: bool
    violations: List[str]
    warnings: List[str]


def validate_code(code: str) -> ValidationResult:
    """Validate Python code for safety.

    Checks:
    1. Regex pattern matching for dangerous calls
    2. AST analysis for forbidden imports
    3. Code complexity limits

    Returns ValidationResult with is_safe flag and violation messages.
    """
    violations: List[str] = []
    warnings: List[str] = []

    if not code or not code.strip():
        return ValidationResult(is_safe=False, violations=["Empty code"], warnings=[])

    # ── Length Check ───────────────────────────────────
    if len(code) > 50_000:
        violations.append("Code exceeds maximum length of 50,000 characters")
        return ValidationResult(is_safe=False, violations=violations, warnings=warnings)

    # ── Regex Pattern Check ───────────────────────────
    for pattern, message in _FORBIDDEN_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            violations.append(message)

    # ── AST Analysis ──────────────────────────────────
    try:
        tree = ast.parse(code)
        _check_ast(tree, violations, warnings)
    except SyntaxError as e:
        violations.append(f"Syntax error: {e}")

    is_safe = len(violations) == 0

    if not is_safe:
        logger.warning(f"Code validation failed: {violations}")
    elif warnings:
        logger.info(f"Code validation passed with warnings: {warnings}")

    return ValidationResult(is_safe=is_safe, violations=violations, warnings=warnings)


def _check_ast(tree: ast.AST, violations: List[str], warnings: List[str]):
    """Walk the AST to check for forbidden patterns."""
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in _BLOCKED_MODULES:
                    violations.append(f"Importing '{alias.name}' is forbidden")

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module in _BLOCKED_MODULES:
                    violations.append(f"Importing from '{node.module}' is forbidden")

        # Check for builtins-based __import__ calls: builtins.__import__, __builtins__.__import__
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == '__import__':
                violations.append("Dynamic __import__ via attribute access is forbidden")
            elif isinstance(func, ast.Name) and func.id in ('exec', 'eval', 'compile', '__import__', 'breakpoint'):
                violations.append(f"Calling {func.id}() is forbidden")

        # Check for infinite loops (basic heuristic)
        elif isinstance(node, ast.While):
            if isinstance(node.test, ast.Constant) and node.test.value is True:
                warnings.append("Detected `while True` loop — may timeout")

        # Check for overly deep nesting
        elif isinstance(node, (ast.For, ast.While)):
            depth = _get_nesting_depth(node)
            if depth > 5:
                warnings.append(f"Deep nesting detected ({depth} levels) — may be slow")


def _get_nesting_depth(node: ast.AST, current: int = 0) -> int:
    """Calculate the nesting depth of loops/conditionals."""
    max_depth = current
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.For, ast.While, ast.If)):
            max_depth = max(max_depth, _get_nesting_depth(child, current + 1))
    return max_depth


def sanitize_code(code: str) -> str:
    """Light sanitization of code before execution.

    - Strips trailing whitespace
    - Ensures proper line endings
    - Adds chart capture boilerplate if matplotlib is used
    """
    code = code.strip()
    code = code.replace("\r\n", "\n")

    # Auto-inject matplotlib save-to-buffer if plt is used but no savefig
    if "matplotlib" in code or "plt." in code:
        if "savefig" not in code and "plt.show()" in code:
            code = code.replace(
                "plt.show()",
                'import io, base64\n'
                'buf = io.BytesIO()\n'
                'plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")\n'
                'buf.seek(0)\n'
                'print("__CHART_BASE64__" + base64.b64encode(buf.read()).decode() + "__END_CHART__")\n'
                'plt.close()'
            )

    return code
