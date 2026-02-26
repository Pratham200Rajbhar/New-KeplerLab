"""Model Manager — validates and downloads required AI models on startup.

Key fix: the original code loaded SentenceTransformer up to 3 times per
validation cycle (_is_model_cached → _download → _verify). This version
checks the cache by directory existence and only loads the model once.
"""

from __future__ import annotations

import logging
import os
import asyncio
from pathlib import Path
from typing import Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # Registry of required models
        self.required_models: Dict[str, dict] = {
            "embedding": {
                "name": settings.EMBEDDING_MODEL,
                "type": "sentence_transformer",
                "required": True,
            },
        }

    # ── Public API ────────────────────────────────────────

    async def validate_and_load_models(self) -> Dict[str, bool]:
        """Validate all required models; download missing ones.

        Returns mapping of model_id → success.
        Runs blocking model operations in a thread executor to avoid
        blocking the async event loop during multi-GB downloads.
        """
        logger.info("Starting model validation …")
        results: Dict[str, bool] = {}
        loop = asyncio.get_running_loop()

        for model_id, cfg in self.required_models.items():
            try:
                ok = await loop.run_in_executor(None, self._ensure_model, cfg)
                results[model_id] = ok
                logger.info(f"Model {model_id}: {'ready' if ok else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error with model {model_id}: {e}")
                results[model_id] = False

        ready = sum(results.values())
        logger.info(f"Model validation complete: {ready}/{len(results)} ready")
        return results

    def get_model_info(self) -> dict:
        return {
            "models_directory": str(self.models_dir),
            "required_models": self.required_models,
            "cache_size": self._human_cache_size(),
        }

    # ── Internals ─────────────────────────────────────────

    def _ensure_model(self, cfg: dict) -> bool:
        """Download if missing, then verify with a single load."""
        name = cfg["name"]
        mtype = cfg["type"]

        if mtype == "sentence_transformer":
            return self._ensure_sentence_transformer(name)
        if mtype == "tts":
            return True  # placeholder
        logger.error(f"Unknown model type: {mtype}")
        return False

    def _ensure_sentence_transformer(self, name: str) -> bool:
        """Check cache by directory, download + verify with ONE load."""
        cache_dir = str(self.models_dir)

        # Fast cache check: directory exists with files?
        dir_name = name.replace("/", "--")
        local = self.models_dir / dir_name
        # Also check HuggingFace-style nested path
        hf_path = self.models_dir / f"models--{dir_name}"
        cached = (local.exists() and any(local.iterdir())) or (
            hf_path.exists() and any(hf_path.iterdir())
        )

        if not cached:
            logger.info(f"Downloading: {name}")

        try:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(name, cache_folder=cache_dir)
            emb = model.encode("test")
            if emb is not None and len(emb) > 0:
                return True
            logger.error(f"{name}: produced invalid embedding")
            return False
        except Exception as e:
            logger.error(f"{name}: load/verify failed — {e}")
            return False

    def _is_model_cached(self, name: str) -> bool:
        """Quick check without loading the model (used by /models/status)."""
        d = name.replace("/", "--")
        local = self.models_dir / d
        hf = self.models_dir / f"models--{d}"
        return (local.exists() and any(local.iterdir())) or (
            hf.exists() and any(hf.iterdir())
        )

    @staticmethod
    def _human_cache_size(path: Path | None = None) -> str:
        target = path or Path(settings.MODELS_DIR)
        try:
            total = sum(
                f.stat().st_size for f in target.rglob("*") if f.is_file()
            )
        except Exception:
            return "Unknown"
        for unit in ("B", "KB", "MB", "GB"):
            if total < 1024.0:
                return f"{total:.1f} {unit}"
            total /= 1024.0
        return f"{total:.1f} TB"


# Global singleton
model_manager = ModelManager()