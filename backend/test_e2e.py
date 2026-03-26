"""End-to-end test of the full LogoGen pipeline.

Runs the actual models (Qwen3 + Flux) — this is slow and requires GPU.
"""
import asyncio
import json
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("e2e")


async def main():
    # Ensure data dirs exist
    from logogen.config import DATA_DIR, BRANDS_DIR, DATABASE_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    BRANDS_DIR.mkdir(parents=True, exist_ok=True)

    from logogen.db.connection import get_db
    from logogen.db import repository as repo
    from logogen.models.schemas import BrandBrief, BrandStatus

    db = await get_db()

    # Step 1: Create brand
    logger.info("=" * 60)
    logger.info("STEP 1: Creating brand")
    brief = BrandBrief(
        company_name="Solaris",
        industry="Solar Energy & Home Battery",
        target_audience="Eco-conscious homeowners looking to reduce energy bills and carbon footprint",
        mood_keywords=["sustainable", "bright", "trustworthy", "innovative"],
        description="Residential solar panels and home battery systems with AI-optimized energy management.",
    )
    brand_id = await repo.create_brand(db, brief)
    brand_dir = BRANDS_DIR / brand_id
    brand_dir.mkdir(parents=True, exist_ok=True)
    (brand_dir / "concepts").mkdir(exist_ok=True)
    (brand_dir / "assets").mkdir(exist_ok=True)
    logger.info("Brand created: %s", brand_id)

    # Step 2: Generate logos (text + image)
    logger.info("=" * 60)
    logger.info("STEP 2: Generating logos (text LLM + image model)")
    t0 = time.time()

    # Phase 2a: Text generation
    logger.info("--- Phase 2a: Text generation ---")
    from logogen.pipeline.text_gen import generate_text
    t_text_start = time.time()
    text_result = generate_text(brief, on_progress=lambda s, p: logger.info("  [%.0f%%] %s", p * 100, s))
    t_text_end = time.time()
    logger.info("Text generation took %.1fs", t_text_end - t_text_start)

    logger.info("Creative direction: %s", text_result.creative_direction.visual_style)
    logger.info("Tagline: %s", text_result.creative_direction.tagline)
    logger.info("Logo concepts: %s", text_result.creative_direction.logo_concepts)
    logger.info("Colors: %s", [(c.name, c.hex, c.role) for c in text_result.color_palette])
    logger.info("Typography: %s / %s", text_result.typography.heading_font, text_result.typography.body_font)
    logger.info("Logo prompts:")
    for i, p in enumerate([text_result.logo_prompts.concept_1, text_result.logo_prompts.concept_2, text_result.logo_prompts.concept_3]):
        logger.info("  Concept %d: %s", i, p[:120])

    # Save specs
    await repo.save_brand_specs(
        db, brand_id,
        text_result.creative_direction,
        text_result.color_palette,
        text_result.typography,
    )

    # Phase 2b: Image generation
    logger.info("--- Phase 2b: Image generation ---")
    from logogen.pipeline.image_gen import generate_logo_concepts
    prompts = [
        text_result.logo_prompts.concept_1,
        text_result.logo_prompts.concept_2,
        text_result.logo_prompts.concept_3,
    ]
    concepts_dir = brand_dir / "concepts"
    t_img_start = time.time()
    images = generate_logo_concepts(
        prompts, concepts_dir, base_seed=42,
        on_progress=lambda s, p: logger.info("  [%.0f%%] %s", p * 100, s),
    )
    t_img_end = time.time()
    logger.info("Image generation took %.1fs (%.1fs per concept)", t_img_end - t_img_start, (t_img_end - t_img_start) / 3)

    # Save concepts
    concept_records = [
        {"concept_index": i, "prompt": prompts[i], "image_path": f"concepts/concept_{i}.png"}
        for i in range(3)
    ]
    await repo.save_logo_concepts(db, brand_id, concept_records, generation_run=1)
    await repo.update_brand_status(db, brand_id, BrandStatus.READY)

    t1 = time.time()
    logger.info("Total generation time: %.1fs", t1 - t0)

    # Step 3: Select concept and render templates
    logger.info("=" * 60)
    logger.info("STEP 3: Selecting concept 0 and rendering templates")
    import shutil
    src = concepts_dir / "concept_0.png"
    dst = brand_dir / "logo_mark.png"
    shutil.copy2(src, dst)

    # SVG trace
    from logogen.services.svg_service import trace_to_svg
    svg_path = brand_dir / "logo_mark.svg"
    t_svg_start = time.time()
    try:
        trace_to_svg(dst, svg_path)
        logger.info("SVG trace took %.1fs", time.time() - t_svg_start)
    except Exception as e:
        logger.warning("SVG trace failed: %s", e)
        svg_path = None

    # Build context and render
    from logogen.services.template_engine import build_brand_context, render_all_templates
    ctx = build_brand_context(
        brand_name=brief.company_name,
        tagline=text_result.creative_direction.tagline,
        logo_mark_path=dst,
        logo_mark_svg_path=svg_path,
        colors=text_result.color_palette,
        heading_font_name=text_result.typography.heading_font,
        body_font_name=text_result.typography.body_font,
    )

    t_render_start = time.time()
    asset_records = render_all_templates(ctx, brand_id)
    t_render_end = time.time()
    logger.info("Template rendering took %.1fs for %d assets", t_render_end - t_render_start, len(asset_records))

    # Summary
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("Brand: %s (ID: %s)", brief.company_name, brand_id)
    logger.info("Brand dir: %s", brand_dir)
    logger.info("Text gen: %.1fs", t_text_end - t_text_start)
    logger.info("Image gen: %.1fs", t_img_end - t_img_start)
    logger.info("SVG trace: %.1fs", time.time() - t_svg_start if svg_path else 0)
    logger.info("Template render: %.1fs", t_render_end - t_render_start)
    logger.info("Total: %.1fs", time.time() - t0)
    logger.info("Assets rendered: %d", len(asset_records))

    # List all rendered assets
    logger.info("--- Assets ---")
    by_template = {}
    for r in asset_records:
        slug = r["template_slug"]
        by_template.setdefault(slug, []).append(r)
    for slug, records in sorted(by_template.items()):
        logger.info("  %s: %d files", slug, len(records))
        for r in records:
            filepath = brand_dir / r["file_path"]
            size_kb = filepath.stat().st_size / 1024 if filepath.exists() else 0
            logger.info("    %s/%s.%s (%s) %dx%d %.1fKB",
                        r["template_slug"], r["variant"], r["format"], r["scale"],
                        r["width"], r["height"], size_kb)

    await db.close()
    logger.info("Done! Check %s for outputs.", brand_dir)


if __name__ == "__main__":
    asyncio.run(main())
