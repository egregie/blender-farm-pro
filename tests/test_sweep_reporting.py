"""The sweep's own reporting, which has told the repository something false twice.

A code review caught it once (bc44665): a --limit smoke run overwrote a full
group's report. The fix routed partial runs to sweep_report.partial.*, and it
worked for the JSON only -- write_reports computed md_path and then hardcoded
the Markdown path anyway, so a 2-SKU run overwrote the 30-SKU record again and
rode into dc7d8e1 inside a 434-file rename commit.
"""
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import catalogue_sweep


def _record(stem="1-min"):
    """The smallest record write_reports will render without complaining."""
    return {
        "stem": stem,
        "product_name": "Test Product",
        "template_id": "T1",
        "carton_mm": [115.0, 55.0, 48.0],
        "rendered": True,
        "render_seconds": 1.0,
        "measurement": {"measured": False, "reason": "stub"},
    }


class TestPartialRunIsolation(unittest.TestCase):
    def test_partial_run_leaves_the_canonical_report_untouched(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            canonical_md = state / "sweep_report.md"
            canonical_json = state / "sweep_report.json"
            canonical_md.write_text("REAL 30-SKU REPORT", encoding="utf-8")
            canonical_json.write_text('{"counts": {"total": 30}}', encoding="utf-8")

            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "top30", "2026-01-01 00:00:00", limit=2)

            self.assertEqual(canonical_md.read_text(encoding="utf-8"),
                             "REAL 30-SKU REPORT",
                             "a --limit run overwrote the whole-group Markdown")
            self.assertEqual(canonical_json.read_text(encoding="utf-8"),
                             '{"counts": {"total": 30}}',
                             "a --limit run overwrote the whole-group JSON")
            # top30 is a curated group AND this is a limited run, so the name
            # records both narrowings.
            self.assertTrue((state / "sweep_report.top30.partial.md").exists())
            self.assertTrue((state / "sweep_report.top30.partial.json").exists())

    def test_a_narrower_group_leaves_the_canonical_report_untouched(self):
        """The same failure as above, one level up: whole run, narrower group.

        `sweep_report.md` was the 18 SKU of `families` while being named as the
        sweep of record, and a `top30` run would have replaced it with a
        different 30. Neither run is a lie about itself; the FILENAME is.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            canonical = state / "sweep_report.md"
            canonical.write_text("REAL 391-SKU BASELINE", encoding="utf-8")

            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "top30", "2026-01-01 00:00:00", limit=None)

            self.assertEqual(canonical.read_text(encoding="utf-8"),
                             "REAL 391-SKU BASELINE",
                             "a curated group overwrote the catalogue baseline")
            self.assertTrue((state / "sweep_report.top30.md").exists())
            self.assertTrue((state / "sweep_report.top30.json").exists())

    def test_the_whole_catalogue_writes_the_canonical_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], catalogue_sweep.CATALOGUE,
                    "2026-01-01 00:00:00", limit=None)
            self.assertTrue((state / "sweep_report.md").exists())
            self.assertIn("the whole group",
                          (state / "sweep_report.md").read_text(encoding="utf-8"))
            self.assertFalse((state / "sweep_report.partial.md").exists())
            self.assertFalse((state / "sweep_report.catalogue.md").exists())

    def test_a_partial_catalogue_run_is_still_partial(self):
        """The two rules compose: narrow by group AND by limit."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "families", "2026-01-01 00:00:00", limit=2)
            self.assertTrue((state / "sweep_report.families.partial.md").exists())
            self.assertFalse((state / "sweep_report.md").exists())
            self.assertFalse((state / "sweep_report.families.md").exists())


class TestProvenance(unittest.TestCase):
    """A PNG does not say which driver drew it, so the report has to.

    The first catalogue run measured renders from five driver generations and
    reported them as one baseline: eight SKU came back cropped and blown with a
    front face at 138.9, all of them rendered nine days and several rig fixes
    earlier. The measurements were right; the attribution was not.
    """

    def test_the_report_records_what_rendered_it(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], catalogue_sweep.CATALOGUE, "2026-01-01 00:00:00")
            data = json.loads((state / "sweep_report.json").read_text(encoding="utf-8"))
            md = (state / "sweep_report.md").read_text(encoding="utf-8")
        fp = data["rendered_by"]
        self.assertEqual(len(fp["driver_sha256"]), 64, "driver not content-hashed")
        self.assertIsNotNone(fp["engine_type"])
        self.assertIsNotNone(fp["samples"])
        self.assertIn(fp["driver_sha256"][:12], md,
                      "the human-readable report does not say what rendered it")

    def test_a_stale_render_is_flagged_before_anything_is_concluded_from_it(self):
        rec = dict(_record(), render_predates_driver=True)
        problems = catalogue_sweep.problems_for(rec)
        self.assertTrue(problems, "a stale render produced no problem at all")
        self.assertIn("older than the driver", problems[0],
                      "staleness must lead: the rows under it measure other code")

    def test_a_current_render_is_not_flagged_as_stale(self):
        problems = catalogue_sweep.problems_for(_record())
        self.assertFalse([p for p in problems if "older than the driver" in p])

    def test_staleness_is_measured_against_the_driver_not_the_clock(self):
        """A render made after the driver is kept; one made before is not."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "x.png"
            png.write_bytes(b"")
            fp = dict(catalogue_sweep.driver_fingerprint())

            fp["driver_mtime"] = png.stat().st_mtime + 1000
            with patch.object(catalogue_sweep, "_FINGERPRINT", fp):
                self.assertTrue(catalogue_sweep.is_stale(png),
                                "a render older than the driver was kept")

            fp["driver_mtime"] = png.stat().st_mtime - 1000
            with patch.object(catalogue_sweep, "_FINGERPRINT", fp):
                self.assertFalse(catalogue_sweep.is_stale(png),
                                 "a current render was needlessly re-rendered")


class TestCoverageCaveat(unittest.TestCase):
    """The caveat has to describe THIS run, not a run someone had in mind once.

    It used to name the same seven templates as unexercised whatever was
    measured, so the committed `families` report listed all nine templates as
    covered and then declared seven of them absent, two sentences apart.
    """

    def _caveat(self, records, group, limit=None):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    records, group, "2026-01-01 00:00:00", limit=limit)
            md = catalogue_sweep.report_paths(limit, group)[1]
            text = (state / md.name).read_text(encoding="utf-8")
        head = text.split("### Coverage caveat", 1)[1]
        return head.split("##", 1)[0].strip()

    def test_a_template_that_was_measured_is_not_called_absent(self):
        covered = {r["template_id"] for r in
                   [_record("1-min"), _record("2-min")]}
        caveat = self._caveat([_record("1-min"), _record("2-min")], "top30")
        for tid in covered:
            self.assertNotIn(f"`{tid}`", caveat,
                             f"{tid} was measured and the caveat calls it absent")

    def test_every_template_present_is_not_reported_as_every_SKU(self):
        """`families` covers all nine templates with 18 of 391 SKU.

        The first version of the computed caveat called that "catalogue-wide",
        which is the overstatement the caveat exists to prevent — one coverage
        swapped for another.
        """
        records = [dict(_record(f"{i}-min"), template_id=t)
                   for i, t in enumerate(catalogue_sweep.catalogue_templates(), 1)]
        caveat = self._caveat(records, "families")
        self.assertNotIn("not exercised here", caveat)
        self.assertIn(f"{len(records)} of the catalogue's", caveat)
        self.assertNotIn("this run is the catalogue", caveat)

    def test_the_whole_catalogue_is_allowed_to_say_so(self):
        templates = catalogue_sweep.catalogue_templates()
        size = len(list(catalogue_sweep.MANIFEST_DIR.glob("*.json")))
        records = [dict(_record(f"{i}-min"), template_id=templates[i % len(templates)])
                   for i in range(size)]
        caveat = self._caveat(records, catalogue_sweep.CATALOGUE)
        self.assertIn(f"All {size} SKU", caveat)
        self.assertIn("this run is the catalogue", caveat)
        self.assertNotIn("not exercised here", caveat)


if __name__ == "__main__":
    unittest.main()
