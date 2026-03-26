from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import random
from pathlib import Path

from mcp.server.fastmcp import FastMCP, Image

from logogen.config import BRANDS_DIR, DATA_DIR
from logogen.db.connection import close_db, get_db
from logogen.db import repository as repo
from logogen.models.schemas import (
    BrandBrief,
    BrandSpecs,
    BrandStatus,
    ColorEntry,
    CreativeDirection,
    TypographyRec,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "LogoGen",
    instructions=(
        "Brand design system generator. Create brands, set specs, generate logo concepts, "
        "select a concept, and get rendered brand assets. "
        "Typical flow: create_brand → (optional) update_brand_specs → generate_logos → select_logo."
    ),
)


# --- Brand CRUD ---


@mcp.tool()
async def create_brand(
    company_name: str,
    industry: str,
    target_audience: str,
    mood_keywords: list[str],
    color_preferences: list[str] | None = None,
    description: str | None = None,
) -> str:
    """Create a new brand from a brief. Returns brand ID.

    After creating, optionally call update_brand_specs() to set colors/fonts/tagline
    before generating logos, or call generate_logos() directly to let AI fill in everything.
    """
    brief = BrandBrief(
        company_name=company_name,
        industry=industry,
        target_audience=target_audience,
        mood_keywords=mood_keywords,
        color_preferences=color_preferences,
        description=description,
    )
    db = await get_db()
    brand_id = await repo.create_brand(db, brief)

    brand_dir = BRANDS_DIR / brand_id
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "concepts").mkdir(exist_ok=True)
    (brand_dir / "assets").mkdir(exist_ok=True)

    return json.dumps({
        "brand_id": brand_id,
        "name": company_name,
        "status": "created",
        "next_steps": [
            f"update_brand_specs(brand_id='{brand_id}', ...) — optional, set colors/fonts/tagline",
            f"generate_logos(brand_id='{brand_id}') — generate 3 logo concepts",
        ],
    })


@mcp.tool()
async def list_brands() -> str:
    """List all brands with their status."""
    db = await get_db()
    brands = await repo.list_brands(db)
    if not brands:
        return "No brands found. Use create_brand() to create one."
    return json.dumps([b.model_dump(mode="json") for b in brands], indent=2)


@mcp.tool()
async def get_brand(brand_id: str) -> str:
    """Get full details of a brand including specs, concepts, and assets."""
    db = await get_db()
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})
    return json.dumps(brand.model_dump(mode="json"), indent=2)


@mcp.tool()
async def delete_brand(brand_id: str) -> str:
    """Delete a brand and all its generated assets."""
    db = await get_db()
    deleted = await repo.delete_brand(db, brand_id)
    if not deleted:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})

    brand_dir = BRANDS_DIR / brand_id
    if brand_dir.exists():
        import shutil
        shutil.rmtree(brand_dir)

    return json.dumps({"status": "deleted", "brand_id": brand_id})


# --- Brand Specs ---


@mcp.tool()
async def update_brand_specs(
    brand_id: str,
    colors: list[dict] | None = None,
    typography: dict | None = None,
    tagline: str | None = None,
    creative_direction: dict | None = None,
) -> str:
    """Update brand specs (colors, fonts, tagline, creative direction).

    Can be called BEFORE generate_logos() to set preferences the AI should respect,
    or AFTER to override AI-generated values. Providing colors/typography before
    logo generation means the AI will skip generating those and use yours instead.

    Args:
        brand_id: The brand to update.
        colors: List of color entries, each with hex, name, role, rationale.
                Roles: primary, secondary, accent, neutral, background.
        typography: Dict with heading_font, body_font, rationale (Google Fonts names).
        tagline: Brand tagline string.
        creative_direction: Dict with visual_style, mood_description, logo_concepts, brand_voice, tagline.
    """
    db = await get_db()
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})

    # Parse inputs
    parsed_colors = [ColorEntry(**c) for c in colors] if colors else None
    parsed_typography = TypographyRec(**typography) if typography else None
    parsed_direction = CreativeDirection(**creative_direction) if creative_direction else None

    existing_specs = await repo.get_brand_specs(db, brand_id)

    if existing_specs is None:
        # First time setting specs — need at least creative direction for a full save
        if parsed_direction is None:
            # Create a minimal placeholder direction if not provided
            # Will be overwritten by generate_logos if called later
            parsed_direction = CreativeDirection(
                visual_style="Pending AI generation",
                mood_description="Pending AI generation",
                logo_concepts=["Pending"],
                brand_voice="Pending AI generation",
                tagline=tagline or "Pending",
            )
        await repo.save_brand_specs(
            db,
            brand_id,
            parsed_direction,
            parsed_colors or [],
            parsed_typography or TypographyRec(heading_font="", body_font="", rationale=""),
        )
    else:
        # Update existing specs
        if parsed_direction:
            await repo.save_brand_specs(
                db, brand_id, parsed_direction,
                parsed_colors or existing_specs.color_palette,
                parsed_typography or existing_specs.typography,
            )
        else:
            await repo.update_brand_specs(
                db, brand_id,
                color_palette=parsed_colors,
                typography=parsed_typography,
                tagline=tagline,
            )

    specs = await repo.get_brand_specs(db, brand_id)
    return json.dumps({
        "status": "updated",
        "brand_id": brand_id,
        "specs": specs.model_dump(mode="json") if specs else None,
    }, indent=2)


# --- Logo Prompt Access ---

PROMPT_SUFFIX = (
    ", centered on a pure white background, vector style, flat design, "
    "simple geometric shapes, bold clean edges, high contrast, professional brand identity, "
    "isolated icon with generous padding"
)


def _sanitize_prompt(prompt: str) -> str:
    """Ensure prompt has required style suffix for consistent logo generation."""
    prompt = prompt.strip()
    if "white background" not in prompt.lower():
        prompt = f"{prompt}{PROMPT_SUFFIX}"
    return prompt


@mcp.tool()
async def get_logo_prompts(brand_id: str) -> str:
    """Get the current logo generation prompts for a brand.

    Returns the 3 prompts that will be (or were) used to generate logo concepts.
    These are auto-generated by the AI but can be revised with update_logo_prompts().
    """
    db = await get_db()
    concepts = await repo.get_logo_concepts(db, brand_id)
    if concepts:
        return json.dumps({
            "brand_id": brand_id,
            "source": "generated",
            "prompts": {
                f"concept_{c.concept_index}": c.prompt for c in concepts
            },
        }, indent=2)

    # Check if specs have prompts stored (pre-generation)
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})

    return json.dumps({
        "brand_id": brand_id,
        "source": "not_yet_generated",
        "message": "No prompts yet. Call generate_logos() to create them, or set them manually with update_logo_prompts().",
    })


@mcp.tool()
async def update_logo_prompts(
    brand_id: str,
    concept_1: str | None = None,
    concept_2: str | None = None,
    concept_3: str | None = None,
) -> str:
    """Revise the logo generation prompts before calling generate_logos() or regenerate_logos().

    WARNING: The default prompts are carefully engineered for the logo design LoRA model.
    Modifying them may produce lower quality or off-brand results. Recommended approach:
    1. Call get_logo_prompts() to see the current prompts
    2. Make targeted edits to the visual concept (middle part) only
    3. Do NOT remove the "wablogo, logo, Minimalist," prefix — it activates the LoRA
    4. Safety constraints (no text, no NSFW, etc.) will be automatically re-applied

    Each prompt describes a VISUAL CONCEPT (shapes, symbols, motifs) — not text or words.
    The system will enforce the LoRA trigger prefix and safety suffix on any prompt you provide.

    Args:
        brand_id: The brand to update prompts for.
        concept_1: Revised prompt for concept 1 (or None to keep current).
        concept_2: Revised prompt for concept 2 (or None to keep current).
        concept_3: Revised prompt for concept 3 (or None to keep current).
    """
    db = await get_db()
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})

    concepts = await repo.get_logo_concepts(db, brand_id)
    updates = {0: concept_1, 1: concept_2, 2: concept_3}
    sanitized = {}

    for idx, new_prompt in updates.items():
        if new_prompt is not None:
            sanitized[idx] = _sanitize_prompt(new_prompt)

    if not sanitized:
        return json.dumps({"error": "No prompts provided to update."})

    if concepts:
        # Update existing concept prompts in DB
        for c in concepts:
            if c.concept_index in sanitized:
                await db.execute(
                    """UPDATE logo_concepts SET prompt = ?
                       WHERE brand_id = ? AND concept_index = ? AND generation_run = (
                           SELECT MAX(generation_run) FROM logo_concepts WHERE brand_id = ?
                       )""",
                    (sanitized[c.concept_index], brand_id, c.concept_index, brand_id),
                )
        await db.commit()
    else:
        # Store as pending prompts (will be used by next generate_logos call)
        # Save as generation_run 0 to indicate "manual, pre-generation"
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
        for idx, prompt in sanitized.items():
            await db.execute(
                """INSERT OR REPLACE INTO logo_concepts
                   (id, brand_id, concept_index, prompt, image_path, is_selected, generation_run, created_at)
                   VALUES (?, ?, ?, ?, '', 0, 0, ?)""",
                (str(__import__("uuid").uuid4()), brand_id, idx, prompt, now),
            )
        await db.commit()

    # Return the current state
    concepts = await repo.get_logo_concepts(db, brand_id, current_run_only=True)
    return json.dumps({
        "status": "updated",
        "brand_id": brand_id,
        "prompts": {f"concept_{c.concept_index}": c.prompt for c in concepts},
        "note": "Safety constraints have been automatically applied. Call generate_logos() or regenerate_logos() to generate images with these prompts.",
    }, indent=2)


# --- Logo Generation ---


@mcp.tool()
async def generate_logos(brand_id: str) -> list[Image | str]:
    """Generate 3 logo concepts for a brand using AI.

    This runs the full pipeline:
    1. Text LLM generates creative direction, logo prompts, colors, typography
       (respects any specs set via update_brand_specs)
    2. Image model generates 3 logo mark concepts at 1024x1024

    Returns the generated specs and 3 logo images for visual inspection.
    Call select_logo() after reviewing to pick your preferred concept.
    """
    db = await get_db()
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return [json.dumps({"error": f"Brand '{brand_id}' not found"})]

    await repo.update_brand_status(db, brand_id, BrandStatus.GENERATING)

    try:
        # Check for manually-set prompts (from update_logo_prompts)
        manual_concepts = await repo.get_logo_concepts(db, brand_id, current_run_only=True)
        manual_prompts = {c.concept_index: c.prompt for c in manual_concepts if c.prompt}

        # Phase 1: Text generation (respects existing specs)
        from logogen.pipeline.text_gen import generate_text

        existing_specs = brand.specs
        text_result = await asyncio.to_thread(
            generate_text, brand.brief, existing_specs=existing_specs
        )

        # Save/update specs in DB
        await repo.save_brand_specs(
            db, brand_id,
            text_result.creative_direction,
            text_result.color_palette,
            text_result.typography,
        )

        # Phase 2: Image generation
        from logogen.pipeline.image_gen import generate_logo_concepts

        # Use manual prompts if set, otherwise use LLM-generated ones
        ai_prompts = [
            text_result.logo_prompts.concept_1,
            text_result.logo_prompts.concept_2,
            text_result.logo_prompts.concept_3,
        ]
        prompts = [
            manual_prompts.get(i, ai_prompts[i]) for i in range(3)
        ]
        concepts_dir = BRANDS_DIR / brand_id / "concepts"
        seed = random.randint(0, 2**32 - 1)

        images = await asyncio.to_thread(
            generate_logo_concepts, prompts, concepts_dir, base_seed=seed
        )

        # Save concept records in DB
        generation_run = await repo.get_max_generation_run(db, brand_id) + 1
        concept_records = [
            {
                "concept_index": i,
                "prompt": prompts[i],
                "image_path": f"concepts/concept_{i}.png",
            }
            for i in range(len(prompts))
        ]
        await repo.save_logo_concepts(db, brand_id, concept_records, generation_run)
        await repo.update_brand_status(db, brand_id, BrandStatus.READY)

        # Build response: text summary + 3 images
        result: list[Image | str] = []
        specs_summary = {
            "brand_id": brand_id,
            "status": "logos_generated",
            "creative_direction": text_result.creative_direction.model_dump(),
            "tagline": text_result.creative_direction.tagline,
            "color_palette": [c.model_dump() for c in text_result.color_palette],
            "typography": text_result.typography.model_dump(),
            "prompts_used": [prompts[0], prompts[1], prompts[2]],
            "seed": seed,
            "next_step": f"select_logo(brand_id='{brand_id}', concept_index=0|1|2)",
        }
        result.append(json.dumps(specs_summary, indent=2))

        for i, img in enumerate(images):
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            result.append(Image(data=buf.getvalue(), format="png"))

        return result

    except Exception as e:
        await repo.update_brand_status(db, brand_id, BrandStatus.ERROR)
        logger.exception("Logo generation failed for brand %s", brand_id)
        return [json.dumps({"error": str(e), "brand_id": brand_id})]


@mcp.tool()
async def get_logo_concepts(brand_id: str) -> list[Image | str]:
    """Get the current logo concepts for a brand. Returns images for visual inspection."""
    db = await get_db()
    concepts = await repo.get_logo_concepts(db, brand_id)
    if not concepts:
        return [json.dumps({"error": "No concepts found. Call generate_logos() first."})]

    result: list[Image | str] = []
    summary = []
    for c in concepts:
        summary.append({
            "concept_index": c.concept_index,
            "prompt": c.prompt,
            "is_selected": c.is_selected,
        })
    result.append(json.dumps({"brand_id": brand_id, "concepts": summary}, indent=2))

    for c in concepts:
        image_path = BRANDS_DIR / brand_id / c.image_path
        if image_path.exists():
            result.append(Image(data=image_path.read_bytes(), format="png"))

    return result


@mcp.tool()
async def select_logo(brand_id: str, concept_index: int) -> str:
    """Select a logo concept (0, 1, or 2) as the brand's primary logo mark.

    This triggers template rendering of all brand assets using the selected logo.
    Renders logo variants (mark, primary, stacked, wordmark, favicon) in
    light/dark/transparent variants at 1x and 2x resolution.
    """
    db = await get_db()
    brand = await repo.get_brand(db, brand_id)
    if brand is None:
        return json.dumps({"error": f"Brand '{brand_id}' not found"})

    if not brand.specs:
        return json.dumps({"error": "No specs found. Call generate_logos() first."})

    selected = await repo.select_logo_concept(db, brand_id, concept_index)
    if not selected:
        return json.dumps({"error": f"Concept {concept_index} not found"})

    # Copy selected concept to logo_mark.png
    import shutil
    src = BRANDS_DIR / brand_id / f"concepts/concept_{concept_index}.png"
    dst = BRANDS_DIR / brand_id / "logo_mark.png"
    if not src.exists():
        return json.dumps({"error": f"Concept image not found at {src}"})
    shutil.copy2(src, dst)

    # Process logo: remove white background + autocrop to content
    from logogen.services.image_processing import process_logo_mark
    process_logo_mark(dst)

    # SVG trace (from the original, not the bg-removed version — better trace input)
    from logogen.services.svg_service import trace_to_svg
    svg_path = BRANDS_DIR / brand_id / "logo_mark.svg"
    try:
        trace_to_svg(dst, svg_path)
    except Exception as e:
        logger.warning("SVG tracing failed: %s", e)
        svg_path = None

    # Build brand context and render templates
    from logogen.services.template_engine import build_brand_context, render_all_templates

    ctx = build_brand_context(
        brand_name=brand.name,
        tagline=brand.specs.tagline,
        logo_mark_path=dst,
        logo_mark_svg_path=svg_path,
        colors=brand.specs.color_palette,
        heading_font_name=brand.specs.typography.heading_font if brand.specs.typography else "",
        body_font_name=brand.specs.typography.body_font if brand.specs.typography else "",
    )

    # Clear old rendered assets
    await repo.delete_rendered_assets(db, brand_id)

    # Render all templates
    asset_records = await asyncio.to_thread(render_all_templates, ctx, brand_id)

    # Save asset records to DB
    for rec in asset_records:
        await repo.save_rendered_asset(
            db, brand_id,
            template_slug=rec["template_slug"],
            variant=rec["variant"],
            fmt=rec["format"],
            scale=rec["scale"],
            file_path=rec["file_path"],
            width=rec["width"],
            height=rec["height"],
        )

    return json.dumps({
        "status": "rendered",
        "brand_id": brand_id,
        "concept_index": concept_index,
        "assets_rendered": len(asset_records),
        "templates": list({r["template_slug"] for r in asset_records}),
        "message": f"Rendered {len(asset_records)} assets. Use get_brand_assets() or get_asset() to view them.",
    })


@mcp.tool()
async def get_asset(
    brand_id: str,
    template_slug: str,
    variant: str = "light",
    format: str = "png",
    scale: str = "1x",
) -> list[Image | str]:
    """Get a specific rendered asset. Returns the image for visual inspection.

    Args:
        brand_id: The brand ID.
        template_slug: e.g. "logo-mark", "logo-primary", "logo-stacked", "logo-wordmark", "logo-favicon"
        variant: "light", "dark", or "transparent"
        format: "png", "jpeg", or "svg"
        scale: "1x" or "2x"
    """
    db = await get_db()
    assets = await repo.get_rendered_assets(db, brand_id)

    for asset in assets:
        if (asset["template_slug"] == template_slug
                and asset["variant"] == variant
                and asset["format"] == format
                and asset["scale"] == scale):
            filepath = BRANDS_DIR / brand_id / asset["file_path"]
            if not filepath.exists():
                return [json.dumps({"error": f"Asset file not found: {filepath}"})]

            if format == "svg":
                return [filepath.read_text()]
            else:
                return [
                    json.dumps({
                        "template": template_slug,
                        "variant": variant,
                        "format": format,
                        "scale": scale,
                        "width": asset["width"],
                        "height": asset["height"],
                    }),
                    Image(data=filepath.read_bytes(), format=format),
                ]

    return [json.dumps({
        "error": f"Asset not found: {template_slug}/{variant}.{format} ({scale})",
        "available": [
            f"{a['template_slug']}/{a['variant']}.{a['format']} ({a['scale']})"
            for a in assets
        ],
    })]


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRANDS_DIR.mkdir(parents=True, exist_ok=True)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
