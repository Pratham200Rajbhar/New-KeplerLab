"""Sandbox environment — preinstalled packages and package management.

Ensures all required packages are available for AI-generated code execution.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import subprocess
import sys
import threading
from typing import Dict, List

logger = logging.getLogger(__name__)

# ── Stdlib modules — never pip-install these ──────────────────

SKIP_PACKAGES: set[str] = {
    "abc", "argparse", "ast", "asyncio", "base64", "bisect", "builtins",
    "calendar", "cmath", "codecs", "collections", "colorsys", "concurrent",
    "configparser", "contextlib", "copy", "csv", "ctypes", "dataclasses",
    "datetime", "decimal", "difflib", "dis", "email", "enum", "errno",
    "faulthandler", "fileinput", "fnmatch", "fractions", "ftplib",
    "functools", "gc", "getpass", "gettext", "glob", "gzip", "hashlib",
    "heapq", "hmac", "html", "http", "imaplib", "importlib", "inspect",
    "io", "ipaddress", "itertools", "json", "keyword", "linecache",
    "locale", "logging", "lzma", "math", "mimetypes", "multiprocessing",
    "numbers", "operator", "os", "pathlib", "pickle", "pkgutil",
    "platform", "pprint", "pdb", "posixpath", "queue", "quopri",
    "random", "re", "readline", "reprlib", "resource", "secrets",
    "select", "shelve", "shlex", "shutil", "signal", "site", "smtplib",
    "socket", "sqlite3", "ssl", "stat", "statistics", "string",
    "struct", "subprocess", "sys", "sysconfig", "syslog", "tarfile",
    "tempfile", "textwrap", "threading", "time", "timeit", "token",
    "tokenize", "trace", "traceback", "turtle", "types", "typing",
    "unicodedata", "unittest", "urllib", "uuid", "venv", "warnings",
    "wave", "weakref", "webbrowser", "xml", "xmlrpc", "zipfile",
    "zipimport", "zlib",
    # Internal / private
    "__future__", "_thread", "_io",
}

# ── On-demand package installer ───────────────────────────────

_installed_cache: set[str] = set()
_install_lock = threading.Lock()  # Thread-safe install operations


def install_package_if_missing(pkg: str) -> bool:
    """Try to import *pkg*; if missing, pip-install it (quietly).

    Returns True if the package is available after this call.
    Results are cached so each package is only checked/installed once
    per process lifetime.  Thread-safe via _install_lock.
    """
    if pkg in _installed_cache or pkg in SKIP_PACKAGES:
        return True

    import_name = _PIP_TO_MODULE.get(pkg, pkg)
    try:
        importlib.import_module(import_name)
        with _install_lock:
            _installed_cache.add(pkg)
        return True
    except ImportError:
        pass

    with _install_lock:
        # Double-check after acquiring lock (another thread may have installed it)
        if pkg in _installed_cache:
            return True

        logger.info("[sandbox_env] Auto-installing missing package: %s", pkg)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "-q", "--no-input"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0:
                _installed_cache.add(pkg)
                logger.info("[sandbox_env] Installed %s", pkg)
                return True
            else:
                logger.warning("[sandbox_env] pip install %s failed: %s", pkg, result.stderr.strip())
                return False
        except Exception as exc:
            logger.warning("[sandbox_env] Error installing %s: %s", pkg, exc)
            return False


async def install_package_if_missing_async(pkg: str) -> bool:
    """Async wrapper for install_package_if_missing — runs in thread pool.

    Use this from async contexts to avoid blocking the event loop.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, install_package_if_missing, pkg)


# ── Preinstalled Packages ─────────────────────────────────────

PREINSTALLED_PACKAGES: List[str] = [
    "pandas",
    "numpy",
    "matplotlib",
    "seaborn",
    "plotly",
    "kaleido",
    "openpyxl",
    "xlrd",
    "python-docx",
    "fpdf2",
    "reportlab",
    "scipy",
    "scikit-learn",
    "networkx",
    "pillow",
    "tabulate",
    "jinja2",
]

# ── Package → import statement mapping ────────────────────────

PACKAGE_IMPORT_MAP: Dict[str, str] = {
    "pandas": "import pandas as pd",
    "numpy": "import numpy as np",
    "matplotlib": "import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt",
    "seaborn": "import seaborn as sns",
    "plotly": "import plotly.express as px\nimport plotly.graph_objects as go",
    "kaleido": "import kaleido",
    "openpyxl": "import openpyxl",
    "xlrd": "import xlrd",
    "python-docx": "from docx import Document",
    "fpdf2": "from fpdf import FPDF",
    "reportlab": "from reportlab.lib.pagesizes import letter\nfrom reportlab.pdfgen import canvas",
    "scipy": "import scipy",
    "scikit-learn": "from sklearn import *",
    "networkx": "import networkx as nx",
    "pillow": "from PIL import Image",
    "tabulate": "from tabulate import tabulate",
    "jinja2": "from jinja2 import Template",
}

# Map pip package name → importable module name (for packages where they differ)
_PIP_TO_MODULE: Dict[str, str] = {
    "python-docx": "docx",
    "fpdf2": "fpdf",
    "scikit-learn": "sklearn",
    "pillow": "PIL",
}


def _get_import_name(package: str) -> str:
    """Get the importable module name for a pip package."""
    return _PIP_TO_MODULE.get(package, package)


async def ensure_packages() -> None:
    """Install any missing preinstalled packages.

    Runs pip install in quiet mode for each missing package.
    Safe to call multiple times — skips already-installed packages.
    """
    loop = asyncio.get_running_loop()
    missing: List[str] = []

    for pkg in PREINSTALLED_PACKAGES:
        import_name = _get_import_name(pkg)
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing.append(pkg)

    if not missing:
        logger.info("[sandbox_env] All %d packages already installed", len(PREINSTALLED_PACKAGES))
        return

    logger.info("[sandbox_env] Installing %d missing packages: %s", len(missing), missing)

    for pkg in missing:
        try:
            result = await loop.run_in_executor(
                None,
                lambda p=pkg: subprocess.run(
                    [sys.executable, "-m", "pip", "install", p, "-q"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                ),
            )
            if result.returncode == 0:
                logger.info("[sandbox_env] Installed %s", pkg)
            else:
                logger.warning(
                    "[sandbox_env] Failed to install %s: %s",
                    pkg,
                    result.stderr.strip(),
                )
        except Exception as exc:
            logger.warning("[sandbox_env] Error installing %s: %s", pkg, exc)

    logger.info("[sandbox_env] Package installation complete")
