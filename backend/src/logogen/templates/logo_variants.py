from __future__ import annotations

from PIL import Image as PILImage, ImageDraw, ImageFont

from logogen.models.schemas import TemplateCategory
from logogen.templates import (
    BaseTemplate,
    BrandContext,
    LOGO_OUTPUTS,
    OutputSpec,
    TemplateRegistry,
)


def _fit_logo(logo: PILImage.Image, max_w: int, max_h: int) -> PILImage.Image:
    """Scale logo to fit within max_w × max_h, preserving aspect ratio."""
    logo = logo.copy()
    logo.thumbnail((max_w, max_h), PILImage.Resampling.LANCZOS)
    return logo


def _load_font(ctx: BrandContext, size: int, use_heading: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load font at given size, falling back gracefully."""
    font_path = ctx.heading_font if use_heading else ctx.body_font
    if font_path and font_path.exists():
        try:
            return ImageFont.truetype(str(font_path), size)
        except (OSError, IOError):
            pass
    return ImageFont.load_default(size=size)


def _center_paste(canvas: PILImage.Image, item: PILImage.Image, x: int, y: int) -> None:
    """Paste item centered at (x, y) on canvas."""
    px = x - item.width // 2
    py = y - item.height // 2
    canvas.paste(item, (px, py), item if item.mode == "RGBA" else None)


class LogoMarkTemplate(BaseTemplate):
    slug = "logo-mark"
    name = "Logo Mark"
    category = TemplateCategory.LOGO_VARIANT
    width = 1024
    height = 1024
    outputs = LOGO_OUTPUTS
    supports_svg = True

    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        bg = self.get_bg_color(ctx, variant)
        canvas = PILImage.new("RGBA", (self.width, self.height), bg)
        logo = _fit_logo(ctx.logo_mark, int(self.width * 0.65), int(self.height * 0.65))
        _center_paste(canvas, logo, self.width // 2, self.height // 2)
        return canvas

    def render_svg(self, ctx: BrandContext, variant: str) -> str | None:
        return ctx.logo_mark_svg


class PrimaryLogoTemplate(BaseTemplate):
    slug = "logo-primary"
    name = "Primary Logo (Horizontal)"
    category = TemplateCategory.LOGO_VARIANT
    width = 1200
    height = 400
    outputs = LOGO_OUTPUTS
    supports_svg = True

    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        bg = self.get_bg_color(ctx, variant)
        text_color = self.get_text_color(ctx, variant)
        canvas = PILImage.new("RGBA", (self.width, self.height), bg)
        draw = ImageDraw.Draw(canvas)

        padding = int(self.height * 0.12)
        logo_area = self.height - 2 * padding
        logo = _fit_logo(ctx.logo_mark, logo_area, logo_area)
        logo_cx = padding + logo_area // 2
        _center_paste(canvas, logo, logo_cx, self.height // 2)

        text_x = padding + logo_area + int(self.height * 0.15)
        font_size = int(self.height * 0.25)
        font = _load_font(ctx, font_size)
        bbox = draw.textbbox((0, 0), ctx.brand_name, font=font)
        text_y = (self.height - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), ctx.brand_name, fill=text_color, font=font)

        return canvas


class StackedLogoTemplate(BaseTemplate):
    slug = "logo-stacked"
    name = "Stacked Logo"
    category = TemplateCategory.LOGO_VARIANT
    width = 800
    height = 800
    outputs = LOGO_OUTPUTS
    supports_svg = True

    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        bg = self.get_bg_color(ctx, variant)
        text_color = self.get_text_color(ctx, variant)
        canvas = PILImage.new("RGBA", (self.width, self.height), bg)
        draw = ImageDraw.Draw(canvas)

        logo_area_h = int(self.height * 0.50)
        logo = _fit_logo(ctx.logo_mark, int(self.width * 0.50), logo_area_h)
        _center_paste(canvas, logo, self.width // 2, int(self.height * 0.38))

        # Company name below
        font_size = int(self.height * 0.08)
        font = _load_font(ctx, font_size)
        bbox = draw.textbbox((0, 0), ctx.brand_name, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = (self.width - text_w) // 2
        text_y = int(self.height * 0.72)
        draw.text((text_x, text_y), ctx.brand_name, fill=text_color, font=font)

        return canvas


class WordmarkTemplate(BaseTemplate):
    slug = "logo-wordmark"
    name = "Wordmark"
    category = TemplateCategory.LOGO_VARIANT
    width = 1200
    height = 300
    outputs = LOGO_OUTPUTS
    supports_svg = True

    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        bg = self.get_bg_color(ctx, variant)
        canvas = PILImage.new("RGBA", (self.width, self.height), bg)
        draw = ImageDraw.Draw(canvas)

        # Brand primary color for the wordmark
        primary = ctx.get_color("primary")
        if variant == "dark":
            text_color = (255, 255, 255, 255)
        else:
            from logogen.templates import hex_to_rgba
            text_color = hex_to_rgba(primary)

        font_size = int(self.height * 0.45)
        font = _load_font(ctx, font_size)
        bbox = draw.textbbox((0, 0), ctx.brand_name, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (self.width - text_w) // 2
        text_y = (self.height - text_h) // 2
        draw.text((text_x, text_y), ctx.brand_name, fill=text_color, font=font)

        return canvas


class FaviconTemplate(BaseTemplate):
    slug = "logo-favicon"
    name = "Favicon"
    category = TemplateCategory.LOGO_VARIANT
    width = 192
    height = 192
    variants = ["light", "dark", "transparent"]
    outputs = [
        # Multiple favicon sizes
        OutputSpec(suffix="", scale=1.0, formats=["png"]),
    ]
    supports_svg = False

    # Additional sizes to render
    favicon_sizes = [16, 32, 48, 192]

    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        bg = self.get_bg_color(ctx, variant)
        canvas = PILImage.new("RGBA", (self.width, self.height), bg)
        logo = _fit_logo(ctx.logo_mark, int(self.width * 0.8), int(self.height * 0.8))
        _center_paste(canvas, logo, self.width // 2, self.height // 2)
        return canvas

    def render_at_size(self, ctx: BrandContext, variant: str, size: int) -> PILImage.Image:
        """Render favicon at a specific pixel size."""
        bg = self.get_bg_color(ctx, variant)
        canvas = PILImage.new("RGBA", (size, size), bg)
        padding = max(1, int(size * 0.1))
        logo = _fit_logo(ctx.logo_mark, size - 2 * padding, size - 2 * padding)
        _center_paste(canvas, logo, size // 2, size // 2)
        return canvas



def register_logo_templates() -> None:
    TemplateRegistry.register(LogoMarkTemplate())
    TemplateRegistry.register(PrimaryLogoTemplate())
    TemplateRegistry.register(StackedLogoTemplate())
    TemplateRegistry.register(WordmarkTemplate())
    TemplateRegistry.register(FaviconTemplate())
