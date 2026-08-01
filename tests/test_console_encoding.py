"""Tests for console-safe reporting on legacy Windows codepages.

A finished run used to die in ``print_summary`` with UnicodeEncodeError because
the status labels are emoji and rich writes them straight to stdout, whose
encoding on a legacy Windows console is a codepage (cp1251 here) that cannot
represent them. Every stage had already succeeded, so a green run exited 1.

These tests drive the summary through a REAL cp1251 text stream rather than a
StringIO: encoding only happens on the way to bytes, so an in-memory str buffer
would never reproduce the bug.
"""
import io
import logging
import unittest

import main


LEGACY_CODEPAGE = "cp1251"


def _legacy_stream() -> io.TextIOWrapper:
    """A writable text stream that raises on anything cp1251 can't represent."""
    return io.TextIOWrapper(io.BytesIO(), encoding=LEGACY_CODEPAGE, newline="")


def _utf8_stream() -> io.TextIOWrapper:
    return io.TextIOWrapper(io.BytesIO(), encoding="utf-8", newline="")


def _quiet_logger() -> logging.Logger:
    log = logging.getLogger("test_console_encoding")
    log.handlers = [logging.NullHandler()]
    log.propagate = False
    return log


RESULTS = [
    {"stage": "passports", "status": "ok", "duration": 12.3, "rc": 0},
    {"stage": "render", "status": "failed", "duration": 4.0, "rc": 1},
    {"stage": "process-images", "status": "skipped", "duration": 0, "rc": None},
]
COUNTS = {"JSON passports": 391, "MD passports": 391}


class TestStreamCanEncode(unittest.TestCase):

    def test_legacy_codepage_cannot_encode_status_emoji(self):
        self.assertFalse(main.stream_can_encode("✅", _legacy_stream()))

    def test_utf8_stream_can_encode_status_emoji(self):
        self.assertTrue(main.stream_can_encode("✅", _utf8_stream()))

    def test_stream_without_encoding_is_treated_as_unicode_capable(self):
        # StringIO holds str — there is no encode step that could fail.
        self.assertTrue(main.stream_can_encode("✅", io.StringIO()))

    def test_unknown_codec_does_not_raise(self):
        class Weird:
            encoding = "not-a-real-codec"
        self.assertFalse(main.stream_can_encode("✅", Weird()))


class TestConsoleStyle(unittest.TestCase):

    def test_labels_are_encodable_on_a_legacy_codepage(self):
        labels, glyphs = main.console_style(_legacy_stream())
        for text in list(labels.values()) + list(glyphs.values()):
            text.encode(LEGACY_CODEPAGE)  # raises -> test fails, which is the point

    def test_labels_stay_distinguishable_on_a_legacy_codepage(self):
        labels, _ = main.console_style(_legacy_stream())
        self.assertIn("OK", labels["ok"])
        self.assertIn("FAILED", labels["failed"])
        self.assertIn("SKIPPED", labels["skipped"])
        self.assertEqual(len(set(labels.values())), 3, "statuses must stay distinct")

    def test_emoji_are_kept_when_the_stream_can_encode_them(self):
        labels, glyphs = main.console_style(_utf8_stream())
        self.assertIn("✅", labels["ok"])
        self.assertIn("❌", labels["failed"])
        self.assertIn("▶", glyphs["arrow"])

    def test_every_status_used_by_the_pipeline_has_a_label(self):
        labels, _ = main.console_style(_utf8_stream())
        self.assertEqual(set(labels), {r["status"] for r in RESULTS})


class TestPrintSummaryOnLegacyCodepage(unittest.TestCase):
    """The actual regression: the run is over and correct — reporting must not kill it."""

    def test_does_not_raise_on_a_legacy_codepage_stream(self):
        stream = _legacy_stream()
        main.print_summary(RESULTS, COUNTS, None, 16.3, _quiet_logger(), stream=stream)
        stream.flush()

    def test_summary_stays_readable_on_a_legacy_codepage(self):
        stream = _legacy_stream()
        main.print_summary(RESULTS, COUNTS, None, 16.3, _quiet_logger(), stream=stream)
        stream.flush()
        text = stream.buffer.getvalue().decode(LEGACY_CODEPAGE)
        for expected in ("Run Summary", "passports", "OK", "FAILED", "SKIPPED", "391"):
            self.assertIn(expected, text)
        self.assertNotIn("?", text, "glyphs should be chosen, not mangled into '?'")

    def test_summary_keeps_emoji_on_a_utf8_stream(self):
        stream = _utf8_stream()
        main.print_summary(RESULTS, COUNTS, None, 16.3, _quiet_logger(), stream=stream)
        stream.flush()
        text = stream.buffer.getvalue().decode("utf-8")
        self.assertIn("✅", text)


class TestHardenStdout(unittest.TestCase):

    def test_replaces_unencodable_characters_instead_of_raising(self):
        stream = _legacy_stream()
        main.harden_stream(stream)
        stream.write("✅")  # would raise UnicodeEncodeError before hardening
        stream.flush()

    def test_keeps_the_streams_own_encoding(self):
        stream = _legacy_stream()
        main.harden_stream(stream)
        # Switching to utf-8 here would mojibake every non-ASCII byte on a
        # console whose codepage is still cp1251.
        self.assertEqual(stream.encoding, LEGACY_CODEPAGE)

    def test_is_a_no_op_on_streams_that_cannot_be_reconfigured(self):
        main.harden_stream(io.StringIO())
        main.harden_stream(object())


if __name__ == "__main__":
    unittest.main()
