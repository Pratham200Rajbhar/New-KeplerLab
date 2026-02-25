#!/usr/bin/env python3
"""
Comprehensive Feature Test Suite for KeplerLab AI Notebook
==========================================================

Tests EVERY backend API endpoint end-to-end using the "4. IaaS.pdf" as source material.
Also analyses backend logs and output artifacts for errors/anomalies.

Usage:
    python test/test_all_features.py                          # default (localhost:8000)
    python test/test_all_features.py --base-url http://host:port
    python test/test_all_features.py --email user@example.com --password pass123
    python test/test_all_features.py --skip-slow              # skip podcast/presentation (slow LLM calls)
    python test/test_all_features.py --log-file backend/logs/app.log  # custom log path

Outputs a colour-coded terminal report + JSON report at test/test_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import traceback
import uuid
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

# ── Configuration ─────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PDF_PATH = PROJECT_ROOT / "4. IaaS.pdf"
DEFAULT_LOG_PATH = PROJECT_ROOT / "backend" / "logs" / "app.log"
REPORT_PATH = PROJECT_ROOT / "test" / "test_report.json"

# Test user credentials (will signup if not exists, then login)
DEFAULT_EMAIL = f"tester_{uuid.uuid4().hex[:6]}@test.com"
DEFAULT_PASSWORD = "TestPass123!"
DEFAULT_USERNAME = "test_runner"


# ── ANSI colours ──────────────────────────────────────────────────────────

class C:
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"


# ── Data models ───────────────────────────────────────────────────────────

@dataclass
class TestResult:
    name: str
    category: str
    passed: bool
    duration_ms: float
    status_code: Optional[int] = None
    detail: str = ""
    response_snippet: str = ""


@dataclass
class LogAnalysis:
    total_lines: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    endpoints_hit: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    slow_requests: list = field(default_factory=list)
    error_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    status_codes: dict = field(default_factory=dict)


@dataclass
class OutputAnalysis:
    podcast_files: list = field(default_factory=list)
    presentation_files: list = field(default_factory=list)
    upload_files: list = field(default_factory=list)
    material_texts: list = field(default_factory=list)
    issues: list = field(default_factory=list)


# ── Test Runner ───────────────────────────────────────────────────────────

class FeatureTester:
    """Runs all feature tests against the backend API."""

    def __init__(self, base_url: str, pdf_path: str, email: str, password: str,
                 username: str, skip_slow: bool = False):
        self.base = base_url.rstrip("/")
        self.pdf_path = pdf_path
        self.email = email
        self.password = password
        self.username = username
        self.skip_slow = skip_slow
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.results: list[TestResult] = []

        # IDs created during tests (for cleanup)
        self.notebook_id: Optional[str] = None
        self.material_id: Optional[str] = None
        self.job_id: Optional[str] = None
        self.content_ids: list[str] = []
        self.session_id: Optional[str] = None

    # ── Helpers ────────────────────────────────────────────

    def _auth_headers(self) -> dict:
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _run(self, name: str, category: str, method: str, path: str,
             expected_status: int | tuple = 200, json_body: dict = None,
             data: dict = None, files: dict = None, params: dict = None,
             stream: bool = False, auth: bool = True,
             validate_fn=None) -> TestResult:
        """Execute a single API test."""
        headers = self._auth_headers() if auth else {}
        if json_body is not None and "Content-Type" not in headers:
            headers["Content-Type"] = "application/json"

        url = self._url(path)
        t0 = time.time()

        try:
            resp = self.session.request(
                method, url,
                json=json_body if json_body is not None else None,
                data=data,
                files=files,
                params=params,
                headers=headers,
                stream=stream,
                timeout=180,  # generous for LLM endpoints
            )
            duration = (time.time() - t0) * 1000

            if isinstance(expected_status, tuple):
                ok = resp.status_code in expected_status
            else:
                ok = resp.status_code == expected_status

            detail = ""
            snippet = ""

            if ok:
                # Try to get JSON
                try:
                    body = resp.json() if not stream else None
                    snippet = json.dumps(body, indent=2)[:500] if body else ""
                    if validate_fn and body:
                        validation_err = validate_fn(body)
                        if validation_err:
                            ok = False
                            detail = f"Validation failed: {validation_err}"
                except Exception:
                    snippet = resp.text[:500]
            else:
                try:
                    body = resp.json()
                    detail = body.get("detail", str(body))[:300]
                except Exception:
                    detail = resp.text[:300]

            result = TestResult(
                name=name, category=category, passed=ok,
                duration_ms=round(duration, 1),
                status_code=resp.status_code,
                detail=detail, response_snippet=snippet,
            )

        except requests.ConnectionError:
            duration = (time.time() - t0) * 1000
            result = TestResult(
                name=name, category=category, passed=False,
                duration_ms=round(duration, 1),
                detail="Connection refused. Is the backend running?",
            )
        except requests.Timeout:
            duration = (time.time() - t0) * 1000
            result = TestResult(
                name=name, category=category, passed=False,
                duration_ms=round(duration, 1),
                detail="Request timed out (180s)",
            )
        except Exception as e:
            duration = (time.time() - t0) * 1000
            result = TestResult(
                name=name, category=category, passed=False,
                duration_ms=round(duration, 1),
                detail=f"{type(e).__name__}: {e}",
            )

        self.results.append(result)
        self._print_result(result)
        return result

    def _print_result(self, r: TestResult):
        status = f"{C.GREEN}PASS{C.RESET}" if r.passed else f"{C.RED}FAIL{C.RESET}"
        code = f" [{r.status_code}]" if r.status_code else ""
        dur = f"{C.DIM}{r.duration_ms:.0f}ms{C.RESET}"
        print(f"  {status} {r.name}{code} {dur}")
        if not r.passed and r.detail:
            print(f"       {C.RED}→ {r.detail}{C.RESET}")

    def _wait_material_ready(self, material_id: str, timeout: int = 120) -> bool:
        """Poll until material status is 'completed' or 'failed'."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self.session.get(
                    self._url("/materials"),
                    headers=self._auth_headers(),
                    params={"notebook_id": self.notebook_id},
                    timeout=10,
                )
                if resp.ok:
                    mats = resp.json()
                    for m in mats:
                        if m["id"] == material_id:
                            if m["status"] == "completed":
                                return True
                            if m["status"] == "failed":
                                print(f"       {C.RED}→ Material processing FAILED{C.RESET}")
                                return False
            except Exception:
                pass
            time.sleep(2)
        print(f"       {C.YELLOW}→ Material processing timed out ({timeout}s){C.RESET}")
        return False

    # ── Test categories ────────────────────────────────────

    def test_health(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 1. HEALTH CHECKS ═══{C.RESET}")

        self._run("GET /health/simple", "Health", "GET", "/health/simple",
                   auth=False,
                   validate_fn=lambda b: None if b.get("status") == "ok" else "Missing status=ok")

        self._run("GET /health (full)", "Health", "GET", "/health",
                   expected_status=(200, 503), auth=False,
                   validate_fn=lambda b: None if "overall" in b else "Missing 'overall' key")

    def test_models_status(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 2. MODEL STATUS ═══{C.RESET}")

        self._run("GET /models/status", "Models", "GET", "/models/status",
                   auth=False,
                   validate_fn=lambda b: None if "models" in b else "Missing 'models' key")

    def test_supported_formats(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 3. SUPPORTED FORMATS ═══{C.RESET}")

        self._run("GET /upload/supported-formats", "Upload", "GET", "/upload/supported-formats",
                   auth=False,
                   validate_fn=lambda b: None if "file_extensions" in b else "Missing file_extensions")

    def test_auth(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 4. AUTHENTICATION ═══{C.RESET}")

        # Signup
        r = self._run("POST /auth/signup", "Auth", "POST", "/auth/signup",
                       json_body={"email": self.email, "password": self.password, "username": self.username},
                       auth=False,
                       validate_fn=lambda b: None if b.get("id") else "Missing user id")

        # Login
        r = self._run("POST /auth/login", "Auth", "POST", "/auth/login",
                       json_body={"email": self.email, "password": self.password},
                       auth=False,
                       validate_fn=lambda b: None if b.get("access_token") else "Missing access_token")
        if r.passed:
            body = self.session.post(self._url("/auth/login"),
                                     json={"email": self.email, "password": self.password}).json()
            self.token = body["access_token"]

        # Me
        r = self._run("GET /auth/me", "Auth", "GET", "/auth/me",
                       validate_fn=lambda b: None if b.get("email") == self.email else f"Email mismatch")
        if r.passed:
            body = self.session.get(self._url("/auth/me"), headers=self._auth_headers()).json()
            self.user_id = body.get("id")

        # Refresh
        self._run("POST /auth/refresh", "Auth", "POST", "/auth/refresh",
                   auth=False,
                   validate_fn=lambda b: None if b.get("access_token") else "Missing access_token")

    def test_notebooks(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 5. NOTEBOOKS ═══{C.RESET}")

        # Create
        r = self._run("POST /notebooks (create)", "Notebooks", "POST", "/notebooks",
                       expected_status=201,
                       json_body={"name": "IaaS Test Notebook", "description": "Testing with IaaS PDF"},
                       validate_fn=lambda b: None if b.get("id") else "Missing notebook id")
        if r.passed:
            body = self.session.post(self._url("/notebooks"),
                                     json={"name": "IaaS Test Notebook 2"},
                                     headers=self._auth_headers()).json()
            self.notebook_id = body.get("id")
            # Delete the extra one
            if r.response_snippet:
                try:
                    first_id = json.loads(r.response_snippet).get("id")
                    if first_id and first_id != self.notebook_id:
                        self.session.delete(self._url(f"/notebooks/{first_id}"),
                                            headers=self._auth_headers())
                except Exception:
                    pass

        # List
        self._run("GET /notebooks (list)", "Notebooks", "GET", "/notebooks",
                   validate_fn=lambda b: None if isinstance(b, list) else "Expected array")

        # Get single
        if self.notebook_id:
            self._run("GET /notebooks/:id", "Notebooks", "GET", f"/notebooks/{self.notebook_id}",
                       validate_fn=lambda b: None if b.get("id") == self.notebook_id else "ID mismatch")

        # Update
        if self.notebook_id:
            self._run("PUT /notebooks/:id (rename)", "Notebooks", "PUT", f"/notebooks/{self.notebook_id}",
                       json_body={"name": "IaaS Test (Renamed)", "description": "Updated description"},
                       validate_fn=lambda b: None if "Renamed" in b.get("name", "") else "Name not updated")

    def test_upload_file(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 6. FILE UPLOAD & MATERIALS ═══{C.RESET}")

        if not os.path.exists(self.pdf_path):
            self.results.append(TestResult("PDF file exists", "Upload", False, 0,
                                           detail=f"File not found: {self.pdf_path}"))
            print(f"  {C.RED}FAIL{C.RESET} PDF not found at {self.pdf_path}")
            return

        # Upload PDF
        with open(self.pdf_path, "rb") as f:
            r = self._run("POST /upload (IaaS.pdf)", "Upload", "POST", "/upload",
                           expected_status=202,
                           files={"file": ("4. IaaS.pdf", f, "application/pdf")},
                           data={"notebook_id": self.notebook_id} if self.notebook_id else {},
                           validate_fn=lambda b: None if b.get("material_id") else "Missing material_id")

        if r.passed and r.response_snippet:
            try:
                body = json.loads(r.response_snippet)
                self.material_id = body.get("material_id")
                self.job_id = body.get("job_id")
            except Exception:
                pass

        # Wait for processing
        if self.material_id:
            print(f"  {C.DIM}⏳ Waiting for material processing...{C.RESET}")
            ready = self._wait_material_ready(self.material_id)
            self.results.append(TestResult(
                "Material processing completes", "Upload",
                passed=ready, duration_ms=0,
                detail="" if ready else "Processing did not complete in time",
            ))
            self._print_result(self.results[-1])

        # List materials
        if self.notebook_id:
            self._run("GET /materials (list)", "Materials", "GET", "/materials",
                       params={"notebook_id": self.notebook_id},
                       validate_fn=lambda b: None if isinstance(b, list) and len(b) > 0 else "No materials found")

        # Get material text
        if self.material_id:
            self._run("GET /materials/:id/text", "Materials", "GET", f"/materials/{self.material_id}/text",
                       validate_fn=lambda b: None if b.get("text") and len(b["text"]) > 50 else "Text too short or empty")

        # Update material
        if self.material_id:
            self._run("PATCH /materials/:id (rename)", "Materials", "PATCH", f"/materials/{self.material_id}",
                       json_body={"title": "IaaS Cloud Computing Guide"})

    def test_upload_text(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 7. TEXT UPLOAD ═══{C.RESET}")

        sample_text = (
            "Infrastructure as a Service (IaaS) is a cloud computing model that provides "
            "virtualized computing resources over the internet. Key components include "
            "virtual machines, storage, and networking. Major providers are AWS, Azure, and GCP."
        )

        r = self._run("POST /upload/text", "Upload", "POST", "/upload/text",
                       expected_status=202,
                       json_body={
                           "text": sample_text,
                           "title": "IaaS Summary Text",
                           "notebook_id": self.notebook_id,
                       },
                       validate_fn=lambda b: None if b.get("material_id") else "Missing material_id")

        if r.passed and r.response_snippet:
            try:
                body = json.loads(r.response_snippet)
                text_mat_id = body.get("material_id")
                if text_mat_id:
                    print(f"  {C.DIM}⏳ Waiting for text material processing...{C.RESET}")
                    self._wait_material_ready(text_mat_id)
            except Exception:
                pass

    def test_chat(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 8. CHAT ═══{C.RESET}")

        if not self.material_id or not self.notebook_id:
            print(f"  {C.YELLOW}SKIP — no material/notebook available{C.RESET}")
            return

        # Create chat session
        r = self._run("POST /chat/sessions (create)", "Chat", "POST", "/chat/sessions",
                       json_body={"notebook_id": self.notebook_id, "title": "IaaS Test Chat"},
                       validate_fn=lambda b: None if b.get("session_id") else "Missing session_id")
        if r.passed and r.response_snippet:
            try:
                self.session_id = json.loads(r.response_snippet).get("session_id")
            except Exception:
                pass

        # List sessions
        self._run("GET /chat/sessions/:notebook_id", "Chat", "GET",
                   f"/chat/sessions/{self.notebook_id}",
                   validate_fn=lambda b: None if "sessions" in b else "Missing 'sessions'")

        # Non-streaming chat
        self._run("POST /chat (non-streaming)", "Chat", "POST", "/chat",
                   json_body={
                       "material_id": self.material_id,
                       "message": "What are the main components of IaaS?",
                       "notebook_id": self.notebook_id,
                       "session_id": self.session_id,
                       "stream": False,
                   },
                   validate_fn=lambda b: None if b.get("answer") and len(b["answer"]) > 20 else "Answer too short")

        # Streaming chat (SSE)
        print(f"  {C.DIM}Testing SSE streaming chat...{C.RESET}")
        t0 = time.time()
        try:
            resp = self.session.post(
                self._url("/chat"),
                json={
                    "material_id": self.material_id,
                    "message": "Explain virtual machine provisioning in IaaS",
                    "notebook_id": self.notebook_id,
                    "session_id": self.session_id,
                    "stream": True,
                },
                headers={**self._auth_headers(), "Content-Type": "application/json"},
                stream=True,
                timeout=120,
            )
            tokens_received = 0
            got_done = False
            buffer = ""
            current_event = ""
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        if current_event == "token":
                            tokens_received += 1
                        elif current_event == "done":
                            got_done = True
                        current_event = ""
                    elif line == "":
                        current_event = ""
                if got_done:
                    break
            duration = (time.time() - t0) * 1000
            passed = tokens_received > 5 and got_done
            result = TestResult(
                "POST /chat (SSE streaming)", "Chat", passed, round(duration, 1),
                status_code=resp.status_code,
                detail=f"Received {tokens_received} tokens, done={got_done}" if not passed else "",
                response_snippet=f"tokens={tokens_received}",
            )
        except Exception as e:
            duration = (time.time() - t0) * 1000
            result = TestResult("POST /chat (SSE streaming)", "Chat", False, round(duration, 1),
                                detail=str(e))
        self.results.append(result)
        self._print_result(result)

        # Chat suggestions
        self._run("POST /chat/suggestions", "Chat", "POST", "/chat/suggestions",
                   json_body={"partial_input": "What is cloud", "notebook_id": self.notebook_id},
                   validate_fn=lambda b: None if "suggestions" in b else "Missing suggestions")

        # Chat history
        self._run("GET /chat/history/:notebook_id", "Chat", "GET",
                   f"/chat/history/{self.notebook_id}",
                   params={"session_id": self.session_id} if self.session_id else {},
                   validate_fn=lambda b: None if isinstance(b, list) else "Expected list")

    def test_flashcards(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 9. FLASHCARD GENERATION ═══{C.RESET}")

        if not self.material_id:
            print(f"  {C.YELLOW}SKIP — no material available{C.RESET}")
            return

        r = self._run("POST /flashcard", "Flashcards", "POST", "/flashcard",
                       json_body={
                           "material_id": self.material_id,
                           "topic": "IaaS fundamentals",
                           "card_count": 5,
                           "difficulty": "Medium",
                       },
                       validate_fn=lambda b: None if b.get("flashcards") and len(b["flashcards"]) > 0 else "No flashcards generated")

        # Save to notebook
        if r.passed and r.response_snippet and self.notebook_id:
            try:
                fc_data = json.loads(r.response_snippet)
                save_r = self._run("POST /notebooks/:id/content (save flashcards)", "Notebooks", "POST",
                                    f"/notebooks/{self.notebook_id}/content",
                                    json_body={
                                        "content_type": "flashcards",
                                        "title": "IaaS Flashcards",
                                        "data": fc_data,
                                        "material_id": self.material_id,
                                    },
                                    validate_fn=lambda b: None if b.get("id") else "Missing content id")
                if save_r.passed and save_r.response_snippet:
                    cid = json.loads(save_r.response_snippet).get("id")
                    if cid:
                        self.content_ids.append(cid)
            except Exception:
                pass

    def test_quiz(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 10. QUIZ GENERATION ═══{C.RESET}")

        if not self.material_id:
            print(f"  {C.YELLOW}SKIP — no material available{C.RESET}")
            return

        r = self._run("POST /quiz", "Quiz", "POST", "/quiz",
                       json_body={
                           "material_id": self.material_id,
                           "topic": "Cloud infrastructure",
                           "mcq_count": 5,
                           "difficulty": "Medium",
                       },
                       validate_fn=lambda b: None if b.get("questions") and len(b["questions"]) > 0 else "No questions generated")

        # Save to notebook
        if r.passed and r.response_snippet and self.notebook_id:
            try:
                quiz_data = json.loads(r.response_snippet)
                save_r = self._run("POST /notebooks/:id/content (save quiz)", "Notebooks", "POST",
                                    f"/notebooks/{self.notebook_id}/content",
                                    json_body={
                                        "content_type": "quiz",
                                        "title": "IaaS Quiz",
                                        "data": quiz_data,
                                        "material_id": self.material_id,
                                    })
                if save_r.passed and save_r.response_snippet:
                    cid = json.loads(save_r.response_snippet).get("id")
                    if cid:
                        self.content_ids.append(cid)
            except Exception:
                pass

    def test_presentation(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 11. PRESENTATION GENERATION ═══{C.RESET}")

        if not self.material_id:
            print(f"  {C.YELLOW}SKIP — no material available{C.RESET}")
            return

        if self.skip_slow:
            print(f"  {C.YELLOW}SKIP (--skip-slow){C.RESET}")
            return

        r = self._run("POST /presentation (sync)", "Presentation", "POST", "/presentation",
                       json_body={
                           "material_id": self.material_id,
                           "max_slides": 5,
                           "theme": "professional blue",
                       },
                       validate_fn=lambda b: None if b.get("html") and b.get("slide_count", 0) > 0 else "No HTML or slides")

        # Save to notebook
        if r.passed and r.response_snippet and self.notebook_id:
            try:
                ppt_data = json.loads(r.response_snippet)
                save_r = self._run("POST /notebooks/:id/content (save presentation)", "Notebooks", "POST",
                                    f"/notebooks/{self.notebook_id}/content",
                                    json_body={
                                        "content_type": "presentation",
                                        "title": "IaaS Presentation",
                                        "data": ppt_data,
                                        "material_id": self.material_id,
                                    })
                if save_r.passed and save_r.response_snippet:
                    cid = json.loads(save_r.response_snippet).get("id")
                    if cid:
                        self.content_ids.append(cid)
            except Exception:
                pass

    def test_podcast(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 12. PODCAST GENERATION ═══{C.RESET}")

        if not self.material_id:
            print(f"  {C.YELLOW}SKIP — no material available{C.RESET}")
            return

        if self.skip_slow:
            print(f"  {C.YELLOW}SKIP (--skip-slow){C.RESET}")
            return

        r = self._run("POST /podcast", "Podcast", "POST", "/podcast",
                       json_body={"material_id": self.material_id},
                       validate_fn=lambda b: None if b.get("audio_filename") else "Missing audio_filename")

        # Test audio download endpoint
        if r.passed and r.response_snippet and self.user_id:
            try:
                body = json.loads(r.response_snippet)
                filename = body.get("audio_filename")
                file_token = body.get("file_token")
                if filename and file_token:
                    self._run("GET /podcast/audio (stream)", "Podcast", "GET",
                               f"/podcast/audio/{self.user_id}/{filename}",
                               params={"token": file_token}, auth=False,
                               validate_fn=lambda b: "Unexpected JSON for audio" if isinstance(b, dict) else None)
            except Exception:
                pass

    def test_search(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 13. WEB SEARCH ═══{C.RESET}")

        self._run("POST /search/web", "Search", "POST", "/search/web",
                   json_body={"query": "IaaS cloud computing benefits", "engine": "duckduckgo"},
                   validate_fn=lambda b: None if isinstance(b, list) else "Expected array of results")

    def test_agent_execute(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 14. CODE EXECUTION ═══{C.RESET}")

        if not self.notebook_id:
            print(f"  {C.YELLOW}SKIP — no notebook{C.RESET}")
            return

        # Test SSE-based code execution
        print(f"  {C.DIM}Testing code execution (SSE)...{C.RESET}")
        t0 = time.time()
        try:
            resp = self.session.post(
                self._url("/agent/execute"),
                json={
                    "code": "print('IaaS test: 2+2 =', 2+2)\nresult = {'status': 'ok', 'value': 4}",
                    "notebook_id": self.notebook_id,
                    "timeout": 10,
                },
                headers={**self._auth_headers(), "Content-Type": "application/json"},
                stream=True,
                timeout=30,
            )
            got_stdout = False
            got_done = False
            buffer = ""
            current_event = ""
            for chunk in resp.iter_content(chunk_size=None, decode_unicode=True):
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        if current_event in ("stdout", "result", "start"):
                            got_stdout = True
                        elif current_event == "done":
                            got_done = True
                        current_event = ""
                    elif line == "":
                        current_event = ""
                if got_done:
                    break
            duration = (time.time() - t0) * 1000
            passed = got_stdout and got_done
            result = TestResult("POST /agent/execute (SSE)", "Agent", passed, round(duration, 1),
                                status_code=resp.status_code,
                                detail="" if passed else f"stdout={got_stdout}, done={got_done}")
        except Exception as e:
            duration = (time.time() - t0) * 1000
            result = TestResult("POST /agent/execute (SSE)", "Agent", False, round(duration, 1),
                                detail=str(e))
        self.results.append(result)
        self._print_result(result)

    def test_jobs(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 15. JOB STATUS ═══{C.RESET}")

        if self.job_id:
            self._run("GET /jobs/:job_id", "Jobs", "GET", f"/jobs/{self.job_id}",
                       validate_fn=lambda b: None if b.get("status") else "Missing status")
        else:
            # Try with a fake UUID — expect 404
            self._run("GET /jobs/:job_id (404)", "Jobs", "GET", f"/jobs/{uuid.uuid4()}",
                       expected_status=404)

    def test_content_management(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 16. GENERATED CONTENT MANAGEMENT ═══{C.RESET}")

        if not self.notebook_id:
            print(f"  {C.YELLOW}SKIP — no notebook{C.RESET}")
            return

        # List content
        self._run("GET /notebooks/:id/content", "Content", "GET",
                   f"/notebooks/{self.notebook_id}/content",
                   validate_fn=lambda b: None if isinstance(b, list) else "Expected list")

        # Rename content (if we have saved any)
        if self.content_ids:
            cid = self.content_ids[0]
            self._run("PUT /notebooks/:id/content/:cid (rename)", "Content", "PUT",
                       f"/notebooks/{self.notebook_id}/content/{cid}",
                       json_body={"title": "Renamed Content"})

        # Delete one content item
        if len(self.content_ids) > 1:
            cid = self.content_ids.pop()
            self._run("DELETE /notebooks/:id/content/:cid", "Content", "DELETE",
                       f"/notebooks/{self.notebook_id}/content/{cid}",
                       validate_fn=lambda b: None if b.get("deleted") else "Missing deleted flag")

    def test_auth_edge_cases(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 17. AUTH EDGE CASES ═══{C.RESET}")

        # Unauthorized access (FastAPI Depends returns 403 when no credentials, 401 when invalid)
        self._run("GET /notebooks (no auth → 401/403)", "Auth", "GET", "/notebooks",
                   expected_status=(401, 403), auth=False)

        # Invalid token
        old_token = self.token
        self.token = "invalid_token_12345"
        self._run("GET /auth/me (bad token → 401)", "Auth", "GET", "/auth/me",
                   expected_status=401)
        self.token = old_token

    def test_cleanup(self):
        print(f"\n{C.BOLD}{C.CYAN}═══ 18. CLEANUP ═══{C.RESET}")

        # Delete chat history
        if self.notebook_id:
            self._run("DELETE /chat/history/:notebook_id", "Chat", "DELETE",
                       f"/chat/history/{self.notebook_id}",
                       validate_fn=lambda b: None if b.get("cleared") else "Missing cleared flag")

        # Delete chat session
        if self.session_id:
            self._run("DELETE /chat/sessions/:session_id", "Chat", "DELETE",
                       f"/chat/sessions/{self.session_id}",
                       validate_fn=lambda b: None if b.get("deleted") else "Missing deleted flag")

        # Delete material
        if self.material_id:
            self._run("DELETE /materials/:id", "Materials", "DELETE",
                       f"/materials/{self.material_id}",
                       validate_fn=lambda b: None if b.get("deleted") else "Missing deleted flag")

        # Delete notebook
        if self.notebook_id:
            self._run("DELETE /notebooks/:id", "Notebooks", "DELETE",
                       f"/notebooks/{self.notebook_id}",
                       expected_status=204)

        # Logout
        self._run("POST /auth/logout", "Auth", "POST", "/auth/logout")

    def run_all(self):
        """Execute every test in order."""
        print(f"\n{C.BOLD}{C.MAGENTA}{'='*60}")
        print(f"  KeplerLab AI Notebook — Full Feature Test Suite")
        print(f"  Base URL: {self.base}")
        print(f"  PDF: {self.pdf_path}")
        print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}{C.RESET}")

        self.test_health()
        self.test_models_status()
        self.test_supported_formats()
        self.test_auth()

        if not self.token:
            print(f"\n{C.RED}ABORT: Cannot continue without auth token.{C.RESET}")
            return self.results

        self.test_notebooks()
        self.test_upload_file()
        self.test_upload_text()
        self.test_chat()
        self.test_flashcards()
        self.test_quiz()
        self.test_presentation()
        self.test_podcast()
        self.test_search()
        self.test_agent_execute()
        self.test_jobs()
        self.test_content_management()
        self.test_auth_edge_cases()
        self.test_cleanup()

        return self.results


# ── Log Analyser ──────────────────────────────────────────────────────────

def analyse_logs(log_path: str) -> LogAnalysis:
    """Parse backend app.log and produce an analysis."""
    analysis = LogAnalysis()

    if not os.path.exists(log_path):
        analysis.issues = [f"Log file not found: {log_path}"]
        return analysis

    # Patterns
    re_request = re.compile(
        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - main - INFO - "
        r"(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD) (/\S*) (\d{3}) ([\d.]+)s"
    )
    re_error = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ - .+ - (ERROR|CRITICAL) - (.+)")
    re_warning = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+ - .+ - WARNING - (.+)")

    response_times = []
    endpoints = Counter()
    status_codes = Counter()

    with open(log_path, "r", errors="replace") as f:
        for line in f:
            analysis.total_lines += 1

            if " - INFO - " in line:
                analysis.info_count += 1
            elif " - WARNING - " in line:
                analysis.warning_count += 1
                m = re_warning.match(line)
                if m and len(analysis.warnings) < 50:
                    analysis.warnings.append(m.group(1).strip()[:200])
            elif " - ERROR - " in line or " - CRITICAL - " in line:
                analysis.error_count += 1
                m = re_error.match(line)
                if m and len(analysis.errors) < 50:
                    analysis.errors.append(m.group(2).strip()[:200])

            # Request log line
            m = re_request.match(line)
            if m:
                _, method, path, status, duration = m.groups()
                endpoint = f"{method} {path}"
                endpoints[endpoint] += 1
                status_codes[status] += 1
                dt = float(duration)
                response_times.append(dt)
                if dt > 5.0 and len(analysis.slow_requests) < 30:
                    analysis.slow_requests.append(f"{endpoint} → {dt:.2f}s [{status}]")

    total_requests = sum(endpoints.values())
    analysis.endpoints_hit = dict(endpoints.most_common(30))
    analysis.status_codes = dict(status_codes.most_common())
    analysis.error_rate = (
        (status_codes.get("500", 0) + status_codes.get("502", 0) + status_codes.get("503", 0))
        / max(total_requests, 1) * 100
    )

    if response_times:
        analysis.avg_response_time_ms = round(sum(response_times) / len(response_times) * 1000, 1)

    return analysis


# ── Output Analyser ───────────────────────────────────────────────────────

def analyse_outputs(project_root: Path) -> OutputAnalysis:
    """Scan output/ and data/ directories for generated artifacts."""
    analysis = OutputAnalysis()

    # Podcasts
    podcast_dir = project_root / "backend" / "output" / "podcasts"
    if podcast_dir.exists():
        for f in podcast_dir.rglob("*"):
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                analysis.podcast_files.append({"name": f.name, "size_kb": round(size_kb, 1)})
                if size_kb < 1:
                    analysis.issues.append(f"Suspiciously small podcast file: {f.name} ({size_kb:.1f} KB)")

    # Presentations
    ppt_dir = project_root / "backend" / "output" / "presentations"
    if ppt_dir.exists():
        for f in ppt_dir.rglob("*"):
            if f.is_file():
                analysis.presentation_files.append(f.name)

    # HTML output
    html_dir = project_root / "backend" / "output" / "html"
    if html_dir.exists():
        for f in html_dir.rglob("*.html"):
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                if size_kb < 0.5:
                    analysis.issues.append(f"Empty/tiny HTML file: {f.name}")

    # Uploads
    upload_dir = project_root / "backend" / "data" / "uploads"
    if upload_dir.exists():
        for f in upload_dir.rglob("*"):
            if f.is_file():
                analysis.upload_files.append(f.name)

    # Material texts
    text_dir = project_root / "backend" / "data" / "material_text"
    if text_dir.exists():
        for f in text_dir.glob("*.txt"):
            size_kb = f.stat().st_size / 1024
            analysis.material_texts.append({"name": f.name, "size_kb": round(size_kb, 1)})
            if size_kb < 0.1:
                analysis.issues.append(f"Empty material text: {f.name}")

    # ChromaDB
    chroma_db = project_root / "backend" / "data" / "chroma" / "chroma.sqlite3"
    if chroma_db.exists():
        size_mb = chroma_db.stat().st_size / (1024 * 1024)
        if size_mb < 0.01:
            analysis.issues.append("ChromaDB appears empty (< 10 KB)")

    return analysis


# ── Report Printer ────────────────────────────────────────────────────────

def print_test_summary(results: list[TestResult]):
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print(f"\n{C.BOLD}{C.MAGENTA}{'='*60}")
    print(f"  TEST RESULTS SUMMARY")
    print(f"{'='*60}{C.RESET}\n")

    # By category
    by_cat = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    for cat, items in by_cat.items():
        cat_pass = sum(1 for r in items if r.passed)
        cat_total = len(items)
        colour = C.GREEN if cat_pass == cat_total else C.YELLOW if cat_pass > 0 else C.RED
        print(f"  {colour}{cat:20s}  {cat_pass}/{cat_total} passed{C.RESET}")

    print(f"\n  {C.BOLD}Total: {passed}/{total} passed", end="")
    if failed > 0:
        print(f"  ({C.RED}{failed} failed{C.RESET}{C.BOLD})", end="")
    print(f"{C.RESET}")

    # Show failures
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n  {C.RED}{C.BOLD}FAILURES:{C.RESET}")
        for r in failures:
            print(f"    {C.RED}✗ [{r.category}] {r.name}{C.RESET}")
            if r.detail:
                print(f"      {C.DIM}{r.detail}{C.RESET}")

    # Timing
    total_time = sum(r.duration_ms for r in results)
    slowest = sorted(results, key=lambda r: r.duration_ms, reverse=True)[:5]
    print(f"\n  {C.BOLD}Total time: {total_time/1000:.1f}s{C.RESET}")
    print(f"  {C.BOLD}Slowest endpoints:{C.RESET}")
    for r in slowest:
        print(f"    {r.duration_ms:.0f}ms  {r.name}")

    return passed, failed


def print_log_analysis(analysis: LogAnalysis):
    print(f"\n{C.BOLD}{C.BLUE}{'='*60}")
    print(f"  BACKEND LOG ANALYSIS")
    print(f"{'='*60}{C.RESET}\n")

    print(f"  Total lines:         {analysis.total_lines:,}")
    print(f"  INFO messages:       {C.GREEN}{analysis.info_count:,}{C.RESET}")
    print(f"  WARNING messages:    {C.YELLOW}{analysis.warning_count:,}{C.RESET}")
    print(f"  ERROR messages:      {C.RED}{analysis.error_count:,}{C.RESET}")
    print(f"  Server error rate:   ", end="")
    if analysis.error_rate < 1:
        print(f"{C.GREEN}{analysis.error_rate:.2f}%{C.RESET}")
    elif analysis.error_rate < 5:
        print(f"{C.YELLOW}{analysis.error_rate:.2f}%{C.RESET}")
    else:
        print(f"{C.RED}{analysis.error_rate:.2f}%{C.RESET}")
    print(f"  Avg response time:   {analysis.avg_response_time_ms:.0f}ms")

    if analysis.status_codes:
        print(f"\n  {C.BOLD}HTTP Status Codes:{C.RESET}")
        for code, count in sorted(analysis.status_codes.items()):
            colour = C.GREEN if code.startswith("2") else C.YELLOW if code.startswith("4") else C.RED
            print(f"    {colour}{code}: {count:,}{C.RESET}")

    if analysis.endpoints_hit:
        print(f"\n  {C.BOLD}Top Endpoints:{C.RESET}")
        for ep, count in list(analysis.endpoints_hit.items())[:15]:
            print(f"    {count:>5,}× {ep}")

    if analysis.slow_requests:
        print(f"\n  {C.BOLD}{C.YELLOW}Slow Requests (>5s):{C.RESET}")
        for req in analysis.slow_requests[:10]:
            print(f"    {C.YELLOW}⚠ {req}{C.RESET}")

    if analysis.errors:
        print(f"\n  {C.BOLD}{C.RED}Recent Errors (last {len(analysis.errors)}):{C.RESET}")
        for err in analysis.errors[-10:]:
            print(f"    {C.RED}✗ {err}{C.RESET}")

    if analysis.warnings:
        print(f"\n  {C.BOLD}{C.YELLOW}Recent Warnings (sample):{C.RESET}")
        for w in analysis.warnings[-5:]:
            print(f"    {C.YELLOW}⚠ {w}{C.RESET}")

    # Verdict
    print(f"\n  {C.BOLD}Log Health Verdict: ", end="")
    if analysis.error_count == 0 and analysis.error_rate < 1:
        print(f"{C.GREEN}HEALTHY ✓{C.RESET}")
    elif analysis.error_rate < 5 and analysis.error_count < 50:
        print(f"{C.YELLOW}MINOR ISSUES ⚠{C.RESET}")
    else:
        print(f"{C.RED}NEEDS ATTENTION ✗{C.RESET}")


def print_output_analysis(analysis: OutputAnalysis):
    print(f"\n{C.BOLD}{C.BLUE}{'='*60}")
    print(f"  OUTPUT / DATA ANALYSIS")
    print(f"{'='*60}{C.RESET}\n")

    print(f"  Podcast files:       {len(analysis.podcast_files)}")
    for p in analysis.podcast_files[:5]:
        print(f"    {p['name']} ({p['size_kb']:.0f} KB)")

    print(f"  Presentation files:  {len(analysis.presentation_files)}")
    print(f"  Uploaded files:      {len(analysis.upload_files)}")
    print(f"  Material texts:      {len(analysis.material_texts)}")

    total_text_kb = sum(m["size_kb"] for m in analysis.material_texts)
    print(f"  Total text corpus:   {total_text_kb:.0f} KB ({total_text_kb/1024:.1f} MB)")

    if analysis.issues:
        print(f"\n  {C.BOLD}{C.YELLOW}Issues Found:{C.RESET}")
        for issue in analysis.issues:
            print(f"    {C.YELLOW}⚠ {issue}{C.RESET}")
    else:
        print(f"\n  {C.GREEN}No issues found ✓{C.RESET}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="KeplerLab AI Notebook — Full Feature Test Suite")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Backend API base URL")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF_PATH), help="Path to test PDF file")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Test user email")
    parser.add_argument("--password", default=DEFAULT_PASSWORD, help="Test user password")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Test user username")
    parser.add_argument("--log-file", default=str(DEFAULT_LOG_PATH), help="Backend log file path")
    parser.add_argument("--skip-slow", action="store_true", help="Skip podcast/presentation (slow)")
    parser.add_argument("--skip-logs", action="store_true", help="Skip log analysis")
    parser.add_argument("--skip-outputs", action="store_true", help="Skip output analysis")
    args = parser.parse_args()

    # ── 1. Run feature tests ──
    tester = FeatureTester(
        base_url=args.base_url,
        pdf_path=args.pdf,
        email=args.email,
        password=args.password,
        username=args.username,
        skip_slow=args.skip_slow,
    )

    try:
        results = tester.run_all()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Interrupted by user{C.RESET}")
        results = tester.results

    passed, failed = print_test_summary(results)

    # ── 2. Analyse logs ──
    log_analysis = None
    if not args.skip_logs:
        log_analysis = analyse_logs(args.log_file)
        print_log_analysis(log_analysis)

    # ── 3. Analyse outputs ──
    output_analysis = None
    if not args.skip_outputs:
        output_analysis = analyse_outputs(PROJECT_ROOT)
        print_output_analysis(output_analysis)

    # ── 4. Overall verdict ──
    print(f"\n{C.BOLD}{C.MAGENTA}{'='*60}")
    print(f"  OVERALL VERDICT")
    print(f"{'='*60}{C.RESET}\n")

    issues = []
    if failed > 0:
        issues.append(f"{failed} API test(s) failed")
    if log_analysis and log_analysis.error_rate > 5:
        issues.append(f"High server error rate ({log_analysis.error_rate:.1f}%)")
    if log_analysis and log_analysis.error_count > 100:
        issues.append(f"Many backend errors ({log_analysis.error_count})")
    if output_analysis and output_analysis.issues:
        issues.append(f"{len(output_analysis.issues)} output issue(s)")

    if not issues:
        print(f"  {C.GREEN}{C.BOLD}ALL SYSTEMS OPERATIONAL ✓{C.RESET}")
        print(f"  {C.GREEN}All {passed} tests passed. Logs clean. Outputs valid.{C.RESET}")
    else:
        print(f"  {C.YELLOW}{C.BOLD}ISSUES DETECTED:{C.RESET}")
        for issue in issues:
            print(f"    {C.YELLOW}⚠ {issue}{C.RESET}")

    # ── 5. Save JSON report ──
    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": args.base_url,
        "tests": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "results": [asdict(r) for r in results],
        },
        "log_analysis": asdict(log_analysis) if log_analysis else None,
        "output_analysis": asdict(output_analysis) if output_analysis else None,
        "verdict": "PASS" if not issues else "ISSUES",
        "issues": issues,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n  {C.DIM}Report saved to: {REPORT_PATH}{C.RESET}")
    print()

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
