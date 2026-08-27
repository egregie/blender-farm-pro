"""The signed decision, and the guard that makes an unsigned one stop a build.

`00_PROJECT_STATE/MARKS_DECISION.md` says no code may run until its Purpose,
Basis and Scope are written by the owner. That sentence is only worth what
enforces it, so `src/marks_decision.load()` raises on a blank one and these tests
pin that — along with the rule that `yes` is the only value permitting anything.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from src.marks_decision import DECISION_PATH, MarksNotDecided, load

SIGNED = DECISION_PATH.read_text(encoding="utf-8")


def _written(text: str) -> Path:
    tmp = Path(tempfile.mkdtemp()) / "MARKS_DECISION.md"
    tmp.write_text(text, encoding="utf-8")
    return tmp


class TestTheSignedFileIsReadExactly(unittest.TestCase):

    def setUp(self):
        self.d = load()

    def test_the_counts_are_the_ones_the_owner_signed(self):
        self.assertEqual(len(self.d.holes), 8)
        self.assertEqual(len(self.d.components), 15)

    def test_the_header_block_is_the_owners_words_and_not_empty(self):
        for name in ("purpose", "basis", "scope"):
            with self.subTest(name):
                self.assertTrue(getattr(self.d, name).strip())

    def test_the_basis_states_the_limit_the_answers_obey(self):
        """Not a style check: the basis and the answers must be one decision.

        Eleven rows were withdrawn because they carried a mark belonging to
        another company's product. If the basis ever stopped saying so while
        those rows stayed withdrawn, the file would be recording two different
        decisions and nobody could tell which one the build obeyed.
        """
        # Whitespace-normalised: the basis is wrapped prose and a line break
        # falling inside the phrase is not a change of meaning.
        flat = " ".join(self.d.basis.split())
        self.assertIn("belongs to the manufacturer", flat)
        self.assertIn("falsely associate", flat)
        for folder in ("133_Ambien", "60_Cialis_Professional"):
            allowed = [k for f, k in self.d.components if f == folder]
            self.assertEqual(allowed, [], f"{folder} is allowed a mark, but the "
                                          f"basis excludes marks belonging to "
                                          f"another company's product")

    def test_the_holographic_oval_is_refused_by_absence_and_not_by_name(self):
        """`n/a` is not `yes`, and that is the whole mechanism.

        The security feature must not be reachable, and it must not be
        unreachable because a class name was special-cased in code -- a
        later reclassification would then quietly re-open it.
        """
        self.assertNotIn(("59_Cialis", "secondary_1#0"), self.d.components)
        self.assertIn(("59_Cialis", "secondary_1#0"), self.d.refused)
        import src.marks_decision as m
        self.assertNotIn("secondary_1", Path(m.__file__).read_text(encoding="utf-8")
                         .split('"""', 2)[-1],
                         "the loader names the holographic oval in its code; it "
                         "must be refused by the table saying n/a, not by a "
                         "special case that a reclassification could bypass")


class TestAnUnsignedFileStopsTheBuild(unittest.TestCase):
    """The file's own sentence, made executable."""

    def _blanked(self, label: str) -> str:
        return re.sub(rf"(\*\*{re.escape(label)}[^\n]*\*\*)(.*?)(?=\n\*\*|\n---)",
                      r"\1 _______________________", SIGNED, count=1, flags=re.S)

    def test_a_blank_basis_raises(self):
        path = _written(self._blanked(
            "Basis — authorisation, licence, or the reasoning relied on:"))
        with self.assertRaises(MarksNotDecided) as ctx:
            load(path)
        self.assertIn("basis", str(ctx.exception))

    def test_a_blank_purpose_raises(self):
        path = _written(self._blanked("Purpose the catalogue serves:"))
        with self.assertRaises(MarksNotDecided):
            load(path)

    def test_a_blank_scope_raises(self):
        path = _written(self._blanked("Scope in one sentence:"))
        with self.assertRaises(MarksNotDecided):
            load(path)

    def test_an_absent_file_raises_rather_than_returning_nothing(self):
        """An empty decision and an unsigned one are not the same outcome.

        "No to everything" is a valid answer the file explicitly provides for,
        and it looks exactly like an empty allowed set. An unsigned file must
        therefore stop rather than resemble it.
        """
        with self.assertRaises(MarksNotDecided):
            load(Path(tempfile.mkdtemp()) / "absent.md")

    def test_the_signed_file_still_loads(self):
        """Guards the four above: a loader that always raised would pass them."""
        self.assertGreater(len(load().holes), 0)


class TestOnlyYesPermitsAnything(unittest.TestCase):

    HEAD = SIGNED.split("### Per-entry decision")[0] + "### Per-entry decision\n\n"

    def _table(self, decision: str) -> Path:
        return _written(
            self.HEAD
            + "| sku | key | points | what it is | draw? |\n"
            + "|---|---|---|---|---|\n"
            + f"| 74-min | brand#0/hole#0 | +5.290 | oval | {decision} |\n"
            + "\n| folder | key | area % | rights holder | draw? |\n"
            + "|---|---|---|---|---|\n"
            + f"| 64_Kamagra | highlight#7 | 0.395 | device | {decision} |\n")

    def test_yes_permits(self):
        d = load(self._table("yes"))
        self.assertIn(("74-min", "brand#0/hole#0"), d.holes)
        self.assertIn(("64_Kamagra", "highlight#7"), d.components)

    def test_everything_else_refuses(self):
        for decision in ("no", "n/a", "", "maybe", "YES?", "yes, but only in print"):
            with self.subTest(decision=decision):
                d = load(self._table(decision))
                self.assertEqual(d.holes, set(),
                                 f"{decision!r} was read as permission")
                self.assertEqual(d.components, set(),
                                 f"{decision!r} was read as permission")

    def test_emphasis_around_yes_still_reads_as_yes(self):
        """The file writes some answers bold; that is formatting, not meaning."""
        self.assertIn(("74-min", "brand#0/hole#0"), load(self._table("**yes**")).holes)


if __name__ == "__main__":
    unittest.main()
