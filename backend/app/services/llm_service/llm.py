"""LLM provider factory with timeout and token limits.

Usage:
    from app.services.llm_service.llm import get_llm, get_llm_structured
    
    # For chat (higher temperature)
    llm = get_llm()
    
    # For structured output (lower temperature, deterministic)
    llm = get_llm_structured()
    
    response = llm.invoke("Hello")
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import warnings

import requests
from langchain_core.language_models.llms import LLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_ollama import ChatOllama

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Suppress warnings
warnings.simplefilter("ignore", UserWarning)

# ── Provider registry ─────────────────────────────────────────

_PROVIDERS: Dict[str, Any] = {}


def _register_providers():
    """Build the provider map lazily (called once on first ``get_llm``)."""
    if _PROVIDERS:
        return

    _PROVIDERS["OLLAMA"] = _build_ollama
    _PROVIDERS["GOOGLE"] = _build_google
    _PROVIDERS["NVIDIA"] = _build_nvidia
    _PROVIDERS["MYOPENLM"] = _build_openlm


# ── Builder functions ─────────────────────────────────────────


def _common_kwargs(
    temperature: float,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **extra_kwargs
) -> dict:
    """Shared kwargs for all providers with explicit generation control."""
    kwargs = {
        "temperature": temperature,
        "timeout": settings.LLM_TIMEOUT,
    }
    
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    
    if top_p is not None:
        kwargs["top_p"] = top_p
    
    kwargs.update(extra_kwargs)
    return kwargs


def _build_ollama(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    """Build Ollama client with generation parameters."""
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    kw = _common_kwargs(temp, top_p, max_tokens, **extra_kwargs)
    kw["model"] = settings.OLLAMA_MODEL
    
    # Ollama supports top_k
    if "top_k" in extra_kwargs:
        kw["top_k"] = extra_kwargs["top_k"]
    
    return ChatOllama(**kw)


def _build_google(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    """Build Google Gemini client with generation parameters."""
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    kw = _common_kwargs(temp, top_p, max_tokens, **extra_kwargs)
    kw.update(
        model=settings.GOOGLE_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )
    
    # Google supports top_k
    if "top_k" in extra_kwargs:
        kw["top_k"] = extra_kwargs["top_k"]
    
    return ChatGoogleGenerativeAI(**kw)


def _build_nvidia(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    """Build NVIDIA client with generation parameters."""
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    kw = _common_kwargs(temp, top_p, max_tokens, **extra_kwargs)
    kw.update(
        model=settings.NVIDIA_MODEL,
        api_key=settings.NVIDIA_API_KEY,
        streaming=True, # explicitly stream
        model_kwargs={"chat_template_kwargs": {"thinking": False}} # disable 'thinking'
    )
    
    return ChatNVIDIA(**kw)


def _build_openlm(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    """Build custom OpenLM client."""
    return MyOpenLM(
        temperature=temperature or settings.LLM_TEMPERATURE_CHAT,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS_CHAT,
    )


# ── Public API ────────────────────────────────────────────────


def get_llm(
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    provider: Optional[str] = None,
    mode: str = "chat",
    **kwargs
):
    """Return a LangChain-compatible LLM instance with tiered temperature.
    
    Args:
        temperature: Explicit override for generation temperature.
        top_p: Nucleus sampling parameter (default: LLM_TOP_P_CHAT).
        max_tokens: Max tokens to generate (default: LLM_MAX_TOKENS_CHAT).
        provider: Override global config for specific provider.
        mode: Temperature tier — "chat" (0.2), "creative" (0.7),
              "structured" (0.1), "code" (0.1). Only used when
              temperature is not explicitly set.
        **kwargs: Additional provider-specific parameters.
    
    Returns:
        LLM instance configured for the requested mode.
    """
    _register_providers()
    
    # Tiered temperature defaults
    _TEMP_MAP = {
        "chat": settings.LLM_TEMPERATURE_CHAT,          # 0.2 — factual RAG
        "creative": settings.LLM_TEMPERATURE_CREATIVE,   # 0.7 — podcast, brainstorm
        "structured": settings.LLM_TEMPERATURE_STRUCTURED, # 0.1 — JSON output
        "code": settings.LLM_TEMPERATURE_CODE,           # 0.1 — python_tool
    }
    
    temp = temperature if temperature is not None else _TEMP_MAP.get(mode, settings.LLM_TEMPERATURE_CHAT)
    p = top_p if top_p is not None else settings.LLM_TOP_P_CHAT
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS_CHAT
    
    active_provider = provider if provider else settings.LLM_PROVIDER

    builder = _PROVIDERS.get(active_provider)
    if builder is None:
        logger.warning(f"Unknown LLM_PROVIDER '{active_provider}', falling back to OLLAMA")
        builder = _PROVIDERS["OLLAMA"]
    
    return builder(temperature=temp, top_p=p, max_tokens=tokens, **kwargs)


def get_llm_structured(
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    provider: Optional[str] = None,
    **kwargs
):
    """Return a LLM instance for structured output (lower temperature, deterministic).
    
    Args:
        temperature: Generation temperature (default: LLM_TEMPERATURE_STRUCTURED)
        top_p: Nucleus sampling parameter (default: LLM_TOP_P_STRUCTURED)
        max_tokens: Max tokens to generate (default: LLM_MAX_TOKENS)
        provider: Ignore global config and use specific provider (e.g. "MYOPENLM").
        **kwargs: Additional provider-specific parameters
    
    Returns:
        LLM instance configured for structured generation
    """
    _register_providers()
    
    # Use structured defaults if not specified
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_STRUCTURED
    p = top_p if top_p is not None else settings.LLM_TOP_P_STRUCTURED
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS
    
    # Add top_k if not already specified and provider supports it
    if "top_k" not in kwargs:
        kwargs["top_k"] = settings.LLM_TOP_K
    
    active_provider = provider if provider else settings.LLM_PROVIDER

    builder = _PROVIDERS.get(active_provider)
    if builder is None:
        logger.warning(f"Unknown LLM_PROVIDER '{active_provider}', falling back to OLLAMA")
        builder = _PROVIDERS["OLLAMA"]
    
    return builder(temperature=temp, top_p=p, max_tokens=tokens, **kwargs)


# ── Custom OpenLM wrapper ─────────────────────────────────────


class MyOpenLM(LLM):
    """Custom LangChain wrapper for the MyOpenLM REST API."""

    api_url: str = settings.MYOPENLM_API_URL
    model_name: str = settings.MYOPENLM_MODEL
    temperature: float = 0.2
    max_tokens: int = 3000
    _MAX_RETRIES: int = 3

    @property
    def _llm_type(self) -> str:
        return "my_lm"

    def _call(
        self, prompt: str, stop: Optional[List[str]] = None, *args: Any, **kwargs: Any
    ) -> str:
        last_exc: Optional[Exception] = None

        for attempt in range(self._MAX_RETRIES):
            try:
                resp = requests.post(
                    self.api_url,
                    json={
                        "message": prompt,
                        "model": self.model_name,
                        "temperature": self.temperature,
                        "max_tokens": self.max_tokens,
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=settings.LLM_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()["data"]["response"]

            except requests.exceptions.HTTPError as exc:
                last_exc = exc
                if resp.status_code == 500:
                    logger.warning(f"LLM 500 — retry {attempt + 1}/{self._MAX_RETRIES}")
                    time.sleep(2 ** attempt)
                    continue
                raise

            except Exception as exc:
                logger.error(f"LLM call error: {exc}")
                raise

        raise last_exc or Exception("LLM call failed after all retries")
