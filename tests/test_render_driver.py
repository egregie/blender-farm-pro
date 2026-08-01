"""Tests for engine selection in assets/blender/render_driver.py.

The driver imports bpy at module scope, so it only runs inside Blender's own
interpreter. These tests therefore drive the real executable as a subprocess,
the same way src/blender_renderer.py does, and are skipped when the configured
blender.executable is not installed so the suite still passes without Blender.

Renders are 64x64 at 1 sample: what is under test is which engine Blender ends
up using, not image quality.

Regression under test: the driver used to decide availability by introspecting
bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items. `engine` is a
DYNAMIC enum, so that returns only a static placeholder -- ('BLENDER_EEVEE',)
on 5.1.2 -- and never CYCLES, even where Cycles is enabled and working. Every
render silently fell through to EEVEE with `samples` never applied.
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.render_manifest import build_manifest
from src.utils import load_config, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASSPORT = PROJECT_ROOT / "04_passports" / "passports_json" / "1-min.json"

_CFG = load_config()
BLENDER_EXE = Path(_CFG["blender"]["executable"])
DRIVER = resolve_path(_CFG["blender"]["driver_script"])
CONFIGURED_ENGINE = _CFG["blender"]["engine_type"]

_HAVE_BLENDER = BLENDER_EXE.exists()
_SKIP_REASON = f"Blender not installed at {BLENDER_EXE}"


def _manifest(stem: str = "1-min") -> dict:
    path = PROJECT_ROOT / "04_passports" / "passports_json" / f"{stem}.json"
    return build_manifest(json.loads(path.read_text(encoding="utf-8")))


def _run_driver(engine_type: str, workdir: Path, job: dict = None, res: str = "64"):
    """Invoke the driver exactly as blender_renderer.py does, but tiny."""
    job_path = workdir / "job.json"
    out_path = workdir / "out.png"
    job_path.write_text(
        json.dumps(_manifest() if job is None else job),
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            str(BLENDER_EXE), "--background", "--factory-startup",
            "--python", str(DRIVER), "--",
            "--job", str(job_path),
            "--out", str(out_path),
            "--engine-type", engine_type,
            "--samples", "1",
            "--res-x", res,
            "--res-y", res,
        ],
        capture_output=True, text=True, timeout=300,
    )
    return proc, out_path


@unittest.skipUnless(_HAVE_BLENDER, _SKIP_REASON)
class TestEngineIsHonoured(unittest.TestCase):
    """The engine that was asked for is the engine that renders."""

    def test_cycles_is_used_when_requested(self):
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("CYCLES", Path(td))
            self.assertEqual(proc.returncode, 0,
                             f"driver failed:\n{proc.stdout}\n{proc.stderr}")
            self.assertTrue(out_path.exists(), "no PNG written")
            self.assertIn("[render_driver] engine CYCLES", proc.stdout,
                          "driver did not report rendering on CYCLES; it "
                          f"substituted another engine.\n{proc.stdout}")

    def test_eevee_is_used_when_requested(self):
        """The substitution guard must not push everything to Cycles either."""
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("BLENDER_EEVEE", Path(td))
            self.assertEqual(proc.returncode, 0,
                             f"driver failed:\n{proc.stdout}\n{proc.stderr}")
            self.assertTrue(out_path.exists(), "no PNG written")
            self.assertIn("[render_driver] engine BLENDER_EEVEE", proc.stdout)

    def test_configured_engine_type_is_available_in_this_blender(self):
        """config.yaml must name an engine this install can actually provide.

        This is the check that was missing: blender.engine_type said CYCLES
        while every render silently came out of EEVEE.
        """
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver(CONFIGURED_ENGINE, Path(td))
            self.assertEqual(
                proc.returncode, 0,
                f"config.yaml requests blender.engine_type={CONFIGURED_ENGINE!r}, "
                f"which this Blender rejected:\n{proc.stderr}")
            self.assertIn(f"[render_driver] engine {CONFIGURED_ENGINE}", proc.stdout)


@unittest.skipUnless(_HAVE_BLENDER, _SKIP_REASON)
class TestUnavailableEngineIsFatal(unittest.TestCase):
    """An engine this Blender cannot provide stops the run."""

    def test_unknown_engine_exits_nonzero_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("NOT_A_REAL_ENGINE", Path(td))
            self.assertNotEqual(proc.returncode, 0,
                                "unavailable engine was silently substituted")
            self.assertFalse(out_path.exists(),
                             "an off-spec PNG was produced anyway")

    def test_failure_names_the_requested_engine_and_refuses_substitution(self):
        with tempfile.TemporaryDirectory() as td:
            proc, _ = _run_driver("NOT_A_REAL_ENGINE", Path(td))
            combined = proc.stdout + proc.stderr
            self.assertIn("NOT_A_REAL_ENGINE", combined,
                          "error does not say which engine was unavailable")
            self.assertNotIn("falling back", combined.lower(),
                             "driver still advertises a fallback")


@unittest.skipUnless(_HAVE_BLENDER, _SKIP_REASON)
class TestLabelContent(unittest.TestCase):
    """The manifest's label_content must reach the rendered face."""

    def test_all_three_strings_are_placed(self):
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("CYCLES", Path(td))
            self.assertEqual(proc.returncode, 0,
                             f"driver failed:\n{proc.stdout}\n{proc.stderr}")
            self.assertTrue(out_path.exists())
            self.assertIn("[render_driver] label: 3 text object(s)", proc.stdout,
                          f"brand + dosage + count expected\n{proc.stdout}")

    def test_long_brand_wraps_to_a_second_line(self):
        """412-min is the catalogue's worst fit: a 30-character brand on the
        narrowest face. It must wrap rather than overflow or be truncated."""
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("CYCLES", Path(td), job=_manifest("412-min"))
            self.assertEqual(proc.returncode, 0,
                             f"driver failed:\n{proc.stdout}\n{proc.stderr}")
            self.assertIn("[render_driver] label: 4 text object(s)", proc.stdout,
                          f"two brand lines + dosage + count expected\n{proc.stdout}")

    def test_label_text_actually_reaches_the_image(self):
        """Same carton, same palette, different brand string -> different pixels.
        Guards against the text being built but never rendered."""
        from PIL import Image, ImageChops

        job_a = _manifest()
        job_b = _manifest()
        job_b["label_content"]["brand_name_display"] = "ZZZZ WWWW"
        with tempfile.TemporaryDirectory() as td:
            a_dir, b_dir = Path(td) / "a", Path(td) / "b"
            a_dir.mkdir(), b_dir.mkdir()
            proc_a, out_a = _run_driver("CYCLES", a_dir, job=job_a, res="200")
            proc_b, out_b = _run_driver("CYCLES", b_dir, job=job_b, res="200")
            self.assertEqual(proc_a.returncode, 0, proc_a.stderr)
            self.assertEqual(proc_b.returncode, 0, proc_b.stderr)

            img_a = Image.open(out_a).convert("RGB")
            img_b = Image.open(out_b).convert("RGB")
            diff = ImageChops.difference(img_a, img_b).convert("L")
            hist = diff.histogram()
            changed = sum(hist[level] for level in range(3, len(hist)))
            self.assertGreater(
                changed, 20,
                "changing the brand string barely moved the image; the label is "
                "probably not being rendered")


@unittest.skipUnless(_HAVE_BLENDER, _SKIP_REASON)
class TestLabelContractIsEnforced(unittest.TestCase):
    """label_content is `required` in the schema; a job without it bypassed the
    contract, and an unlabelled packshot is a silent content failure."""

    def test_missing_label_content_exits_nonzero_and_writes_nothing(self):
        job = _manifest()
        job.pop("label_content")
        with tempfile.TemporaryDirectory() as td:
            proc, out_path = _run_driver("CYCLES", Path(td), job=job)
            self.assertNotEqual(proc.returncode, 0,
                                "an unlabelled carton was rendered anyway")
            self.assertFalse(out_path.exists())
            self.assertIn("label_content", proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
