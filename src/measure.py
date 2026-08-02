"""Pixel measurement of a rendered packshot.

Lives here rather than in the test suite because both the calibration gate in
tests/test_blender_carton.py and scripts/catalogue_sweep.py need it, and a
script that imports from tests/ inverts the dependency — tests carry no
API-stability contract, and the script would stop working anywhere tests/ is
absent. Copying it instead would give a calibrated measurement two homes and
guarantee they drift.

Not importable inside Blender: this is project-side analysis of a finished PNG,
not part of building the scene.
"""
from __future__ import annotations

# Front-face brightness band, measured off all nine curated references through
# the sampling below. reference_analysis.md §3 is the prose version.
FRONT_FACE_MIN, FRONT_FACE_MAX = 235.0, 241.5
BACKDROP_MIN, BACKDROP_MAX_SD = 250.0, 1.0


def _front_face_and_background(png_path, accent_hex):
    """Mean brightness of the carton's front face, and of the backdrop.

    The front face is sampled as a band immediately above the accent stripe,
    following the stripe's slope column by column. A plain image-space rectangle
    would also catch the TOP face on a flat carton (T3 is 140x35mm), which is
    legitimately brighter, and report it as the front face blowing out.
    """
    import numpy as np
    from PIL import Image

    from numpy.lib.stride_tricks import sliding_window_view

    a = np.asarray(Image.open(png_path).convert("RGB")).astype(float)
    H, W, _ = a.shape
    g = a.mean(axis=2)
    # Only locally FLAT pixels count as "the paper". Glyphs are dark enough to
    # fall out on brightness alone, but their antialiased edges are mid-grey and
    # neutral, and on a shallow T3 face they fill enough of the sampled band to
    # drag the mean below the reference floor. Measure the board, not the print.
    win = 7
    flat = np.zeros_like(g, bool)
    sd = sliding_window_view(g, (win, win)).std(axis=(2, 3))
    flat[win // 2:win // 2 + sd.shape[0], win // 2:win // 2 + sd.shape[1]] = sd < 1.5
    accent = np.array([int(accent_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)],
                      dtype=float)
    stripe = ((a.max(axis=2) - a.min(axis=2)) > 15) & \
             (np.linalg.norm(a - accent, axis=2) < 110)
    stripe[:H // 2, :] = False                       # the band is on the lower half
    if stripe.sum() < 40:
        raise AssertionError(f"no accent stripe found in {png_path}")
    sx = np.nonzero(stripe)[1]
    pad, band = int(0.02 * W), int(0.05 * H)
    region = np.zeros_like(g, bool)
    for x in range(sx.min() + pad, sx.max() - pad):
        col = np.nonzero(stripe[:, x])[0]
        if col.size:
            region[max(0, col.min() - pad - band):max(0, col.min() - pad), x] = True
    front = g[region & flat & (g > 120)]
    corner = g[int(0.03 * H):int(0.11 * H), int(0.03 * W):int(0.11 * W)]
    return front.mean(), corner.mean(), corner.std()
