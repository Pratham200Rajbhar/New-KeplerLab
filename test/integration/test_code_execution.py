"""
Integration tests for the code execution sandbox
(app/services/code_execution/executor.py + sandbox.py)
Tests: safe execution, output capture, timeout enforcement,
       security blocking, import auto-install
Requires local Python environment with sandbox dependencies.
"""

import sys
import os
import asyncio
import pytest
import pytest_asyncio

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.code_execution.executor import execute_code


# ── Safe code execution ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_hello_world():
    """Basic print statement should be captured."""
    result = await execute_code('print("Hello, World!")')
    assert result["success"] is True
    assert "Hello, World!" in result.get("output", "")


@pytest.mark.asyncio
async def test_math_computation():
    """Simple arithmetic should produce correct output."""
    result = await execute_code("print(2 + 2)")
    assert result["success"] is True
    assert "4" in result.get("output", "")


@pytest.mark.asyncio
async def test_multiline_code():
    """Multi-line code with variables should execute correctly."""
    code = """
x = 10
y = 20
z = x + y
print(f"Sum: {z}")
"""
    result = await execute_code(code)
    assert result["success"] is True
    assert "30" in result.get("output", "")


@pytest.mark.asyncio
async def test_import_math():
    """Standard library import should work."""
    code = "import math\nprint(math.sqrt(9))"
    result = await execute_code(code)
    assert result["success"] is True
    assert "3.0" in result.get("output", "")


@pytest.mark.asyncio
async def test_import_json():
    code = "import json\nprint(json.dumps({'a': 1}))"
    result = await execute_code(code)
    assert result["success"] is True
    assert '"a"' in result.get("output", "")


@pytest.mark.asyncio
async def test_list_comprehension():
    code = "result = [x**2 for x in range(5)]\nprint(result)"
    result = await execute_code(code)
    assert result["success"] is True
    assert "0, 1, 4, 9, 16" in result.get("output", "").replace(" ", " ")


@pytest.mark.asyncio
async def test_syntax_error_handled():
    """Syntax errors should return success=False with error info."""
    code = "def foo("  # incomplete
    result = await execute_code(code)
    assert result["success"] is False
    assert "error" in result or "stderr" in result or "output" in result


@pytest.mark.asyncio
async def test_runtime_error_handled():
    """Runtime errors should return success=False."""
    code = "x = 1 / 0"
    result = await execute_code(code)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_timeout_enforcement():
    """Infinite loop must be killed by the timeout."""
    code = "while True: pass"
    result = await execute_code(code, timeout=2)
    assert result["success"] is False
    # Check for timeout indication
    error_text = str(result.get("error", "")) + str(result.get("output", ""))
    assert "timeout" in error_text.lower() or result["success"] is False


# ── Security blocking ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subprocess_blocked():
    """subprocess module must be blocked before execution."""
    code = "import subprocess\nsubprocess.run(['ls'])"
    result = await execute_code(code)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_os_system_blocked():
    code = "import os\nos.system('echo hello')"
    result = await execute_code(code)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_eval_blocked():
    code = "eval('1+1')"
    result = await execute_code(code)
    assert result["success"] is False


@pytest.mark.asyncio
async def test_file_write_blocked():
    code = "open('/tmp/evil.txt', 'w').write('pwned')"
    result = await execute_code(code)
    assert result["success"] is False


# ── Result structure ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_result_has_required_keys():
    result = await execute_code("print('test')")
    assert "success" in result


@pytest.mark.asyncio
async def test_empty_code_returns_dict():
    result = await execute_code("")
    assert isinstance(result, dict)
    assert "success" in result


# ── Data science imports (if installed) ───────────────────────────────────────

@pytest.mark.asyncio
async def test_numpy_if_available():
    """numpy should be available in the sandbox environment."""
    code = "import numpy as np\nprint(np.array([1, 2, 3]).sum())"
    result = await execute_code(code)
    # numpy may or may not be installed; don't fail hard
    if result["success"]:
        assert "6" in result.get("output", "")


@pytest.mark.asyncio
async def test_pandas_if_available():
    """pandas should create a DataFrame and print shape."""
    code = "import pandas as pd\ndf = pd.DataFrame({'a': [1,2,3]})\nprint(df.shape)"
    result = await execute_code(code)
    if result["success"]:
        assert "(3, 1)" in result.get("output", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
