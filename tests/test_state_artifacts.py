"""Guards the permanent record in 00_PROJECT_STATE against self-contradiction.

Task 1 fixed one report's writer. This is the general form: any generated
Markdown that has a JSON sibling must agree with it, whatever produced them.
The failure this exists to prevent is a reader trusting a summary that its own
data disproves.
"""
import json
import re
import unittest
from pathlib import Path

from src.utils import PROJECT_ROOT

STATE_DIR = PROJECT_ROOT / "00_PROJECT_STATE"


class TestStateArtifactsAgree(unittest.TestCase):
    def _pairs(self):
        for json_path in sorted(STATE_DIR.glob("*.json")):
            md_path = json_path.with_suffix(".md")
            if md_path.exists():
                yield json_path, md_path

    def test_at_least_one_pair_exists(self):
        # Prevent vacuity: ensure each content check has at least one pair to exercise it.
        # legibility_report.json has none of the keys the content tests look for, so deleting
        # sweep_report.json/md would leave all three content tests passing via continue() on a
        # pair that carries nothing. This asserts the existence of covering data before tests
        # that would skip silently if it were absent.
        pairs = list(self._pairs())
        self.assertTrue(pairs,
                        f"no *.json/*.md report pairs found in {STATE_DIR}")

        has_covers_whole_group = False
        has_counts_total = False
        has_records = False

        for json_path, _ in pairs:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if "covers_whole_group" in data:
                has_covers_whole_group = True
            if data.get("counts", {}).get("total") is not None:
                has_counts_total = True
            if "records" in data:
                has_records = True

        missing_keys = []
        if not has_covers_whole_group:
            missing_keys.append("covers_whole_group")
        if not has_counts_total:
            missing_keys.append("counts.total")
        if not has_records:
            missing_keys.append("records")

        self.assertFalse(
            missing_keys,
            f"no report pairs carry keys needed for content tests: {', '.join(missing_keys)}"
        )

    def test_scope_claim_matches_the_data(self):
        for json_path, md_path in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if "covers_whole_group" not in data:
                    continue
                text = md_path.read_text(encoding="utf-8")
                says_partial = "a partial run" in text
                self.assertEqual(
                    says_partial, not data["covers_whole_group"],
                    f"{md_path.name} says partial={says_partial} but "
                    f"{json_path.name} says covers_whole_group="
                    f"{data['covers_whole_group']}")

    def test_headline_count_matches_the_data(self):
        for json_path, md_path in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                total = (data.get("counts") or {}).get("total")
                if total is None:
                    continue
                text = md_path.read_text(encoding="utf-8")
                m = re.search(r"SKU in group: \*\*(\d+)\*\*", text)
                self.assertIsNotNone(
                    m, f"{md_path.name} has no 'SKU in group' line to check")
                self.assertEqual(
                    int(m.group(1)), total,
                    f"{md_path.name} claims {m.group(1)} SKU, "
                    f"{json_path.name} holds {total}")

    def test_record_count_matches_the_headline(self):
        for json_path, _ in self._pairs():
            with self.subTest(report=json_path.name):
                data = json.loads(json_path.read_text(encoding="utf-8"))
                records, counts = data.get("records"), data.get("counts")
                if records is None or counts is None:
                    continue
                self.assertEqual(
                    len(records), counts["total"],
                    f"{json_path.name} summarises {counts['total']} SKU but "
                    f"carries {len(records)} records")


if __name__ == "__main__":
    unittest.main()
