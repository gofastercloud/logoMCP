import json
from unittest.mock import MagicMock, patch

import pytest

from logogen.models.schemas import (
    BrandBrief,
    BrandSpecs,
    ColorEntry,
    CreativeDirection,
    TypographyRec,
)
from logogen.pipeline.text_gen import _generate_json, generate_text


def _sample_brief() -> BrandBrief:
    return BrandBrief(
        company_name="Acme Corp",
        industry="Technology",
        target_audience="Developers",
        mood_keywords=["modern", "minimal"],
    )


MOCK_CREATIVE_DIRECTION = json.dumps(
    {
        "visual_style": "Modern minimalist",
        "mood_description": "Clean and professional",
        "logo_concepts": ["Geometric shape", "Abstract A", "Circuit node"],
        "brand_voice": "Confident and direct",
        "tagline": "Build better, ship faster",
    }
)

MOCK_LOGO_PROMPTS = json.dumps(
    {
        "concept_1": "wablogo, logo, Minimalist, geometric hexagon shape with clean lines",
        "concept_2": "wablogo, logo, Minimalist, abstract letter form with sharp angles",
        "concept_3": "wablogo, logo, Minimalist, interconnected circuit nodes",
    }
)

MOCK_COLOR_TYPOGRAPHY = json.dumps(
    {
        "color_palette": [
            {"hex": "#2E86AB", "name": "Ocean Blue", "role": "primary", "rationale": "Trust"},
            {"hex": "#A23B72", "name": "Berry", "role": "secondary", "rationale": "Energy"},
            {"hex": "#F18F01", "name": "Amber", "role": "accent", "rationale": "Warmth"},
            {"hex": "#4A4A4A", "name": "Charcoal", "role": "neutral", "rationale": "Grounding"},
            {"hex": "#F5F5F5", "name": "Snow", "role": "background", "rationale": "Clean"},
        ],
        "typography": {
            "heading_font": "Inter",
            "body_font": "Source Sans Pro",
            "rationale": "Modern and highly legible pairing",
        },
    }
)


class TestGenerateJson:
    def test_parses_valid_json(self):
        model = MagicMock()
        tokenizer = MagicMock()
        tokenizer.apply_chat_template.return_value = "formatted prompt"
        mock_gen = MagicMock(return_value='{"key": "value"}')

        result = _generate_json(model, tokenizer, "system", "user", generate_fn=mock_gen)
        assert result == {"key": "value"}

    def test_strips_markdown_fences(self):
        model = MagicMock()
        tokenizer = MagicMock()
        tokenizer.apply_chat_template.return_value = "formatted prompt"
        mock_gen = MagicMock(return_value='```json\n{"key": "value"}\n```')

        result = _generate_json(model, tokenizer, "system", "user", generate_fn=mock_gen)
        assert result == {"key": "value"}

    def test_retries_on_invalid_json(self):
        model = MagicMock()
        tokenizer = MagicMock()
        tokenizer.apply_chat_template.return_value = "formatted prompt"
        mock_gen = MagicMock(side_effect=["not json at all", '{"key": "value"}'])

        result = _generate_json(
            model, tokenizer, "system", "user", max_retries=2, generate_fn=mock_gen
        )
        assert result == {"key": "value"}
        assert mock_gen.call_count == 2

    def test_raises_after_max_retries(self):
        model = MagicMock()
        tokenizer = MagicMock()
        tokenizer.apply_chat_template.return_value = "formatted prompt"
        mock_gen = MagicMock(return_value="not json")

        with pytest.raises(ValueError, match="Failed to get valid JSON"):
            _generate_json(
                model, tokenizer, "system", "user", max_retries=2, generate_fn=mock_gen
            )


class TestGenerateText:
    @patch("logogen.pipeline.text_gen.unload_model")
    @patch("logogen.pipeline.text_gen.load_text_model")
    @patch("logogen.pipeline.text_gen._generate_json")
    def test_full_pipeline(self, mock_gen_json, mock_load, mock_unload):
        mock_model = MagicMock()
        mock_tokenizer = MagicMock()
        mock_load.return_value = (mock_model, mock_tokenizer)

        mock_gen_json.side_effect = [
            json.loads(MOCK_CREATIVE_DIRECTION),
            json.loads(MOCK_LOGO_PROMPTS),
            json.loads(MOCK_COLOR_TYPOGRAPHY),
        ]

        brief = _sample_brief()
        result = generate_text(brief)

        assert result.creative_direction.visual_style == "Modern minimalist"
        assert result.creative_direction.tagline == "Build better, ship faster"
        assert result.logo_prompts.concept_1.startswith("wablogo")
        assert len(result.color_palette) == 5
        assert result.typography.heading_font == "Inter"

        mock_load.assert_called_once()
        mock_unload.assert_called_once()
        assert mock_gen_json.call_count == 3

    @patch("logogen.pipeline.text_gen.unload_model")
    @patch("logogen.pipeline.text_gen.load_text_model")
    @patch("logogen.pipeline.text_gen._generate_json")
    def test_progress_callbacks(self, mock_gen_json, mock_load, mock_unload):
        mock_load.return_value = (MagicMock(), MagicMock())
        mock_gen_json.side_effect = [
            json.loads(MOCK_CREATIVE_DIRECTION),
            json.loads(MOCK_LOGO_PROMPTS),
            json.loads(MOCK_COLOR_TYPOGRAPHY),
        ]

        progress_calls = []
        generate_text(_sample_brief(), on_progress=lambda s, p: progress_calls.append((s, p)))

        assert len(progress_calls) == 5
        assert progress_calls[0][1] == 0.0
        assert progress_calls[-1][1] == 1.0

    @patch("logogen.pipeline.text_gen.unload_model")
    @patch("logogen.pipeline.text_gen.load_text_model")
    @patch("logogen.pipeline.text_gen._generate_json")
    def test_unloads_on_error(self, mock_gen_json, mock_load, mock_unload):
        mock_load.return_value = (MagicMock(), MagicMock())
        mock_gen_json.side_effect = ValueError("LLM failed")

        with pytest.raises(ValueError):
            generate_text(_sample_brief())

        mock_unload.assert_called_once()

    @patch("logogen.pipeline.text_gen.unload_model")
    @patch("logogen.pipeline.text_gen.load_text_model")
    @patch("logogen.pipeline.text_gen._generate_json")
    def test_respects_existing_specs(self, mock_gen_json, mock_load, mock_unload):
        """When existing specs have colors+typography, only logo prompts are generated."""
        mock_load.return_value = (MagicMock(), MagicMock())

        # Only logo prompts should be generated (direction + colors/typography pre-set)
        mock_gen_json.side_effect = [
            json.loads(MOCK_LOGO_PROMPTS),
        ]

        existing = BrandSpecs(
            creative_direction=CreativeDirection(
                visual_style="Pre-set style",
                mood_description="Pre-set mood",
                logo_concepts=["Pre-set concept"],
                brand_voice="Pre-set voice",
                tagline="Pre-set tagline",
            ),
            color_palette=[
                ColorEntry(hex="#111111", name="Custom", role="primary", rationale="Set by agent"),
            ],
            typography=TypographyRec(
                heading_font="CustomFont", body_font="CustomBody", rationale="Agent choice"
            ),
        )

        result = generate_text(_sample_brief(), existing_specs=existing)

        assert result.creative_direction.visual_style == "Pre-set style"
        assert result.color_palette[0].hex == "#111111"
        assert result.typography.heading_font == "CustomFont"
        assert result.logo_prompts.concept_1.startswith("wablogo")
        assert mock_gen_json.call_count == 1

    @patch("logogen.pipeline.text_gen.unload_model")
    @patch("logogen.pipeline.text_gen.load_text_model")
    @patch("logogen.pipeline.text_gen._generate_json")
    def test_partial_existing_specs(self, mock_gen_json, mock_load, mock_unload):
        """When existing specs have colors but not typography, LLM generates typography."""
        mock_load.return_value = (MagicMock(), MagicMock())

        mock_gen_json.side_effect = [
            json.loads(MOCK_CREATIVE_DIRECTION),
            json.loads(MOCK_LOGO_PROMPTS),
            json.loads(MOCK_COLOR_TYPOGRAPHY),
        ]

        existing = BrandSpecs(
            creative_direction=None,
            color_palette=[
                ColorEntry(hex="#222222", name="Custom", role="primary", rationale="Set"),
            ],
            typography=None,
        )

        result = generate_text(_sample_brief(), existing_specs=existing)

        assert result.color_palette[0].hex == "#222222"
        assert result.typography.heading_font == "Inter"
        assert mock_gen_json.call_count == 3
