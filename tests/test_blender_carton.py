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
FILM_EXPOSURE_LANDSCAPE = -2.75
FILM_EXPOSURE_PORTRAIT = -2.88

# Studio-strobe-scale wattages, restated independently of the driver. These are
# the power at the rig's reference carton size, not for every carton - see
# light_energy() for why they have to scale with the square of the size.
KEY_W, FILL_W = 25.0, 8.0

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


def _front_face_and_background(png_path, accent_hex):
    """Mean brightness of the carton's front face, and of the backdrop.

    The front face is sampled as a band immediately above the accent stripe,
    following the stripe's slope column by column. A plain image-space rectangle
    would also catch the TOP face on a flat carton (T3 is 140x35mm), which is
    legitimately brighter, and report it as the front face blowing out.
    """
    import numpy as np
    from PIL import Image

    a = np.asarray(Image.open(png_path).convert("RGB")).astype(float)
    H, W, _ = a.shape
    g = a.mean(axis=2)
    accent = np.array([int(accent_hex.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)],
                      dtype=float)
    stripe = ((a.max(axis=2) - a.min(axis=2)) > 15) & \
             (np.linalg.norm(a - accent, axis=2) < 110)
    stripe[:H // 2, :] = False                       # the band is on the lower half
    if stripe.sum() < 40:
        raise AssertionError(f"no accent stripe found in {png_path}")
    sx = np.nonzero(stripe)[1]
    pad, band = int(0.02 * W), int(0.05 * H)
    samples = []
    for x in range(sx.min() + pad, sx.max() - pad):
        col = np.nonzero(stripe[:, x])[0]
        if col.size:
            samples.append(g[max(0, col.min() - pad - band):max(0, col.min() - pad), x])
    front = np.concatenate([s for s in samples if s.size])
    corner = g[int(0.03 * H):int(0.11 * H), int(0.03 * W):int(0.11 * W)]
    return front[front > 120].mean(), corner.mean(), corner.std()


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
