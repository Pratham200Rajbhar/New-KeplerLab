## Project Context
This is a full-stack AI-powered study assistant called **KeplerLab AI Notebook**.
- Backend: FastAPI (Python 3.11), LangGraph, PostgreSQL + Prisma, ChromaDB
- Frontend: React 19, Vite, TailwindCSS
- Agent lives in: `backend/app/services/agent/`
- Code sandbox lives in: `backend/app/services/code_execution/`
- Routes live in: `backend/app/routes/`
- Frontend chat lives in: `frontend/src/components/ChatPanel.jsx` and `ChatMessage.jsx`

## Goal
Upgrade the agentic system to work like Claude / ChatGPT Advanced Data Analysis:
- Step-by-step streaming (not all at once)
- Self-healing code execution (read error → fix → re-run)
- Universal file generation (Word, Excel, CSV, PDF, charts, diagrams)
- AI knows its full environment (real file paths, installed packages)
- Clean UI — hide internals by default, show on click (like Claude's "Thinking" block)

---

## IMPORTANT RULES FOR THE AI AGENT MAKING THESE CHANGES
1. Do NOT break any existing features (RAG chat, flashcards, quiz, podcast, presentation)
2. Make changes file by file — do not rewrite everything at once
3. Follow the existing code style in each file
4. All new services go inside `backend/app/services/agent/tools/`
5. All new prompts go inside `backend/app/prompts/`
6. All new frontend components go inside `frontend/src/components/chat/`
7. After each file change, check for import errors before moving to next file
8. Never use `plt.show()` in any generated code — backend has no display

---

## PHASE 1 — Backend: Environment & Package Setup

### Task 1.1 — Create `backend/app/services/code_execution/sandbox_env.py`
Create a new file with:
- A list called `PREINSTALLED_PACKAGES` containing:
  `pandas`, `numpy`, `matplotlib`, `seaborn`, `plotly`, `kaleido`,
  `openpyxl`, `xlrd`, `python-docx`, `fpdf2`, `reportlab`,
  `scipy`, `scikit-learn`, `networkx`, `pillow`, `tabulate`, `jinja2`
- An async function `ensure_packages()` that installs any missing package
  using `subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])`
- A dict `PACKAGE_IMPORT_MAP` mapping package name → its import statement
  (e.g. `"matplotlib"` → `"import matplotlib\nmatplotlib.use('Agg')\nimport matplotlib.pyplot as plt"`)

### Task 1.2 — Update `backend/app/main.py`
In the `lifespan` startup sequence, after step 4 (job_processor task),
add step 5: call `ensure_packages()` from `sandbox_env.py`.
Also ensure `output/generated/` directory is created at startup
alongside the existing `output/podcasts/` and `output/presentations/` dirs.

### Task 1.3 — Update `backend/app/core/config.py`
Add these new settings to the Pydantic `BaseSettings` class:
- `GENERATED_OUTPUT_DIR: str = "output/generated"`
- `MAX_CODE_REPAIR_ATTEMPTS: int = 3`
- `CODE_EXECUTION_TIMEOUT: int = 15`

---

## PHASE 2 — Backend: Agent State Expansion

### Task 2.1 — Update `backend/app/services/agent/state.py`
Add these new fields to `AgentState` TypedDict:
- `workspace_files: List[Dict]`
  — list of dicts: `{id, filename, real_path, text_path, ext, type}`
  — populated from uploaded materials before agent runs
- `generated_files: List[Dict]`
  — list of dicts: `{filename, path, download_url, size, type}`
  — files AI created this session
- `last_stdout: str` — stdout from last code execution
- `last_stderr: str` — stderr from last code execution
- `analysis_context: Dict` — dataset shape, columns, dtypes after profiling
- `edit_history: List[Dict]` — log of append/replace/delete ops
- `step_log: List[Dict]` — each step: `{tool, label, status, time_taken, code, stdout, stderr}`
- `repair_attempts: int` — current repair loop counter, default 0
- `code_vars: Dict[str, str]` — variable name → type from last execution

---

## PHASE 3 — Backend: New Agent Tools

### Task 3.1 — Create `backend/app/services/agent/tools/workspace_builder.py`
Create a function `build_workspace_header(state: AgentState) -> str` that:
- Iterates over `state["workspace_files"]`
- For each file, creates a Python variable pointing to the real path:
  - CSV/XLSX: `{varname}_path = "{real_path}"  # load with pd.read_csv()`
  - PDF/DOCX/TXT: `{varname}_text_path = "{text_path}"  # load with open().read()`
- Always includes these standard imports at the top:
  ```python
  import pandas as pd
  import numpy as np
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  import os, json, csv
  OUTPUT_DIR = "output/generated/{user_id}/{session_id}"
  os.makedirs(OUTPUT_DIR, exist_ok=True)
```

- Returns the full header string to be prepended to any generated code


### Task 3.2 — Create `backend/app/services/agent/tools/data_profiler.py`

Create an async function `profile_dataset(state: AgentState) -> AgentState` that:

- Finds the first CSV or XLSX file in `state["workspace_files"]`
- Loads it with pandas in a thread pool executor
- Runs `df.describe()`, `df.dtypes`, `df.shape`, `df.columns.tolist()`
- Stores result in `state["analysis_context"]`
- Returns updated state


### Task 3.3 — Create `backend/app/services/agent/tools/code_repair.py`

Create an async function `repair_code(broken_code: str, stderr: str, llm) -> str` that:

- Builds a focused repair prompt (load from `prompts/code_repair_prompt.txt`)
- Calls `await llm.ainvoke(repair_prompt)` with `temperature=0.0`
- Extracts only the code block from the response (strip markdown fences)
- Returns the fixed code string


### Task 3.4 — Create `backend/app/services/agent/tools/file_generator.py`

Create an async function `generate_file(state: AgentState, stream_cb) -> ToolResult` that:

- Gets the workspace header from `workspace_builder.build_workspace_header(state)`
- Gets the AI-generated code from the current plan step
- Prepends the workspace header to the code
- Runs it through the existing code sandbox executor
- Watches stdout for lines starting with `FILE_SAVED:`
- For each `FILE_SAVED:` line, extracts the path, builds a download URL,
and appends to `state["generated_files"]`
- Calls `stream_cb` with `file_ready` event data
- Returns a `ToolResult` with the file info

---

## PHASE 4 — Backend: New Prompt Files

### Task 4.1 — Create `backend/app/prompts/code_generation_prompt.txt`

Write a prompt with these rules for the LLM:

```
You are an expert Python developer generating code to run in a secure sandbox.

AVAILABLE LIBRARIES:
- pandas, numpy → data manipulation
- matplotlib (Agg backend), seaborn, plotly → charts and graphs  
- python-docx → Word documents (.docx)
- fpdf2 → PDF files (.pdf)
- openpyxl → Excel files (.xlsx)
- csv (stdlib) → CSV files
- networkx → network/graph diagrams
- pillow → image manipulation and editing
- scipy, scikit-learn → statistical analysis

RULES YOU MUST FOLLOW:
1. The variable OUTPUT_DIR is already defined — always save files there
2. For charts: use plt.savefig(f"{OUTPUT_DIR}/chart.png", dpi=150, bbox_inches='tight') then plt.close()
3. For Word docs: doc.save(f"{OUTPUT_DIR}/report.docx")
4. For Excel: wb.save(f"{OUTPUT_DIR}/data.xlsx")
5. For PDF: pdf.output(f"{OUTPUT_DIR}/report.pdf")
6. ALWAYS print the saved path at the end: print(f"FILE_SAVED:{OUTPUT_DIR}/filename.ext")
7. NEVER use plt.show() — there is no display
8. NEVER use input() — there is no terminal input
9. File paths for uploaded data are already defined as variables — use them directly
10. Keep code clean and efficient — no unnecessary loops or redundant operations
```


### Task 4.2 — Create `backend/app/prompts/code_repair_prompt.txt`

Write a focused repair prompt:

```
You are a Python debugger. Your ONLY job is to fix the error below.

=== ORIGINAL CODE ===
{broken_code}

=== ERROR MESSAGE ===
{stderr}

=== INSTRUCTIONS ===
- Return ONLY the corrected Python code
- Do NOT add any explanation or comments
- Do NOT wrap in markdown fences
- Fix ONLY the specific error — do not change anything else
- If the error is a missing import, add it at the top
- If the error is a wrong variable name, fix just that variable

=== FIXED CODE ===
```


### Task 4.3 — Create `backend/app/prompts/data_analysis_prompt.txt`

Write a multi-step analysis prompt that:

- Receives `analysis_context` (columns, dtypes, shape, describe output)
- Receives the user's natural language request
- Tells the LLM to: first decide what analysis is needed, then write code to do it,
then explain the results in plain English after the code runs

---

## PHASE 5 — Backend: Intent, Planner, Router Updates

### Task 5.1 — Update `backend/app/services/agent/intent.py`

Add new intent `FILE_GENERATION` with keyword rules BEFORE `CONTENT_GENERATION`:

- Keywords: `create csv`, `generate word`, `export excel`, `make pdf`,
`write report`, `create spreadsheet`, `generate diagram`, `make chart`,
`draw graph`, `create document`, `export as`, `save as file`
Expand `DATA_ANALYSIS` keywords to include:
- `analyze`, `visualize`, `distribution`, `correlation`, `heatmap`,
`trend`, `compare columns`, `plot`, `statistics`, `outlier`, `scatter`


### Task 5.2 — Update `backend/app/services/agent/planner.py`

- Before building any code-generation plan step, call
`workspace_builder.build_workspace_header(state)` and store it in the plan step
- Add `FILE_GENERATION` plan templates mapping file type to the right library
- Add edit action planning: if user message contains words like "add", "update",
"fix", "modify", "change" AND a file already exists in `generated_files`,
plan an `EditAction` with `op: replace/append/delete` instead of full regeneration
- For `DATA_ANALYSIS` intent, add a multi-step plan:

1. `data_profiler` tool
2. `code_executor` for analysis
3. `generate_response` for explanation


### Task 5.3 — Update `backend/app/services/agent/router.py`

- Add dispatch case for `FILE_GENERATION` → `file_generator` tool
- Add dispatch case for `data_profiler` → `data_profiler.profile_dataset()`
- For EVERY tool dispatch, before calling the tool:
    - Emit SSE event: `{"event": "step", "data": {"label": "...", "tool": "tool_name"}}`
- For EVERY tool dispatch, after the tool completes:
    - Append to `state["step_log"]`: `{tool, label, status, time_taken, stdout, stderr, code}`
    - Emit SSE event: `{"event": "step_done", "data": {"tool": "tool_name", "status": "success/error"}}`
- Do NOT pass stdout to the main response — only to `step_log`


### Task 5.4 — Update `backend/app/services/agent/reflection.py`

Replace the existing retry logic with a self-healing loop:

- Check if last tool was `code_executor` or `file_generator`
- Check if `state["last_stderr"]` is non-empty
- If error AND `state["repair_attempts"] < settings.MAX_CODE_REPAIR_ATTEMPTS`:
    - Call `code_repair.repair_code(broken_code, stderr, llm)`
    - Update the plan step's code with the fixed version
    - Increment `state["repair_attempts"]`
    - Emit SSE event: `{"event": "repair_attempt", "data": {"attempt": N, "error_summary": "..."}}`
    - Return `"retry"` edge
- If repair succeeds (exit_code == 0):
    - Emit SSE event: `{"event": "repair_success", "data": {"attempt": N}}`
    - Reset `state["repair_attempts"]` to 0
- If 3 repairs all fail → return `"respond"` with error explanation to user


### Task 5.5 — Update `backend/app/services/agent/graph.py`

- Remove the all-at-end response buffering in `generate_response` node
- Each tool streams output immediately via `yield` as it completes
- `generate_response` node only: combines tool summaries + writes final answer
- Add `data_profiler` as a new graph node
- Add new graph edge: `repair_attempt` → `tool_router` (the backtrack loop)
- Add new LangGraph conditional edge from `reflection`:
    - `"retry"` → `tool_router`
    - `"respond"` → `generate_response`
    - `"continue"` → `tool_router`

---

## PHASE 6 — Backend: Routes

### Task 6.1 — Update `backend/app/routes/agent.py`

Add these new routes:

**GET `/agent/files`**

- Requires auth (use existing `get_current_user` dependency)
- Accepts query param `session_id`
- Lists all files in `output/generated/{user_id}/{session_id}/`
- Returns: `{"files": [{name, url, size, type, created_at}]}`

**GET `/agent/download/{user_id}/{session_id}/{filename}`**

- Accepts query param `token` (signed file token)
- Verify token using existing `verify_file_token()` (same system used for podcast download)
- Serve the file using FastAPI `FileResponse`
- Set correct `Content-Disposition` header for download

---

## PHASE 7 — Frontend: New Components

### Task 7.1 — Create `frontend/src/components/chat/AgentThinkingBar.jsx`

Create a React component that:

- Props: `{ isActive, currentStep, stepNumber, totalSteps }`
- Shows an animated spinner (CSS, not a library) while `isActive` is true
- Shows the `currentStep` label text (updates in place — no new DOM nodes per step)
- Shows a subtle step counter: `Step {stepNumber} of {totalSteps}` if totalSteps > 1
- Auto-hides (returns null) when `isActive` becomes false
- Use TailwindCSS for styling — dark mode compatible
- Step label examples to style for:
    - 🔍 Searching your materials
    - 🧠 Planning analysis
    - 🐍 Writing Python code
    - ⚙️ Running code
    - ⚠️ Error found, fixing...
    - ✅ Fix applied, re-running
    - 📄 Generating document
    - 📊 Building chart


### Task 7.2 — Create `frontend/src/components/chat/AgentActionBlock.jsx`

Create a collapsible drawer component that:

- Props: `{ stepLog, toolsUsed, totalTime, isStreaming }`
- **Collapsed state (default):** Shows one line:
`▶ Ran {N} steps · {tool1}, {tool2} · {time}s`
- **Expanded state (on click):** Shows each step from `stepLog`:
    - Step number, tool icon, tool name, status (✅/❌), time taken
    - If step has `code`: show it in a syntax-highlighted read-only code block with Copy button
    - If step has `stdout`: show in a monospace scrollable box (max height 200px)
    - If step has `stderr`: show in red-tinted monospace box
    - If step has repair info: show mini diff — red crossed-out error line, green fixed line
- Toggle open/close with smooth CSS transition (not a library)
- While `isStreaming` is true, show a pulsing dot next to the summary line
- Use TailwindCSS — dark mode compatible


### Task 7.3 — Create `frontend/src/components/chat/GeneratedFileCard.jsx`

Create a file card component that:

- Props: `{ filename, downloadUrl, size, fileType }`
- Shows a file type icon (emoji is fine):
    - `.xlsx` → 📊 green border
    - `.docx` → 📝 blue border
    - `.csv` → 🗃️ gray border
    - `.pdf` → 📕 red border
    - `.png`/`.jpg` → 🖼️ purple border
- Shows filename, human-readable size (e.g. "42 KB")
- Download button: clicking it fetches a signed token then triggers browser download
- Preview button: for images/charts, clicking opens existing `Modal.jsx` with the image
- Use TailwindCSS — dark mode compatible

---

## PHASE 8 — Frontend: Update Existing Components

### Task 8.1 — Update `frontend/src/components/ChatMessage.jsx`

- Import `AgentActionBlock` and `GeneratedFileCard`
- If `message.agent_metadata` exists AND `message.step_log` has entries:
→ Render `<AgentActionBlock>` ABOVE the message text
- If `message.generated_files` exists and has entries:
→ Render one `<GeneratedFileCard>` per file BELOW the message text
- REMOVE any direct rendering of raw stdout lines in the message body
- Code blocks in the AI's **explanation text** still render normally via react-markdown
- Code blocks from `step_log` (what AI wrote and ran) only appear inside the drawer


### Task 8.2 — Update `frontend/src/components/ChatPanel.jsx`

Add state variables:

```js
const [thinkingStep, setThinkingStep] = useState('')
const [isThinking, setIsThinking] = useState(false)
const [stepLog, setStepLog] = useState([])
const [currentStepNum, setCurrentStepNum] = useState(0)
```

Update the SSE stream parser to handle these new events:

- `event: step` → `setThinkingStep(data.label)`, increment step counter
- `event: step_done` → append to `stepLog` state
- `event: code_written` → append code to last `stepLog` entry
- `event: stdout` → append to last `stepLog` entry's stdout (NOT to message body)
- `event: repair_attempt` → `setThinkingStep("⚠️ Error found, fixing attempt " + data.attempt)`
- `event: repair_success` → `setThinkingStep("✅ Fix applied, re-running...")`
- `event: file_ready` → append file info to `pendingFiles` state array
- `event: meta` → store tools used + total time for `AgentActionBlock`
- `event: done` → `setIsThinking(false)`, attach `stepLog` + `generated_files` to final message

Render `<AgentThinkingBar>` just above the message input box while `isThinking` is true.
Pass `stepLog` to the final message object so `ChatMessage.jsx` can render the drawer.

---

## PHASE 9 — Frontend: API Layer

### Task 9.1 — Create `frontend/src/api/agent.js`

Add these functions using the existing `apiFetch` from `api/config.js`:

- `listGeneratedFiles(sessionId)` → `GET /agent/files?session_id={sessionId}`
- `getDownloadUrl(userId, sessionId, filename)` → builds the download URL
- `downloadGeneratedFile(userId, sessionId, filename)` → fetches signed token then triggers download via blob URL

---

## FINAL CHECKLIST — Verify These After All Changes

- [ ] Existing RAG chat still works end to end
- [ ] Existing flashcard generation still works
- [ ] Existing quiz generation still works
- [ ] Existing podcast generation still works
- [ ] Existing presentation generation still works
- [ ] New: Asking "create a CSV of top 10 countries by population" generates and offers download
- [ ] New: Asking "analyze this dataset" runs profiler → code → explanation
- [ ] New: If generated code has an error, AI fixes and re-runs automatically (up to 3 times)
- [ ] New: Thinking bar shows live step labels during agent work
- [ ] New: Thinking bar disappears cleanly when agent finishes
- [ ] New: Agent action drawer is collapsed by default on every message
- [ ] New: Clicking drawer shows code, stdout, and any repair attempts
- [ ] New: Generated files show as download cards in chat
- [ ] No raw stdout visible in main chat message body
- [ ] Dark mode works on all new components

```

***
