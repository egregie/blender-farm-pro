"""The analytic silhouette model, checked against Blender's own arithmetic.

This model exists because the project's only measure of "how much of the frame
does the carton fill" was pixel measurement of a rendered image, and a white
carton on a 255 backdrop is precisely the case that defeats it: the brightly lit
top face blends into the background, so a landscape carton reads shorter than it
is. Every landscape row of the measured table in CURRENT_STATE.md is 5-9 points
low on height as a result.

So the model has to be trustworthy before anything is built on it, and the only
trustworthy check is Blender's own output. `05_assets/blender/render_driver.py`
projects the carton's printed faces itself and writes the result beside each
render as `{stem}.view.json`; one of those is committed as a fixture. If the
model reproduces those pixels, it is doing the same arithmetic Blender is.
"""
import json
import math
import re
import unittest
from pathlib import Path

from src import silhouette
from src.utils import PROJECT_ROOT

FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "ocr" / "1-min.view.json"
DRIVER = PROJECT_ROOT / "05_assets" / "blender" / "render_driver.py"

# 1-min: T1, the catalogue's modal carton. Dimensions read from its manifest
# rather than hardcoded, so the fixture and the test cannot drift apart.
FIXTURE_MANIFEST = PROJECT_ROOT / "tests" / "fixtures" / "ocr" / "1-min.manifest.json"


class TestModelMatchesBlender(unittest.TestCase):
    """The model must agree with the renderer, not merely look plausible."""

    @classmethod
    def setUpClass(cls):
        cls.view = json.loads(FIXTURE.read_text(encoding="utf-8"))
        manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))
        c = manifest["carton"]
        cls.dims = (c["width_mm"], c["height_mm"], c["depth_mm"])
        cls.template = manifest["template_id"]
        cls.res = cls.view["resolution"]

    def test_front_face_corners_match_the_renderers_own_projection(self):
        got = silhouette.front_face_px(self.dims, self.template, self.res)
        want = self.view["front_face_px"]
        self.assertEqual(len(got), 4)
        for label, g, w in zip(("TL", "TR", "BR", "BL"), got, want):
            delta = math.hypot(g[0] - w[0], g[1] - w[1])
            self.assertLess(
                delta, 0.1,
                f"{label}: model says {g[0]:.1f},{g[1]:.1f} but the driver "
                f"wrote {w[0]:.1f},{w[1]:.1f} ({delta:.2f} px apart). The "
                f"model is not doing the same arithmetic as the renderer.")

    def test_side_panel_corners_match_too(self):
        got = silhouette.side_panel_px(self.dims, self.template, self.res)
        want = self.view["side_panel_px"]
        for label, g, w in zip(("TL", "TR", "BR", "BL"), got, want):
            delta = math.hypot(g[0] - w[0], g[1] - w[1])
            self.assertLess(delta, 0.1, f"side {label}: {delta:.2f} px apart")

    def test_the_silhouette_encloses_both_printed_faces(self):
        # Weak on its own, but it catches a silhouette computed from the wrong
        # corner set -- the printed faces are part of the carton, so whatever
        # bounds the carton must bound them.
        x0, y0, x1, y1 = silhouette.silhouette_px(self.dims, self.template, self.res)
        for quad in (self.view["front_face_px"], self.view["side_panel_px"]):
            for x, y in quad:
                self.assertGreaterEqual(x, x0 - 0.1)
                self.assertLessEqual(x, x1 + 0.1)
                self.assertGreaterEqual(y, y0 - 0.1)
                self.assertLessEqual(y, y1 + 0.1)


class TestCameraConstantsAgreeWithTheDriver(unittest.TestCase):
    """`render_driver.py` cannot be imported outside Blender -- it does
    `import bpy` at module scope -- so its camera constants are duplicated here.
    Duplication without a check is how two sources of truth start disagreeing,
    so this reads the driver as text and fails the moment they part company.
    """

    @classmethod
    def setUpClass(cls):
        cls.source = DRIVER.read_text(encoding="utf-8")

    def _literal(self, name):
        m = re.search(rf"^{name}\s*=\s*([0-9.]+)", self.source, re.M)
        self.assertIsNotNone(m, f"{name} not found as a module-level constant "
                                f"in render_driver.py; the model can no longer "
                                f"verify it and must be updated deliberately")
        return float(m.group(1))

    def test_lens_and_sensor_match(self):
        self.assertEqual(silhouette.LENS_MM, self._literal("LENS_MM"))
        self.assertEqual(silhouette.SENSOR_MM, self._literal("SENSOR_MM"))

    def test_sphere_fill_matches(self):
        self.assertEqual(silhouette.SPHERE_FILL, self._literal("SPHERE_FILL"))

    def test_both_camera_families_match(self):
        # The driver assigns PITCH_DEG/ROTATION_DEG in two branches, one per
        # family. Both pairs must be found and both must match.
        pairs = re.findall(
            r"PITCH_DEG,\s*ROTATION_DEG\s*=\s*([0-9.]+),\s*([0-9.]+)", self.source)
        self.assertEqual(len(pairs), 2,
                         "expected exactly two camera branches in the driver")
        found = {(float(p), float(r)) for p, r in pairs}
        self.assertIn(silhouette.CAMERA_VERTICAL, found)
        self.assertIn(silhouette.CAMERA_DEFAULT, found)

    def test_the_camera_family_is_the_drivers_not_the_manifests(self):
        # A trap worth pinning: render_manifest.py also defines VERTICAL_FAMILY,
        # and it is a DIFFERENT set -- it includes T_BOTTLE_BOX because that
        # carton stands upright, while the driver's set governs which CAMERA is
        # used and excludes it. Taking the manifest's set here would silently
        # shoot T_BOTTLE_BOX with the wrong pitch and rotation.
        from src.render_manifest import VERTICAL_FAMILY as orientation_family
        self.assertNotEqual(silhouette.CAMERA_VERTICAL_TEMPLATES, orientation_family)
        self.assertIn("T_BOTTLE_BOX", orientation_family)
        self.assertNotIn("T_BOTTLE_BOX", silhouette.CAMERA_VERTICAL_TEMPLATES)

        m = re.search(r"^VERTICAL_FAMILY\s*=\s*\{([^}]*)\}", self.source, re.M)
        self.assertIsNotNone(m, "driver's VERTICAL_FAMILY not found")
        in_driver = {t.strip().strip('"\'') for t in m.group(1).split(",") if t.strip()}
        self.assertEqual(silhouette.CAMERA_VERTICAL_TEMPLATES, in_driver)


class TestFrameFill(unittest.TestCase):
    def test_fill_is_a_percentage_of_the_frame(self):
        w, h = silhouette.frame_fill((115.0, 55.0, 48.0), "T1")
        for v in (w, h):
            self.assertGreater(v, 0.0)
            self.assertLessEqual(v, 100.0)

    def test_aspect_is_width_over_height(self):
        dims, tpl = (115.0, 55.0, 48.0), "T1"
        w, h = silhouette.frame_fill(dims, tpl)
        self.assertAlmostEqual(silhouette.silhouette_aspect(dims, tpl), w / h, places=6)

    def test_a_wider_carton_has_a_wider_silhouette(self):
        narrow = silhouette.silhouette_aspect((80.0, 170.0, 35.0), "T_VERT_VIAL")
        wide = silhouette.silhouette_aspect((150.0, 170.0, 35.0), "T_VERT_VIAL")
        self.assertGreater(wide, narrow)

    def test_scale_alone_does_not_change_the_silhouette(self):
        # Framing is solved from the bounding sphere, so doubling every edge
        # doubles the distance too and the picture is identical. This is why
        # only proportions can be art-directed, not size.
        a = silhouette.frame_fill((115.0, 55.0, 48.0), "T1")
        b = silhouette.frame_fill((230.0, 110.0, 96.0), "T1")
        self.assertAlmostEqual(a[0], b[0], places=6)
        self.assertAlmostEqual(a[1], b[1], places=6)


if __name__ == "__main__":
    unittest.main()
