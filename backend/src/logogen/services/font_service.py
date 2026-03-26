from __future__ import annotations

import logging
import urllib.request
import urllib.parse
from pathlib import Path

from logogen.config import FONTS_DIR

logger = logging.getLogger(__name__)

# Google Fonts CSS API — returns CSS with TTF URLs
_GOOGLE_FONTS_CSS_URL = "https://fonts.googleapis.com/css2?family={family}&display=swap"
# User-agent that triggers TTF (not woff2) URLs
_TTF_USER_AGENT = "Mozilla/4.0"


def _find_system_font() -> Path | None:
    candidates = [
        Path("/System/Library/Fonts/Helvetica.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/SFNSText.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _download_google_font(font_name: str, dest_dir: Path) -> Path | None:
    """Download a font from Google Fonts API."""
    try:
        family = urllib.parse.quote(font_name)
        url = _GOOGLE_FONTS_CSS_URL.format(family=family)

        req = urllib.request.Request(url, headers={"User-Agent": _TTF_USER_AGENT})
        with urllib.request.urlopen(req, timeout=15) as resp:
            css = resp.read().decode("utf-8")

        # Extract first TTF URL from CSS
        import re
        ttf_urls = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.ttf)\)", css)
        if not ttf_urls:
            logger.warning("No TTF URLs found in Google Fonts CSS for '%s'", font_name)
            return None

        ttf_url = ttf_urls[0]
        safe_name = font_name.replace(" ", "") + ".ttf"
        dest = dest_dir / safe_name

        logger.info("Downloading %s → %s", ttf_url, dest)
        urllib.request.urlretrieve(ttf_url, str(dest))
        return dest

    except Exception as e:
        logger.warning("Failed to download Google Font '%s': %s", font_name, e)
        return None


def ensure_font(font_name: str) -> Path | None:
    """Get a font by name. Downloads from Google Fonts if not cached.

    Returns path to TTF file, or None if unavailable.
    """
    if not font_name or font_name.strip() == "":
        return _find_system_font()

    FONTS_DIR.mkdir(parents=True, exist_ok=True)

    # Check cache
    safe_name = font_name.replace(" ", "")
    cached = list(FONTS_DIR.glob(f"{safe_name}*.ttf")) + list(FONTS_DIR.glob(f"{safe_name}*.TTF"))
    if cached:
        return cached[0]

    # Download
    result = _download_google_font(font_name, FONTS_DIR)
    if result:
        return result

    # Fallback to system font
    fallback = _find_system_font()
    if fallback:
        logger.info("Using system fallback font: %s", fallback)
    return fallback
