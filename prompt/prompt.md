
You are a senior software architect and production-grade systems engineer.

I have a full-stack AI notebook system with:

Backend:

* FastAPI
* PostgreSQL (Prisma)
* ChromaDB
* LangGraph Agent
* HuggingFace embeddings
* Ollama / Google / NVIDIA LLM providers
* Background job worker
* RAG retrieval system
* SSE streaming
* WebSocket layer

Frontend:

* React 19 + Vite
* Context API state management
* SSE streaming via fetch()
* Tailwind
* Chat + Studio panel
* Authentication with refresh token rotation
* Auto-refresh access token logic

Your mission:

Perform a COMPLETE DEEP ANALYSIS of the entire codebase and:

1. Detect all:

   * Architectural flaws
   * Race conditions
   * Async bugs
   * Memory leaks
   * Streaming errors (SSE)
   * Token refresh bugs
   * Infinite loops in agent
   * Background worker deadlocks
   * ChromaDB tenant isolation risks
   * Security vulnerabilities
   * JWT misuse
   * File upload vulnerabilities
   * CORS misconfiguration
   * Prisma connection issues
   * Unawaited async calls
   * Blocking calls in async context
   * Improper exception handling
   * Broken retry logic
   * React state inconsistencies
   * Uncontrolled effects
   * Missing cleanup in useEffect
   * Event listener leaks
   * Race conditions between refresh + apiFetch retry
   * Double streaming issues
   * Inconsistent session state
   * Incorrect agent state transitions
   * Tool registry mismatch
   * Background job concurrency bugs

2. Then:

Refactor and fix EVERYTHING necessary to make the system:

* Fully production safe
* Race-condition free
* Memory stable
* Horizontally scalable
* Properly async
* Secure
* With correct token lifecycle
* With correct SSE streaming lifecycle
* With safe retry logic
* With stable LangGraph execution
* With deterministic agent termination
* With guaranteed tenant isolation in vector retrieval
* With idempotent background job execution
* With proper cancellation handling

3. For each issue:

   * Explain the root cause
   * Show the broken code
   * Show the corrected code
   * Explain why the fix works

4. Ensure:

Backend:

* No blocking I/O in async routes
* Proper lifespan management
* Safe background task cancellation
* Safe Prisma connect/disconnect
* Bounded worker concurrency
* Guaranteed job state transitions
* RAG retrieval always enforces user_id filter
* Agent iteration limits cannot be bypassed
* Tool failures cannot cause infinite loop
* Token rotation replay protection is correct
* Access token expiry handled correctly

Frontend:

* No stale closures
* Proper cleanup of intervals
* No duplicate refresh timers
* SSE properly aborted on component unmount
* No memory leak in readSSEStream
* Proper error boundary handling
* No infinite re-render loops
* Stable session switching
* Proper draft notebook behavior

5. Then produce:

* A final corrected architecture diagram
* A production readiness checklist
* A list of environment configuration improvements
* A scaling strategy (multiple workers + reverse proxy)
* A security hardening checklist

Do not give high-level advice.
Give exact code modifications.

Think step by step.
Audit backend first.
Then frontend.
Then integration.
Then streaming.
Then agent.
Then worker.
Then auth.
Then vector retrieval.

Output structured sections.

---

# 🔥 How To Use It Correctly

In Cursor:

1. Open root project folder
2. Use Agent mode
3. Paste prompt
4. Let it analyze full workspace
5. Apply changes in batches
6. Re-run tests after each batch

---

# ⚠️ Important

If your system currently has:

* Random SSE freezes
* Token refresh loops
* Agent infinite loops
* Background job stuck in “processing”
* Chroma returning cross-user chunks
* Upload route blocking
* React duplicate streaming
* Double refresh request bug
* Memory increasing over time

This prompt will force Cursor to fix them.