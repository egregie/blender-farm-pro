"""Geometry only. OCR is Task 8's business; if this test needed Tesseract it
would report recogniser problems as deskew bugs."""
import unittest

import numpy as np
from PIL import Image, ImageDraw

from src.deskew import flatten_face, perspective_coefficients


def _forward_warp(img, dst_quad):
    """Project a rectangular image onto `dst_quad` inside a white canvas."""
    w, h = img.size
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    canvas = Image.new("RGB", (w, h), "white")
    coeffs = perspective_coefficients(src, dst_quad)
    warped = img.transform((w, h), Image.PERSPECTIVE, coeffs, Image.BICUBIC,
                           fillcolor=(255, 255, 255))
    canvas.paste(warped)
    return canvas


class TestFlattenFace(unittest.TestCase):
    def setUp(self):
        # A white card with one black square at a known place: 20%-40% across,
        # 10%-30% down.
        self.card = Image.new("RGB", (600, 400), "white")
        ImageDraw.Draw(self.card).rectangle([120, 40, 240, 120], fill="black")
        self.quad = [(90.0, 70.0), (540.0, 20.0), (560.0, 350.0), (60.0, 300.0)]

    def test_flattening_undoes_a_known_warp(self):
        warped = _forward_warp(self.card, self.quad)
        flat = flatten_face(warped, self.quad, out_width=600, aspect=400 / 600)
        self.assertEqual(flat.size, (600, 400))

        a = np.asarray(flat.convert("L")).astype(float)
        ys, xs = np.nonzero(a < 128)
        self.assertGreater(len(xs), 500, "the black square did not survive")
        # Tolerance is 12 px on a 600 px width: resampling twice softens edges,
        # but a misordered corner would move these by hundreds of pixels.
        self.assertAlmostEqual(xs.min(), 120, delta=12)
        self.assertAlmostEqual(xs.max(), 240, delta=12)
        self.assertAlmostEqual(ys.min(), 40, delta=12)
        self.assertAlmostEqual(ys.max(), 120, delta=12)

    def test_aspect_defaults_to_the_quads_own_proportions(self):
        flat = flatten_face(self.card, self.quad, out_width=600)
        self.assertEqual(flat.width, 600)
        self.assertGreater(flat.height, 200)
        self.assertLess(flat.height, 600)

    def test_accepts_a_path(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "card.png"
            self.card.save(p)
            flat = flatten_face(p, self.quad, out_width=300)
            self.assertEqual(flat.width, 300)

    def test_rejects_a_quad_that_is_not_four_corners(self):
        with self.assertRaises(ValueError):
            flatten_face(self.card, self.quad[:3])


if __name__ == "__main__":
    unittest.main()
