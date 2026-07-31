"""Art-direction invariants of the procedural Blender carton.

These assert GEOMETRY, not pixels. The driver runs inside Blender's own bundled
interpreter, so `bpy` can never be imported from the project's Python; instead
the driver is invoked headless with --dump-scene, which builds the scene and
writes the measured geometry as JSON without rendering. Measuring the built
scene is both far cheaper than a render and far less brittle than inspecting
pixels — and it is the only way these rules can be checked in the normal suite.

The rules under test come from, in order of authority:
  * src/passport_generator.py — the front-panel grid ("Row 6 / Accent Stripe:
    ... at the very bottom edge of the FRONT FACE") and the [SURFACE COLOUR
    MANDATE] in the prompt templates;
  * 01_input_raster/reference_analysis.md §4-§5, which confirms both against
    direct inspection of the curated reference renders;
  * CLAUDE.md, which summarises them as the fork's hard constraints.

Skipped rather than failed when Blender is not installed, so the suite still
runs on a machine that only exercises the Gemini engine.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.utils import load_config, resolve_path

_ROOT = Path(__file__).resolve().parents[1]
_CFG = load_config()
_BLENDER_EXE = _CFG["blender"]["executable"]
_DRIVER = str(resolve_path(_CFG["blender"]["driver_script"]))

# 1-min is the SKU the reference set was analysed against (T1_1.webp), and its
# palette makes every rule falsifiable: primary #DDA7A5 is a pink that would be
# unmistakable if it leaked onto the body, and accent #6B2D5C is distinct from it.
_SKU = "1-min"
_PALETTE_PRIMARY = "#DDA7A5"
_PALETTE_ACCENT = "#6B2D5C"


def _blender_available() -> bool:
    return bool(_BLENDER_EXE) and Path(_BLENDER_EXE).exists()


def _manifest_path() -> Path:
    return _ROOT / "04_passports" / "render_manifests" / f"{_SKU}.json"


@unittest.skipUnless(_blender_available(), f"Blender not installed at {_BLENDER_EXE}")
@unittest.skipUnless(_manifest_path().exists(), "render manifest for 1-min not generated")
class TestBlenderCarton(unittest.TestCase):
    """One Blender launch for the whole class — it costs a few seconds."""

    scene: dict

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.mkdtemp(prefix="carton_dump_")
        dump = Path(cls._tmp) / "scene.json"
        proc = subprocess.run(
            [_BLENDER_EXE, "--background", "--factory-startup",
             "--python", _DRIVER, "--",
             "--job", str(_manifest_path()), "--dump-scene", str(dump)],
            capture_output=True, text=True, timeout=300,
        )
        if not dump.exists():
            raise AssertionError(
                f"--dump-scene produced nothing (exit={proc.returncode}):\n"
                f"{(proc.stderr or proc.stdout)[-2000:]}"
            )
        cls.scene = json.loads(dump.read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp, ignore_errors=True)

    # ── body colour ──────────────────────────────────────────────────────────
    def test_carton_body_is_white_not_palette_primary(self):
        """[SURFACE COLOUR MANDATE]: the body is white on every SKU.

        Regression guard: the body used to be painted palette.primary, which
        rendered 1-min as a pink box.
        """
        body = self.scene["carton"]["material"]
        self.assertEqual(body["base_color_hex"], "#FFFFFF")
        self.assertNotEqual(
            body["base_color_hex"].upper(), _PALETTE_PRIMARY,
            "carton body is painted palette.primary — brand colour belongs "
            "only on the stripe and the badge",
        )

    def test_carton_body_is_matte_cardboard(self):
        """Roughness ~0.6-0.8; 0.5 read as semi-gloss."""
        self.assertGreaterEqual(self.scene["carton"]["material"]["roughness"], 0.6)
        self.assertLessEqual(self.scene["carton"]["material"]["roughness"], 0.8)

    # ── accent stripe: Row 6, very bottom edge, full width ───────────────────
    def test_accent_stripe_exists_and_uses_palette_accent(self):
        stripe = self.scene["accent_stripe"]
        self.assertIsNotNone(stripe, "no accent stripe was built")
        self.assertEqual(stripe["material"]["base_color_hex"].upper(), _PALETTE_ACCENT)

    def test_accent_stripe_sits_at_the_very_bottom_edge(self):
        """Row 6 is at the bottom edge, not mid-face.

        Regression guard: the stripe centre used to be at 55% of face height.
        """
        stripe = self.scene["accent_stripe"]
        self.assertAlmostEqual(
            stripe["bottom_y_fraction"], 0.0, delta=0.01,
            msg="stripe's lower edge is not flush with the carton's bottom edge",
        )
        self.assertLess(
            stripe["face_y_fraction"], 0.15,
            "stripe centre is too high up the face to be a bottom stripe",
        )

    def test_accent_stripe_thickness_within_documented_band(self):
        """8-12% of front-face height."""
        self.assertGreaterEqual(self.scene["accent_stripe"]["height_fraction"], 0.08)
        self.assertLessEqual(self.scene["accent_stripe"]["height_fraction"], 0.12)

    def test_accent_stripe_spans_the_full_width(self):
        """'thin FULL-WIDTH horizontal colour band' — it used to span 49%."""
        self.assertAlmostEqual(
            self.scene["accent_stripe"]["width_fraction"], 1.0, delta=0.02)
        self.assertAlmostEqual(
            self.scene["accent_stripe"]["face_x_fraction"], 0.0, delta=0.01)

    # ── brand badge: top-right corner of the front face ──────────────────────
    def test_brand_badge_exists_and_uses_palette_primary(self):
        """`badge_bg_hex = primary_hex` in the front-panel grid — the badge
        takes the BRAND colour, which is not the stripe's accent."""
        badge = self.scene["brand_badge"]
        self.assertIsNotNone(badge, "no brand badge was built")
        self.assertEqual(badge["material"]["base_color_hex"].upper(), _PALETTE_PRIMARY)

    def test_brand_badge_is_in_the_top_right_corner(self):
        badge = self.scene["brand_badge"]
        self.assertGreater(badge["face_y_fraction"], 0.8, "badge is not near the top")
        self.assertGreater(badge["face_x_fraction"], 0.3, "badge is not near the right")

    def test_brand_badge_is_a_small_square(self):
        """'approximately 6-8% of panel width', and subordinate to typography."""
        badge = self.scene["brand_badge"]
        self.assertGreaterEqual(badge["width_fraction"], 0.06)
        self.assertLessEqual(badge["width_fraction"], 0.08)
        self.assertAlmostEqual(
            badge["local_aabb"]["size"][0], badge["local_aabb"]["size"][2], delta=1e-6,
            msg="badge is not square",
        )

    # ── both elements must be ON the face, not floating in front of it ───────
    def test_printed_elements_are_welded_to_the_front_face(self):
        """Regression guard: decoration was positioned from the REQUESTED dims
        while the box is built at a different size, leaving the stripe hanging
        12mm in front of the carton instead of printed on it."""
        depth = self.scene["carton"]["measured_local_aabb"]["size"][1]
        for name in ("accent_stripe", "brand_badge"):
            with self.subTest(element=name):
                el = self.scene[name]
                self.assertTrue(
                    el["straddles_front_face"],
                    f"{name} does not touch the front face at all "
                    f"(protrusion {el['protrusion_m'] * 1000:.2f}mm, "
                    f"embed {el['embed_m'] * 1000:.2f}mm)",
                )
                self.assertGreater(el["protrusion_m"], 0.0,
                                   f"{name} is fully sunk inside the carton")
                self.assertLess(
                    el["protrusion_m"], depth * 0.01,
                    f"{name} stands {el['protrusion_m'] * 1000:.2f}mm proud of the "
                    f"face — printing should read flush at this scale",
                )

    # ── framing invariants (must survive any change to the decoration) ───────
    def test_carton_is_centred_and_fully_inside_the_frame(self):
        framing = self.scene["framing"]
        self.assertAlmostEqual(framing["centre_x"], 0.5, delta=0.05)
        self.assertAlmostEqual(framing["centre_y"], 0.5, delta=0.05)
        for axis in ("fill_x", "fill_y"):
            with self.subTest(axis=axis):
                self.assertLess(framing[axis], 1.0,
                                "carton's bounding box is cropped by the frame")

    def test_camera_keeps_the_documented_optics(self):
        self.assertAlmostEqual(self.scene["camera"]["lens_mm"], 85.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
