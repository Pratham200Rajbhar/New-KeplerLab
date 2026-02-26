"""Tool registry — wraps existing services as agent-callable tools.

Contract
--------
Every handler MUST return a ToolResult with:
    success  : bool  – True if the tool produced usable output
    output   : str   – human-readable response (never None)
    metadata : dict  – any structured data the frontend / downstream needs
    tool_name: str   – identifier (must match registry name)
    tokens_used: int – rough estimate for budget tracking

Registered tools
-----------------
    rag_tool          → QUESTION
    quiz_tool         → CONTENT_GENERATION
    flashcard_tool    → CONTENT_GENERATION
    ppt_tool          → CONTENT_GENERATION
    python_tool       → DATA_ANALYSIS, CODE_EXECUTION
    research_tool     → RESEARCH
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List

from app.core.config import settings
from app.services.agent.state import ToolResult

logger = logging.getLogger(__name__)


# ── Tool Registry ─────────────────────────────────────────────

_TOOLS: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    handler: Callable[..., Coroutine[Any, Any, ToolResult]],
    intents: List[str],
):
    """Register a tool in the registry."""
    _TOOLS[name] = {
        "name": name,
        "description": description,
        "handler": handler,
        "intents": intents,
    }
    logger.info(f"Registered tool: {name}")


def get_tool(name: str) -> Dict[str, Any] | None:
    """Get a tool by name."""
    return _TOOLS.get(name)


def get_tools_for_intent(intent: str) -> List[Dict[str, Any]]:
    """Get all tools that handle a given intent."""
    return [t for t in _TOOLS.values() if intent in t["intents"]]


def list_tools() -> List[str]:
    """Return list of registered tool names."""
    return list(_TOOLS.keys())


# ── Built-in Tool Implementations ─────────────────────────────


async def rag_tool(
    user_id: str,
    query: str,
    material_ids: List[str],
    notebook_id: str,
    session_id: str,
    **kwargs,
) -> ToolResult:
    """RAG retrieval + LLM answer — wraps the secure retriever and chat service."""
    t0 = time.time()
    logger.info(
        "[rag_tool] START | user=%s | materials=%s | query=%r",
        user_id, material_ids, query[:80],
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        from app.services.chat.service import generate_rag_response

        # secure_similarity_search_enhanced is synchronous — offload to thread pool
        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query=query,
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        if not context or context.strip() == "No relevant context found.":
            logger.warning("[rag_tool] No context retrieved for query=%r", query[:80])
            return ToolResult(
                tool_name="rag_tool",
                success=False,
                output="I couldn't find relevant information in your materials for that question.",
                metadata={"context_length": 0},
                error="No relevant context found",
                tokens_used=0,
            )

        answer: str = await generate_rag_response(
            notebook_id=notebook_id,
            user_id=user_id,
            context=context,
            user_message=query,
            session_id=session_id,
        )
        elapsed = time.time() - t0
        logger.info(
            "[rag_tool] OK | elapsed=%.2fs | answer_len=%d | context_len=%d",
            elapsed, len(answer), len(context),
        )
        return ToolResult(
            tool_name="rag_tool",
            success=True,
            output=answer,
            metadata={"context_length": len(context)},
            tokens_used=len(answer.split()) * 2,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[rag_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="rag_tool",
            success=False,
            output="An error occurred while searching your materials.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def quiz_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    **kwargs,
) -> ToolResult:
    """Quiz generation — retrieves context then generates structured quiz questions."""
    t0 = time.time()
    logger.info(
        "[quiz_tool] START | user=%s | materials=%s", user_id, material_ids
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        # Correct import: module is quiz.generator, NOT quiz.service
        from app.services.quiz.generator import generate_quiz

        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query="Generate comprehensive quiz questions covering the key concepts",
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        # generate_quiz is synchronous — offload to thread pool
        result: dict = await asyncio.to_thread(generate_quiz, context)

        questions = result.get("questions", [])
        title = result.get("title", "Quiz")
        elapsed = time.time() - t0
        logger.info(
            "[quiz_tool] OK | elapsed=%.2fs | questions=%d",
            elapsed, len(questions),
        )
        return ToolResult(
            tool_name="quiz_tool",
            success=True,
            output=f"Generated **{title}** with {len(questions)} question(s) from your materials.",
            metadata=result,
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[quiz_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="quiz_tool",
            success=False,
            output="Quiz generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def flashcard_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    **kwargs,
) -> ToolResult:
    """Flashcard generation — retrieves context then generates study flashcards."""
    t0 = time.time()
    logger.info(
        "[flashcard_tool] START | user=%s | materials=%s", user_id, material_ids
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        # Correct import: module is flashcard.generator, NOT flashcard.service
        from app.services.flashcard.generator import generate_flashcards

        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query="Generate comprehensive flashcards covering the key concepts and definitions",
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        # generate_flashcards is synchronous — offload to thread pool
        result: dict = await asyncio.to_thread(generate_flashcards, context)

        cards = result.get("flashcards", [])
        title = result.get("title", "Flashcards")
        elapsed = time.time() - t0
        logger.info(
            "[flashcard_tool] OK | elapsed=%.2fs | cards=%d",
            elapsed, len(cards),
        )
        return ToolResult(
            tool_name="flashcard_tool",
            success=True,
            output=f"Generated **{title}** with {len(cards)} flashcard(s) from your materials.",
            metadata=result,
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[flashcard_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="flashcard_tool",
            success=False,
            output="Flashcard generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def ppt_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    topic: str = "",
    **kwargs,
) -> ToolResult:
    """Presentation generation — directs the user to the Studio panel.

    Full PPT generation is a multi-step flow that requires the frontend Studio
    UI.  This tool acknowledges the request and signals the frontend to open
    the Studio panel.
    """
    logger.info(
        "[ppt_tool] START | user=%s | materials=%s | topic=%r",
        user_id, material_ids, topic,
    )
    try:
        message = (
            "Presentation generation has been initiated. "
            "Please use the **Studio** panel to configure and generate your presentation."
        )
        logger.info("[ppt_tool] OK | redirected to Studio")
        return ToolResult(
            tool_name="ppt_tool",
            success=True,
            output=message,
            metadata={"action": "open_studio", "topic": topic},
            tokens_used=0,
        )
    except Exception as exc:
        logger.error("[ppt_tool] FAILED | error=%s", exc)
        return ToolResult(
            tool_name="ppt_tool",
            success=False,
            output="Presentation generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def python_tool(
    query: str,
    session_id: str = "",
    user_id: str = "",
    notebook_id: str = "",
    material_ids: List[str] = None,
    intent: str = "",
    **kwargs,
) -> ToolResult:
    """Python code generation + execution in a sandboxed subprocess.

    Uses generate_and_execute() which:
      1. Prompts the LLM to write Python targeting the user request
      2. Validates the code against security rules
      3. Runs it in an isolated subprocess with a timeout
    """
    t0 = time.time()
    logger.info("[python_tool] START | query=%r", query[:80])
    try:
        from app.services.code_execution.executor import generate_and_execute
        from app.services.material_service import get_material_for_user, get_material_text
        import json
        from app.services.llm_service.llm import get_llm

        # Emit code_generating event so the frontend shows "Generating code…"
        try:
            from langchain_core.callbacks import adispatch_custom_event
            await adispatch_custom_event("code_generating", {"tool": "python_tool", "status": "generating"})
        except Exception:
            pass

        # ── Incorporate previous RAG context if tool chaining (DATA_ANALYSIS) ──
        previous_context = kwargs.get("previous_context", "")

        csv_files = []
        parquet_files: list[dict[str, str]] = []  # {"name": "sales.parquet", "path": "/abs/path.parquet"}

        if material_ids and user_id:
            for m_id in material_ids:
                material = await get_material_for_user(m_id, user_id)
                if not material:
                    continue
                fname = getattr(material, "filename", "") or ""
                fname_lower = fname.lower()

                # Parse stored extraction metadata for parquet side-car paths
                meta_raw = getattr(material, "metadata", None)
                meta: dict = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    except (json.JSONDecodeError, TypeError):
                        pass

                import os
                # Excel: structured_data_paths is {sheet_name: path}
                sdp = meta.get("structured_data_paths")
                if sdp and isinstance(sdp, dict):
                    for sheet_name, ppath in sdp.items():
                        if ppath and os.path.isfile(ppath):
                            safe = fname.rsplit(".", 1)[0] if "." in fname else fname
                            display = f"{safe}_{sheet_name}.parquet"
                            parquet_files.append({"name": display, "path": ppath})
                    continue

                # CSV: structured_data_path is a string
                sdp_single = meta.get("structured_data_path")
                if sdp_single and isinstance(sdp_single, str) and os.path.isfile(sdp_single):
                    display = fname.rsplit(".", 1)[0] + ".parquet" if "." in fname else fname + ".parquet"
                    parquet_files.append({"name": display, "path": sdp_single})
                    continue

                # Legacy fallback: pass raw CSV text for files without parquet
                if fname_lower.endswith(".csv"):
                    text = await get_material_text(m_id, user_id)
                    if text:
                        csv_files.append({"filename": fname, "content": text})

        async def on_stdout(line: str):
            try:
                from langchain_core.callbacks import adispatch_custom_event
                await adispatch_custom_event("code_stdout", {"line": line})
            except ImportError:
                # Fallback if langchain_core is older or not configured for custom events
                pass

        # ── Pre-validate data files before executing ────────────────
        validated_parquet = []
        for pf in parquet_files:
            try:
                import pandas as _pd
                _pd.read_parquet(pf["path"], columns=None).head(0)  # schema-only read
                validated_parquet.append(pf)
            except Exception as val_err:
                logger.warning("[python_tool] Skipping unreadable parquet %s: %s", pf["name"], val_err)

        validated_csv = []
        for cf in csv_files:
            try:
                import io as _io, pandas as _pd
                _pd.read_csv(_io.StringIO(cf["content"]), nrows=0)
                validated_csv.append(cf)
            except Exception as val_err:
                logger.warning("[python_tool] Skipping unreadable CSV %s: %s", cf["filename"], val_err)

        if not validated_parquet and not validated_csv and material_ids:
            return ToolResult(
                tool_name="python_tool",
                success=False,
                output="No readable data files found for the selected materials. "
                       "Ensure the files are valid CSV or Excel format.",
                metadata={},
                error="data_validation_failed",
                tokens_used=0,
            )

        # Callback for when code generation is complete — emit the generated code immediately
        async def on_code_generated(code: str):
            try:
                from langchain_core.callbacks import adispatch_custom_event
                await adispatch_custom_event("code_generated", {"code": code})
            except Exception:
                pass

        result = await generate_and_execute(
            user_query=query,
            csv_files=validated_csv,
            parquet_files=validated_parquet,
            timeout=15,
            on_stdout_line=on_stdout,
            additional_context=previous_context,
            on_code_generated=on_code_generated,
        )

        elapsed = time.time() - t0
        success: bool = result.get("success", False)

        if intent == "DATA_ANALYSIS":
            explanation = ""
            if success:
                llm = get_llm(mode="chat")  # factual explanation
                prompt = (
                    "Analyze this output and provide a well-structured, professional summary of the findings.\n\n"
                    "Format your response in clean Markdown with:\n"
                    "- A bold **Executive Summary** opening line (1-2 sentences)\n"
                    "- **Key Findings** as a bullet list with bold labels for each point\n"
                    "- A brief **Strategic Implications** paragraph at the end\n\n"
                    "Use line breaks between sections for readability. Keep it concise but insightful.\n\n"
                    f"Query: {query}\n\nOutput:\n{result.get('stdout', '')}"
                )
                try:
                    resp = await llm.ainvoke(prompt)
                    explanation = getattr(resp, "content", str(resp)).strip()
                except Exception as e:
                    logger.warning(f"Failed to generate explanation: {e}")
                    explanation = "Analysis completed successfully."
            else:
                explanation = "Execution failed. Please check the error details."

            output_data = {
                "stdout": result.get("stdout", "") if success else result.get("stderr", result.get("error", "Unknown error")),
                "exit_code": result.get("exit_code", -1),
                "base64_chart": result.get("chart_base64"),
                "explanation": explanation,
            }
            output = json.dumps(output_data)
        else:
            # Build human-readable answer string
            parts: list[str] = []
            if result.get("generated_code"):
                parts.append(f"```python\n{result['generated_code']}\n```")
            if success:
                if result.get("stdout"):
                    parts.append(f"**Output:**\n```\n{result['stdout'].rstrip()}\n```")
                if result.get("chart_base64"):
                    parts.append("📊 *Chart generated successfully.*")
            else:
                if result.get("violations"):
                    parts.append(
                        "⚠️ **Security violation:**\n"
                        + "\n".join(f"- {v}" for v in result["violations"])
                    )
                elif result.get("stderr"):
                    parts.append(f"**Error:**\n```\n{result['stderr'].rstrip()}\n```")
                elif result.get("error"):
                    parts.append(f"**Error:** {result['error']}")

            output = "\n\n".join(parts) if parts else "Code execution completed with no output."

        logger.info(
            "[python_tool] %s | elapsed=%.2fs | exit_code=%s",
            "OK" if success else "FAILED",
            elapsed,
            result.get("exit_code", -1),
        )
        return ToolResult(
            tool_name="python_tool",
            success=success,
            output=output,
            metadata={
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "exit_code": result.get("exit_code", -1),
                "chart_base64": result.get("chart_base64"),
                "elapsed": result.get("elapsed", 0.0),
                "violations": result.get("violations", []),
                "generated_code": result.get("generated_code", ""),
            },
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[python_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="python_tool",
            success=False,
            output="Python execution failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def research_tool(
    query: str,
    user_id: str = "",
    notebook_id: str = "",
    material_ids: list = None,
    **kwargs,
) -> ToolResult:
    """Deep research — multi-source web research with structured report."""
    t0 = time.time()
    logger.info("[research_tool] START | user=%s | query=%r", user_id, query[:80])
    try:
        from app.services.agent.subgraphs.research_graph import run_research

        result = await run_research(
            user_query=query,
            user_id=user_id,
            notebook_id=notebook_id,
            material_ids=material_ids,
        )

        elapsed = time.time() - t0

        if result.startswith('{"executive_summary": "Failed'):
            # It's our graceful failure JSON
            logger.warning("[research_tool] Graceful failure structure returned")

        # result is now a JSON string containing the final report


        report_json: str = result
        logger.info(
            "[research_tool] OK | elapsed=%.2fs | report_len=%d",
            elapsed, len(report_json),
        )
        return ToolResult(
            tool_name="research_tool",
            success=True,
            output=report_json,
            metadata={
                "intent": "RESEARCH"
            },
            tokens_used=2000,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[research_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="research_tool",
            success=False,
            output="Research execution failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


# ── Register All Tools ────────────────────────────────────────


def initialize_tools():
    """Register all built-in tools. Called once at startup."""
    register_tool(
        name="rag_tool",
        description="Answer questions using retrieved context from uploaded materials (PDFs, documents, etc.)",
        handler=rag_tool,
        intents=["QUESTION"],
    )

    register_tool(
        name="quiz_tool",
        description="Generate quiz questions from uploaded materials",
        handler=quiz_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="flashcard_tool",
        description="Generate flashcards from uploaded materials",
        handler=flashcard_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="ppt_tool",
        description="Generate presentations/slides from uploaded materials",
        handler=ppt_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="python_tool",
        description="Generate and execute Python code for data analysis, calculations, and visualizations",
        handler=python_tool,
        intents=["DATA_ANALYSIS", "CODE_EXECUTION"],
    )

    register_tool(
        name="research_tool",
        description="Conduct deep multi-source web research and generate a structured report with citations",
        handler=research_tool,
        intents=["RESEARCH"],
    )

    logger.info(f"Initialized {len(_TOOLS)} tools: {list_tools()}")


# Lazy initialization — called on first graph build, NOT on module import.
_tools_initialized = False


def ensure_tools_initialized():
    """Initialize tools once, on first call.  Safe to call multiple times."""
    global _tools_initialized
    if not _tools_initialized:
        initialize_tools()
        _tools_initialized = True

