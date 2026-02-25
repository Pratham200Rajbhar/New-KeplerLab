"""LLM service module.

Provides language model abstraction layer supporting multiple providers
(Ollama, Google Gemini, NVIDIA, custom endpoints).

Key modules:
- llm.py: Provider factory and client creation
- structured_invoker.py: Structured output generation
- llm_schemas.py: Pydantic schemas for structured outputs
- llm_utils.py: Utility functions and helpers
"""
