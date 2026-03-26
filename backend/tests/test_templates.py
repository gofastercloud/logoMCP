from pathlib import Path

import pytest
from PIL import Image as PILImage

from logogen.models.schemas import ColorEntry, TemplateCategory
from logogen.templates import BrandContext, TemplateRegistry, hex_to_rgba
from logogen.templates.logo_variants import (
    FaviconTemplate,
    LogoMarkTemplate,
    PrimaryLogoTemplate,
    StackedLogoTemplate,
    WordmarkTemplate,
    register_logo_templates,
)


@pytest.fixture
def brand_ctx(tmp_path: Path) -> BrandContext:
    """Create a minimal BrandContext for testing."""
    logo = PILImage.new("RGBA", (256, 256), color=(255, 0, 0, 255))
    return BrandContext(
        brand_name="TestBrand",
        tagline="Test tagline",
        logo_mark=logo,
        logo_mark_svg="<svg></svg>",
        colors=[
            ColorEntry(hex="#2E86AB", name="Blue", role="primary", rationale="Test"),
            ColorEntry(hex="#A23B72", name="Berry", role="secondary", rationale="Test"),
            ColorEntry(hex="#F18F01", name="Amber", role="accent", rationale="Test"),
            ColorEntry(hex="#333333", name="Dark", role="neutral", rationale="Test"),
            ColorEntry(hex="#F5F5F5", name="Light", role="background", rationale="Test"),
        ],
        heading_font=None,
        body_font=None,
        heading_font_name="Inter",
        body_font_name="Source Sans Pro",
    )


class TestHexToRgba:
    def test_basic(self):
        assert hex_to_rgba("#FF0000") == (255, 0, 0, 255)
        assert hex_to_rgba("#00FF00") == (0, 255, 0, 255)

    def test_with_alpha(self):
        assert hex_to_rgba("#FF0000", alpha=128) == (255, 0, 0, 128)


class TestBrandContext:
    def test_get_color_by_role(self, brand_ctx):
        assert brand_ctx.get_color("primary") == "#2E86AB"
        assert brand_ctx.get_color("background") == "#F5F5F5"

    def test_get_color_fallback(self, brand_ctx):
        brand_ctx.colors = []
        assert brand_ctx.get_color("primary") == "#333333"

    def test_get_dark_bg(self, brand_ctx):
        assert brand_ctx.get_dark_bg() == "#333333"

    def test_get_light_bg(self, brand_ctx):
        assert brand_ctx.get_light_bg() == "#F5F5F5"


class TestTemplateRegistry:
    def setup_method(self):
        TemplateRegistry.clear()

    def test_register_and_get(self):
        t = LogoMarkTemplate()
        TemplateRegistry.register(t)
        assert TemplateRegistry.get("logo-mark") is t

    def test_all(self):
        register_logo_templates()
        templates = TemplateRegistry.all()
        assert len(templates) == 5

    def test_by_category(self):
        register_logo_templates()
        logos = TemplateRegistry.by_category(TemplateCategory.LOGO_VARIANT)
        assert len(logos) == 5

    def test_get_nonexistent(self):
        assert TemplateRegistry.get("nonexistent") is None

    def teardown_method(self):
        TemplateRegistry.clear()


class TestLogoMarkTemplate:
    def test_render_light(self, brand_ctx):
        t = LogoMarkTemplate()
        img = t.render(brand_ctx, "light")
        assert img.size == (1024, 1024)
        assert img.mode == "RGBA"

    def test_render_dark(self, brand_ctx):
        t = LogoMarkTemplate()
        img = t.render(brand_ctx, "dark")
        assert img.size == (1024, 1024)
        # Check that background is dark
        bg_pixel = img.getpixel((0, 0))
        assert bg_pixel[0] < 100  # R should be low (dark)

    def test_render_transparent(self, brand_ctx):
        t = LogoMarkTemplate()
        img = t.render(brand_ctx, "transparent")
        bg_pixel = img.getpixel((0, 0))
        assert bg_pixel[3] == 0  # Alpha should be 0

    def test_render_svg(self, brand_ctx):
        t = LogoMarkTemplate()
        svg = t.render_svg(brand_ctx, "light")
        assert svg == "<svg></svg>"


class TestPrimaryLogoTemplate:
    def test_render(self, brand_ctx):
        t = PrimaryLogoTemplate()
        img = t.render(brand_ctx, "light")
        assert img.size == (1200, 400)

    def test_render_dark(self, brand_ctx):
        t = PrimaryLogoTemplate()
        img = t.render(brand_ctx, "dark")
        assert img.size == (1200, 400)


class TestStackedLogoTemplate:
    def test_render(self, brand_ctx):
        t = StackedLogoTemplate()
        img = t.render(brand_ctx, "light")
        assert img.size == (800, 800)


class TestWordmarkTemplate:
    def test_render(self, brand_ctx):
        t = WordmarkTemplate()
        img = t.render(brand_ctx, "light")
        assert img.size == (1200, 300)

    def test_render_dark(self, brand_ctx):
        t = WordmarkTemplate()
        img = t.render(brand_ctx, "dark")
        assert img.size == (1200, 300)


class TestFaviconTemplate:
    def test_render_native(self, brand_ctx):
        t = FaviconTemplate()
        img = t.render(brand_ctx, "light")
        assert img.size == (192, 192)

    def test_render_at_size(self, brand_ctx):
        t = FaviconTemplate()
        for size in [16, 32, 48]:
            img = t.render_at_size(brand_ctx, "transparent", size)
            assert img.size == (size, size)
