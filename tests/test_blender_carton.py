"""Geometry tests for the procedural carton built inside Blender.

These are the only tests that check what Blender ACTUALLY builds rather than
what the project side intended. They drive the driver's `--dump-scene` mode,
which builds the real scene and writes measured geometry as JSON without
rendering, so the whole file costs a couple of Blender launches instead of a
Cycles/EEVEE pass.

Everything is asserted from MEASURED extents (`bound_box` through
`matrix_world`), never recomputed from the manifest — a test that re-derived
the expected numbers the same way the driver does would pass no matter how
wrong the scene was.

Skipped, not failed, when Blender is not installed: the rest of the suite is
pure-Python and must stay runnable without a 3D application on PATH.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.utils import load_config, get_path, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

_CFG = load_config()
BLENDER_EXE = _CFG["blender"]["executable"]
DRIVER = resolve_path(_CFG["blender"]["driver_script"])
MANIFESTS = get_path(_CFG, "passports_manifests")

# Landscape blister carton (the 287-SKU majority) and a tall vial tray from the
# vertical family, which takes the other camera calibration branch.
T1_STEM = "1-min"
VERT_STEM = "144-min"

# Tolerance in metres. Blender stores vertices as float32, so a 0.115 m edge
# round-trips with ~1e-8 m of error; 0.01 mm is far inside that and far below
# anything that matters on a carton.
TOL_M = 1e-5

_DUMPS: dict[str, dict] = {}


def _blender_available() -> bool:
    return Path(BLENDER_EXE).exists() and Path(DRIVER).exists()


def dump_for(stem: str) -> dict:
    """Build the scene for one manifest in Blender and return the measurements.

    Cached per stem for the whole module, so adding assertions is free and only
    adding a new SKU costs another Blender launch.
    """
    if stem in _DUMPS:
        return _DUMPS[stem]

    manifest = MANIFESTS / f"{stem}.json"
    if not manifest.exists():
        raise unittest.SkipTest(f"manifest not generated yet: {manifest}")

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"{stem}.scene.json"
        proc = subprocess.run(
            [BLENDER_EXE, "--background", "--factory-startup",
             "--python", str(DRIVER), "--",
             "--job", str(manifest), "--dump-scene", str(out)],
            capture_output=True, text=True, timeout=180,
        )
        if not out.exists():
            raise AssertionError(
                f"--dump-scene produced nothing for {stem} "
                f"(exit={proc.returncode}):\n{(proc.stderr or proc.stdout)[-2000:]}"
            )
        _DUMPS[stem] = json.loads(out.read_text(encoding="utf-8"))
    return _DUMPS[stem]


@unittest.skipUnless(_blender_available(), f"Blender not found at {BLENDER_EXE}")
class TestCartonScale(unittest.TestCase):
    """Scene units are real metres: 115mm of carton is 0.115 in Blender.

    The regression this pins down: `primitive_cube_add(size=1.0)` makes a cube
    of EDGE length 1 (spanning -0.5..0.5), so scaling it by (w/2, d/2, h/2)
    built every carton at half its nominal millimetres.
    """

    def _assert_true_scale(self, stem):
        dump = dump_for(stem)
        req = dump["requested_mm"]
        # object.dimensions is the local bounding box, so it reports true edge
        # lengths regardless of the carton's Z rotation.
        got_w, got_d, got_h = dump["carton"]["dimensions"]
        self.assertAlmostEqual(got_w, req["width"] / 1000.0, delta=TOL_M,
                               msg=f"{stem}: carton width is not the manifest width")
        self.assertAlmostEqual(got_h, req["height"] / 1000.0, delta=TOL_M,
                               msg=f"{stem}: carton height is not the manifest height")
        self.assertAlmostEqual(got_d, req["depth"] / 1000.0, delta=TOL_M,
                               msg=f"{stem}: carton depth is not the manifest depth")

    def test_landscape_carton_is_true_scale(self):
        self._assert_true_scale(T1_STEM)

    def test_vertical_family_carton_is_true_scale(self):
        self._assert_true_scale(VERT_STEM)

    def test_vertical_family_carton_stands_taller_than_it_is_wide(self):
        # Orientation survives the trip into Blender: orient_for_template()
        # stands the longest edge up for this family.
        dump = dump_for(VERT_STEM)
        w, _d, h = dump["carton"]["dimensions"]
        self.assertGreater(h, w, "vertical-family carton came out landscape")


@unittest.skipUnless(_blender_available(), f"Blender not found at {BLENDER_EXE}")
class TestCartonSeating(unittest.TestCase):
    """The carton rests ON the backdrop, it does not hover over it.

    A floating box throws a detached contact shadow, and
    01_input_raster/reference_analysis.md reads the references as
    near-shadowless — so seating is a reference-matching requirement, not
    housekeeping.
    """

    def _assert_seated(self, stem):
        dump = dump_for(stem)
        gap = dump["carton"]["ground_gap"]
        self.assertAlmostEqual(
            gap, 0.0, delta=TOL_M,
            msg=f"{stem}: carton floats {gap * 1000:.2f}mm above the ground plane",
        )

    def test_landscape_carton_sits_on_the_ground_plane(self):
        self._assert_seated(T1_STEM)

    def test_vertical_family_carton_sits_on_the_ground_plane(self):
        self._assert_seated(VERT_STEM)


@unittest.skipUnless(_blender_available(), f"Blender not found at {BLENDER_EXE}")
class TestAccentStripe(unittest.TestCase):
    """The accent stripe is printed ON the front face.

    Asserted in the carton's LOCAL frame, so the carton's Z rotation is
    factored out and the stripe's placement can be compared against the face it
    is supposed to be lying on.
    """

    def setUp(self):
        dump = dump_for(T1_STEM)
        self.stripe = dump["stripe"]["local"]
        self.face = dump["stripe"]["carton_local"]

    def test_stripe_is_flush_against_the_front_face(self):
        # Front face is the carton's -Y side; the stripe's back edge should meet
        # it, sitting a hair proud to avoid z-fighting rather than floating in
        # mid-air in front of the box.
        gap = self.face["min"][1] - self.stripe["max"][1]
        self.assertAlmostEqual(
            gap, 0.0, delta=2e-4,
            msg=f"stripe hangs {gap * 1000:.2f}mm off the front face",
        )

    def test_stripe_stands_proud_of_the_face_not_sunk_into_it(self):
        self.assertLess(
            self.stripe["min"][1], self.face["min"][1],
            "stripe is buried inside the carton instead of printed on it",
        )

    def test_stripe_stays_within_the_front_face(self):
        self.assertGreaterEqual(self.stripe["min"][0], self.face["min"][0] - TOL_M,
                                "stripe overhangs the left edge")
        self.assertLessEqual(self.stripe["max"][0], self.face["max"][0] + TOL_M,
                             "stripe overhangs the right edge")
        self.assertGreaterEqual(self.stripe["min"][2], self.face["min"][2] - TOL_M,
                                "stripe hangs below the carton")
        self.assertLessEqual(self.stripe["max"][2], self.face["max"][2] + TOL_M,
                             "stripe runs off the top of the carton")

    def test_stripe_band_is_8_to_12_percent_of_face_height(self):
        # The band thickness rule from reference_analysis.md.
        frac = self.stripe["size"][2] / self.face["size"][2]
        self.assertGreaterEqual(frac, 0.08 - 1e-6)
        self.assertLessEqual(frac, 0.12 + 1e-6)


@unittest.skipUnless(_blender_available(), f"Blender not found at {BLENDER_EXE}")
class TestFraming(unittest.TestCase):
    """Framing is an INVARIANT across the true-scale change.

    SPHERE_FILL exists to hit the framing measured off the reference renders.
    Making the carton twice as big without re-solving it would have doubled the
    object in frame, so these bounds are what forced the constant to be
    recalibrated rather than left alone.
    """

    def test_landscape_carton_fills_the_reference_share_of_frame(self):
        f = dump_for(T1_STEM)["framing"]
        self.assertAlmostEqual(
            f["max_frac"], 0.756, delta=0.01,
            msg="T1 framing drifted; SPHERE_FILL no longer matches the "
                "reference calibration",
        )

    def test_every_template_lands_in_the_calibrated_band(self):
        # The band the SPHERE_FILL comment claims for the sampled templates.
        for stem in (T1_STEM, VERT_STEM):
            with self.subTest(stem=stem):
                frac = dump_for(stem)["framing"]["max_frac"]
                self.assertGreater(frac, 0.70, f"{stem} renders too small in frame")
                self.assertLess(frac, 0.85, f"{stem} is cropped or nearly touching "
                                            "the frame edge")

    def test_carton_is_vertically_centred(self):
        # reference_analysis.md: object centred at 50-52% of frame height.
        for stem in (T1_STEM, VERT_STEM):
            with self.subTest(stem=stem):
                centre = dump_for(stem)["framing"]["centre_y_frac"]
                self.assertAlmostEqual(centre, 0.5, delta=0.05)


if __name__ == "__main__":
    unittest.main()
