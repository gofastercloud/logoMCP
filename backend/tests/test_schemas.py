import pytest
from pydantic import ValidationError

from logogen.models.schemas import (
    AssetInfo,
    BrandBrief,
    BrandDetail,
    BrandSpecs,
    BrandStatus,
    BrandSummary,
    ColorEntry,
    CreativeDirection,
    LogoConcept,
    LogoPrompts,
    TemplateCategory,
    TextGenResult,
    TypographyRec,
)
from datetime import datetime, timezone


class TestBrandBrief:
    def test_valid_brief(self):
        brief = BrandBrief(
            company_name="Acme Corp",
            industry="Technology",
            target_audience="Small business owners aged 30-50",
            mood_keywords=["modern", "bold", "trustworthy"],
        )
        assert brief.company_name == "Acme Corp"
        assert brief.color_preferences is None
        assert brief.description is None

    def test_valid_brief_with_optionals(self):
        brief = BrandBrief(
            company_name="Acme Corp",
            industry="Technology",
            target_audience="Developers",
            mood_keywords=["minimal"],
            color_preferences=["#FF5733", "#2E86AB"],
            description="A developer tools company",
        )
        assert brief.color_preferences == ["#FF5733", "#2E86AB"]

    def test_empty_company_name_rejected(self):
        with pytest.raises(ValidationError):
            BrandBrief(
                company_name="",
                industry="Tech",
                target_audience="Devs",
                mood_keywords=["bold"],
            )

    def test_empty_mood_keywords_rejected(self):
        with pytest.raises(ValidationError):
            BrandBrief(
                company_name="Acme",
                industry="Tech",
                target_audience="Devs",
                mood_keywords=[],
            )

    def test_too_many_mood_keywords_rejected(self):
        with pytest.raises(ValidationError):
            BrandBrief(
                company_name="Acme",
                industry="Tech",
                target_audience="Devs",
                mood_keywords=[f"kw{i}" for i in range(11)],
            )


class TestColorEntry:
    def test_valid_color(self):
        c = ColorEntry(
            hex="#FF5733", name="Coral", role="primary", rationale="Warm and inviting"
        )
        assert c.hex == "#FF5733"

    def test_invalid_hex_rejected(self):
        with pytest.raises(ValidationError):
            ColorEntry(hex="FF5733", name="Coral", role="primary", rationale="test")

    def test_invalid_role_rejected(self):
        with pytest.raises(ValidationError):
            ColorEntry(hex="#FF5733", name="Coral", role="tertiary", rationale="test")


class TestTypographyRec:
    def test_valid(self):
        t = TypographyRec(
            heading_font="Inter",
            body_font="Source Sans Pro",
            rationale="Clean and modern",
        )
        assert t.heading_font == "Inter"


class TestCreativeDirection:
    def test_valid_with_tagline(self):
        d = CreativeDirection(
            visual_style="Modern minimalist",
            mood_description="Clean and professional",
            logo_concepts=["Abstract hexagon", "Upward arrow"],
            brand_voice="Confident",
            tagline="Build faster, ship smarter",
        )
        assert d.tagline == "Build faster, ship smarter"


class TestLogoPrompts:
    def test_valid(self):
        p = LogoPrompts(
            concept_1="wablogo, logo, Minimalist, abstract hexagon",
            concept_2="wablogo, logo, Minimalist, upward arrow",
            concept_3="wablogo, logo, Minimalist, interconnected nodes",
        )
        assert p.concept_1.startswith("wablogo")


class TestTextGenResult:
    def test_valid(self):
        result = TextGenResult(
            creative_direction=CreativeDirection(
                visual_style="Modern minimalist",
                mood_description="Clean and professional",
                logo_concepts=["Abstract geometric shape"],
                brand_voice="Confident and approachable",
                tagline="Build better brands",
            ),
            logo_prompts=LogoPrompts(
                concept_1="wablogo, logo, Minimalist, abstract shape",
                concept_2="wablogo, logo, Minimalist, simple icon",
                concept_3="wablogo, logo, Minimalist, geometric mark",
            ),
            color_palette=[
                ColorEntry(hex="#2E86AB", name="Ocean Blue", role="primary", rationale="Trust"),
                ColorEntry(hex="#F5F5F5", name="Light Gray", role="background", rationale="Clean"),
                ColorEntry(hex="#333333", name="Charcoal", role="neutral", rationale="Readable"),
            ],
            typography=TypographyRec(
                heading_font="Inter",
                body_font="Source Sans Pro",
                rationale="Modern pairing",
            ),
        )
        assert len(result.color_palette) == 3


class TestAssetInfo:
    def test_valid(self):
        a = AssetInfo(
            template_slug="logo-primary",
            template_name="Primary Logo",
            category=TemplateCategory.LOGO_VARIANT,
            variant="light",
            format="png",
            scale="1x",
            width=1200,
            height=400,
            file_path="brands/abc/assets/logo-primary/light.png",
        )
        assert a.template_slug == "logo-primary"


class TestBrandSummary:
    def test_valid(self):
        now = datetime.now(timezone.utc)
        s = BrandSummary(
            id="abc123",
            name="Acme Corp",
            status=BrandStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        assert s.status == BrandStatus.CREATED


class TestBrandDetail:
    def test_minimal(self):
        now = datetime.now(timezone.utc)
        d = BrandDetail(
            id="abc123",
            name="Acme Corp",
            status=BrandStatus.CREATED,
            brief=BrandBrief(
                company_name="Acme Corp",
                industry="Tech",
                target_audience="Devs",
                mood_keywords=["modern"],
            ),
            created_at=now,
            updated_at=now,
        )
        assert d.specs is None
        assert d.concepts == []
        assert d.assets == []

    def test_with_specs_and_concepts(self):
        now = datetime.now(timezone.utc)
        d = BrandDetail(
            id="abc123",
            name="Acme Corp",
            status=BrandStatus.READY,
            brief=BrandBrief(
                company_name="Acme Corp",
                industry="Tech",
                target_audience="Devs",
                mood_keywords=["modern"],
            ),
            specs=BrandSpecs(
                creative_direction=CreativeDirection(
                    visual_style="Bold",
                    mood_description="Energetic",
                    logo_concepts=["Lightning bolt"],
                    brand_voice="Dynamic",
                    tagline="Move fast",
                ),
                color_palette=[
                    ColorEntry(hex="#FF0000", name="Red", role="primary", rationale="Energy"),
                    ColorEntry(hex="#000000", name="Black", role="neutral", rationale="Contrast"),
                    ColorEntry(hex="#FFFFFF", name="White", role="background", rationale="Clean"),
                ],
                typography=TypographyRec(
                    heading_font="Montserrat",
                    body_font="Open Sans",
                    rationale="Bold and readable",
                ),
                tagline="Move fast",
            ),
            concepts=[
                LogoConcept(concept_index=0, prompt="wablogo...", is_selected=True, image_path="concepts/concept_0.png"),
                LogoConcept(concept_index=1, prompt="wablogo...", is_selected=False, image_path="concepts/concept_1.png"),
            ],
            created_at=now,
            updated_at=now,
        )
        assert d.specs is not None
        assert len(d.concepts) == 2
