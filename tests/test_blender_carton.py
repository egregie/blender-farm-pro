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
import os
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.utils import load_config, resolve_path
from src.measure import _front_face_and_background

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CFG = load_config()
_BLENDER = _CFG.get("blender", {})
BLENDER_EXE = _BLENDER.get("executable", "")
DRIVER_SCRIPT = str(resolve_path(_BLENDER.get("driver_script",
                                              "assets/blender/render_driver.py")))

# reference_analysis.md 5 originally eyeballed the stripe at "roughly 8-12%" of
# the front-face height and flagged that estimate as unmeasured in 9. Measuring
# all nine curated references pixel-wise puts it at 2.9-6.1% (median 4.0%), so
# these are the measured bounds, not the eyeballed ones.
STRIPE_MIN_FRAC, STRIPE_MAX_FRAC = 0.03, 0.06

# reference_analysis.md 4: "roughness reads high (~0.6-0.8 in a Principled-BSDF
# sense), not the ~0.35 currently hardcoded"; 8 asks for the body specifically.
MATTE_MIN, MATTE_MAX = 0.6, 0.8

# The top-right brand badge. Restated here rather than imported: the driver only
# imports under Blender's own interpreter, and a test that reads its constants
# would pass no matter what the driver actually built.
BADGE_SIDE_FRAC         = 0.25
BADGE_MARGIN_RIGHT_FRAC = 0.05
BADGE_MARGIN_TOP_FRAC   = 0.03
# Measured spread of the badge across the nine curated references, as a fraction
# of the shorter front-face edge. BADGE_SIDE_FRAC has to stay inside it.
BADGE_SIDE_MIN, BADGE_SIDE_MAX = 0.21, 0.37
MARGIN_TOL = 0.01

# The film response is pinned so exposure is deterministic across installs, and
# because Blender's default AgX rolls the highlights off far enough to hide a
# ~2.6-stop over-exposure: it left the white body looking plausible while landing
# the ~15%-albedo accent stripe at mid-grey, (195,135,179) against the (99,42,72)
# measured in the references. The stop count is measured off an unclipped render,
# not read off an AgX one - AgX is not linear and estimating from it gives 2.0,
# which still clips the T1 front face.
# Exposure is metered per carton SHAPE, not per template and not globally. The
# light rig is identical for every carton; a wide front face simply sits closer
# to the key across its width and reads ~0.13 stops darker than a narrow one, so
# landscape and portrait cartons are metered separately - exactly as a
# photographer re-reads the meter without touching the strobes.
FILM_VIEW_TRANSFORM = "Standard"
FILM_EXPOSURE_LANDSCAPE = -2.76
FILM_EXPOSURE_PORTRAIT = -2.84

# Studio-strobe-scale wattages, restated independently of the driver. These are
# the power at the rig's reference carton size, not for every carton - see
# light_energy() for why they have to scale with the square of the size.
KEY_W, FILL_W = 25.0, 8.0

# A representative job. Deliberately a literal rather than a manifest read off
# disk: these assertions are about how the driver TREATS a manifest, so the
# input must stay fixed even if the catalogue changes.
JOB = {
    "manifest_version": "1.2",
    "sku_id": "test-carton",
    "template_id": "T1",
    "is_bottle_override": False,
    "packaging_geometry": "BLISTER",
    "carton": {"width_mm": 115.0, "height_mm": 55.0, "depth_mm": 48.0,
               "source": "passport_secondary",
               "features": ["Braille", "DataMatrix_Zone", "Tamper_Evident_Seal"],
               "material": "GZ-Cardboard (Pharmaceutical Grade)"},
    "palette": {"primary": "#DDA7A5", "accent": "#6B2D5C", "background": "#FFFFFF"},
    "label_content": {"brand_name_display": "Atomoxetine Generic",
                      "active_ingredient_display": "Atomoxetine",
                      "dosage_display": "40mg", "unit_count_display": "10 Pills"},
}

# The label grid, restated independently of the driver, in the front face's own
# coordinates: u across (0 = near corner, 1 = far edge), v down (0 = top).
LABEL_ROWS = ("label_brand", "label_ingredient", "label_dosage", "label_unit_count")
LABEL_LEFT_FRAC, LABEL_RIGHT_FRAC = 0.07, 0.95


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


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestCartonIsMatte(unittest.TestCase):
    """reference_analysis.md 4/8: matte uncoated cardstock, not semi-gloss.

    Asserted on every printed surface, not just the body: 3 records no hard
    specular highlight anywhere on the carton, and the stripe and badge are ink
    on the same board.
    """

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)

    def _assert_matte(self, part):
        got = self.scene[part]["roughness"]
        self.assertIsNotNone(got, f"{part} reports no Principled BSDF roughness")
        self.assertGreaterEqual(
            got, MATTE_MIN,
            f"{part} roughness {got} is below {MATTE_MIN}; the references read as "
            "matte cardboard, not semi-gloss")
        self.assertLessEqual(
            got, MATTE_MAX,
            f"{part} roughness {got} is above {MATTE_MAX}, past matte into a "
            "fully diffuse surface the references do not show")

    def test_body_is_matte(self):
        self._assert_matte("carton")

    def test_stripe_is_matte(self):
        self._assert_matte("stripe")

    def test_badge_is_matte(self):
        self._assert_matte("badge")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestBrandBadge(unittest.TestCase):
    """The second of the two places brand colour is allowed to appear.

    reference_analysis.md 5: a coloured square in the TOP-RIGHT corner of the
    front face. Measured across all nine references it is filled with
    palette.PRIMARY - the lighter tone - while the bottom stripe takes the darker
    palette.accent. Getting those two the wrong way round is the likely failure
    here, so it has its own assertion.
    """

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)
        cls.badge = cls.scene["badge"]
        b = cls.scene["carton"]["self_bounds"]
        cls.face_w = b["max"][0] - b["min"][0]
        cls.face_h = b["max"][2] - b["min"][2]
        cls.depth = b["max"][1] - b["min"][1]
        cls.right_x, cls.top_z, cls.front_y = b["max"][0], b["max"][2], b["min"][1]

    def test_badge_exists(self):
        self.assertIsNotNone(
            self.badge,
            "no brand_badge object was built; reference_analysis.md 5 puts a "
            "coloured square in the top-right corner of every front face")

    def test_badge_is_the_palette_primary(self):
        expected = srgb_hex_to_linear(JOB["palette"]["primary"])
        actual = self.badge["base_color"][:3]
        for channel, (want, got) in zip("RGB", zip(expected, actual)):
            self.assertAlmostEqual(
                got, want, places=4,
                msg=f"badge {channel} is {got:.4f}, expected {want:.4f} from "
                    f"palette.primary {JOB['palette']['primary']}")

    def test_badge_is_not_the_accent(self):
        """The stripe takes accent and the badge takes primary, never swapped."""
        accent = srgb_hex_to_linear(JOB["palette"]["accent"])
        actual = self.badge["base_color"][:3]
        close = all(abs(g - w) < 1e-4 for g, w in zip(actual, accent))
        self.assertFalse(
            close,
            f"badge is filled with palette.accent {JOB['palette']['accent']}, "
            f"which belongs to the bottom stripe; it must take palette.primary "
            f"{JOB['palette']['primary']}")

    def test_badge_is_square(self):
        s = self.badge["bounds_in_carton_frame"]
        width = s["max"][0] - s["min"][0]
        height = s["max"][2] - s["min"][2]
        self.assertAlmostEqual(
            width, height, places=6,
            msg=f"badge is {width:.5f} x {height:.5f}; the references show a square")

    def test_badge_sits_on_the_front_face(self):
        """Same failure the stripe once had: geometry placed from the carton's
        NOMINAL millimetres floats a quarter-depth in front of the real face,
        because the mesh is built at half its nominal extents."""
        s = self.badge["bounds_in_carton_frame"]
        standoff = self.front_y - s["min"][1]
        self.assertGreaterEqual(
            standoff, 0.0, "badge's outer surface is sunk inside the carton body")
        self.assertLess(
            standoff, 0.02 * self.depth,
            f"badge floats {standoff:.5f} in front of the face "
            f"(front face at y={self.front_y:.5f}, badge outer at {s['min'][1]:.5f})")
        self.assertLessEqual(
            s["max"][1], self.front_y + 0.02 * self.depth,
            "badge extends into the carton body instead of skinning the face")

    def test_badge_is_inset_from_the_top_right_corner(self):
        s = self.badge["bounds_in_carton_frame"]
        gap_right = (self.right_x - s["max"][0]) / self.face_w
        gap_top = (self.top_z - s["max"][2]) / self.face_h
        self.assertAlmostEqual(
            gap_right, BADGE_MARGIN_RIGHT_FRAC, delta=MARGIN_TOL,
            msg=f"badge sits {gap_right:.1%} of the face width from the right "
                f"edge, not the measured {BADGE_MARGIN_RIGHT_FRAC:.0%}")
        self.assertAlmostEqual(
            gap_top, BADGE_MARGIN_TOP_FRAC, delta=MARGIN_TOL,
            msg=f"badge sits {gap_top:.1%} of the face height below the top "
                f"edge, not the measured {BADGE_MARGIN_TOP_FRAC:.0%}")

    def test_badge_does_not_overhang_the_face(self):
        s = self.badge["bounds_in_carton_frame"]
        c = self.scene["carton"]["self_bounds"]
        self.assertLessEqual(s["max"][0], c["max"][0] + 1e-6, "badge overhangs the right edge")
        self.assertGreaterEqual(s["min"][0], c["min"][0] - 1e-6, "badge overhangs the left edge")
        self.assertLessEqual(s["max"][2], c["max"][2] + 1e-6, "badge overhangs the top edge")
        self.assertGreaterEqual(s["min"][2], c["min"][2] - 1e-6, "badge overhangs the bottom edge")

    def test_badge_does_not_touch_the_stripe(self):
        """Brand colour appears in exactly two separate places, not one band."""
        self.assertGreater(
            self.badge["bounds_in_carton_frame"]["min"][2],
            self.scene["stripe"]["bounds_in_carton_frame"]["max"][2],
            "badge overlaps the accent stripe")

    def test_badge_side_matches_the_reference_proportion(self):
        s = self.badge["bounds_in_carton_frame"]
        side = s["max"][0] - s["min"][0]
        frac = side / min(self.face_w, self.face_h)
        self.assertAlmostEqual(
            frac, BADGE_SIDE_FRAC, places=6,
            msg=f"badge is {frac:.1%} of the shorter front-face edge, not "
                f"{BADGE_SIDE_FRAC:.0%}")
        self.assertGreaterEqual(frac, BADGE_SIDE_MIN)
        self.assertLessEqual(frac, BADGE_SIDE_MAX)

    def test_badge_stays_welded_when_the_carton_is_rotated(self):
        """Rebuild through the vertical family, which rotates 27.5 deg instead of
        35. Measured in the carton's own frame the badge must not move at all."""
        other = build_scene(dict(JOB, template_id="T_VERT_INHALER"))
        self.assertAlmostEqual(other["carton"]["rotation_z_deg"], 27.5, places=3)
        for key in ("min", "max"):
            for axis in range(3):
                self.assertAlmostEqual(
                    other["badge"]["bounds_in_carton_frame"][key][axis],
                    self.badge["bounds_in_carton_frame"][key][axis], places=6,
                    msg="badge placement in the carton's own frame changed with "
                        "the carton's rotation - it is not rigidly attached")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestBadgeIsOptional(unittest.TestCase):
    """A palette without primary must lose the badge, not crash the render."""

    def test_no_primary_means_no_badge(self):
        job = dict(JOB, palette={"accent": "#6B2D5C", "background": "#FFFFFF"})
        scene = build_scene(job)
        self.assertIsNone(scene["badge"],
                          "a badge was built without a palette.primary to fill it")
        self.assertIsNotNone(scene["stripe"], "the stripe should be unaffected")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestLightingIsOneStudio(unittest.TestCase):
    """Every carton must look photographed in the same studio.

    The rig scales with the carton, so what has to be invariant is not the raw
    numbers but the RELATIONSHIPS: same directions, same key:fill ratio, same
    apparent light size. Energy is the one quantity that must vary, and it must
    vary as the square of the size ratio - anything less and big cartons come out
    dark, which is the defect this class exists to catch.
    """

    @classmethod
    def setUpClass(cls):
        # Two cartons of deliberately different size: T1 at the reference scale,
        # and a T_VERT_VIAL-shaped carton at the catalogue's largest, 170mm.
        cls.small = build_scene(JOB)["lighting"]
        big = dict(JOB, template_id="T_VERT_VIAL",
                   carton=dict(JOB["carton"], width_mm=80.0, height_mm=170.0,
                               depth_mm=35.0))
        cls.big = build_scene(big)["lighting"]

    def test_target_size_differs(self):
        """Test premise: the two scenes really are built at different scales."""
        self.assertAlmostEqual(self.small["target_size"], 0.115, places=6)
        self.assertAlmostEqual(self.big["target_size"], 0.170, places=6)

    def _direction(self, lighting, name):
        loc = lighting[name]["location"]
        norm = math.sqrt(sum(c * c for c in loc))
        return [c / norm for c in loc]

    def test_light_directions_are_identical(self):
        for name in ("key_light", "fill_light"):
            for axis, (s, b) in enumerate(zip(self._direction(self.small, name),
                                              self._direction(self.big, name))):
                self.assertAlmostEqual(
                    s, b, places=6,
                    msg=f"{name} arrives from a different direction on a "
                        f"different-sized carton (axis {axis}): one studio means "
                        "only the distance may scale, never the angle")

    def test_key_is_camera_right_and_fill_camera_left(self):
        """Guards against 'correcting' the rig to a described-but-wrong layout."""
        self.assertGreater(self.small["key_light"]["location"][0], 0,
                           "key light must stay on the camera's right (+X)")
        self.assertLess(self.small["fill_light"]["location"][0], 0,
                        "fill light must stay on the camera's left (-X)")

    def test_key_to_fill_ratio_is_constant(self):
        for lighting, label in ((self.small, "small"), (self.big, "big")):
            ratio = lighting["key_light"]["energy"] / lighting["fill_light"]["energy"]
            self.assertAlmostEqual(
                ratio, KEY_W / FILL_W, places=4,
                msg=f"key:fill is {ratio:.3f} on the {label} carton, not "
                    f"{KEY_W / FILL_W:.3f}; the lighting ratio defines the look "
                    "and may not vary by template")

    def test_apparent_light_size_is_constant(self):
        """size/distance is the angle the light subtends: the softness of the
        shadow and of the falloff across a face. It must not vary."""
        for name in ("key_light", "fill_light"):
            angles = []
            for lighting in (self.small, self.big):
                loc = lighting[name]["location"]
                dist = math.sqrt(sum(c * c for c in loc))
                angles.append(lighting[name]["size"] / dist)
            self.assertAlmostEqual(
                angles[0], angles[1], places=6,
                msg=f"{name} subtends a different angle on a different-sized "
                    "carton, so shadows are softer on one than the other")

    def test_energy_scales_with_the_square_of_size(self):
        """The fix. Distance scales linearly with the carton, irradiance falls as
        1/distance^2, so power must rise as size^2 to hold irradiance constant."""
        ratio = self.big["target_size"] / self.small["target_size"]
        for name, base in (("key_light", KEY_W), ("fill_light", FILL_W)):
            self.assertAlmostEqual(
                self.big[name]["energy"] / self.small[name]["energy"], ratio ** 2,
                places=4,
                msg=f"{name} energy does not scale as size squared; a "
                    f"{ratio:.2f}x larger carton is lit from {ratio:.2f}x the "
                    f"distance and needs {ratio ** 2:.2f}x the power")

    def test_reference_size_keeps_the_documented_wattages(self):
        """25W/8W are protected numbers; they must survive untouched at the size
        they were tuned at, which is also the catalogue's modal carton."""
        self.assertAlmostEqual(self.small["key_light"]["energy"], KEY_W, places=4)
        self.assertAlmostEqual(self.small["fill_light"]["energy"], FILL_W, places=4)

    def test_light_size_has_no_lower_clamp(self):
        """A clamp would make small cartons relatively softer-lit than big ones."""
        tiny = dict(JOB, carton=dict(JOB["carton"], width_mm=20.0,
                                     height_mm=10.0, depth_mm=8.0))
        lighting = build_scene(tiny)["lighting"]
        expected = lighting["target_size"] * 2.0
        self.assertAlmostEqual(
            lighting["key_light"]["size"], expected, places=6,
            msg="light size is clamped rather than proportional, so this carton "
                "is lit by a relatively larger, softer source than a big one")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestFilmResponse(unittest.TestCase):
    """Exposure is pinned, for the same reason the world background is."""

    @classmethod
    def setUpClass(cls):
        cls.film = build_scene(JOB)["film"]                       # 115x55, landscape
        portrait = dict(JOB, carton=dict(JOB["carton"], width_mm=55.0,
                                         height_mm=115.0, depth_mm=48.0))
        cls.portrait_film = build_scene(portrait)["film"]

    def test_view_transform_is_pinned(self):
        self.assertEqual(
            self.film["view_transform"], FILM_VIEW_TRANSFORM,
            "view transform is not pinned; Blender's default AgX desaturates the "
            "brand colour until the accent stripe no longer reads as the brand")

    def test_landscape_carton_is_metered_for_its_shape(self):
        self.assertAlmostEqual(
            self.film["exposure"], FILM_EXPOSURE_LANDSCAPE, places=6,
            msg="exposure compensation is missing or wrong; without it the scene "
                "renders ~2.8 stops hot. This is a FILM setting - do NOT correct "
                "it by changing the 25W/8W energies in setup_lighting()")

    def test_portrait_carton_is_metered_for_its_shape(self):
        self.assertAlmostEqual(
            self.portrait_film["exposure"], FILM_EXPOSURE_PORTRAIT, places=6,
            msg="a portrait carton must be metered separately from a landscape "
                "one; its narrow front face reads ~0.13 stops brighter under the "
                "identical rig")

    def test_the_two_exposures_differ_only_slightly(self):
        """A shape correction, not a per-template free-for-all. If this gap ever
        grows past a fifth of a stop the rig itself has drifted and the fix
        belongs in setup_lighting(), not here."""
        gap = abs(FILM_EXPOSURE_LANDSCAPE - FILM_EXPOSURE_PORTRAIT)
        self.assertLess(gap, 0.2, f"shape correction is {gap:.2f} stops")


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestLabelText(unittest.TestCase):
    """The front panel, and the one guarantee this engine exists to make.

    reference_analysis.md 7 caught the Gemini renders printing "Datels" - not a
    word - as a side-panel field label on the Lumigan sample. A text object draws
    the string it is handed or nothing at all, so that class of failure is
    structurally impossible here. That claim is only worth making if something
    checks it, which is what test_every_string_survives_verbatim does.
    """

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)
        cls.rows = {t["name"]: t for t in cls.scene["label"]}
        b = cls.scene["carton"]["self_bounds"]
        cls.left_x, cls.top_z = b["min"][0], b["max"][2]
        cls.face_w = b["max"][0] - b["min"][0]
        cls.face_h = b["max"][2] - b["min"][2]
        cls.front_y, cls.depth = b["min"][1], b["max"][1] - b["min"][1]

    def _uv(self, name):
        b = self.rows[name]["bounds_in_carton_frame"]
        return {
            "u0": (b["min"][0] - self.left_x) / self.face_w,
            "u1": (b["max"][0] - self.left_x) / self.face_w,
            "v0": (self.top_z - b["max"][2]) / self.face_h,
            "v1": (self.top_z - b["min"][2]) / self.face_h,
            "y0": b["min"][1], "y1": b["max"][1],
        }

    def test_all_four_rows_are_built(self):
        self.assertEqual(sorted(self.rows), sorted(LABEL_ROWS))

    def test_every_string_survives_verbatim(self):
        """No truncation, no ellipsis, no invented characters. Line breaks are
        the one permitted edit, because wrapping is layout and not content."""
        for row, field in (("label_brand", "brand_name_display"),
                           ("label_ingredient", "active_ingredient_display"),
                           ("label_dosage", "dosage_display"),
                           ("label_unit_count", "unit_count_display")):
            want = JOB["label_content"][field]
            got = self.rows[row]["body"].replace("\n", " ")
            self.assertEqual(
                got, want,
                f"{row} draws {got!r} but the manifest says {want!r}. The whole "
                "point of rendering text as geometry is that this cannot drift")

    def test_rows_run_top_to_bottom_in_the_documented_order(self):
        """Three bands, not four: dosage and unit count share the bottom row, so
        their tops differ only by whichever string happens to carry an ascender.
        Comparing those two against each other would assert on typography."""
        brand = self._uv("label_brand")
        ingredient = self._uv("label_ingredient")
        bottom = min(self._uv("label_dosage")["v0"],
                     self._uv("label_unit_count")["v0"])
        self.assertLess(brand["v1"], ingredient["v0"],
                        "the brand block runs into the ingredient row")
        self.assertLess(ingredient["v1"], bottom,
                        "the ingredient row runs into the dosage/count row")

    def test_nothing_overhangs_the_front_face(self):
        for row in LABEL_ROWS:
            uv = self._uv(row)
            self.assertGreaterEqual(uv["u0"], 0.0, f"{row} runs off the left edge")
            self.assertLessEqual(uv["u1"], 1.0, f"{row} runs off the right edge")
            self.assertGreaterEqual(uv["v0"], 0.0, f"{row} runs off the top edge")
            self.assertLessEqual(uv["v1"], 1.0, f"{row} runs off the bottom edge")

    def test_rows_respect_the_side_margins(self):
        for row in ("label_brand", "label_ingredient", "label_dosage"):
            self.assertAlmostEqual(
                self._uv(row)["u0"], LABEL_LEFT_FRAC, delta=0.02,
                msg=f"{row} does not start at the grid's left margin")
        self.assertAlmostEqual(
            self._uv("label_unit_count")["u1"], LABEL_RIGHT_FRAC, delta=0.02,
            msg="the unit count is right-aligned to the grid's right margin")

    def test_dosage_is_left_and_unit_count_is_right_on_a_shared_row(self):
        dose, count = self._uv("label_dosage"), self._uv("label_unit_count")
        self.assertLess(dose["u1"], count["u0"],
                        "dosage and unit count overlap; they grow toward each "
                        "other from opposite margins and must not meet")
        self.assertAlmostEqual(dose["v0"], count["v0"], delta=0.02,
                               msg="the two sit on one row in every reference")

    def test_no_row_collides_with_another(self):
        for i, a in enumerate(LABEL_ROWS):
            for b in LABEL_ROWS[i + 1:]:
                p, q = self._uv(a), self._uv(b)
                overlap = (p["v0"] < q["v1"] and q["v0"] < p["v1"]
                           and p["u0"] < q["u1"] and q["u0"] < p["u1"])
                self.assertFalse(overlap, f"{a} overlaps {b}")

    def test_no_row_collides_with_the_stripe_or_the_badge(self):
        stripe = self.scene["stripe"]["bounds_in_carton_frame"]
        badge = self.scene["badge"]["bounds_in_carton_frame"]
        stripe_v = (self.top_z - stripe["max"][2]) / self.face_h
        badge_u = (badge["min"][0] - self.left_x) / self.face_w
        badge_v = (self.top_z - badge["min"][2]) / self.face_h
        for row in LABEL_ROWS:
            uv = self._uv(row)
            self.assertLessEqual(uv["v1"], stripe_v, f"{row} runs into the stripe")
            self.assertFalse(uv["v0"] < badge_v and uv["u1"] > badge_u,
                             f"{row} runs into the brand badge")

    def test_text_sits_on_the_face_not_inside_or_adrift(self):
        for row in LABEL_ROWS:
            standoff = self.front_y - self._uv(row)["y1"]
            self.assertGreaterEqual(standoff, 0.0,
                                    f"{row} is sunk inside the carton body")
            self.assertLess(standoff, 0.02 * self.depth,
                            f"{row} floats in front of the face")

    def test_a_long_string_is_fitted_rather_than_left_to_overflow(self):
        """The real catalogue reaches 61 characters on the ingredient row."""
        long_job = dict(JOB, label_content=dict(
            JOB["label_content"],
            active_ingredient_display="Sildenafil / Tadalafil / Vardenafil / "
                                      "Avanafil (Specimen Mix)"))
        scene = build_scene(long_job)
        row = next(t for t in scene["label"] if t["name"] == "label_ingredient")
        b = row["bounds_in_carton_frame"]
        c = scene["carton"]["self_bounds"]
        u1 = (b["max"][0] - c["min"][0]) / (c["max"][0] - c["min"][0])
        self.assertLessEqual(u1, 1.0, "long ingredient string overhangs the face")
        self.assertEqual(row["body"].replace("\n", " "),
                         long_job["label_content"]["active_ingredient_display"],
                         "the string was shortened to make it fit; it must be "
                         "scaled down instead, never truncated")

    def test_a_wrapped_brand_name_stays_clear_of_the_ingredient_row(self):
        """A two-line name at the one-line cap height does not fit the band the
        grid leaves above the ingredient row. Sweeping all 391 SKU found 18 that
        wrap, and every one of them ran into the row below before the brand block
        was made to shrink to fit."""
        job = dict(JOB, label_content=dict(JOB["label_content"],
                                           brand_name_display="Cialis Super Active"))
        scene = build_scene(job)
        rows = {t["name"]: t for t in scene["label"]}
        c = scene["carton"]["self_bounds"]
        top_z, face_h = c["max"][2], c["max"][2] - c["min"][2]
        brand = rows["label_brand"]
        self.assertIn("\n", brand["body"], "test premise: this name should wrap")
        brand_bottom = (top_z - brand["bounds_in_carton_frame"]["min"][2]) / face_h
        ingredient_top = (top_z - rows["label_ingredient"]
                          ["bounds_in_carton_frame"]["max"][2]) / face_h
        self.assertLess(
            brand_bottom, ingredient_top,
            f"the wrapped brand runs to v {brand_bottom:.3f}, past the ingredient "
            f"row at v {ingredient_top:.3f}")

    def test_a_missing_string_drops_its_row_without_failing(self):
        job = dict(JOB, label_content={"brand_name_display": "Solo",
                                       "active_ingredient_display": "",
                                       "dosage_display": "", "unit_count_display": ""})
        names = {t["name"] for t in build_scene(job)["label"]}
        self.assertEqual(names, {"label_brand"})

    def test_the_font_is_the_vendored_one(self):
        """A system font would render differently on a machine that lacks it,
        which breaks the project's determinism invariant."""
        for row in LABEL_ROWS:
            self.assertIn("DejaVu", self.rows[row]["font"] or "",
                          f"{row} is not using the vendored font")


# Code 128 element-width patterns, symbol values 0..106. The table is the
# published standard, so both sides necessarily share it; what makes the reader
# below an independent check is that it runs the other way — geometry to widths
# to symbols to text — and recomputes the modulo-103 checksum itself.
_C128 = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213",
    "122312", "132212", "221213", "221312", "231212", "112232", "122132",
    "122231", "113222", "123122", "123221", "223211", "221132", "221231",
    "213212", "223112", "312131", "311222", "321122", "321221", "312212",
    "322112", "322211", "212123", "212321", "232121", "111323", "131123",
    "131321", "112313", "132113", "132311", "211313", "231113", "231311",
    "112133", "112331", "132131", "113123", "113321", "133121", "313121",
    "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111",
    "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114",
    "413111", "241112", "134111", "111242", "121142", "121241", "114212",
    "124112", "124211", "411212", "421112", "421211", "212141", "214121",
    "412121", "111143", "111341", "131141", "114113", "114311", "411113",
    "411311", "113141", "114131", "311141", "411131", "211412", "211214",
    "211232", "233111",
)


def decode_code128_from_bars(bars):
    """Read a Code 128 symbol out of built bar GEOMETRY, the way a scanner does.

    `bars` is a list of (low_z, high_z) intervals. Spaces are not objects, so
    they are recovered from the gaps between consecutive bars — which means this
    decodes what was actually modelled, not a pattern the driver reported about
    itself. Returns the decoded text.
    """
    bars = sorted(bars, key=lambda b: -b[1])          # top of the symbol first
    runs = []
    for i, (low, high) in enumerate(bars):
        runs.append(high - low)                        # bar
        if i + 1 < len(bars):
            runs.append(low - bars[i + 1][1])          # space up to the next bar
    module = min(runs)
    if module <= 0:
        raise AssertionError("a bar or space has zero width")
    widths = [int(round(r / module)) for r in runs]
    if any(w < 1 or w > 4 for w in widths):
        raise AssertionError(f"element widths outside Code 128's 1-4 modules: {widths}")

    # last 7 elements are the stop pattern; the rest are 6-element symbols
    stop, body = widths[-7:], widths[:-7]
    if "".join(map(str, stop)) != "2331112":
        raise AssertionError(f"stop pattern is {stop}, not 2331112")
    if len(body) % 6:
        raise AssertionError(f"{len(body)} body elements is not a multiple of 6")

    values = []
    for i in range(0, len(body), 6):
        pattern = "".join(map(str, body[i:i + 6]))
        if pattern not in _C128:
            raise AssertionError(f"symbol {i // 6} pattern {pattern} is not Code 128")
        values.append(_C128.index(pattern))
    if values[0] != 104:
        raise AssertionError(f"start symbol is {values[0]}, not START B (104)")

    checksum = values[0] + sum(i * v for i, v in enumerate(values[1:-1], start=1))
    if checksum % 103 != values[-1]:
        raise AssertionError(
            f"checksum is {values[-1]}, recomputed {checksum % 103}")
    return "".join(chr(v + 32) for v in values[1:-1])


@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestSidePanel(unittest.TestCase):
    """The visible side panel: a real barcode, empty LOT/EXP fields, a data block.

    The reference renders put a 2D code on this panel that is a blob of noise
    with no finder pattern, LOT/EXP values reading "SLAQF FD9T", and a microprint
    paragraph that is not text. None of that is copied. The layout is; the
    content comes from the manifest or is not drawn at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.scene = build_scene(JOB)
        cls.panel = cls.scene["side_panel"]
        cls.by_name = {o["name"]: o for o in cls.panel}
        b = cls.scene["carton"]["self_bounds"]
        cls.left_x, cls.back_y = b["min"][0], b["min"][1]
        cls.panel_w = b["max"][1] - b["min"][1]
        cls.panel_h = b["max"][2] - b["min"][2]
        cls.top_z, cls.bottom_z = b["max"][2], b["min"][2]
        cls.front_y = b["min"][1]

    def _bars(self):
        return [(o["bounds_in_carton_frame"]["min"][2],
                 o["bounds_in_carton_frame"]["max"][2])
                for o in self.panel if o["kind"] == "barcode"]

    def test_the_barcode_decodes_to_the_sku_id(self):
        """The assertion that makes "a real barcode" a fact rather than a claim.
        Reproducing the reference's unscannable 2D blob would be re-creating by
        hand the exact hallucination this engine exists to remove."""
        decoded = decode_code128_from_bars(self._bars())
        self.assertEqual(
            decoded, JOB["sku_id"],
            f"the built symbol reads {decoded!r}, not the manifest's "
            f"{JOB['sku_id']!r}")

    def test_barcode_has_bars(self):
        self.assertGreater(len(self._bars()), 20, "no barcode geometry was built")

    def test_barcode_lies_within_the_panel(self):
        for low, high in self._bars():
            self.assertGreaterEqual(low, self.bottom_z - 1e-6)
            self.assertLessEqual(high, self.top_z + 1e-6)

    def test_lot_and_exp_are_labels_with_no_values(self):
        """There is no lot or expiry data in this project, and a real carton does
        not carry one either - it is inkjetted at packing time onto a blank rule.
        Printing a plausible value would be inventing data on pharmaceutical
        packaging, which is precisely what the references did wrong."""
        self.assertEqual(self.by_name["panel_field_lot"]["body"], "LOT")
        self.assertEqual(self.by_name["panel_field_exp"]["body"], "EXP")
        bodies = [o["body"] for o in self.panel if o["body"]]
        for body in bodies:
            self.assertNotRegex(
                body, r"(?i)\b(lot|exp)\b\s*[:.]?\s*\S",
                f"{body!r} looks like a LOT/EXP field carrying a value")

    def test_every_panel_string_comes_from_the_manifest(self):
        """Same guarantee the front panel has: nothing invented, nothing padded."""
        allowed = {"LOT", "EXP", JOB["sku_id"], JOB["packaging_geometry"],
                   JOB["carton"]["material"],
                   "115x55x48mm", " / ".join(JOB["carton"]["features"])}
        for o in self.panel:
            if not o["body"]:
                continue
            for line in o["body"].split("\n"):
                self.assertIn(
                    line, allowed,
                    f"{line!r} is on the carton but not in the manifest")

    def test_nothing_on_the_panel_reaches_the_front_face(self):
        for o in self.panel:
            b = o["bounds_in_carton_frame"]
            self.assertLessEqual(
                b["min"][0], self.left_x + 0.02 * self.panel_w,
                f"{o['name']} has drifted off the side panel")

    def test_panel_elements_do_not_overlap_each_other(self):
        text = [o for o in self.panel if o["kind"] != "barcode"]
        for i, a in enumerate(text):
            for b in text[i + 1:]:
                pa, pb = a["bounds_in_carton_frame"], b["bounds_in_carton_frame"]
                overlap = (pa["min"][2] < pb["max"][2] and pb["min"][2] < pa["max"][2]
                           and pa["min"][1] < pb["max"][1] and pb["min"][1] < pa["max"][1])
                self.assertFalse(overlap, f"{a['name']} overlaps {b['name']}")

    def test_the_smallest_panel_in_the_catalogue_still_fits(self):
        """A 25x35mm T3 side panel, the shallowest there is. The data block is
        anchored under the LOT/EXP fields and sized in absolute millimetres, so
        without a shrink-to-fit its lines run off the bottom of the carton. One
        SKU in 391 hit this, and only the full sweep found it."""
        job = dict(JOB, carton=dict(JOB["carton"], width_mm=140.0, height_mm=35.0,
                                    depth_mm=25.0, features=[],
                                    material="Aluminum / Laminated"))
        scene = build_scene(job)
        c = scene["carton"]["self_bounds"]
        for o in scene["side_panel"]:
            b = o["bounds_in_carton_frame"]
            self.assertGreaterEqual(
                b["min"][2], c["min"][2] - 1e-6,
                f"{o['name']} runs off the bottom of the smallest panel")
            self.assertLessEqual(b["max"][2], c["max"][2] + 1e-6,
                                 f"{o['name']} runs off the top")

    def test_a_carton_declaring_no_features_still_builds(self):
        """21 of the 391 declare nothing. They must not get a features line, and
        must not crash."""
        job = dict(JOB, carton=dict(JOB["carton"], features=[]))
        panel = build_scene(job)["side_panel"]
        block = next(o for o in panel if o["name"] == "panel_data_block")
        self.assertNotIn("Braille", block["body"])
        self.assertTrue(any(o["kind"] == "barcode" for o in panel))


@unittest.skipUnless(os.environ.get("PHARMAGEN_SLOW_TESTS") == "1",
                     "slow: renders real packshots; set PHARMAGEN_SLOW_TESTS=1")
@unittest.skipUnless(Path(BLENDER_EXE).exists(),
                     f"Blender not installed at {BLENDER_EXE}")
class TestRenderedLuminance(unittest.TestCase):
    """The calibration gate: does a real render land where the references do?

    Everything else in this file asserts on scene STATE. This one asserts on
    pixels, which is the only way to catch the failure that started this work:
    the rig looked correct at every individual template and still lit a 170mm
    carton visibly darker than a 55mm one.

    Targets are measured from all nine curated references in
    01_input_raster/reference/ through the same sampling used here: front face
    235.0-241.5, backdrop a flat 254.9.
    """

    FRONT_MIN, FRONT_MAX = 235.0, 241.5
    BACKGROUND_MIN, BACKGROUND_FLAT = 250.0, 1.0
    # Deliberately spans both shapes and the full size range: a landscape 115mm
    # carton, the flattest (35mm tall), the tallest (170mm) and a portrait one.
    CASES = [("1-min", "#6B2D5C"), ("111-min", "#4B4632"),
             ("144-min", "#0D5FB8"), ("268-min", "#0D5FB8")]

    def test_every_shape_and_size_lands_in_the_reference_band(self):
        manifests = resolve_path("04_passports/render_manifests")
        with tempfile.TemporaryDirectory() as tmp:
            for stem, accent in self.CASES:
                out = Path(tmp) / f"{stem}.png"
                subprocess.run(
                    [BLENDER_EXE, "--background", "--factory-startup",
                     "--python", DRIVER_SCRIPT, "--",
                     "--job", str(Path(manifests) / f"{stem}.json"),
                     "--out", str(out), "--samples", "16",
                     "--res-x", "480", "--res-y", "480"],
                    capture_output=True, text=True, timeout=600,
                )
                self.assertTrue(out.exists(), f"{stem} did not render")
                front, bg, bg_sd = _front_face_and_background(out, accent)
                self.assertGreaterEqual(
                    front, self.FRONT_MIN,
                    f"{stem} front face is {front:.1f}, darker than any reference "
                    f"({self.FRONT_MIN}-{self.FRONT_MAX}) - the rig is under-"
                    "lighting this carton's size or shape")
                self.assertLessEqual(
                    front, self.FRONT_MAX,
                    f"{stem} front face is {front:.1f}, brighter than any reference")
                self.assertGreaterEqual(
                    bg, self.BACKGROUND_MIN,
                    f"{stem} backdrop is {bg:.1f}, not the clean white the "
                    "references show")
                self.assertLess(
                    bg_sd, self.BACKGROUND_FLAT,
                    f"{stem} backdrop varies by {bg_sd:.1f} across one corner; it "
                    "must be seamless, with no hot spot or falloff")


if __name__ == "__main__":
    unittest.main()
