from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image as PILImage

from logogen.models.schemas import ColorEntry
from logogen.templates import BrandContext, TemplateRegistry
from logogen.templates.logo_variants import register_logo_templates


@pytest.fixture(autouse=True)
def clean_registry():
    TemplateRegistry.clear()
    yield
    TemplateRegistry.clear()


@pytest.fixture
def brand_ctx() -> BrandContext:
    logo = PILImage.new("RGBA", (256, 256), color=(0, 100, 200, 255))
    return BrandContext(
        brand_name="TestCo",
        tagline="Test tagline",
        logo_mark=logo,
        logo_mark_svg="<svg></svg>",
        colors=[
            ColorEntry(hex="#2E86AB", name="Blue", role="primary", rationale="Test"),
            ColorEntry(hex="#A23B72", name="Berry", role="secondary", rationale="Test"),
            ColorEntry(hex="#F18F01", name="Amber", role="accent", rationale="Test"),
            ColorEntry(hex="#333333", name="Dark", role="neutral", rationale="Test"),
            ColorEntry(hex="#FFFFFF", name="White", role="background", rationale="Test"),
        ],
        heading_font=None,
        body_font=None,
        heading_font_name="Inter",
        body_font_name="Source Sans Pro",
    )


class TestRenderAllTemplates:
    @patch("logogen.services.template_engine.BRANDS_DIR")
    def test_renders_all_templates(self, mock_brands_dir, brand_ctx, tmp_path):
        mock_brands_dir.__truediv__ = lambda self, x: tmp_path / x
        # Also need to handle the Path operations
        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir(parents=True)
        (brand_dir / "assets").mkdir()

        from logogen.services.template_engine import render_all_templates

        with patch("logogen.services.template_engine.BRANDS_DIR", tmp_path):
            records = render_all_templates(brand_ctx, "test-brand")

        assert len(records) > 0

        # Check we got records for all 5 templates
        slugs = {r["template_slug"] for r in records}
        assert "logo-mark" in slugs
        assert "logo-primary" in slugs
        assert "logo-stacked" in slugs
        assert "logo-wordmark" in slugs
        assert "logo-favicon" in slugs

        # Check we got light, dark, transparent variants
        variants = {r["variant"] for r in records}
        assert "light" in variants
        assert "dark" in variants
        assert "transparent" in variants

        # Check formats
        formats = {r["format"] for r in records}
        assert "png" in formats
        assert "jpeg" in formats
        assert "svg" in formats

        # Verify files actually exist
        for rec in records:
            filepath = tmp_path / "test-brand" / rec["file_path"]
            assert filepath.exists(), f"Missing: {filepath}"

    @patch("logogen.services.template_engine.BRANDS_DIR")
    def test_no_jpeg_for_transparent(self, mock_brands_dir, brand_ctx, tmp_path):
        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir(parents=True)
        (brand_dir / "assets").mkdir()

        from logogen.services.template_engine import render_all_templates

        with patch("logogen.services.template_engine.BRANDS_DIR", tmp_path):
            records = render_all_templates(brand_ctx, "test-brand")

        transparent_jpegs = [
            r for r in records
            if r["variant"] == "transparent" and r["format"] == "jpeg"
        ]
        assert len(transparent_jpegs) == 0

    @patch("logogen.services.template_engine.BRANDS_DIR")
    def test_favicon_multiple_sizes(self, mock_brands_dir, brand_ctx, tmp_path):
        brand_dir = tmp_path / "test-brand"
        brand_dir.mkdir(parents=True)
        (brand_dir / "assets").mkdir()

        from logogen.services.template_engine import render_all_templates

        with patch("logogen.services.template_engine.BRANDS_DIR", tmp_path):
            records = render_all_templates(brand_ctx, "test-brand")

        favicon_records = [r for r in records if r["template_slug"] == "logo-favicon"]
        favicon_sizes = {(r["width"], r["height"]) for r in favicon_records}
        # Should have 16, 32, 48, 192 sizes (192 is native)
        assert (16, 16) in favicon_sizes
        assert (32, 32) in favicon_sizes
        assert (48, 48) in favicon_sizes
        assert (192, 192) in favicon_sizes
