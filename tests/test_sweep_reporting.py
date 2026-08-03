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
            self.assertTrue((state / "sweep_report.partial.md").exists())
            self.assertTrue((state / "sweep_report.partial.json").exists())

    def test_whole_group_run_writes_the_canonical_report(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with patch.object(catalogue_sweep, "STATE_DIR", state):
                catalogue_sweep.write_reports(
                    [_record()], "top30", "2026-01-01 00:00:00", limit=None)
            self.assertTrue((state / "sweep_report.md").exists())
            self.assertIn("the whole group",
                          (state / "sweep_report.md").read_text(encoding="utf-8"))
            self.assertFalse((state / "sweep_report.partial.md").exists())


if __name__ == "__main__":
    unittest.main()
