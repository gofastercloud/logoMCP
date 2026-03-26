from __future__ import annotations

import logging
from pathlib import Path

import vtracer

logger = logging.getLogger(__name__)


def trace_to_svg(input_path: Path, output_path: Path | None = None) -> str:
    """Convert a PNG image to SVG using vtracer.

    Returns the SVG string. Also saves to output_path if provided.
    """
    if output_path is None:
        output_path = input_path.with_suffix(".svg")

    logger.info("Tracing %s → %s", input_path, output_path)

    vtracer.convert_image_to_svg_py(
        str(input_path),
        str(output_path),
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    )

    svg_str = output_path.read_text()
    logger.info("SVG trace complete: %d bytes", len(svg_str))
    return svg_str
