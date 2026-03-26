from __future__ import annotations

from logogen.models.schemas import BrandBrief, CreativeDirection

CREATIVE_DIRECTION_SYSTEM = """\
You are a brand strategist and visual designer. Given a brand brief, produce a creative direction document.

Output ONLY valid JSON matching this exact schema — no markdown, no explanation:
{
  "visual_style": "description of the visual style",
  "mood_description": "description of the mood and feeling",
  "logo_concepts": ["concept 1", "concept 2", "concept 3"],
  "brand_voice": "description of the brand voice and tone",
  "tagline": "a short brand tagline or slogan"
}

Rules:
- visual_style: 1-2 sentences describing the overall look and feel
- mood_description: 1-2 sentences describing the emotional response
- logo_concepts: exactly 3 concrete visual concepts for the logo (shapes, symbols, motifs — NOT text)
- brand_voice: 1-2 sentences describing how the brand communicates
- tagline: a memorable brand tagline, 3-8 words
"""

LOGO_PROMPTS_SYSTEM = """\
You are an AI image prompt engineer specializing in logo and brand design. \
Given a brand brief and creative direction, generate 3 image prompts for a Flux AI image model. \
Each prompt should explore a DIFFERENT visual concept from the creative direction's logo_concepts list.

Output ONLY valid JSON matching this exact schema — no markdown, no explanation:
{
  "concept_1": "prompt for logo concept 1",
  "concept_2": "prompt for logo concept 2",
  "concept_3": "prompt for logo concept 3"
}

Every prompt MUST follow this EXACT structure — do not deviate:
"A minimalist flat-color logo mark of [CONCEPT], solid [1-2 COLORS] on pure white background, \
vector style, flat design, bold geometric shapes, thick clean edges, high contrast, \
professional brand identity, isolated centered icon"

Rules:
- Each prompt explores a different visual direction (shape, symbol, motif)
- Describe ONLY abstract shapes, geometric forms, or stylized symbols
- Colors must be FLAT and SOLID — use phrases like "solid dark blue", "flat black", "bold red"
- NEVER use: gradient, soft, fading, blending, translucent, glow, shadow, or shading
- Always end with "on pure white background, vector style, flat design"
- Keep each prompt under 80 words

ABSOLUTE PROHIBITIONS — the prompt must NEVER describe:
- Text, letters, words, numbers, typography, writing, lettermarks, monograms
- Watermarks, signatures, stamps, labels, or captions
- NSFW, violent, offensive, or controversial imagery
- Photographic, photorealistic, or 3D rendered elements
- Gradients, color gradients, soft shading, translucency, or glow effects
- Busy backgrounds, patterns, textures, or noise
- Thin lines, intricate detail, or filigree
- Dark or colored backgrounds — ONLY pure white
"""

COLOR_TYPOGRAPHY_SYSTEM = """\
You are a brand designer specializing in color theory and typography. \
Given a brand brief and creative direction, produce a color palette and typography recommendations.

Output ONLY valid JSON matching this exact schema — no markdown, no explanation:
{
  "color_palette": [
    {"hex": "#XXXXXX", "name": "Color Name", "role": "primary|secondary|accent|neutral|background", "rationale": "why this color"}
  ],
  "typography": {
    "heading_font": "Font Name",
    "body_font": "Font Name",
    "rationale": "why this pairing works"
  }
}

Rules:
- Provide exactly 5 colors: one primary, one secondary, one accent, one neutral, one background
- The "background" color MUST be white or very light (e.g. #FFFFFF, #F8F8F8, #FAFAFA)
- The "neutral" color should be dark (for text on light backgrounds), e.g. #333333, #2D2D2D
- All hex codes must be valid 6-digit hex with # prefix
- Font recommendations should be freely available (Google Fonts preferred)
- If the brief includes color preferences, incorporate them as primary/secondary colors
"""


def format_creative_direction_prompt(brief: BrandBrief) -> str:
    parts = [
        f"Company: {brief.company_name}",
        f"Industry: {brief.industry}",
        f"Target audience: {brief.target_audience}",
        f"Mood/style: {', '.join(brief.mood_keywords)}",
    ]
    if brief.color_preferences:
        parts.append(f"Color preferences: {', '.join(brief.color_preferences)}")
    if brief.description:
        parts.append(f"Description: {brief.description}")
    return "\n".join(parts)


def format_logo_prompts_prompt(
    brief: BrandBrief, direction: CreativeDirection
) -> str:
    return (
        f"Brand brief:\n"
        f"Company: {brief.company_name}\n"
        f"Industry: {brief.industry}\n"
        f"Mood/style: {', '.join(brief.mood_keywords)}\n\n"
        f"Creative direction:\n"
        f"Visual style: {direction.visual_style}\n"
        f"Mood: {direction.mood_description}\n"
        f"Logo concepts to explore: {', '.join(direction.logo_concepts)}"
    )


def format_color_typography_prompt(
    brief: BrandBrief, direction: CreativeDirection
) -> str:
    parts = [
        "Brand brief:",
        f"Company: {brief.company_name}",
        f"Industry: {brief.industry}",
        f"Mood/style: {', '.join(brief.mood_keywords)}",
    ]
    if brief.color_preferences:
        parts.append(f"Color preferences: {', '.join(brief.color_preferences)}")
    parts.extend(
        [
            "",
            "Creative direction:",
            f"Visual style: {direction.visual_style}",
            f"Mood: {direction.mood_description}",
        ]
    )
    return "\n".join(parts)
