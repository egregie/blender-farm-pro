"""Flatten the carton's front face so its printed text can be read.

A packshot is shot with the carton rotated 27.5-35 degrees about Z, which puts
every label row on a perspective-skewed plane. Tesseract reads that badly.
Measured on 2026-08-03 against six real renders: "Atomoxetine Generic" came back
as "Germetine", "Tramadol" as "{ra m a d O", and 11-min returned an empty string
-- in page-segmentation modes 3, 6, 11 and 12 alike. The same four strings drawn
flat in the same vendored DejaVu at the same cap heights read 4 of 4 cleanly.
The rotation is the whole problem, so undoing it is the whole fix.

Corners come from the renderer's {stem}.view.json, never from the image. Two
probes tried to recover them by colour-matching the accent stripe: the mask
cannot separate the stripe from the brand badge when palette.primary and
palette.accent are close, and the SVD principal axis is sign-ambiguous.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def perspective_coefficients(src_quad, dst_quad) -> np.ndarray:
    """The eight coefficients PIL's PERSPECTIVE transform wants.

    PIL samples backwards -- for each output pixel it asks where in the source
    to read -- so the map it needs runs destination to source, which is why
    dst_quad supplies the left-hand side below.
    """
    a, b = [], []
    for (sx, sy), (dx, dy) in zip(src_quad, dst_quad):
        a.append([dx, dy, 1, 0, 0, 0, -sx * dx, -sx * dy])
        a.append([0, 0, 0, dx, dy, 1, -sy * dx, -sy * dy])
        b += [sx, sy]
    return np.linalg.solve(np.asarray(a, dtype=float), np.asarray(b, dtype=float))


def flatten_face(image, corners, out_width: int = 1500, aspect: float | None = None):
    """Return quadrilateral *corners* of *image* as an axis-aligned image.

    corners:   [top-left, top-right, bottom-right, bottom-left] in pixels, the
               order 05_assets/blender/render_driver.py emits.
    out_width: width of the returned image in pixels.
    aspect:    height / width of the real face. Defaults to the quad's own
               averaged edge ratio, which is close enough for OCR and needs no
               knowledge of the carton.
    """
    if corners is None or len(corners) != 4:
        raise ValueError(
            f"need exactly four corners in TL, TR, BR, BL order; got "
            f"{0 if corners is None else len(corners)}")

    img = image if isinstance(image, Image.Image) else Image.open(Path(image))
    img = img.convert("RGB")

    tl, tr, br, bl = [(float(c[0]), float(c[1])) for c in corners]
    if aspect is None:
        top = float(np.hypot(tr[0] - tl[0], tr[1] - tl[1]))
        bottom = float(np.hypot(br[0] - bl[0], br[1] - bl[1]))
        left = float(np.hypot(bl[0] - tl[0], bl[1] - tl[1]))
        right = float(np.hypot(br[0] - tr[0], br[1] - tr[1]))
        width = (top + bottom) / 2.0
        aspect = ((left + right) / 2.0 / width) if width else 1.0

    out_h = max(1, int(round(out_width * aspect)))
    dst = [(0, 0), (out_width, 0), (out_width, out_h), (0, out_h)]
    coeffs = perspective_coefficients([tl, tr, br, bl], dst)
    return img.transform((out_width, out_h), Image.PERSPECTIVE, coeffs,
                         Image.BICUBIC, fillcolor=(255, 255, 255))
