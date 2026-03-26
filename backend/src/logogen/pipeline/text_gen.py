from __future__ import annotations

import json
import logging
from typing import Any, Callable

from logogen.config import TEXT_MAX_RETRIES, TEXT_MAX_TOKENS, TEXT_MODEL_ID
from logogen.models.schemas import (
    BrandBrief,
    BrandSpecs,
    ColorEntry,
    CreativeDirection,
    LogoPrompts,
    TextGenResult,
    TypographyRec,
)
from logogen.pipeline.memory import load_text_model, unload_model
from logogen.prompts.templates import (
    COLOR_TYPOGRAPHY_SYSTEM,
    CREATIVE_DIRECTION_SYSTEM,
    LOGO_PROMPTS_SYSTEM,
    format_color_typography_prompt,
    format_creative_direction_prompt,
    format_logo_prompts_prompt,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str, float], None]


def _get_generate_fn() -> Callable:
    import mlx_lm

    return mlx_lm.generate


def _generate_json(
    model: Any,
    tokenizer: Any,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = TEXT_MAX_RETRIES,
    max_tokens: int = TEXT_MAX_TOKENS,
    generate_fn: Callable | None = None,
) -> dict:
    if generate_fn is None:
        generate_fn = _get_generate_fn()

    for attempt in range(max_retries):
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt + " /nothink"},
        ]

        if hasattr(tokenizer, "apply_chat_template"):
            prompt = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            prompt = f"{system_prompt}\n\n{user_prompt}"

        response = generate_fn(
            model,
            tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
        )

        try:
            text = response.strip()
            # Strip Qwen3 thinking blocks: <think>...</think>
            if "<think>" in text:
                think_end = text.find("</think>")
                if think_end != -1:
                    text = text[think_end + len("</think>"):].strip()
            # Strip markdown fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]
            # Extract JSON object if there's surrounding text
            json_start = text.find("{")
            json_end = text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                text = text[json_start:json_end]
            return json.loads(text)
        except (json.JSONDecodeError, IndexError) as e:
            logger.warning(
                "JSON parse failed (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                e,
            )
            if attempt == max_retries - 1:
                raise ValueError(
                    f"Failed to get valid JSON after {max_retries} attempts. "
                    f"Last response: {response[:200]}"
                ) from e


def generate_text(
    brief: BrandBrief,
    existing_specs: BrandSpecs | None = None,
    on_progress: ProgressCallback | None = None,
    model_id: str = TEXT_MODEL_ID,
) -> TextGenResult:
    """Generate brand text specs, respecting any pre-existing specs.

    If existing_specs has colors/typography/tagline set, those are kept
    and the LLM only fills in the gaps (creative direction + logo prompts).
    """
    def _progress(step: str, pct: float) -> None:
        if on_progress:
            on_progress(step, pct)

    has_direction = existing_specs is not None and existing_specs.creative_direction is not None
    has_palette = existing_specs is not None and existing_specs.color_palette
    has_typography = existing_specs is not None and existing_specs.typography is not None

    _progress("Loading text model", 0.0)
    model, tokenizer = load_text_model(model_id)

    try:
        # 1. Creative direction + tagline (generate if not pre-set)
        if has_direction:
            direction = existing_specs.creative_direction
            _progress("Using existing creative direction", 0.2)
        else:
            _progress("Generating creative direction", 0.1)
            user_prompt = format_creative_direction_prompt(brief)
            direction_data = _generate_json(
                model, tokenizer, CREATIVE_DIRECTION_SYSTEM, user_prompt
            )
            direction = CreativeDirection(**direction_data)

        # 2. Logo prompts (always generated — these are unique per run)
        _progress("Generating logo prompts", 0.4)
        user_prompt = format_logo_prompts_prompt(brief, direction)
        prompts_data = _generate_json(
            model, tokenizer, LOGO_PROMPTS_SYSTEM, user_prompt
        )
        logo_prompts = LogoPrompts(**prompts_data)

        # 3. Color palette + typography (generate if not pre-set)
        if has_palette and has_typography:
            color_palette = existing_specs.color_palette
            typography = existing_specs.typography
            _progress("Using existing color palette and typography", 0.8)
        else:
            _progress("Generating color palette and typography", 0.7)
            user_prompt = format_color_typography_prompt(brief, direction)
            ct_data = _generate_json(
                model, tokenizer, COLOR_TYPOGRAPHY_SYSTEM, user_prompt
            )
            color_palette = (
                existing_specs.color_palette if has_palette
                else [ColorEntry(**c) for c in ct_data["color_palette"]]
            )
            typography = (
                existing_specs.typography if has_typography
                else TypographyRec(**ct_data["typography"])
            )

        _progress("Text generation complete", 1.0)

        return TextGenResult(
            creative_direction=direction,
            logo_prompts=logo_prompts,
            color_palette=color_palette,
            typography=typography,
        )

    finally:
        unload_model(model, tokenizer)
