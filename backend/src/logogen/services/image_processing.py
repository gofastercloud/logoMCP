from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image as PILImage, ImageFilter

logger = logging.getLogger(__name__)


def remove_white_background(
    image: PILImage.Image,
    threshold: int = 230,
) -> PILImage.Image:
    """Remove white/near-white background from a logo image.

    Converts bright pixels to transparent based on luminance threshold.
    Uses edge detection to preserve anti-aliased edges around the logo.
    """
    img = image.convert("RGBA")
    w, h = img.size
    pixels = img.load()

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            lum = int(0.299 * r + 0.587 * g + 0.114 * b)
            if lum >= threshold:
                pixels[x, y] = (r, g, b, 0)
            elif lum >= threshold - 20:
                # Soft edge: partial transparency
                alpha = int(255 * (threshold - lum) / 20)
                pixels[x, y] = (r, g, b, min(a, alpha))

    return img


def autocrop_to_content(
    image: PILImage.Image,
    padding_pct: float = 0.05,
) -> PILImage.Image:
    """Crop image to content bounding box with percentage-based padding.

    Finds the bounding box of non-transparent content and crops to it
    with uniform padding. This removes the excessive whitespace that
    Flux generates around logo marks.
    """
    img = image.convert("RGBA")

    # Get alpha channel bounding box
    bbox = img.getbbox()
    if bbox is None:
        return img  # Fully transparent, return as-is

    left, top, right, bottom = bbox
    content_w = right - left
    content_h = bottom - top

    # Add padding as percentage of content size
    pad = int(max(content_w, content_h) * padding_pct)
    left = max(0, left - pad)
    top = max(0, top - pad)
    right = min(img.width, right + pad)
    bottom = min(img.height, bottom + pad)

    # Make it square (logos should be square)
    crop_w = right - left
    crop_h = bottom - top
    if crop_w != crop_h:
        size = max(crop_w, crop_h)
        # Center the content in the square
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        left = max(0, cx - size // 2)
        top = max(0, cy - size // 2)
        right = min(img.width, left + size)
        bottom = min(img.height, top + size)
        # Adjust if we hit image edges
        if right - left < size:
            left = max(0, right - size)
        if bottom - top < size:
            top = max(0, bottom - size)

    cropped = img.crop((left, top, right, bottom))
    return cropped


def process_logo_mark(
    input_path: Path,
    output_path: Path | None = None,
    threshold: int = 230,
) -> PILImage.Image:
    """Full logo mark processing pipeline: remove bg → autocrop → save.

    This is the main entry point for preparing a Flux-generated logo
    for use in templates.
    """
    img = PILImage.open(input_path)

    # Step 1: Remove white background
    img = remove_white_background(img, threshold=threshold)

    # Step 2: Autocrop to content
    img = autocrop_to_content(img, padding_pct=0.08)

    if output_path is None:
        output_path = input_path
    img.save(str(output_path), "PNG")
    logger.info("Logo processed: %s → %s (%dx%d)", input_path, output_path, img.width, img.height)
    return img
