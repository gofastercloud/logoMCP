from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from PIL import Image as PILImage

from logogen.config import (
    IMAGE_MODEL_NAME,
    IMAGE_MODEL_QUANTIZE,
    LOGO_HEIGHT,
    LOGO_LORA_SCALE,
    LOGO_STEPS,
    LOGO_WIDTH,
    LORA_REPO_ID,
)
from logogen.pipeline.memory import unload_model

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]


# NOTE: Flux.1 does NOT support negative prompts (parameter accepted but ignored).
# All constraints must be in the positive prompt. The LLM prompt template
# and the _sanitize_prompt suffix in server.py handle this.


def _resolve_lora_path(repo_id: str) -> str | None:
    try:
        from huggingface_hub import hf_hub_download

        path = hf_hub_download(repo_id=repo_id, filename="pytorch_lora_weights.safetensors")
        return path
    except Exception as e:
        logger.warning("Could not resolve LoRA path for %s: %s", repo_id, e)
        return None


def generate_logo_concepts(
    prompts: list[str],
    output_dir: Path,
    base_seed: int = 42,
    on_progress: ProgressCallback | None = None,
    model_name: str = IMAGE_MODEL_NAME,
    quantize: int = IMAGE_MODEL_QUANTIZE,
) -> list[PILImage.Image]:
    from mflux.models.flux.variants.txt2img.flux import Flux1

    def _progress(step: str, pct: float) -> None:
        if on_progress:
            on_progress(step, pct)

    output_dir.mkdir(parents=True, exist_ok=True)

    _progress("Loading image model", 0.0)
    flux = Flux1.from_name(model_name=model_name, quantize=quantize)

    images: list[PILImage.Image] = []
    try:
        for i, prompt in enumerate(prompts):
            _progress(f"Generating concept {i + 1}/{len(prompts)}", (i + 1) / (len(prompts) + 1))
            logger.info("Generating concept %d: %s", i, prompt[:100])

            generated = flux.generate_image(
                seed=base_seed + i,
                prompt=prompt,
                num_inference_steps=LOGO_STEPS,
                height=LOGO_HEIGHT,
                width=LOGO_WIDTH,
            )

            image_path = output_dir / f"concept_{i}.png"
            generated.save(str(image_path))
            images.append(PILImage.open(str(image_path)))
            logger.info("Saved concept %d to %s", i, image_path)

        _progress("Image generation complete", 1.0)
        return images

    finally:
        unload_model(flux)
