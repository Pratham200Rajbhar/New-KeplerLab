"""
Unit tests for backend/app/services/code_execution/security.py
Tests: forbidden pattern detection, allowed/blocked modules, code sanitization,
edge cases (empty code, obfuscation attempts, legitimate data-science code)
No sandbox execution — pure static analysis tests.
"""

import sys
import os
import pytest

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests-only-32chars!")

from app.services.code_execution.security import (
    validate_code,
    sanitize_code,
    ValidationResult,
)


# ── Valid / safe code ─────────────────────────────────────────────────────────

SAFE_SNIPPETS = [
    # Pure math
    "import math\nresult = math.sqrt(16)\nprint(result)",
    # Pandas / numpy (data science)
    "import pandas as pd\nimport numpy as np\ndf = pd.DataFrame({'a': [1,2,3]})\nprint(df.head())",
    # Matplotlib plot
    "import matplotlib.pyplot as plt\nplt.plot([1,2,3])\nplt.title('Test')",
    # Standard library (safe subset)
    "import json\ndata = json.dumps({'key': 'value'})\nprint(data)",
    # List comprehension, no imports
    "result = [x**2 for x in range(10)]\nprint(result)",
    # datetime
    "from datetime import datetime\nprint(datetime.now())",
    # collections
    "from collections import Counter\nc = Counter('hello')\nprint(c)",
    # csv
    "import csv\nimport io\nf = io.StringIO('a,b\\n1,2\\n')\nreader = csv.reader(f)\nprint(list(reader))",
    # seaborn import
    "import seaborn as sns\nprint(sns.__version__)",
]


class TestSafeCode:
    @pytest.mark.parametrize("code", SAFE_SNIPPETS)
    def test_safe_snippet_passes_validation(self, code):
        result = validate_code(code)
        assert result.is_safe is True, (
            f"Expected safe but got violations: {result.violations!r}\nCode: {code}"
        )


# ── Forbidden patterns ────────────────────────────────────────────────────────

DANGEROUS_SNIPPETS = [
    # subprocess
    ("import subprocess\nsubprocess.run(['ls'])", "subprocess"),
    # os.system
    ("import os\nos.system('ls')", "os.system"),
    # os.popen
    ("import os\nos.popen('cat /etc/passwd')", "os.popen"),
    # eval
    ("eval('__import__(\"os\").system(\"ls\")')", "eval"),
    # exec
    ("exec('import os')", "exec"),
    # __import__
    ("__import__('os').system('ls')", "__import__"),
    # open for write
    ("with open('evil.txt', 'w') as f:\n    f.write('pwned')", "write"),
    # socket
    ("import socket\ns = socket.socket()\ns.connect(('evil.com', 80))", "socket"),
    # requests
    ("import requests\nr = requests.get('http://evil.com')", "requests"),
    # urllib
    ("import urllib\nurllib.request.urlopen('http://evil.com')", "urllib"),
    # ctypes
    ("import ctypes\nctypes.CDLL('libc.so.6').system('ls')", "ctypes"),
    # shutil
    ("import shutil\nshutil.rmtree('/tmp/test')", "shutil"),
    # pickle
    ("import pickle\npickle.loads(b'')", "pickle"),
    # threading
    ("import threading\nt = threading.Thread(target=lambda: None)\nt.start()", "threading"),
    # os.environ
    ("import os\nprint(os.environ['PATH'])", "environ"),
    # os.remove
    ("import os\nos.remove('/etc/hosts')", "os.remove"),
    # globals()
    ("print(globals())", "globals"),
    # compile
    ("compile('print(1)', '<str>', 'exec')", "compile"),
]


class TestDangerousCode:
    @pytest.mark.parametrize("code,description", DANGEROUS_SNIPPETS)
    def test_dangerous_snippet_rejected(self, code, description):
        result = validate_code(code)
        assert result.is_safe is False, (
            f"Expected UNSAFE for '{description}' but validation passed.\n"
            f"Code: {code!r}"
        )
        assert len(result.violations) > 0, (
            f"Expected at least one violation for '{description}'"
        )


# ── Edge cases ────────────────────────────────────────────────────────────────

class TestValidateEdgeCases:

    def test_empty_code_rejected(self):
        """Empty code is rejected by security policy (nothing to execute)."""
        result = validate_code("")
        assert result.is_safe is False

    def test_whitespace_only_rejected(self):
        """Whitespace-only code is also rejected."""
        result = validate_code("   \n\t  ")
        assert result.is_safe is False

    def test_comment_only_code_is_safe(self):
        """Pure comment code has no dangerous patterns — should be safe."""
        result = validate_code("# This is a comment\n# Nothing dangerous here")
        assert result.is_safe is True

    def test_returns_validation_result(self):
        result = validate_code("x = 1")
        assert isinstance(result, ValidationResult)

    def test_validation_result_has_is_safe_field(self):
        result = validate_code("x = 1")
        assert hasattr(result, "is_safe")

    def test_validation_result_has_violations_list(self):
        result = validate_code("x = 1")
        assert hasattr(result, "violations")
        assert isinstance(result.violations, list)


# ── sanitize_code ─────────────────────────────────────────────────────────────

class TestSanitizeCode:

    def test_returns_string(self):
        result = sanitize_code("x = 1\nprint(x)")
        assert isinstance(result, str)

    def test_empty_code_returns_string(self):
        result = sanitize_code("")
        assert isinstance(result, str)

    def test_strips_leading_trailing_whitespace(self):
        result = sanitize_code("  \nx = 1\n  ")
        assert not result.startswith("  ")

    def test_preserves_code_logic(self):
        code = "import pandas as pd\ndf = pd.DataFrame({'a': [1]})\nprint(df)"
        result = sanitize_code(code)
        assert "pd" in result or "pandas" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
