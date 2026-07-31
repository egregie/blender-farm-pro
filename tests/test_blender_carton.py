"""Geometry/colour tests for the procedural carton built by render_driver.py.

These drive a real Blender in --background and assert on the scene it builds,
because the things that go wrong here (a stripe that detaches from the box, a
body painted the wrong colour) are properties of the assembled scene and cannot
be reached from the project-side interpreter: `import bpy` only works inside
Blender's own bundled Python. The driver's --dump-scene flag writes the measured
geometry out as JSON so the assertions can live here as ordinary unittest.

Every measurement is taken in the CARTON'S LOCAL FRAME. In world space a thin
plate lying flat on a box rotated 35 deg has an AABB that pokes outside the
box's own AABB even when perfectly glued on, so world-space containment gives
false alarms; in the carton's frame the checks are plain interval comparisons.

Skipped (not failed) when blender.exe is absent, so the suite still runs on a
machine without Blender installed.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.utils import load_config, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CFG = load_config()
_BLENDER = _CFG.get("blender", {})
BLENDER_EXE = _BLENDER.get("executable", "")
DRIVER_SCRIPT = str(resolve_path(_BLENDER.get("driver_script",
                                              "assets/blender/render_driver.py")))

# reference_analysis.md 5: the stripe measures roughly 8-12% of the front-face
# height in every curated reference.
STRIPE_MIN_FRAC, STRIPE_MAX_FRAC = 0.08, 0.12

# A representative job. Deliberately a literal rather than a manifest read off
# disk: these assertions are about how the driver TREATS a manifest, so the
# input must stay fixed even if the catalogue changes.
JOB = {
    "manifest_version": "1.0",
    "sku_id": "test-carton",
    "template_id": "T1",
    "is_bottle_override": False,
    "packaging_geometry": "BLISTER",
    "carton": {"width_mm": 115.0, "height_mm": 55.0, "depth_mm": 48.0,
               "source": "passport_secondary"},
    "palette": {"primary": "#DDA7A5", "accent": "#6B2D5C", "background": "#FFFFFF"},
    "label_content": {"brand_name_display": "Atomoxetine Generic",
                      "dosage_display": "40mg", "unit_count_display": "10 Pills"},
}


def srgb_hex_to_linear(hex_str):
    """Same sRGB -> linear transform the driver applies, computed independently."""
    h = hex_str.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def build_scene(job):
    """Run the driver in --dump-scene mode and return the measured geometry."""
    with tempfile.TemporaryDirectory() as tmp:
        job_path = Path(tmp) / "job.json"
        dump_path = Path(tmp) / "scene.json"
        job_path.write_text(json.dumps(job), encoding="utf-8")
        proc = subprocess.run(
            [BLENDER_EXE, "--background", "--factory-startup",
             "--python", DRIVER_SCRIPT, "--",
             "--job", str(job_path), "--dump-scene", str(dump_path)],
            capture_output=True, text=True, timeout=300,
        )
        if not dump_path.exists():
            raise AssertionError(
                f"driver produced no scene dump (exit {proc.returncode})\n"
                f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
            )
        return json.loads(dump_path.read_text(encoding="utf-8"))


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestCartonGeometry(unittest.TestCase):
    """The accent stripe must be a band welded to the bottom of the FRONT face."""

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)
        cls.carton = cls.scene["carton"]
        cls.stripe = cls.scene["stripe"]
        b = cls.carton["self_bounds"]
        cls.half_w = (b["max"][0] - b["min"][0]) / 2.0
        cls.half_d = (b["max"][1] - b["min"][1]) / 2.0
        cls.height = b["max"][2] - b["min"][2]
        cls.bottom_z = b["min"][2]
        cls.front_y = b["min"][1]

    def test_stripe_exists(self):
        self.assertIsNotNone(self.stripe, "no accent_stripe object was built")

    def test_stripe_is_on_the_front_face_not_floating_in_front_of_it(self):
        """The regression: the stripe was placed using the carton's NOMINAL
        dimensions while the mesh is built at half those extents, so it hung a
        quarter-depth in front of the face and swung clear of the box once the
        carton was rotated."""
        s = self.stripe["bounds_in_carton_frame"]
        standoff = self.front_y - s["min"][1]
        self.assertGreaterEqual(
            standoff, 0.0,
            "stripe's outer surface is behind the carton's front face (sunk inside)")
        self.assertLess(
            standoff, 0.02 * (2 * self.half_d),
            f"stripe floats {standoff:.5f} in front of the face "
            f"(front face at y={self.front_y:.5f}, stripe outer at {s['min'][1]:.5f}) "
            "- it must sit ON the surface, not hover in front of it")

    def test_stripe_does_not_penetrate_the_back_of_the_carton(self):
        s = self.stripe["bounds_in_carton_frame"]
        self.assertLessEqual(
            s["max"][1], self.front_y + 0.02 * (2 * self.half_d),
            "stripe extends deep into the carton body instead of skinning the face")

    def test_stripe_sits_hard_against_the_bottom_edge(self):
        """Every reference puts the band at the very bottom of the front face;
        it used to sit at h * 0.55, i.e. mid-height."""
        s = self.stripe["bounds_in_carton_frame"]
        offset = abs(s["min"][2] - self.bottom_z)
        self.assertLess(
            offset, 0.01 * self.height,
            f"stripe's lower edge is {offset / self.height:.1%} of the face height "
            f"above the carton's bottom edge; it must be flush with it")

    def test_stripe_height_matches_the_reference_band(self):
        s = self.stripe["bounds_in_carton_frame"]
        frac = (s["max"][2] - s["min"][2]) / self.height
        self.assertGreaterEqual(frac, STRIPE_MIN_FRAC - 1e-6,
                                f"stripe is {frac:.1%} of face height, thinner than "
                                f"the reference band ({STRIPE_MIN_FRAC:.0%}-{STRIPE_MAX_FRAC:.0%})")
        self.assertLessEqual(frac, STRIPE_MAX_FRAC + 1e-6,
                             f"stripe is {frac:.1%} of face height, thicker than "
                             f"the reference band ({STRIPE_MIN_FRAC:.0%}-{STRIPE_MAX_FRAC:.0%})")

    def test_stripe_spans_the_full_width_of_the_face(self):
        s = self.stripe["bounds_in_carton_frame"]
        span = (s["max"][0] - s["min"][0]) / (2 * self.half_w)
        self.assertGreater(span, 0.95,
                           f"stripe spans only {span:.1%} of the face width; the "
                           "references show a full-width band")
        self.assertLessEqual(s["max"][0], self.half_w + 1e-6,
                             "stripe overhangs the right edge of the face")
        self.assertGreaterEqual(s["min"][0], -self.half_w - 1e-6,
                                "stripe overhangs the left edge of the face")

    def test_stripe_stays_welded_when_the_carton_is_rotated(self):
        """The carton is rotated for the packshot; the stripe is parented to it.
        Its position in the carton's frame must not depend on that rotation."""
        self.assertAlmostEqual(
            self.carton["rotation_z_deg"], 35.0, places=3,
            msg="T1 should be rotated 35 deg; test premise no longer holds")
        upright = dict(JOB, template_id="T1")
        rotated_bounds = self.stripe["bounds_in_carton_frame"]
        # Rebuild through the vertical family, which uses a different rotation
        # (27.5 deg). Same carton frame => same numbers, if truly parented.
        other = build_scene(dict(upright, template_id="T_VERT_INHALER"))
        self.assertAlmostEqual(other["carton"]["rotation_z_deg"], 27.5, places=3)
        for key in ("min", "max"):
            for axis in range(3):
                self.assertAlmostEqual(
                    other["stripe"]["bounds_in_carton_frame"][key][axis],
                    rotated_bounds[key][axis], places=6,
                    msg="stripe placement in the carton's own frame changed with "
                        "the carton's rotation - it is not rigidly attached")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestCartonSurfaceColour(unittest.TestCase):
    """The SURFACE COLOUR MANDATE: white body, brand colour only in the stripe."""

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)

    def test_carton_body_is_white_not_the_brand_primary(self):
        body = self.scene["carton"]["base_color"]
        self.assertIsNotNone(body, "carton has no Principled BSDF base colour")
        for channel, value in zip("RGB", body[:3]):
            self.assertAlmostEqual(
                value, 1.0, places=3,
                msg=f"carton body {channel} is {value:.3f}, not white - the body "
                    f"must not be painted palette.primary ({JOB['palette']['primary']})")

    def test_stripe_is_the_palette_accent(self):
        expected = srgb_hex_to_linear(JOB["palette"]["accent"])
        actual = self.scene["stripe"]["base_color"][:3]
        for channel, (want, got) in zip("RGB", zip(expected, actual)):
            self.assertAlmostEqual(
                got, want, places=4,
                msg=f"stripe {channel} is {got:.4f}, expected {want:.4f} from "
                    f"palette.accent {JOB['palette']['accent']}")


if __name__ == "__main__":
    unittest.main()
