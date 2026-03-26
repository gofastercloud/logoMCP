from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PIL import Image as PILImage

from logogen.models.schemas import ColorEntry, TemplateCategory


@dataclass
class BrandContext:
    brand_name: str
    tagline: str | None
    logo_mark: PILImage.Image
    logo_mark_svg: str | None
    colors: list[ColorEntry]
    heading_font: Path | None
    body_font: Path | None
    heading_font_name: str
    body_font_name: str

    def get_color(self, role: str) -> str:
        for c in self.colors:
            if c.role == role:
                return c.hex
        defaults = {
            "primary": "#333333",
            "secondary": "#666666",
            "accent": "#0066CC",
            "neutral": "#4A4A4A",
            "background": "#FFFFFF",
        }
        return defaults.get(role, "#333333")

    def get_dark_bg(self) -> str:
        """Get the darkest color from the palette for dark backgrounds."""
        if not self.colors:
            return "#1A1A2E"
        # Find the darkest color by luminance
        darkest = None
        darkest_lum = float("inf")
        for c in self.colors:
            r, g, b = int(c.hex[1:3], 16), int(c.hex[3:5], 16), int(c.hex[5:7], 16)
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            if lum < darkest_lum:
                darkest_lum = lum
                darkest = c.hex
        # If the darkest color is still too light (lum > 100), use a hardcoded dark
        if darkest_lum > 100:
            return "#1A1A2E"
        return darkest

    def get_light_bg(self) -> str:
        return self.get_color("background")


@dataclass
class OutputSpec:
    suffix: str
    scale: float
    formats: list[str]


DEFAULT_OUTPUTS = [
    OutputSpec(suffix="", scale=1.0, formats=["png", "jpeg"]),
    OutputSpec(suffix="@2x", scale=2.0, formats=["png"]),
]

LOGO_OUTPUTS = [
    OutputSpec(suffix="", scale=1.0, formats=["png", "jpeg", "svg"]),
    OutputSpec(suffix="@2x", scale=2.0, formats=["png"]),
]


def hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return (r, g, b, alpha)


class BaseTemplate(ABC):
    slug: str
    name: str
    category: TemplateCategory
    width: int
    height: int
    variants: list[str]
    outputs: list[OutputSpec]
    supports_svg: bool = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not getattr(cls, 'variants', None):
            cls.variants = ["light", "dark", "transparent"]
        if not getattr(cls, 'outputs', None):
            cls.outputs = DEFAULT_OUTPUTS

    @abstractmethod
    def render(self, ctx: BrandContext, variant: str) -> PILImage.Image:
        ...

    def render_svg(self, ctx: BrandContext, variant: str) -> str | None:
        return None

    def get_bg_color(self, ctx: BrandContext, variant: str) -> tuple[int, int, int, int]:
        """Get background color for variant. Light/dark are hardcoded for consistency."""
        if variant == "transparent":
            return (0, 0, 0, 0)
        elif variant == "dark":
            return (26, 26, 46, 255)  # #1A1A2E — always dark regardless of palette
        else:
            return (255, 255, 255, 255)  # Always white for light variant

    def get_text_color(self, ctx: BrandContext, variant: str) -> tuple[int, int, int, int]:
        """Get text color appropriate for variant background."""
        if variant == "dark" or variant == "transparent":
            return (255, 255, 255, 255)
        # Light variant: use the brand's primary color for visual interest
        return hex_to_rgba(ctx.get_color("primary"))


class TemplateRegistry:
    _templates: dict[str, BaseTemplate] = {}

    @classmethod
    def register(cls, template: BaseTemplate) -> None:
        cls._templates[template.slug] = template

    @classmethod
    def get(cls, slug: str) -> BaseTemplate | None:
        return cls._templates.get(slug)

    @classmethod
    def all(cls) -> list[BaseTemplate]:
        return list(cls._templates.values())

    @classmethod
    def by_category(cls, category: TemplateCategory) -> list[BaseTemplate]:
        return [t for t in cls._templates.values() if t.category == category]

    @classmethod
    def clear(cls) -> None:
        cls._templates.clear()
