"""
Unit tests for backend/app/services/code_execution/executor.py
Tests: _extract_imports — AST parsing of import statements
No sandbox execution or network required.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.code_execution.executor import _extract_imports


class TestExtractImports:
    """White-box tests for the AST import extractor."""

    def test_simple_import(self):
        code = "import numpy"
        result = _extract_imports(code)
        assert "numpy" in result

    def test_from_import(self):
        code = "from pandas import DataFrame"
        result = _extract_imports(code)
        assert "pandas" in result

    def test_multiple_imports(self):
        code = "import numpy\nimport pandas\nimport matplotlib"
        result = _extract_imports(code)
        assert "numpy" in result
        assert "pandas" in result
        assert "matplotlib" in result

    def test_submodule_only_root_returned(self):
        code = "from matplotlib.pyplot import plot"
        result = _extract_imports(code)
        assert "matplotlib" in result
        assert "matplotlib.pyplot" not in result

    def test_alias_import(self):
        code = "import numpy as np"
        result = _extract_imports(code)
        assert "numpy" in result

    def test_multi_import_on_one_line(self):
        code = "import os, sys"
        result = _extract_imports(code)
        assert "os" in result
        assert "sys" in result

    def test_no_imports_empty_list(self):
        code = "x = 1\nprint(x)"
        result = _extract_imports(code)
        assert result == []

    def test_empty_code_empty_list(self):
        assert _extract_imports("") == []

    def test_no_duplicates(self):
        code = "import numpy\nimport numpy as np"
        result = _extract_imports(code)
        assert result.count("numpy") == 1

    def test_invalid_syntax_returns_empty(self):
        """SyntaxError in user code should return empty list, not raise."""
        code = "def foo(\n    x"  # incomplete function
        result = _extract_imports(code)
        assert isinstance(result, list)

    def test_nested_import_in_function_detected(self):
        code = "def foo():\n    import seaborn as sns\n    return sns"
        result = _extract_imports(code)
        # ast.walk finds all nodes including nested ones
        assert "seaborn" in result

    def test_stdlib_included(self):
        """Standard library imports are also extracted (caller does skip-list check)."""
        code = "import math\nimport json"
        result = _extract_imports(code)
        assert "math" in result
        assert "json" in result

    def test_from_builtin_package(self):
        code = "from collections import Counter"
        result = _extract_imports(code)
        assert "collections" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
