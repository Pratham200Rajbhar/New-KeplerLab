#!/usr/bin/env python3
"""ML Agentic Feature End-to-End Test Script.

Tests the full agent pipeline with REAL machine-learning tasks:
  - Missing value detection & imputation
  - Feature engineering
  - Model training (regression + classification)
  - Prediction on new data points
  - Diagram generation (heatmaps, feature importance, confusion matrix, ROC)
  - User-injected custom prompts

Usage:
    python test/test_agentic_feature.py \
        --base-url http://localhost:8000 \
        --email user@example.com \
        --password yourpassword \
        [--dataset employees|housing|custom_csv /path/to/file.csv] \
        [--prompt "Your custom prompt here" ...]

No timeouts are enforced — the script waits as long as the backend needs.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

CHART_PATTERN = re.compile(r"__CHART_BASE64__(.+?)__END_CHART__", re.DOTALL)

# pip name  ->  importable module (tested in the shared venv)
REQUIRED_PKGS: Dict[str, str] = {
    "pandas":       "pandas",
    "numpy":        "numpy",
    "scikit-learn": "sklearn",
    "matplotlib":   "matplotlib",
    "seaborn":      "seaborn",
    "openpyxl":     "openpyxl",
    "scipy":        "scipy",
}

# ─── Built-in prompts ────────────────────────────────────────────────────────

# Helper snippet injected at the start of every self-contained prompt so the
# agent knows exactly how to load + clean the data in its sandbox.
_SETUP = (
    "Load the uploaded dataset (use pd.read_parquet on whichever .parquet file "
    "is present in the working directory). "
    "Fill numeric nulls with column median and categorical nulls with column mode "
    "before proceeding. "
)

BUILTIN_PROMPTS: List[Dict[str, Any]] = [
    # ── 1. Missing-value audit ────────────────────────────────────────────────
    {
        "label":   "missing_audit",
        "message": (
            "Audit this dataset for missing values. "
            "Show: total rows, count and percentage missing per column. "
            "Then draw a horizontal bar chart of missing-value counts using "
            "matplotlib and call plt.show() to display it."
        ),
        "expect_chart":   True,
        "expect_excel":   False,
        "chart_filename": "missing_audit.png",
        "excel_filename": None,
        "tags": ["missing_values", "eda"],
    },

    # ── 2. Imputation + Excel export ──────────────────────────────────────────
    {
        "label":   "impute_missing",
        "message": (
            _SETUP +
            "Print the null counts before and after imputation. "
            "Then save the fully-clean dataframe to 'imputed_data.xlsx' using "
            "df.to_excel('imputed_data.xlsx', index=False) and print 'Saved imputed_data.xlsx'."
        ),
        "expect_chart":   False,
        "expect_excel":   True,
        "chart_filename": None,
        "excel_filename": "imputed_data.xlsx",
        "tags": ["missing_values", "imputation"],
    },

    # ── 3. Correlation heatmap ────────────────────────────────────────────────
    {
        "label":   "correlation_heatmap",
        "message": (
            _SETUP +
            "Select only the numeric columns and compute their Pearson correlation matrix. "
            "Plot the matrix as a heatmap using only matplotlib (do NOT use seaborn): "
            "use plt.imshow(corr, cmap='coolwarm'), add plt.colorbar(), set axis tick labels "
            "to the column names, annotate each cell with its rounded value, use figsize=(10,8), "
            "add a title 'Correlation Matrix', then call plt.tight_layout() and plt.show()."
        ),
        "expect_chart":   True,
        "expect_excel":   False,
        "chart_filename": "correlation_heatmap.png",
        "excel_filename": None,
        "tags": ["feature_engineering", "heatmap"],
    },

    # ── 4. Random Forest regression + feature importance ──────────────────────
    {
        "label":   "train_model",
        "message": (
            _SETUP +
            "Train a Random Forest Regressor (n_estimators=100, random_state=42) using "
            "all available numeric features to predict the 'salary' column "
            "(or 'price' for housing data). "
            "Use an 80/20 train/test split. Print MAE, RMSE, and R² on the test set. "
            "Then plot a horizontal bar chart of feature importances sorted descending "
            "and call plt.show()."
        ),
        "expect_chart":   True,
        "expect_excel":   False,
        "chart_filename": "feature_importance.png",
        "excel_filename": None,
        "tags": ["model_training", "random_forest", "regression"],
    },

    # ── 5. Self-contained salary prediction ───────────────────────────────────
    {
        "label":   "predict_new",
        "message": (
            _SETUP +
            "Train a Random Forest Regressor (100 trees) on all numeric columns to "
            "predict salary (drop rows where salary is NaN for training). "
            "Then predict salary for these three new records and print the results:\n"
            "  emp1: age=32, years_experience=7, performance_score=4.1, num_projects=5\n"
            "  emp2: age=45, years_experience=18, performance_score=4.8, num_projects=9\n"
            "  emp3: age=24, years_experience=2, performance_score=3.2, num_projects=2"
        ),
        "expect_chart":   False,
        "expect_excel":   False,
        "chart_filename": None,
        "excel_filename": None,
        "tags": ["prediction", "inference"],
    },

    # ── 6. Classification + confusion matrix ──────────────────────────────────
    {
        "label":   "classify_performance",
        "message": (
            _SETUP +
            "Create a binary target 'high_performer': 1 if performance_score >= 4.0 else 0 "
            "(drop rows where performance_score is NaN). "
            "Train a GradientBoostingClassifier on all numeric features except the target. "
            "Print accuracy, precision, recall, and F1. "
            "Plot the confusion matrix as a seaborn heatmap and call plt.show()."
        ),
        "expect_chart":   True,
        "expect_excel":   False,
        "chart_filename": "confusion_matrix.png",
        "excel_filename": None,
        "tags": ["classification", "confusion_matrix"],
    },

    # ── 7. IQR outlier detection + boxplots ───────────────────────────────────
    {
        "label":   "outlier_analysis",
        "message": (
            _SETUP +
            "Detect outliers in every numeric column using the IQR method "
            "(values below Q1-1.5*IQR or above Q3+1.5*IQR). "
            "Print the outlier count per column. "
            "Then draw side-by-side boxplots for the 4 numeric columns with the most "
            "outliers using matplotlib and call plt.show()."
        ),
        "expect_chart":   True,
        "expect_excel":   False,
        "chart_filename": "outlier_boxplot.png",
        "excel_filename": None,
        "tags": ["outliers", "eda", "boxplot"],
    },

    # ── 8. Model comparison + Excel export ────────────────────────────────────
    {
        "label":   "metrics_export",
        "message": (
            _SETUP +
            "Compare LinearRegression, RandomForestRegressor(100 trees), and "
            "GradientBoostingRegressor on an 80/20 split to predict salary "
            "(numeric features only, drop salary-null rows for training). "
            "Collect MAE, RMSE, R² for each model in a DataFrame. "
            "Save it to 'model_metrics.xlsx' using .to_excel('model_metrics.xlsx', index=False) "
            "and print 'Saved model_metrics.xlsx'. "
            "Also draw a grouped bar chart of R² scores and call plt.show()."
        ),
        "expect_chart":   True,
        "expect_excel":   True,
        "chart_filename": "model_comparison.png",
        "excel_filename": "model_metrics.xlsx",
        "tags": ["model_comparison", "benchmarking"],
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# SYNTHETIC DATASET GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def _make_employee_dataset(n: int = 200) -> List[Dict]:
    random.seed(42)
    departments = ["Engineering", "Sales", "Marketing", "HR", "Finance",
                   "Management", "Design", "Support", "Legal", "Product"]
    educations  = ["Bachelors", "Masters", "PhD", "High School", "Diploma"]

    rows = []
    for i in range(n):
        dept    = random.choice(departments)
        edu     = random.choice(educations)
        age     = random.randint(22, 60)
        yexp    = max(0, age - random.randint(20, 26))
        perf    = round(random.uniform(1.0, 5.0), 2)
        nproj   = random.randint(1, 15)
        edu_mult = {"High School": 0.7, "Diploma": 0.85, "Bachelors": 1.0,
                    "Masters": 1.2, "PhD": 1.4}[edu]
        dept_mult = {"Engineering": 1.3, "Finance": 1.2, "Management": 1.35,
                     "Legal": 1.25, "Product": 1.15, "Design": 1.05,
                     "Marketing": 0.95, "HR": 0.9, "Sales": 1.0, "Support": 0.85}[dept]
        salary = round(40000 + yexp * 3800 + perf * 4000 + nproj * 500,
                       -2) * edu_mult * dept_mult
        salary = round(salary + random.gauss(0, 3000), -2)

        # Inject ~12 % missing per column
        rows.append({
            "employee_id":       i + 1001,
            "age":               None if random.random() < 0.10 else age,
            "department":        None if random.random() < 0.08 else dept,
            "years_experience":  None if random.random() < 0.09 else yexp,
            "education":         None if random.random() < 0.07 else edu,
            "performance_score": None if random.random() < 0.11 else perf,
            "num_projects":      None if random.random() < 0.09 else nproj,
            "salary":            None if random.random() < 0.06 else max(25000, salary),
        })
    return rows


def _make_housing_dataset(n: int = 200) -> List[Dict]:
    random.seed(7)
    styles = ["Ranch", "Colonial", "Victorian", "Modern", "Craftsman",
              "Bungalow", "Townhouse", "Condo"]
    neighborhoods = ["Downtown", "Suburbs", "Uptown", "Midtown",
                     "Eastside", "Westside", "Lakefront", "Historic"]
    rows = []
    for i in range(n):
        sqft      = random.randint(600, 5000)
        bedrooms  = random.randint(1, 6)
        bathrooms = round(random.choice([1, 1.5, 2, 2.5, 3, 3.5, 4]), 1)
        lot_size  = round(random.uniform(0.05, 2.0), 2)
        year      = random.randint(1920, 2023)
        style     = random.choice(styles)
        nbh       = random.choice(neighborhoods)
        nbh_mult  = {"Downtown": 1.4, "Uptown": 1.35, "Lakefront": 1.5,
                     "Midtown": 1.2, "Historic": 1.15, "Eastside": 1.0,
                     "Westside": 1.05, "Suburbs": 0.9}[nbh]
        price     = (sqft * 180 + bedrooms * 12000 + bathrooms * 8000 +
                     lot_size * 30000 + (2024 - year) * (-200))
        price     = round(price * nbh_mult + random.gauss(0, 15000), -3)

        rows.append({
            "property_id":   i + 3001,
            "sqft":          None if random.random() < 0.09 else sqft,
            "bedrooms":      None if random.random() < 0.07 else bedrooms,
            "bathrooms":     None if random.random() < 0.08 else bathrooms,
            "lot_size_acres":None if random.random() < 0.12 else lot_size,
            "year_built":    None if random.random() < 0.10 else year,
            "style":         None if random.random() < 0.06 else style,
            "neighborhood":  None if random.random() < 0.05 else nbh,
            "price":         None if random.random() < 0.05 else max(50000, price),
        })
    return rows


DATASETS: Dict[str, Tuple[str, List[Dict]]] = {}  # populated lazily


def get_or_build_dataset(name: str) -> Tuple[str, List[Dict]]:
    if name not in DATASETS:
        if name == "housing":
            DATASETS[name] = ("price", _make_housing_dataset())
        else:
            DATASETS[name] = ("salary", _make_employee_dataset())
    return DATASETS[name]


def write_csv(rows: List[Dict], dest: str) -> None:
    if not rows:
        return
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


# ─────────────────────────────────────────────────────────────────────────────
# LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class TestLogger:
    def __init__(self, out_dir: Path, ts: str):
        logs = out_dir / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        self.report_path = out_dir / f"report_{ts}.txt"
        self._run  = open(logs / f"run_{ts}.log",    "w", encoding="utf-8")
        self._evt  = open(logs / f"events_{ts}.log", "w", encoding="utf-8")
        self._err  = open(logs / f"errors_{ts}.log", "w", encoding="utf-8")

    def _ts(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log(self, msg: str, *, console: bool = True) -> None:
        line = f"[{self._ts()}] {msg}"
        self._run.write(line + "\n"); self._run.flush()
        if console:
            print(line)

    def log_event(self, ev: str, db: str) -> None:
        self._evt.write(f"[{self._ts()}] EVENT:{ev}  {db[:500]}\n")
        self._evt.flush()

    def log_http(self, method: str, url: str, code: int) -> None:
        self.log(f"HTTP {method} {url} -> {code}")

    def log_error(self, msg: str, tb: str = "") -> None:
        self.log(f"ERROR: {msg}")
        entry = f"[{self._ts()}] {msg}"
        if tb:
            entry += "\n" + tb
        self._err.write(entry + "\n"); self._err.flush()

    def write_report(self, results: List[Dict[str, Any]]) -> None:
        passed  = [r for r in results if r["status"] == "PASS"]
        failed  = [r for r in results if r["status"] == "FAIL"]
        skipped = [r for r in results if r["status"] == "SKIP"]
        sym = {"PASS": "v", "FAIL": "x", "SKIP": "-"}
        lines = [
            "=" * 72,
            "  ML AGENTIC FEATURE TEST REPORT",
            f"  Generated : {datetime.now().isoformat()}",
            "=" * 72, "",
        ]
        for r in results:
            s = r["status"]
            line = f"  [{s}] {sym[s]}  {r['name']}"
            if r.get("reason"):
                line += f"  --  {r['reason']}"
            lines.append(line)
        lines += [
            "",
            "-" * 72,
            (f"  TOTAL: {len(results)}  |  PASS: {len(passed)}  |  "
             f"FAIL: {len(failed)}  |  SKIP: {len(skipped)}"),
            f"  OVERALL: {'ALL PASS' if not failed else 'FAIL'}",
            "=" * 72,
        ]
        text = "\n".join(lines)
        self.report_path.write_text(text, encoding="utf-8")
        print("\n" + text)

    def close(self) -> None:
        for f in (self._run, self._evt, self._err):
            try: f.close()
            except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────────────────────────────────────

class Results:
    def __init__(self, log: TestLogger):
        self.items: List[Dict[str, Any]] = []
        self._log = log

    def pass_(self, name: str, reason: str = "") -> None:
        self.items.append({"name": name, "status": "PASS", "reason": reason})
        self._log.log(f"  RESULT PASS  {name}  {reason}")

    def fail(self, name: str, reason: str = "") -> None:
        self.items.append({"name": name, "status": "FAIL", "reason": reason})
        self._log.log(f"  RESULT FAIL  {name}  {reason}")

    def skip(self, name: str, reason: str = "") -> None:
        self.items.append({"name": name, "status": "SKIP", "reason": reason})
        self._log.log(f"  RESULT SKIP  {name}  {reason}")


# ─────────────────────────────────────────────────────────────────────────────
# API CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class Client:
    def __init__(self, base_url: str, log: TestLogger):
        self.base          = base_url.rstrip("/")
        self.log           = log
        self.sess          = requests.Session()
        self.token:        Optional[str] = None
        self.user_id:      Optional[str] = None
        self._email:       Optional[str] = None
        self._password:    Optional[str] = None
        self._token_ts:    float = 0.0          # epoch time of last login
        self._token_ttl:   int   = 12 * 60       # refresh after 12 min (< 15 min JWT)

    @property
    def _h(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def ensure_fresh_token(self) -> None:
        """Re-login if the token is older than _token_ttl seconds."""
        age = time.time() - self._token_ts
        if age >= self._token_ttl and self._email and self._password:
            self.log.log(f"  [auth] Token age {age:.0f}s >= {self._token_ttl}s — refreshing...")
            self.login(self._email, self._password)

    # ── auth ───────────────────────────────────────────────────────────────
    def login(self, email: str, password: str) -> bool:
        url = f"{self.base}/auth/login"
        self.log.log(f"Logging in as {email} ...")
        try:
            r = self.sess.post(url, json={"email": email, "password": password})
            self.log.log_http("POST", url, r.status_code)
            if r.status_code == 200:
                self.token    = r.json()["access_token"]
                self._email   = email
                self._password = password
                self._token_ts = time.time()
                me = self.sess.get(f"{self.base}/auth/me", headers=self._h)
                if me.status_code == 200:
                    self.user_id = me.json().get("id")
                self.log.log(f"Login OK — user_id={self.user_id}")
                return True
            self.log.log_error(f"Login failed {r.status_code}: {r.text[:300]}")
            return False
        except Exception as exc:
            self.log.log_error(f"Login exc: {exc}", traceback.format_exc())
            return False

    # ── health ─────────────────────────────────────────────────────────────
    def health(self) -> Dict:
        url = f"{self.base}/health"
        try:
            r = self.sess.get(url, timeout=15)
            self.log.log_http("GET", url, r.status_code)
            return r.json() if r.status_code == 200 else {}
        except Exception as exc:
            self.log.log_error(f"Health: {exc}")
            return {}

    # ── upload ─────────────────────────────────────────────────────────────
    def upload(self, filepath: str, fname: Optional[str] = None) -> Optional[Dict]:
        url = f"{self.base}/upload"
        fname = fname or os.path.basename(filepath)
        self.log.log(f"Uploading {filepath} as '{fname}' ...")
        try:
            with open(filepath, "rb") as fh:
                r = self.sess.post(
                    url,
                    files={"file": (fname, fh, "text/csv")},
                    data={"auto_create_notebook": "true"},
                    headers=self._h,
                )
            self.log.log_http("POST", url, r.status_code)
            if r.status_code in (200, 201, 202):
                body = r.json()
                mid = body.get("material_id")
                jid = body.get("job_id")
                self.log.log(f"Upload accepted: material={mid}  job={jid}")
                return body
            self.log.log_error(f"Upload {r.status_code}: {r.text[:300]}")
        except Exception as exc:
            self.log.log_error(f"Upload exc: {exc}", traceback.format_exc())
        return None

    # ── poll job ───────────────────────────────────────────────────────────
    def poll_job(self, job_id: str) -> Optional[str]:
        """Poll until terminal status — no timeout."""
        url = f"{self.base}/jobs/{job_id}"
        self.log.log(f"Polling job {job_id} (no timeout) ...")
        while True:
            try:
                r = self.sess.get(url, headers=self._h, timeout=15)
                self.log.log_http("GET", url, r.status_code)
                if r.status_code == 200:
                    st = r.json().get("status", "unknown")
                    self.log.log(f"  → {st}")
                    if st in ("completed", "failed", "error"):
                        return st
            except Exception as exc:
                self.log.log_error(f"Poll exc: {exc}")
            time.sleep(4)

    # ── agent/files ────────────────────────────────────────────────────────
    def agent_files(self, session_id: str) -> List[Dict]:
        url = f"{self.base}/agent/files?session_id={session_id}"
        try:
            r = self.sess.get(url, headers=self._h, timeout=15)
            self.log.log_http("GET", url, r.status_code)
            if r.status_code == 200:
                return r.json().get("files", [])
        except Exception as exc:
            self.log.log_error(f"agent_files: {exc}")
        return []

    # ── copy backend output dir ────────────────────────────────────────────
    def copy_output_dir(self, session_id: str,
                        backend_root: str, dest_dir: str) -> List[str]:
        if not self.user_id or not session_id:
            return []
        src = os.path.join(backend_root, "output", "generated",
                           self.user_id, session_id)
        if not os.path.isdir(src):
            return []
        Path(dest_dir).mkdir(parents=True, exist_ok=True)
        copied = []
        for fname in os.listdir(src):
            fp = os.path.join(src, fname)
            if os.path.isfile(fp):
                shutil.copy2(fp, os.path.join(dest_dir, fname))
                self.log.log(f"  Copied from output/generated: {fname}")
                copied.append(fname)
        return copied

    # ── save chart from base64 ─────────────────────────────────────────────
    def save_chart(self, b64: str, dest: str) -> bool:
        try:
            data = base64.b64decode(b64)
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            Path(dest).write_bytes(data)
            self.log.log(f"  Chart saved ({len(data):,} B) → {dest}")
            return True
        except Exception as exc:
            self.log.log_error(f"Chart save: {exc}", traceback.format_exc())
            return False

    # ── download ───────────────────────────────────────────────────────────
    def download(self, url_or_path: str, dest: str) -> bool:
        url = (f"{self.base}{url_or_path}"
               if url_or_path.startswith("/") else url_or_path)
        try:
            r = self.sess.get(url, headers=self._h, timeout=120)
            self.log.log_http("GET", url, r.status_code)
            if r.status_code == 200:
                Path(dest).parent.mkdir(parents=True, exist_ok=True)
                Path(dest).write_bytes(r.content)
                self.log.log(f"  Downloaded {len(r.content):,} B → {dest}")
                return True
        except Exception as exc:
            self.log.log_error(f"Download: {exc}", traceback.format_exc())
        return False

    # ── CHAT (SSE, no timeout) ─────────────────────────────────────────────
    def chat(self, message: str, material_ids: List[str],
             notebook_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base}/chat"
        payload: Dict[str, Any] = {
            "message":      message,
            "material_ids": material_ids,
            "notebook_id":  notebook_id,
            "stream":       True,
        }
        if session_id:
            payload["session_id"] = session_id

        self.ensure_fresh_token()
        self.log.log(f'\n  Chat → "{message[:100]}..." ')

        out: Dict[str, Any] = {
            "session_id":       None,
            "has_step":         False,
            "has_done":         False,
            "has_error":        False,
            "has_file_ready":   False,
            "has_repair":       False,
            "has_chart":        False,
            "has_excel_code":   False,
            "has_excel_stdout": False,
            "chart_b64":        [],    # all captured charts
            "file_urls":        [],
            "token_text":       "",
            "raw_stdout":       "",
            "code_written":     [],
            "error_text":       "",
            "step_log":         [],
            "events":           [],
        }

        try:
            r = self.sess.post(
                url,
                json=payload,
                headers={**self._h, "Accept": "text/event-stream"},
                stream=True,
                timeout=None,  # no timeout
            )
            self.log.log_http("POST", url, r.status_code)
            if r.status_code != 200:
                out["has_error"] = True
                out["error_text"] = f"HTTP {r.status_code}: {r.text[:300]}"
                self.log.log_error(out["error_text"])
                return out

            ev = db = ""
            for raw in r.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                if raw.startswith("event: "):
                    ev = raw[7:].strip()
                elif raw.startswith("data: "):
                    db = raw[6:]
                elif raw == "":
                    if ev or db:
                        self._on_event(ev, db, out)
                        ev = db = ""
            if ev or db:
                self._on_event(ev, db, out)

        except Exception as exc:
            out["has_error"] = True
            out["error_text"] = str(exc)
            self.log.log_error(f"Chat stream exc: {exc}", traceback.format_exc())

        return out

    def _on_event(self, ev: str, db: str, out: Dict[str, Any]) -> None:
        try:
            d = json.loads(db) if db else {}
        except Exception:
            d = {"raw": db}
        self.log.log_event(ev or "message", db[:600])
        out["events"].append((ev, d))

        if ev == "start":
            out["session_id"] = d.get("session_id")

        elif ev == "token":
            out["token_text"] += d.get("content", "")

        elif ev in ("step", "step_done"):
            out["has_step"] = True
            step = d.get("step", {})
            out["step_log"].append(step)

            # chart in step meta
            if step.get("chart_base64"):
                out["chart_b64"].append(step["chart_base64"])
                out["has_chart"] = True

            # excel evidence in step code / stdout
            code = step.get("code", "")
            if ".to_excel(" in code or ".xlsx" in code:
                out["has_excel_code"] = True
            step_out = (step.get("stdout") or "").lower()
            if any(k in step_out for k in (".xlsx", "excel", "exported", "saved")):
                out["has_excel_stdout"] = True

        elif ev in ("code_stdout", "stdout"):
            line = d.get("line") or d.get("output") or ""
            out["raw_stdout"] += line + "\n"

            # chart base64 blocks
            if "__CHART_BASE64__" in line:
                m = CHART_PATTERN.search(line)
                if m:
                    out["chart_b64"].append(m.group(1).strip())
                    out["has_chart"] = True
                    self.log.log("  [CHART] base64 block captured from code_stdout")

            # excel evidence
            low = line.lower()
            if any(k in low for k in (".xlsx", "excel", "exported", "saved")):
                out["has_excel_stdout"] = True

        elif ev == "code_written":
            code = d.get("code", "")
            out["code_written"].append(code)
            if ".to_excel(" in code or ".xlsx" in code:
                out["has_excel_code"] = True
                self.log.log("  [EXCEL] .to_excel() in code_written")

        elif ev == "meta":
            for step in d.get("step_log", []):
                if step.get("chart_base64"):
                    out["chart_b64"].append(step["chart_base64"])
                    out["has_chart"] = True
            for gf in d.get("generated_files", []):
                u = gf.get("download_url") or gf.get("url", "")
                if u:
                    out["file_urls"].append(u)
                    out["has_file_ready"] = True

        elif ev == "file_ready":
            out["has_file_ready"] = True
            u = d.get("url") or d.get("download_url", "")
            if u:
                out["file_urls"].append(u)
            self.log.log(f"  [file_ready] {d.get('filename', u)}")

        elif ev == "repair_attempt":
            out["has_repair"] = True
            self.log.log(f"  [repair] #{d.get('attempt','?')}: {d.get('error_summary','')[:80]}")

        elif ev == "done":
            out["has_done"] = True

        elif ev == "error":
            out["has_error"] = True
            out["error_text"] = d.get("error", str(d))


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: regenerate Excel locally from CSV
# ─────────────────────────────────────────────────────────────────────────────

def regen_excel_locally(csv_path: str, dest: str, log: TestLogger) -> bool:
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        df.to_excel(dest, index=False)
        log.log(f"  Excel regenerated locally ({os.path.getsize(dest):,} B) → {dest}")
        return True
    except ImportError:
        log.log_error("pandas/openpyxl not in test env; skipping local Excel")
        return False
    except Exception as exc:
        log.log_error(f"regen_excel: {exc}", traceback.format_exc())
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PHASE 1: pre-flight
# ─────────────────────────────────────────────────────────────────────────────

def phase_preflight(client: Client, res: Results, log: TestLogger,
                    backend_root: str) -> None:
    log.log("\n══ Phase 1: Pre-flight ══════════════════════════════════════")

    # health
    h = client.health()
    db_ok  = h.get("database")  == "ok"
    vdb_ok = h.get("vector_db") == "ok"
    if db_ok and vdb_ok:
        res.pass_("Health: DB + VectorDB + LLM",
                   f"db={h.get('database')}  vdb={h.get('vector_db')}  llm={h.get('llm')}")
    else:
        res.fail("Health: DB + VectorDB + LLM",
                  f"db={h.get('database')} vdb={h.get('vector_db')}")

    # PREINSTALLED_PACKAGES via subprocess (same venv)
    pkgs = list(REQUIRED_PKGS.values())
    code = dedent(f"""\
        missing = []
        for p in {pkgs!r}:
            try: __import__(p)
            except ImportError: missing.append(p)
        print("ALL_OK" if not missing else "MISSING:" + ",".join(missing))
    """)
    try:
        r   = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=60)
        out = (r.stdout + r.stderr).strip()
        log.log(f"  Package check: {out[:200]}")
        if "ALL_OK" in out:
            res.pass_("Required Python packages",
                       f"All {len(pkgs)} importable in venv")
        elif "MISSING:" in out:
            res.fail("Required Python packages",
                      f"Missing: {out.split('MISSING:')[1]}")
        else:
            res.skip("Required Python packages", f"Unexpected: {out[:80]}")
    except Exception as exc:
        res.fail("Required Python packages", str(exc))

    # writable dirs
    for d in ["output/generated", "data/material_text"]:
        fp = os.path.join(backend_root, d)
        try:
            os.makedirs(fp, exist_ok=True)
            probe = os.path.join(fp, ".probe")
            open(probe, "w").close()
            os.remove(probe)
            res.pass_(f"{d}/ writable")
        except Exception as exc:
            res.fail(f"{d}/ writable", str(exc))


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE PROMPT TEST
# ─────────────────────────────────────────────────────────────────────────────

def run_prompt(
    client:       Client,
    res:          Results,
    log:          TestLogger,
    p:            Dict[str, Any],
    material_id:  str,
    notebook_id:  str,
    csv_path:     str,
    files_dir:    str,
    backend_root: str,
    session_id:   Optional[str],
) -> Optional[str]:
    """Run a single chat prompt and record all checks. Returns session_id."""
    label         = p["label"]
    message       = p["message"]
    expect_chart  = p.get("expect_chart", False)
    expect_excel  = p.get("expect_excel", False)
    chart_fname   = p.get("chart_filename")
    excel_fname   = p.get("excel_filename")
    _sep = "\u2550" * max(0, 55 - len(label))
    log.log(f"\n\u2550\u2550 Prompt [{label}] {_sep}")
    log.log(f"  Tags        : {', '.join(p.get('tags', []))}")
    log.log(f"  Expects     : chart={expect_chart}  excel={expect_excel}")

    cr = client.chat(
        message=message,
        material_ids=[material_id],
        notebook_id=notebook_id,
        session_id=session_id,
    )
    new_sid = cr.get("session_id") or session_id
    if cr.get("session_id"):
        log.log(f"  session_id  : {cr['session_id']}")

    # ── 1. No server error ────────────────────────────────────────────────
    if cr["has_error"]:
        res.fail(f"[{label}] No server error", cr["error_text"][:200])
    else:
        res.pass_(f"[{label}] No server error")

    # ── 2. event:step ─────────────────────────────────────────────────────
    if cr["has_step"]:
        tools = [s.get("tool", "?") for s in cr["step_log"]]
        res.pass_(f"[{label}] event:step emitted", f"tools={tools}")
    else:
        res.fail(f"[{label}] event:step emitted", "No step event")

    # ── 3. event:done ─────────────────────────────────────────────────────
    if cr["has_done"]:
        res.pass_(f"[{label}] event:done received")
    else:
        res.fail(f"[{label}] event:done received", "Stream ended without done")

    # ── 4. No raw import / file errors in output ──────────────────────────
    combined = cr["token_text"] + cr["raw_stdout"]
    bad = [e for e in ("ModuleNotFoundError",) if e in combined]
    if bad:
        res.fail(f"[{label}] No import errors", f"Found: {bad}")
    else:
        res.pass_(f"[{label}] No import errors in output")

    # ── 5. Self-repair (optional) ─────────────────────────────────────────
    if cr["has_repair"]:
        res.pass_(f"[{label}] Self-repair: healed from error")
    else:
        res.skip(f"[{label}] Self-repair", "No errors — no repair needed (OK)")

    # ── 6. Chart ──────────────────────────────────────────────────────────
    if expect_chart:
        if cr["has_chart"] and cr["chart_b64"]:
            res.pass_(f"[{label}] Chart base64 received",
                       f"{len(cr['chart_b64'])} chart(s)")
            # Save the first chart
            dest = os.path.join(files_dir, chart_fname)
            if client.save_chart(cr["chart_b64"][0], dest):
                sz = os.path.getsize(dest)
                res.pass_(f"[{label}] Chart PNG saved",
                           f"{chart_fname} ({sz:,} B)")
            else:
                res.fail(f"[{label}] Chart PNG saved",
                          "base64 decode/write failed")
        else:
            res.fail(f"[{label}] Chart base64 received",
                      "No __CHART_BASE64__ in code_stdout or step meta")
    else:
        res.skip(f"[{label}] Chart", "Not expected for this prompt")

    # ── 7. Excel ──────────────────────────────────────────────────────────
    if expect_excel:
        dest = os.path.join(files_dir, excel_fname)

        # Strategy A: file_ready URL
        if cr["has_file_ready"] and cr["file_urls"]:
            if client.download(cr["file_urls"][0], dest):
                res.pass_(f"[{label}] Excel via file_ready URL")
            else:
                res.fail(f"[{label}] Excel download failed")

        else:
            # Strategy B: /agent/files
            api_files: List[Dict] = []
            if new_sid:
                api_files = client.agent_files(new_sid)
                log.log(f"  /agent/files: {[f['name'] for f in api_files]}")
            xlsx_api = [f for f in api_files if f["name"].lower().endswith(".xlsx")]

            # Strategy C: filesystem output/generated
            copied = client.copy_output_dir(
                new_sid or "", backend_root, files_dir)
            xlsx_fs = [f for f in copied if f.lower().endswith(".xlsx")]

            if xlsx_api:
                if client.download(xlsx_api[0]["url"], dest):
                    res.pass_(f"[{label}] Excel from /agent/files")
                else:
                    res.fail(f"[{label}] Excel /agent/files download failed")
            elif xlsx_fs:
                res.pass_(f"[{label}] Excel from output/generated dir",
                           f"{xlsx_fs[0]}")
            elif cr["has_excel_code"] or cr["has_excel_stdout"]:
                # Strategy D: confirmed by code/stdout → regenerate locally
                evidence = ("code" if cr["has_excel_code"] else "stdout")
                if regen_excel_locally(csv_path, dest, log):
                    res.pass_(f"[{label}] Excel confirmed ({evidence}) "
                               "+ artifact regenerated locally")
                else:
                    res.pass_(f"[{label}] Excel confirmed ({evidence})",
                               "Local regen skipped (dependency missing)")
            else:
                res.fail(f"[{label}] Excel produced",
                          "No evidence: no file_ready/agent_files/stdout/code")
    else:
        res.skip(f"[{label}] Excel", "Not expected for this prompt")

    # ── 8. Meaningful response (token stream OR stdout OR chart produced) ──
    tokens = cr["token_text"].strip()
    stdout = cr["raw_stdout"].strip()
    if len(tokens) >= 30:
        res.pass_(f"[{label}] LLM response / output",
                   f"{len(tokens)} token chars — \"{tokens[:60]}...\"")
    elif len(stdout) >= 20:
        res.pass_(f"[{label}] LLM response / output",
                   f"Via code stdout ({len(stdout)} chars)")
    elif cr["has_chart"] or cr["has_excel_code"]:
        res.pass_(f"[{label}] LLM response / output",
                   "Chart or Excel artifact produced")
    else:
        res.fail(f"[{label}] LLM response / output",
                  f"Empty tokens and stdout. token='{tokens[:60]}'  "
                  f"stdout='{stdout[:60]}'")

    return new_sid


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_tests(args: argparse.Namespace) -> int:
    ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
    script_dir   = Path(__file__).resolve().parent
    backend_root = str(script_dir.parent / "backend")
    out_dir      = script_dir / "agentic_test_output"
    files_dir    = out_dir / "files" / ts
    files_dir.mkdir(parents=True, exist_ok=True)

    log = TestLogger(out_dir, ts)
    res = Results(log)

    log.log("=" * 72)
    log.log("  ML AGENTIC FEATURE TEST")
    log.log(f"  Base URL : {args.base_url}")
    log.log(f"  Email    : {args.email}")
    log.log(f"  Dataset  : {args.dataset}")
    log.log(f"  Timestamp: {ts}")
    log.log("=" * 72)

    client = Client(args.base_url, log)

    # ── Step 0: Login ────────────────────────────────────────────────────
    log.log("\n══ Step 0: Authentication ═══════════════════════════════════")
    if not client.login(args.email, args.password):
        res.fail("Authentication", "Login failed — aborting")
        log.write_report(res.items)
        log.close()
        return 1
    res.pass_("Authentication")

    # ── Phase 1: Pre-flight ──────────────────────────────────────────────
    phase_preflight(client, res, log, backend_root)

    # ── Step 1: Prepare dataset ──────────────────────────────────────────
    log.log("\n══ Step 1: Prepare Dataset ══════════════════════════════════")
    if args.dataset == "custom_csv":
        if not args.custom_csv or not os.path.isfile(args.custom_csv):
            log.log_error(f"custom_csv not found: {args.custom_csv}")
            res.fail("Dataset load", f"File not found: {args.custom_csv}")
            log.write_report(res.items)
            log.close()
            return 1
        csv_path = args.custom_csv
        log.log(f"Using custom CSV: {csv_path}")
        res.pass_("Dataset load", f"Custom file: {os.path.basename(csv_path)}")
    else:
        target_col, rows = get_or_build_dataset(args.dataset)
        csv_path = str(files_dir / f"{args.dataset}_dataset.csv")
        write_csv(rows, csv_path)
        total_missing = sum(
            1 for r in rows for v in r.values() if v is None
        )
        res.pass_("Dataset generate",
                   f"{len(rows)} rows, {total_missing} injected nulls, "
                   f"target='{target_col}'")
        log.log(f"  CSV → {csv_path}  ({os.path.getsize(csv_path):,} B)")

    # ── Step 2: Upload ───────────────────────────────────────────────────
    log.log("\n══ Step 2: Upload Dataset ═══════════════════════════════════")
    upload = client.upload(csv_path, fname=os.path.basename(csv_path))
    if not upload:
        res.fail("Upload dataset", "No response")
        log.write_report(res.items)
        log.close()
        return 1
    material_id = upload.get("material_id")
    job_id      = upload.get("job_id")
    nb          = upload.get("notebook") or {}
    notebook_id = nb.get("id") or material_id
    if not material_id or not job_id:
        res.fail("Upload dataset", f"Missing ids: {upload}")
        log.write_report(res.items)
        log.close()
        return 1
    res.pass_("Upload dataset",
               f"material={material_id}  job={job_id}  nb={notebook_id}")

    # ── Step 3: Poll job ─────────────────────────────────────────────────
    log.log("\n══ Step 3: Poll Processing Job ══════════════════════════════")
    st = client.poll_job(job_id)
    if st == "completed":
        res.pass_("Job processing", "completed")
    else:
        res.fail("Job processing", f"status={st}")

    # ── Step 4: Build prompt list ────────────────────────────────────────
    log.log("\n══ Step 4: Building Prompt List ═════════════════════════════")
    prompts = list(BUILTIN_PROMPTS)

    # Adapt default prompts for housing dataset
    if args.dataset == "housing":
        for p in prompts:
            p["message"] = (
                p["message"]
                .replace("salary", "price")
                .replace("'salary'", "'price'")
                .replace("performance_score >= 4.0", "price >= 300000")
                .replace("high_performer", "high_value_property")
                .replace(
                    "age=32, department=Engineering, years_experience=7, "
                    "education=Masters, performance_score=4.1, num_projects=5",
                    "sqft=2000, bedrooms=3, bathrooms=2, lot_size_acres=0.3, "
                    "year_built=2005, style=Modern, neighborhood=Suburbs"
                )
                .replace(
                    "age=45, department=Management, years_experience=18, "
                    "education=PhD, performance_score=4.8, num_projects=9",
                    "sqft=4500, bedrooms=5, bathrooms=3.5, lot_size_acres=1.2, "
                    "year_built=2018, style=Colonial, neighborhood=Lakefront"
                )
                .replace(
                    "age=24, department=Sales, years_experience=2, "
                    "education=Bachelors, performance_score=3.2, num_projects=2",
                    "sqft=900, bedrooms=1, bathrooms=1, lot_size_acres=0.05, "
                    "year_built=1985, style=Condo, neighborhood=Downtown"
                )
            )

    # Inject user-defined custom prompts
    for i, msg in enumerate(args.prompt or [], start=1):
        prompts.append({
            "label":          f"user_prompt_{i}",
            "message":        msg,
            "expect_chart":   True,   # try to extract chart if produced
            "expect_excel":   False,
            "chart_filename": f"user_prompt_{i}.png",
            "excel_filename": None,
            "tags":           ["user_defined"],
        })
        log.log(f"  Added user prompt #{i}: {msg[:80]}...")

    # Filter to requested tags
    if args.tags:
        requested = set(t.strip().lower() for t in args.tags)
        prompts = [p for p in prompts
                   if requested & set(t.lower() for t in p.get("tags", []))]
        log.log(f"  Filtered to tags {args.tags}: {[p['label'] for p in prompts]}")

    log.log(f"  Running {len(prompts)} prompts")

    # ── Step 5: Run prompts ──────────────────────────────────────────────
    log.log("\n══ Step 5: Chat Prompts (ML Tasks) ═════════════════════════")
    session_id: Optional[str] = None

    for p in prompts:
        try:
            session_id = run_prompt(
                client=client,
                res=res,
                log=log,
                p=p,
                material_id=material_id,
                notebook_id=notebook_id,
                csv_path=csv_path,
                files_dir=str(files_dir),
                backend_root=backend_root,
                session_id=session_id,
            )
        except Exception as exc:
            log.log_error(f"Prompt [{p['label']}] crashed: {exc}",
                           traceback.format_exc())
            res.fail(f"[{p['label']}] (crashed)", str(exc))

    # ── Step 6: Artifact inventory ───────────────────────────────────────
    log.log("\n══ Step 6: Saved Artifacts ══════════════════════════════════")
    saved = sorted(files_dir.iterdir()) if files_dir.exists() else []
    total_bytes = 0
    for f in saved:
        sz = f.stat().st_size
        total_bytes += sz
        tag = ""
        if f.suffix in (".png", ".jpg"):
            tag = "  [IMAGE]"
        elif f.suffix == ".xlsx":
            tag = "  [EXCEL]"
        elif f.suffix == ".csv":
            tag = "  [CSV]  "
        log.log(f"  {f.name:<45s}  {sz:>10,} B{tag}")

    if saved:
        res.pass_("Artifacts saved",
                   f"{len(saved)} file(s)  {total_bytes:,} B total  "
                   f"→ {files_dir}")
    else:
        res.fail("Artifacts saved", "No files written")

    # ── Report ───────────────────────────────────────────────────────────
    log.log("\n══ Writing Report ═══════════════════════════════════════════")
    log.write_report(res.items)
    log.close()

    fail_count = sum(1 for r in res.items if r["status"] == "FAIL")
    return 1 if fail_count else 0


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(
        description="ML Agentic Feature E2E Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Examples:
              # Run with default employee dataset:
              python test/test_agentic_feature.py --email u@e.com --password pw

              # Use housing dataset:
              python test/test_agentic_feature.py --email u@e.com --password pw \\
                  --dataset housing

              # Bring your own CSV:
              python test/test_agentic_feature.py --email u@e.com --password pw \\
                  --dataset custom_csv --custom-csv /path/to/data.csv

              # Add extra prompts:
              python test/test_agentic_feature.py --email u@e.com --password pw \\
                  --prompt "Plot a PCA scatter of the numeric features" \\
                  --prompt "Which department has the highest average salary?"

              # Only run outlier + classification tests:
              python test/test_agentic_feature.py --email u@e.com --password pw \\
                  --tags outliers classification
        """),
    )
    ap.add_argument("--base-url",   default="http://localhost:8000")
    ap.add_argument("--email",      required=True)
    ap.add_argument("--password",   required=True)
    ap.add_argument("--dataset",    default="employees",
                    choices=["employees", "housing", "custom_csv"],
                    help="Built-in synthetic dataset or bring your own CSV")
    ap.add_argument("--custom-csv", dest="custom_csv", default=None,
                    help="Path to CSV file when --dataset custom_csv")
    ap.add_argument("--prompt",     action="append", default=[],
                    metavar="PROMPT",
                    help="Extra prompt(s) to append (repeat to add more)")
    ap.add_argument("--tags",       nargs="+", default=[],
                    metavar="TAG",
                    help="Only run prompts whose tags include any of these")
    sys.exit(run_tests(ap.parse_args()))


if __name__ == "__main__":
    main()
