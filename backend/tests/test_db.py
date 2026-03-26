import pytest

from logogen.db.connection import get_test_db
from logogen.db import repository as repo
from logogen.models.schemas import (
    BrandBrief,
    BrandStatus,
    ColorEntry,
    CreativeDirection,
    TypographyRec,
)


@pytest.fixture
async def db():
    conn = await get_test_db()
    try:
        yield conn
    finally:
        await conn.close()


def _sample_brief(**overrides) -> BrandBrief:
    defaults = dict(
        company_name="Acme Corp",
        industry="Technology",
        target_audience="Developers",
        mood_keywords=["modern", "bold"],
    )
    defaults.update(overrides)
    return BrandBrief(**defaults)


def _sample_direction() -> CreativeDirection:
    return CreativeDirection(
        visual_style="Modern minimalist",
        mood_description="Clean and professional",
        logo_concepts=["Hexagon", "Arrow", "Node"],
        brand_voice="Confident",
        tagline="Build better",
    )


def _sample_palette() -> list[ColorEntry]:
    return [
        ColorEntry(hex="#2E86AB", name="Blue", role="primary", rationale="Trust"),
        ColorEntry(hex="#F5F5F5", name="Light", role="background", rationale="Clean"),
        ColorEntry(hex="#333333", name="Dark", role="neutral", rationale="Readable"),
    ]


def _sample_typography() -> TypographyRec:
    return TypographyRec(heading_font="Inter", body_font="Source Sans Pro", rationale="Modern")


class TestBrandCRUD:
    async def test_create_and_get(self, db):
        brief = _sample_brief()
        brand_id = await repo.create_brand(db, brief)
        assert brand_id

        brand = await repo.get_brand(db, brand_id)
        assert brand is not None
        assert brand.name == "Acme Corp"
        assert brand.status == BrandStatus.CREATED
        assert brand.brief.company_name == "Acme Corp"
        assert brand.specs is None
        assert brand.concepts == []

    async def test_list_brands(self, db):
        await repo.create_brand(db, _sample_brief(company_name="Brand A"))
        await repo.create_brand(db, _sample_brief(company_name="Brand B"))

        brands = await repo.list_brands(db)
        assert len(brands) == 2
        names = {b.name for b in brands}
        assert names == {"Brand A", "Brand B"}

    async def test_delete_brand(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        deleted = await repo.delete_brand(db, brand_id)
        assert deleted is True

        brand = await repo.get_brand(db, brand_id)
        assert brand is None

    async def test_delete_nonexistent(self, db):
        deleted = await repo.delete_brand(db, "nonexistent")
        assert deleted is False

    async def test_get_nonexistent(self, db):
        brand = await repo.get_brand(db, "nonexistent")
        assert brand is None

    async def test_update_status(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.update_brand_status(db, brand_id, BrandStatus.GENERATING)

        brand = await repo.get_brand(db, brand_id)
        assert brand.status == BrandStatus.GENERATING


class TestBrandSpecs:
    async def test_save_and_get_specs(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        direction = _sample_direction()
        palette = _sample_palette()
        typography = _sample_typography()

        await repo.save_brand_specs(db, brand_id, direction, palette, typography)

        specs = await repo.get_brand_specs(db, brand_id)
        assert specs is not None
        assert specs.creative_direction.visual_style == "Modern minimalist"
        assert specs.tagline == "Build better"
        assert len(specs.color_palette) == 3
        assert specs.typography.heading_font == "Inter"

    async def test_get_specs_nonexistent(self, db):
        specs = await repo.get_brand_specs(db, "nonexistent")
        assert specs is None

    async def test_update_specs_partial(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.save_brand_specs(
            db, brand_id, _sample_direction(), _sample_palette(), _sample_typography()
        )

        new_palette = [
            ColorEntry(hex="#FF0000", name="Red", role="primary", rationale="Energy"),
        ]
        await repo.update_brand_specs(db, brand_id, color_palette=new_palette)

        specs = await repo.get_brand_specs(db, brand_id)
        assert len(specs.color_palette) == 1
        assert specs.color_palette[0].hex == "#FF0000"
        # Typography unchanged
        assert specs.typography.heading_font == "Inter"

    async def test_specs_cascade_on_brand_delete(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.save_brand_specs(
            db, brand_id, _sample_direction(), _sample_palette(), _sample_typography()
        )
        await repo.delete_brand(db, brand_id)

        specs = await repo.get_brand_specs(db, brand_id)
        assert specs is None


class TestLogoConcepts:
    async def test_save_and_get_concepts(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        concepts = [
            {"concept_index": 0, "prompt": "wablogo concept 0", "image_path": "concepts/concept_0.png"},
            {"concept_index": 1, "prompt": "wablogo concept 1", "image_path": "concepts/concept_1.png"},
            {"concept_index": 2, "prompt": "wablogo concept 2", "image_path": "concepts/concept_2.png"},
        ]
        await repo.save_logo_concepts(db, brand_id, concepts)

        result = await repo.get_logo_concepts(db, brand_id)
        assert len(result) == 3
        assert result[0].concept_index == 0
        assert not result[0].is_selected

    async def test_select_concept(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        concepts = [
            {"concept_index": 0, "prompt": "p0", "image_path": "c0.png"},
            {"concept_index": 1, "prompt": "p1", "image_path": "c1.png"},
        ]
        await repo.save_logo_concepts(db, brand_id, concepts)

        selected = await repo.select_logo_concept(db, brand_id, 1)
        assert selected is True

        result = await repo.get_logo_concepts(db, brand_id)
        assert not result[0].is_selected
        assert result[1].is_selected

    async def test_reselect_concept(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        concepts = [
            {"concept_index": 0, "prompt": "p0", "image_path": "c0.png"},
            {"concept_index": 1, "prompt": "p1", "image_path": "c1.png"},
        ]
        await repo.save_logo_concepts(db, brand_id, concepts)

        await repo.select_logo_concept(db, brand_id, 0)
        await repo.select_logo_concept(db, brand_id, 1)

        result = await repo.get_logo_concepts(db, brand_id)
        assert not result[0].is_selected
        assert result[1].is_selected

    async def test_generation_run(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.save_logo_concepts(db, brand_id, [
            {"concept_index": 0, "prompt": "run1", "image_path": "r1c0.png"},
        ], generation_run=1)
        await repo.save_logo_concepts(db, brand_id, [
            {"concept_index": 0, "prompt": "run2", "image_path": "r2c0.png"},
        ], generation_run=2)

        # Default: current run only
        result = await repo.get_logo_concepts(db, brand_id)
        assert len(result) == 1
        assert result[0].prompt == "run2"

    async def test_max_generation_run(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        assert await repo.get_max_generation_run(db, brand_id) == 0

        await repo.save_logo_concepts(db, brand_id, [
            {"concept_index": 0, "prompt": "p", "image_path": "c.png"},
        ], generation_run=3)
        assert await repo.get_max_generation_run(db, brand_id) == 3


class TestRenderedAssets:
    async def test_save_and_get_assets(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.save_rendered_asset(
            db, brand_id, "logo-primary", "light", "png", "1x",
            "assets/logo-primary/light.png", 1200, 400,
        )
        await repo.save_rendered_asset(
            db, brand_id, "logo-primary", "dark", "png", "1x",
            "assets/logo-primary/dark.png", 1200, 400,
        )

        assets = await repo.get_rendered_assets(db, brand_id)
        assert len(assets) == 2

    async def test_delete_assets(self, db):
        brand_id = await repo.create_brand(db, _sample_brief())
        await repo.save_rendered_asset(
            db, brand_id, "logo-primary", "light", "png", "1x",
            "path.png", 100, 100,
        )
        await repo.delete_rendered_assets(db, brand_id)

        assets = await repo.get_rendered_assets(db, brand_id)
        assert len(assets) == 0
