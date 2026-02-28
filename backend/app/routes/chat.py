"""Chat route — Agent-powered conversation with materials.

Replaces the linear RAG chat with a LangGraph agent that:
- Auto-detects user intent
- Routes to the correct tool (RAG, quiz, flashcard, PPT)
- Streams responses via SSE with agent step metadata
"""

import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.auth import get_current_user
from app.services.material_service import filter_completed_material_ids
from app.services.token_counter import estimate_token_count, track_token_usage, get_model_token_limit
from app.services.audit_logger import log_api_usage
from app.core.config import settings
from app.services.chat import service as chat_service
from .utils import require_material

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    message: str = Field(..., min_length=1, max_length=50000)
    notebook_id: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True  # Default to streaming now
    intent_override: Optional[str] = None  # e.g. "RESEARCH" to force research mode


class ClearChatRequest(BaseModel):
    notebook_id: str
    session_id: Optional[str] = None


class BlockFollowupRequest(BaseModel):
    block_id: str
    question: str = Field(..., min_length=1, max_length=10000)
    action: str = "ask"  # ask, simplify, translate, explain


class SuggestionRequest(BaseModel):
    partial_input: str = Field(..., min_length=1, max_length=1000)
    notebook_id: str

class CreateSessionRequest(BaseModel):
    notebook_id: str
    title: Optional[str] = "New Chat"


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user=Depends(get_current_user),
    debug: bool = Query(False, description="Enable debug mode"),
):
    start_time = time.time()

    # Resolve material IDs
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    # Validate all materials belong to user
    for mid in ids:
        material = await require_material(mid, current_user.id)
        if material.notebookId and material.notebookId != request.notebook_id:
            raise HTTPException(
                status_code=400,
                detail=f"Material {mid} does not belong to the current notebook.",
            )

    # Guard: only search materials that have finished processing
    ids = await filter_completed_material_ids(ids, str(current_user.id))
    if not ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "None of the selected materials have finished processing yet. "
                "Please wait for their status to reach 'completed' before chatting."
            ),
        )

    # Use provided session_id or create a new session
    session_id = request.session_id
    if not session_id:
        title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        session_id = await chat_service.create_chat_session(request.notebook_id, str(current_user.id), title)
    else:
        # Auto-title untitled sessions on first real message
        try:
            from app.db.prisma_client import prisma
            existing = await prisma.chatsession.find_unique(where={"id": session_id})
            if existing and (not existing.title or existing.title in ("", "New Chat")):
                new_title = request.message[:30] + ("..." if len(request.message) > 30 else "")
                await prisma.chatsession.update(where={"id": session_id}, data={"title": new_title})
        except Exception:
            pass  # non-critical — don't fail the chat request

    try:
        from app.services.agent.graph import run_agent, run_agent_stream
        from app.services.agent.state import AgentState

        # ── Build workspace_files from material records ────────────────
        # Required by data_profiler and workspace_builder tools so they can
        # locate the raw uploaded file (real_path) and extracted text (text_path).
        import os
        from app.db.prisma_client import prisma as _prisma

        workspace_files = []
        for mid in ids:
            try:
                mat = await _prisma.material.find_unique(where={"id": mid})
                if not mat:
                    continue
                fname = mat.filename or ""
                ext = os.path.splitext(fname)[1].lower()
                meta: dict = {}
                if mat.metadata:
                    try:
                        meta = json.loads(mat.metadata) if isinstance(mat.metadata, str) else mat.metadata
                    except (json.JSONDecodeError, TypeError):
                        pass
                workspace_files.append({
                    "id": mid,
                    "filename": fname,
                    "real_path": meta.get("upload_path", ""),
                    "text_path": f"data/material_text/{mid}.txt",
                    "ext": ext,
                    "type": getattr(mat, "sourceType", None) or "file",
                })
            except Exception as _wf_err:
                logger.warning("workspace_files: failed to load material %s: %s", mid, _wf_err)

        initial_state: AgentState = {
            "user_message": request.message,
            "user_id": str(current_user.id),
            "notebook_id": request.notebook_id,
            "material_ids": ids,
            "session_id": session_id,
            "workspace_files": workspace_files,
            "intent": "",
            "intent_confidence": 0.0,
            "plan": [],
            "current_step": 0,
            "tool_results": [],
            "iterations": 0,
            "total_tokens": 0,
            "total_tool_calls": 0,
            "needs_retry": False,
            "step_retries": 0,
            "response": "",
            "agent_metadata": {},
            **({"intent_override": request.intent_override} if request.intent_override else {}),
        }

        if request.stream:
            # ── SSE Streaming Response ─────────────────────
            async def generate():
                try:
                    full_response = []
                    agent_meta = {}

                    async for event in run_agent_stream(initial_state):
                        yield event

                        # Parse events to accumulate response for DB persistence
                        if event.startswith("event: token"):
                            data_line = event.split("data: ", 1)[-1].strip()
                            try:
                                token_data = json.loads(data_line)
                                full_response.append(token_data.get("content", ""))
                            except json.JSONDecodeError:
                                pass
                        elif event.startswith("event: meta"):
                            data_line = event.split("data: ", 1)[-1].strip()
                            try:
                                agent_meta = json.loads(data_line)
                            except json.JSONDecodeError:
                                pass

                    # Persist messages to DB after streaming completes.
                    # For structured JSON responses (DATA_ANALYSIS), no token events
                    # are emitted — use the response carried in the meta event instead.
                    complete_answer = "".join(full_response) or agent_meta.get("response", "")
                    if complete_answer:
                        msg_id = await chat_service.save_conversation(
                            notebook_id=request.notebook_id,
                            user_id=str(current_user.id),
                            user_message=request.message,
                            assistant_answer=complete_answer,
                            session_id=session_id,
                            agent_meta=agent_meta if agent_meta else None,
                        )
                        if msg_id:
                            blocks = await chat_service.save_response_blocks(msg_id, complete_answer)
                            if blocks:
                                blocks_data = json.dumps({"blocks": blocks})
                                yield f"event: blocks\ndata: {blocks_data}\n\n"

                        if agent_meta:
                            elapsed = time.time() - start_time
                            await chat_service.log_agent_execution(
                                user_id=str(current_user.id),
                                notebook_id=request.notebook_id,
                                meta=agent_meta,
                                elapsed=elapsed,
                            )

                except Exception as e:
                    logger.error(f"Streaming chat failed: {e}")
                    error_data = json.dumps({"error": str(e)})
                    yield f"event: error\ndata: {error_data}\n\n"

            return StreamingResponse(
                generate(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        else:
            # ── Non-Streaming Response ─────────────────────
            result = await run_agent(initial_state)

            answer = result["response"]
            metadata = result.get("agent_metadata", {})

            # Token counting
            context_tokens = estimate_token_count(request.message)
            response_tokens = estimate_token_count(answer)
            total_tokens = context_tokens + response_tokens

            model_name = settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "OLLAMA" else settings.GOOGLE_MODEL
            model_max_tokens = get_model_token_limit(model_name)

            # Track token usage
            try:
                await track_token_usage(str(current_user.id), total_tokens)
            except Exception as e:
                logger.error(f"Token tracking failed: {e}")

            # Log API usage
            total_time = time.time() - start_time
            try:
                await log_api_usage(
                    user_id=str(current_user.id),
                    endpoint="/chat",
                    material_ids=ids,
                    context_token_count=context_tokens,
                    response_token_count=response_tokens,
                    model_used=model_name,
                    llm_latency=total_time,
                    retrieval_latency=0.0,
                    total_latency=total_time,
                )
            except Exception as e:
                logger.error(f"Audit logging failed: {e}")

            # Persist messages to DB
            msg_id = await chat_service.save_conversation(
                notebook_id=request.notebook_id,
                user_id=str(current_user.id),
                user_message=request.message,
                assistant_answer=answer,
                session_id=session_id,
            )

            blocks = []
            if msg_id:
                blocks = await chat_service.save_response_blocks(msg_id, answer)

            confidence = chat_service.compute_confidence_score("", answer)

            response_data = {
                "session_id": session_id,
                "answer": answer,
                "confidence": confidence,
                "context_tokens": context_tokens,
                "response_tokens": response_tokens,
                "total_tokens": total_tokens,
                "model_max_tokens": model_max_tokens,
                "truncated": False,
                "agent_metadata": metadata,
                "blocks": blocks,
            }

            if debug:
                response_data["debug"] = {
                    "total_time": round(total_time, 3),
                    "material_ids": ids,
                    "model_used": model_name,
                    "agent": metadata,
                }

            return JSONResponse(content=response_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


# ── Block Followup (Phase 4 endpoint, registered early) ──────

@router.post("/chat/block-followup")
async def block_followup(
    request: BlockFollowupRequest,
    current_user=Depends(get_current_user),
):
    """Block-level mini chat — streams a focused LLM response for a single paragraph.
    
    Persists the full follow-up response as a new ResponseBlock after streaming.
    Validates block ownership through the chat message's notebook → user chain.
    """
    try:
        # Validate block ownership — ensure the block belongs to this user
        from app.db.prisma_client import get_prisma
        prisma = get_prisma()
        parent_block = await prisma.responseblock.find_unique(
            where={"id": request.block_id},
            include={"chatMessage": {"include": {"notebook": True}}},
        )
        if not parent_block or not parent_block.chatMessage:
            raise HTTPException(status_code=404, detail="Block not found")
        notebook = parent_block.chatMessage.notebook
        if not notebook or str(notebook.userId) != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        async def generate():
            accumulated = []
            try:
                async for text_chunk in chat_service.block_followup_stream(
                    block_id=request.block_id,
                    action=request.action,
                    question=request.question,
                ):
                    accumulated.append(text_chunk)
                    token_data = json.dumps({"content": text_chunk})
                    yield f"event: token\ndata: {token_data}\n\n"

                # Persist the followup response as a child ResponseBlock
                full_response = "".join(accumulated)
                if full_response.strip():
                    try:
                        from app.db.prisma_client import get_prisma
                        prisma = get_prisma()
                        # Find the parent block to get the chatMessageId
                        parent_block = await prisma.responseblock.find_unique(
                            where={"id": request.block_id}
                        )
                        if parent_block:
                            # Get next block index
                            max_block = await prisma.responseblock.find_first(
                                where={"chatMessageId": parent_block.chatMessageId},
                                order={"blockIndex": "desc"},
                            )
                            next_idx = (max_block.blockIndex + 1) if max_block else 0
                            await prisma.responseblock.create(
                                data={
                                    "chatMessageId": parent_block.chatMessageId,
                                    "blockIndex": next_idx,
                                    "text": f"[{request.action}] {full_response}",
                                }
                            )
                    except Exception as persist_err:
                        logger.warning("Failed to persist block followup: %s", persist_err)

                yield f"event: done\ndata: {{}}\n\n"
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                yield f"event: error\ndata: {error_data}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Block followup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process block followup")


# ── Prompt Suggestions (Phase 4 endpoint, registered early) ──

@router.post("/chat/suggestions")
async def get_suggestions(
    request: SuggestionRequest,
    current_user=Depends(get_current_user),
):
    """Generate smart prompt suggestions based on partial input."""
    suggestions = await chat_service.get_suggestions(
        request.partial_input, 
        request.notebook_id, 
        str(current_user.id)
    )
    return JSONResponse(content={"suggestions": suggestions})


# ── Chat History ──────────────────────────────────────────────

@router.get("/chat/history/{notebook_id}")
async def get_notebook_chat_history(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    """Get all chat messages for a notebook (or specific session)."""
    return await chat_service.get_chat_history(notebook_id, str(current_user.id), session_id)


@router.delete("/chat/history/{notebook_id}")
async def clear_notebook_chat(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    """Clear all chat messages for a notebook (or specific session)."""
    await chat_service.clear_chat_history(
        notebook_id=notebook_id,
        user_id=str(current_user.id),
        session_id=session_id,
    )
    return {"cleared": True}

# ── Chat Sessions ──────────────────────────────────────────────

@router.get("/chat/sessions/{notebook_id}")
async def get_chat_sessions_endpoint(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    """Get all chat sessions for a notebook."""
    sessions = await chat_service.get_chat_sessions(notebook_id, str(current_user.id))
    return JSONResponse(content={"sessions": sessions})


@router.post("/chat/sessions")
async def create_chat_session_endpoint(
    request: CreateSessionRequest,
    current_user=Depends(get_current_user),
):
    """Create a new chat session."""
    session_id = await chat_service.create_chat_session(
        notebook_id=request.notebook_id,
        user_id=str(current_user.id),
        title=request.title
    )
    return JSONResponse(content={"session_id": session_id})


@router.delete("/chat/sessions/{session_id}")
async def delete_chat_session_endpoint(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a chat session."""
    success = await chat_service.delete_chat_session(session_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or could not be deleted")
    return {"deleted": True}
