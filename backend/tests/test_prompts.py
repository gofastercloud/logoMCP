from logogen.models.schemas import BrandBrief, CreativeDirection
from logogen.prompts.templates import (
    format_color_typography_prompt,
    format_creative_direction_prompt,
    format_logo_prompts_prompt,
)


def _sample_brief(**overrides) -> BrandBrief:
    defaults = dict(
        company_name="Acme Corp",
        industry="Technology",
        target_audience="Small business owners",
        mood_keywords=["modern", "bold"],
    )
    defaults.update(overrides)
    return BrandBrief(**defaults)


def _sample_direction() -> CreativeDirection:
    return CreativeDirection(
        visual_style="Modern minimalist with geometric shapes",
        mood_description="Clean, professional, trustworthy",
        logo_concepts=["Abstract hexagon", "Upward arrow", "Circuit node"],
        brand_voice="Confident and approachable",
        tagline="Build better brands",
    )


class TestFormatCreativeDirectionPrompt:
    def test_includes_required_fields(self):
        brief = _sample_brief()
        prompt = format_creative_direction_prompt(brief)
        assert "Acme Corp" in prompt
        assert "Technology" in prompt
        assert "Small business owners" in prompt
        assert "modern" in prompt
        assert "bold" in prompt

    def test_includes_color_preferences(self):
        brief = _sample_brief(color_preferences=["#FF0000", "#00FF00"])
        prompt = format_creative_direction_prompt(brief)
        assert "#FF0000" in prompt
        assert "#00FF00" in prompt

    def test_includes_description(self):
        brief = _sample_brief(description="A SaaS platform for invoicing")
        prompt = format_creative_direction_prompt(brief)
        assert "A SaaS platform for invoicing" in prompt

    def test_excludes_optionals_when_none(self):
        brief = _sample_brief()
        prompt = format_creative_direction_prompt(brief)
        assert "Color preferences" not in prompt
        assert "Description" not in prompt


class TestFormatLogoPromptsPrompt:
    def test_includes_brief_and_direction(self):
        brief = _sample_brief()
        direction = _sample_direction()
        prompt = format_logo_prompts_prompt(brief, direction)
        assert "Acme Corp" in prompt
        assert "Modern minimalist" in prompt
        assert "Abstract hexagon" in prompt


class TestFormatColorTypographyPrompt:
    def test_includes_brief_and_direction(self):
        brief = _sample_brief()
        direction = _sample_direction()
        prompt = format_color_typography_prompt(brief, direction)
        assert "Acme Corp" in prompt
        assert "Modern minimalist" in prompt

    def test_includes_color_preferences(self):
        brief = _sample_brief(color_preferences=["#336699"])
        direction = _sample_direction()
        prompt = format_color_typography_prompt(brief, direction)
        assert "#336699" in prompt
