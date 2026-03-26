from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image as PILImage

from logogen.config import BRANDS_DIR
from logogen.models.schemas import ColorEntry
from logogen.services.font_service import ensure_font
from logogen.services.svg_service import trace_to_svg
from logogen.templates import BrandContext, TemplateRegistry
from logogen.templates.logo_variants import FaviconTemplate, register_logo_templates

logger = logging.getLogger(__name__)


def _ensure_registered() -> None:
    """Register all templates if not already done."""
    if not TemplateRegistry.all():
        register_logo_templates()


def build_brand_context(
    brand_name: str,
    tagline: str | None,
    logo_mark_path: Path,
    logo_mark_svg_path: Path | None,
    colors: list[ColorEntry],
    heading_font_name: str,
    body_font_name: str,
) -> BrandContext:
    """Build a BrandContext from stored brand data."""
    logo_mark = PILImage.open(logo_mark_path).convert("RGBA")

    logo_mark_svg = None
    if logo_mark_svg_path and logo_mark_svg_path.exists():
        logo_mark_svg = logo_mark_svg_path.read_text()

    heading_font = ensure_font(heading_font_name)
    body_font = ensure_font(body_font_name)

    return BrandContext(
        brand_name=brand_name,
        tagline=tagline,
        logo_mark=logo_mark,
        logo_mark_svg=logo_mark_svg,
        colors=colors,
        heading_font=heading_font,
        body_font=body_font,
        heading_font_name=heading_font_name,
        body_font_name=body_font_name,
    )


def render_all_templates(
    ctx: BrandContext,
    brand_id: str,
) -> list[dict]:
    """Render all registered templates for a brand. Returns list of asset records."""
    _ensure_registered()

    assets_dir = BRANDS_DIR / brand_id / "assets"
    asset_records = []

    for template in TemplateRegistry.all():
        template_dir = assets_dir / template.slug
        template_dir.mkdir(parents=True, exist_ok=True)

        for variant in template.variants:
            # Render at native resolution
            img = template.render(ctx, variant)

            for output_spec in template.outputs:
                # Scale if needed
                if output_spec.scale != 1.0:
                    scaled_w = int(img.width * output_spec.scale)
                    scaled_h = int(img.height * output_spec.scale)
                    scaled_img = img.resize((scaled_w, scaled_h), PILImage.Resampling.LANCZOS)
                else:
                    scaled_img = img
                    scaled_w = img.width
                    scaled_h = img.height

                for fmt in output_spec.formats:
                    # Skip JPEG for transparent variant
                    if fmt == "jpeg" and variant == "transparent":
                        continue

                    # SVG handling
                    if fmt == "svg":
                        if template.supports_svg:
                            svg_str = template.render_svg(ctx, variant)
                            if svg_str:
                                filename = f"{variant}{output_spec.suffix}.svg"
                                filepath = template_dir / filename
                                filepath.write_text(svg_str)
                                asset_records.append({
                                    "template_slug": template.slug,
                                    "variant": variant,
                                    "format": "svg",
                                    "scale": f"{output_spec.scale:.0f}x" if output_spec.scale >= 1 else f"{output_spec.scale}x",
                                    "file_path": str(filepath.relative_to(BRANDS_DIR / brand_id)),
                                    "width": scaled_w,
                                    "height": scaled_h,
                                })
                        continue

                    # Raster output
                    suffix = output_spec.suffix
                    scale_label = "1x" if output_spec.scale == 1.0 else f"{output_spec.scale:.0f}x"
                    filename = f"{variant}{suffix}.{fmt}"
                    filepath = template_dir / filename

                    if fmt == "jpeg":
                        # Convert RGBA → RGB for JPEG
                        rgb_img = PILImage.new("RGB", scaled_img.size, (255, 255, 255))
                        rgb_img.paste(scaled_img, mask=scaled_img.split()[3] if scaled_img.mode == "RGBA" else None)
                        rgb_img.save(str(filepath), "JPEG", quality=90)
                    else:
                        scaled_img.save(str(filepath), "PNG")

                    asset_records.append({
                        "template_slug": template.slug,
                        "variant": variant,
                        "format": fmt,
                        "scale": scale_label,
                        "file_path": str(filepath.relative_to(BRANDS_DIR / brand_id)),
                        "width": scaled_w,
                        "height": scaled_h,
                    })

        # Special handling for favicon sizes
        if isinstance(template, FaviconTemplate):
            for size in template.favicon_sizes:
                if size == template.width:
                    continue  # Already rendered at native
                for variant in template.variants:
                    img = template.render_at_size(ctx, variant, size)
                    filename = f"{variant}_{size}x{size}.png"
                    filepath = template_dir / filename
                    img.save(str(filepath), "PNG")
                    asset_records.append({
                        "template_slug": template.slug,
                        "variant": variant,
                        "format": "png",
                        "scale": "1x",
                        "file_path": str(filepath.relative_to(BRANDS_DIR / brand_id)),
                        "width": size,
                        "height": size,
                    })

    logger.info("Rendered %d assets for brand %s", len(asset_records), brand_id)
    return asset_records
