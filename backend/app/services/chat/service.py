"""In-memory chat session manager with citation validation.

NOTE: Sessions live in process memory and are lost on restart.
For production, consider backing sessions with Redis or the DB.
"""

from __future__ import annotations

import logging
import re
import time
from typing import AsyncIterator, Dict, List

from app.services.llm_service.llm import get_llm
from app.prompts import get_chat_prompt
from app.services.rag.citation_validator import validate_citations
from app.services.rag.context_formatter import build_citation_correction_prompt

logger = logging.getLogger(__name__)

def _count_sources_in_context(context: str) -> int:
    """Count how many [SOURCE N] markers are in the formatted context."""
    pattern = r'\[SOURCE\s+(\d+)\]'
    matches = re.findall(pattern, context)
    if not matches:
        return 0
    # Return the highest source number found
    return max(int(n) for n in matches)


async def generate_rag_response(
    notebook_id: str, user_id: str, context: str, user_message: str, session_id: str = None
) -> str:
    """Generate RAG response using DB history and citation validation."""
    # Count sources
    num_sources = _count_sources_in_context(context)
    
    # Get history from DB
    raw_history = await get_chat_history(notebook_id, user_id, session_id)
    history_lines = []
    for msg in raw_history[-10:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")
    formatted_history = "\n".join(history_lines) if history_lines else "None"
    
    prompt = get_chat_prompt(context, formatted_history, user_message)
    llm = get_llm()
    
    from langchain_core.callbacks import adispatch_custom_event

    full_response = []
    async for chunk in llm.astream(prompt):
        content = getattr(chunk, "content", str(chunk))
        if content:
            full_response.append(content)
            try:
                await adispatch_custom_event("rag_token", {"content": content})
            except Exception:
                pass
            
    answer = "".join(full_response).strip()
    
    # Citation Validation — strip invalid citations from the response
    if num_sources > 0:
        validation = validate_citations(
            response=answer,
            num_sources=num_sources,
            strict=True,
        )
        if not validation["is_valid"]:
            logger.warning(f"RAG response validation failed: {validation['error_message']}")
            # Remove hallucinated source references that cite out-of-range numbers
            import re as _citation_re
            invalid = validation.get("invalid_sources", [])
            if invalid:
                for inv_src in invalid:
                    answer = _citation_re.sub(
                        rf'\[SOURCE\s+{inv_src}\]', '', answer
                    )
                answer = answer.strip()
            
    return answer


# ── Confidence scoring ────────────────────────────────────────


import re as _re


def compute_confidence_score(
    context: str,
    answer: str,
    reranker_scores: List[float] | None = None,
) -> float:
    """Compute a 0–1 confidence score based on reranker signals and citation density."""
    scores = []

    if reranker_scores:
        avg = sum(reranker_scores[:3]) / min(3, len(reranker_scores))
        scores.append(max(0.0, min(1.0, (avg + 5) / 10)))

    if answer:
        citations = _re.findall(r'\[SOURCE\s+\d+\]', answer)
        word_count = len(answer.split())
        if word_count > 0:
            density = (len(citations) / word_count) * 100
            scores.append(min(1.0, density / 3.0))

    return round(sum(scores) / len(scores), 2) if scores else 0.5


# ── DB persistence helpers ────────────────────────────────────


async def save_conversation(
    notebook_id: str,
    user_id: str,
    user_message: str,
    assistant_answer: str,
    session_id: str = None,
) -> str:
    """Persist a user/assistant exchange.  Returns the assistant ChatMessage id."""
    from app.db.prisma_client import prisma

    assistant_msg_id = ""
    for role, content in [("user", user_message), ("assistant", assistant_answer)]:
        if not content:
            continue
        try:
            data = {
                "notebookId": notebook_id,
                "userId": user_id,
                "role": role,
                "content": content,
            }
            if session_id:
                data["chatSessionId"] = session_id

            msg = await prisma.chatmessage.create(data=data)
            if role == "assistant":
                assistant_msg_id = str(msg.id)
        except Exception as exc:
            logger.error("save_conversation failed (role=%s): %s", role, exc)
    return assistant_msg_id


async def save_response_blocks(message_id: str, content: str) -> List[Dict]:
    """Split *content* on double-newline and persist each block as a ResponseBlock."""
    from app.db.prisma_client import prisma

    created_blocks = []
    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    for idx, block_text in enumerate(blocks):
        try:
            block = await prisma.responseblock.create(
                data={
                    "chatMessageId": message_id,
                    "blockIndex": idx,
                    "text": block_text[:5000],
                }
            )
            created_blocks.append({
                "id": str(block.id),
                "index": block.blockIndex,
                "text": block.text
            })
        except Exception as exc:
            logger.debug("save_response_blocks failed (idx=%d): %s", idx, exc)
    
    return created_blocks


async def log_agent_execution(
    user_id: str,
    notebook_id: str,
    meta: Dict,
    elapsed: float,
) -> None:
    """Write an AgentExecutionLog row.  Best-effort."""
    from app.db.prisma_client import prisma

    try:
        await prisma.agentexecutionlog.create(
            data={
                "userId": user_id,
                "notebookId": notebook_id,
                "intent": meta.get("intent") or "UNKNOWN",
                "confidence": float(meta.get("confidence", 0.0) or 0.0),
                "toolsUsed": meta.get("tools_used") or [],
                "stepsCount": int(meta.get("iterations", 0) or 0),
                "tokensUsed": int(meta.get("total_tokens", 0) or 0),
                "elapsedTime": float(elapsed or 0.0),
            }
        )
    except Exception as exc:
        logger.debug("log_agent_execution failed: %s", exc)


async def get_chat_history(notebook_id: str, user_id: str, session_id: str = None) -> List[Dict]:
    """Return serialised chat messages for *notebook_id* ordered oldest first."""
    from app.db.prisma_client import prisma

    try:
        where_clause = {"notebookId": notebook_id, "userId": user_id}
        if session_id:
            where_clause["chatSessionId"] = session_id

        messages = await prisma.chatmessage.find_many(
            where=where_clause,
            order={"createdAt": "asc"},
            include={"responseBlocks": True}
        )
        return [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.createdAt.isoformat(),
                "blocks": sorted(
                    [{"id": str(b.id), "index": b.blockIndex, "text": b.text}
                     for b in getattr(m, "responseBlocks", []) or []],
                    key=lambda x: x["index"]
                ) if m.role == "assistant" else []
            }
            for m in messages
        ]
    except Exception as exc:
        logger.error("get_chat_history failed: %s", exc)
        return []


async def clear_chat_history(notebook_id: str, user_id: str, session_id: str = None) -> None:
    """Delete all ChatMessage rows for *notebook_id*."""
    from app.db.prisma_client import prisma
    try:
        where_clause = {"notebookId": notebook_id, "userId": user_id}
        if session_id:
            where_clause["chatSessionId"] = session_id

        await prisma.chatmessage.delete_many(where=where_clause)
    except Exception as exc:
        logger.error("clear_chat_history failed: %s", exc)


# ── Chat sessions ───────────────────────────────────────


async def get_chat_sessions(notebook_id: str, user_id: str) -> List[Dict]:
    """Return all chat sessions for a notebook, including message content for searching."""
    from app.db.prisma_client import prisma
    try:
        sessions = await prisma.chatsession.find_many(
            where={"notebookId": notebook_id, "userId": user_id},
            order={"createdAt": "desc"},
            include={"chatMessages": True}
        )
        return [
            {
                "id": str(s.id), 
                "title": s.title, 
                "created_at": s.createdAt.isoformat(),
                "messages_text": " ".join(m.content for m in getattr(s, "chatMessages", []) or [])
            } 
            for s in sessions
        ]
    except Exception as exc:
        logger.error("get_chat_sessions failed: %s", exc)
        return []


async def create_chat_session(notebook_id: str, user_id: str, title: str = "New Chat") -> str:
    """Create a new chat session."""
    from app.db.prisma_client import prisma
    try:
        session = await prisma.chatsession.create(
            data={"notebookId": notebook_id, "userId": user_id, "title": title}
        )
        return str(session.id)
    except Exception as exc:
        logger.error("create_chat_session failed: %s", exc)
        return ""


async def delete_chat_session(session_id: str, user_id: str) -> bool:
    """Delete a chat session."""
    from app.db.prisma_client import prisma
    try:
        await prisma.chatsession.delete_many(
            where={"id": session_id, "userId": user_id}
        )
        return True
    except Exception as exc:
        logger.error("delete_chat_session failed: %s", exc)
        return False


# ── Block followup & suggestions ─────────────────────────────


async def block_followup_stream(
    block_id: str,
    action: str,
    question: str,
) -> AsyncIterator[str]:
    """Stream an LLM response for a block-level follow-up action strictly based on DB content.

    Supported *action* values: ``ask``, ``simplify``, ``translate``, ``explain``.
    Yields raw text chunks as strings.
    """
    from app.db.prisma_client import prisma
    
    block = await prisma.responseblock.find_unique(where={"id": block_id})
    if not block:
        yield f"Error: Could not find paragraph block with ID {block_id}"
        return
        
    block_text = block.text

    action_prompts = {
        "ask": (
            f"Based on this specific paragraph:\n\n\"{block_text}\"\n\n"
            f"Answer this question: {question}"
        ),
        "simplify": (
            f"Simplify the following paragraph to make it easier to understand. "
            f"Keep the key information but use simpler language:\n\n\"{block_text}\""
        ),
        "translate": f"Translate the following paragraph to {question}:\n\n\"{block_text}\"",
        "explain": (
            f"Explain the following paragraph in much more depth and detail. "
            f"Provide examples and context:\n\n\"{block_text}\""
        ),
    }

    prompt = action_prompts.get(action, action_prompts["ask"])
    llm = get_llm()

    async for chunk in llm.astream(prompt):
        content = getattr(chunk, "content", str(chunk))
        if content:
            yield content


def _compute_overlap(partial: str, text: str) -> float:
    """Compute simple word intersection over partial input length."""
    partial_words = set(partial.lower().split())
    if not partial_words:
        return 0.0
    text_words = set(text.lower().split())
    intersection = partial_words.intersection(text_words)
    return len(intersection) / len(partial_words)

async def get_suggestions(partial_input: str, notebook_id: str, user_id: str) -> List[Dict]:
    """Return up to 5 auto-complete suggestions for *partial_input*.
    
    Provides LLM with Notebook and Material titles for context.
    Returns a list of ``{"suggestion": str, "confidence": float}`` dicts.
    """
    from app.services.llm_service.llm import get_llm_structured
    from app.services.llm_service.structured_invoker import parse_json_robust
    from app.db.prisma_client import prisma

    # 1. Fetch Notebook context
    notebook = await prisma.notebook.find_unique(
        where={"id": notebook_id},
        include={"materials": True}
    )
    
    if not notebook or notebook.userId != user_id:
        return []
        
    notebook_title = notebook.name
    material_titles = [m.title or m.filename for m in getattr(notebook, "materials", [])]
    materials_context = "\n".join(f"- {title}" for title in material_titles) if material_titles else "No materials uploaded yet."

    prompt = f"""You are an expert AI prompt engineer assistant for an educational platform.
The user is typing an inquiry regarding their uploaded documents, and needs auto-complete suggestions.

Notebook Context:
Title: "{notebook_title}"
Available Materials:
{materials_context}

Partial user input: "{partial_input}"

Your task is to predict the user's intent and provide 3-5 highly optimized, agentic, and comprehensive prompt completions.
Transform the user's basic thought into a structured, powerful prompt that will yield an exceptional AI response.

Return ONLY a JSON array in the exact format:
[
    {{"suggestion": "In-depth and structured prompt replacing or extending the user's input...", "confidence": 0.95}},
    {{"suggestion": "Alternative highly optimized prompt based on the context...", "confidence": 0.85}}
]

Rules for suggestions:
1. Must logically start with or seamlessly replace/extend the user's partial input.
2. Elevate the prompt (e.g., if user types "summarize", suggest "Summarize the core arguments of this material, providing a structured breakdown of key findings and actionable takeaways").
3. Make them context-aware based on the notebook materials.
4. Set confidence from 0.0 to 1.0 based on relevance.
5. Provide ONLY the JSON array.
"""

    try:
        llm = get_llm_structured()
        response = await llm.ainvoke(prompt)
        text = getattr(response, "content", str(response)).strip()
        parsed = parse_json_robust(text)
        if not isinstance(parsed, list):
            parsed = parsed.get("suggestions", [])
            
        suggestions = []
        for item in parsed:
            suggestion_text = item.get("suggestion", "")
            if not suggestion_text:
                continue
                
            llm_conf = float(item.get("confidence", 0.5))
            overlap_score = _compute_overlap(partial_input, suggestion_text)
            
            # Simple average of semantic (LLM) and lexical (overlap) relevance
            final_conf = (llm_conf + overlap_score) / 2
            
            suggestions.append({
                "suggestion": suggestion_text,
                "confidence": round(final_conf, 2)
            })
            
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:5]
    except Exception as exc:
        logger.error("get_suggestions failed: %s", exc)
        return []
