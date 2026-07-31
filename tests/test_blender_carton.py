"""Geometry/colour tests for the procedural carton built by render_driver.py.

These drive a real Blender in --background and assert on the scene it builds,
because the things that go wrong here (a carton built at the wrong scale, a
stripe that detaches from the box, a body painted the wrong colour) are
properties of the assembled scene and cannot be reached from the project-side
interpreter: `import bpy` only works inside Blender's own bundled Python. The
driver's --dump-scene flag writes the measured geometry out as JSON so the
assertions can live here as ordinary unittest.

Placement is asserted in the CARTON'S LOCAL FRAME. In world space a thin plate
lying flat on a box rotated 35 deg has an AABB that pokes outside the box's own
AABB even when perfectly glued on, so world-space containment gives false
alarms; in the carton's frame the checks are plain interval comparisons. Scale,
seating and framing are the exceptions — those are genuinely questions about
world space and the camera, and are measured there.

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

# Tolerance in metres for "is this the size the manifest asked for". Blender
# stores vertices as float32, so a 0.115 m edge round-trips with ~1e-8 m of
# error; 0.01 mm is far inside that and far below anything that matters.
TOL_M = 1e-5

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

# A tall carton from the vertical family, which takes the other camera
# calibration branch (20 deg pitch / 27.5 deg rotation) and is portrait rather
# than landscape. Dimensions are T_VERT_VIAL's, as resolved by
# orient_for_template() for every vial SKU in the catalogue.
VERT_JOB = dict(
    JOB,
    sku_id="test-carton-vertical",
    template_id="T_VERT_VIAL",
    carton={"width_mm": 80.0, "height_mm": 170.0, "depth_mm": 35.0,
            "source": "passport_secondary"},
)


def srgb_hex_to_linear(hex_str):
    """Same sRGB -> linear transform the driver applies, computed independently."""
    h = hex_str.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


_SCENES = {}


def build_scene(job):
    """Run the driver in --dump-scene mode and return the measured geometry.

    Cached by job, because a Blender launch costs a couple of seconds and the
    classes below ask for the same two scenes repeatedly.
    """
    key = json.dumps(job, sort_keys=True)
    if key in _SCENES:
        return _SCENES[key]

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
        _SCENES[key] = json.loads(dump_path.read_text(encoding="utf-8"))
    return _SCENES[key]


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestCartonScale(unittest.TestCase):
    """Scene units are real metres: 115mm of carton is 0.115 in Blender.

    The regression this pins down: primitive_cube_add(size=1.0) makes a cube of
    EDGE length 1 (it spans -0.5..0.5), so scaling it by the half-extents
    (w/2, d/2, h/2) built every carton at half its nominal millimetres. It went
    unnoticed because SPHERE_FILL had been tuned up to 1.70 to compensate.
    """

    def _assert_true_scale(self, job):
        scene = build_scene(job)
        req = scene["requested_mm"]
        # dimensions is the local bounding box, so it reports true edge lengths
        # regardless of the carton's Z rotation.
        got_w, got_d, got_h = scene["carton"]["dimensions"]
        for axis, got, want_mm in (("width", got_w, req["width"]),
                                   ("height", got_h, req["height"]),
                                   ("depth", got_d, req["depth"])):
            self.assertAlmostEqual(
                got, want_mm / 1000.0, delta=TOL_M,
                msg=f"{job['template_id']}: carton {axis} is {got * 1000:.2f}mm, "
                    f"manifest asked for {want_mm:.2f}mm")

    def test_landscape_carton_is_true_scale(self):
        self._assert_true_scale(JOB)

    def test_vertical_family_carton_is_true_scale(self):
        self._assert_true_scale(VERT_JOB)

    def test_vertical_family_carton_stands_taller_than_it_is_wide(self):
        # The manifest's height must reach Blender's Z, not get transposed on
        # the way in: orient_for_template() already stood the longest edge up.
        w, _d, h = build_scene(VERT_JOB)["carton"]["dimensions"]
        self.assertGreater(h, w, "vertical-family carton came out landscape")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestCartonSeating(unittest.TestCase):
    """The carton rests ON the backdrop, it does not hover over it.

    It used to be positioned at z = h/2 while its half-height was only h/4, so
    it floated a quarter-height up and threw a detached contact shadow.
    reference_analysis.md reads the references as near-shadowless, which makes
    seating a reference-matching requirement rather than housekeeping.
    """

    def _assert_seated(self, job):
        gap = build_scene(job)["carton"]["ground_gap"]
        self.assertAlmostEqual(
            gap, 0.0, delta=TOL_M,
            msg=f"{job['template_id']}: carton floats {gap * 1000:.2f}mm above "
                "the ground plane")

    def test_landscape_carton_sits_on_the_ground_plane(self):
        self._assert_seated(JOB)

    def test_vertical_family_carton_sits_on_the_ground_plane(self):
        self._assert_seated(VERT_JOB)


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
        dimensions while the mesh was built at half those extents, so it hung a
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


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestFraming(unittest.TestCase):
    """Framing is an INVARIANT across the true-scale change.

    SPHERE_FILL exists to hit the framing measured off the reference renders.
    Doubling the carton without re-solving it would have doubled the object in
    frame, so these bounds are what forced the constant to be recalibrated
    (1.70 -> 0.8365) rather than left alone.
    """

    def test_landscape_carton_fills_the_reference_share_of_frame(self):
        frac = build_scene(JOB)["framing"]["max_frac"]
        self.assertAlmostEqual(
            frac, 0.756, delta=0.01,
            msg=f"T1 fills {frac:.1%} of frame; SPHERE_FILL no longer matches "
                "the reference calibration")

    def test_every_template_lands_in_the_calibrated_band(self):
        for job in (JOB, VERT_JOB):
            with self.subTest(template=job["template_id"]):
                frac = build_scene(job)["framing"]["max_frac"]
                self.assertGreater(frac, 0.70, "carton renders too small in frame")
                self.assertLess(frac, 0.85, "carton is cropped or nearly touching "
                                            "the frame edge")

    def test_carton_is_vertically_centred(self):
        # reference_analysis.md: object centred at 50-52% of frame height.
        for job in (JOB, VERT_JOB):
            with self.subTest(template=job["template_id"]):
                centre = build_scene(job)["framing"]["centre_y_frac"]
                self.assertAlmostEqual(centre, 0.5, delta=0.05)


if __name__ == "__main__":
    unittest.main()
