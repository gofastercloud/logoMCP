from __future__ import annotations

import gc
import logging
from typing import Any

logger = logging.getLogger(__name__)


def unload_model(*refs: Any) -> None:
    for ref in refs:
        del ref
    gc.collect()
    try:
        import mlx.core as mx

        mx.metal.clear_cache()
    except (ImportError, AttributeError):
        pass
    logger.info("Model unloaded, memory cleared")


def load_text_model(
    model_id: str,
) -> tuple[Any, Any]:
    import mlx_lm

    logger.info("Loading text model: %s", model_id)
    model, tokenizer = mlx_lm.load(model_id)
    logger.info("Text model loaded")
    return model, tokenizer


