import json
import unittest
from unittest.mock import patch
from pathlib import Path
import scripts.render_qa as render_qa
from scripts.render_qa import check_image

class TestManifestBackedChecks(unittest.TestCase):
    """QA must check the contract the renderer actually consumed.

    The Blender engine renders from the manifest's label_content. render_qa read
    brand_name and label_content off the PASSPORT, so wherever the two differ it
    reported a failure against a contract the renderer never saw.
    """

    MANIFEST = {
        "sku_id": "TEST-1",
        "template_id": "T1",
        "label_content": {
            "brand_name_display": "Atomoxetine Generic",
            "active_ingredient_display": "Atomoxetine",
            "dosage_display": "40mg",
            "unit_count_display": "10 Pills",
        },
    }

    @patch("scripts.render_qa.extract_text")
    def test_all_four_fields_found_scores_full_confidence(self, mock_extract):
        mock_extract.return_value = (
            True, "Atomoxetine Generic Atomoxetine 40mg 10 Pills")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "OK")
        self.assertEqual(res["confidence"], 1.0)
        self.assertTrue(all(res["fields"].values()))

    @patch("scripts.render_qa.extract_text")
    def test_a_missing_field_warns_and_never_hard_fails(self, mock_extract):
        mock_extract.return_value = (True, "Atomoxetine 40mg 10 Pills")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "WARN")
        self.assertFalse(res["fields"]["brand_name_display"])
        self.assertAlmostEqual(res["confidence"], 0.75)
        # Its own docstring promises the module never blocks the pipeline.
        self.assertNotIn("HARD_FAIL", res["status"])

    @patch("scripts.render_qa.extract_text")
    def test_dosage_still_matches_on_a_word_boundary(self, mock_extract):
        manifest = json.loads(json.dumps(self.MANIFEST))
        manifest["label_content"]["dosage_display"] = "5 mg"
        mock_extract.return_value = (True, "Atomoxetine Generic Atomoxetine 500mg 10 Pills")
        res = check_image(Path("dummy.png"), manifest)
        self.assertFalse(res["fields"]["dosage_display"],
                         "'5' must not match inside '500'")

    @patch("scripts.render_qa.extract_text")
    def test_ocr_unavailable_is_reported_not_scored(self, mock_extract):
        mock_extract.return_value = (False, "Tesseract binary not found")
        res = check_image(Path("dummy.png"), self.MANIFEST)
        self.assertEqual(res["status"], "UNAVAILABLE")
        self.assertIsNone(res["confidence"])


class TestFieldPresent(unittest.TestCase):
    """Pins `_field_present` directly, independent of `check_image`.

    The brief's own verbatim implementation fails these cases -- confirmed
    interactively before this class was written (see task-7-report.md,
    "second attempt" section). Kept as a standing regression class so a
    future edit that reintroduces either bug fails immediately here, rather
    than only surfacing as a lower confidence score somewhere else.
    """

    def test_numeric_field_matches_when_unit_is_glued_to_the_digits(self):
        # '\b40\b' cannot match inside "40mg" -- '0' and 'm' are both word
        # characters, so \b finds no boundary between them. Every dosage in
        # this catalogue glues the unit straight onto the number this way.
        self.assertTrue(
            render_qa._field_present("40mg", "Atomoxetine 40mg 10 Pills"))

    def test_numeric_field_does_not_match_inside_a_longer_number(self):
        self.assertFalse(
            render_qa._field_present("5 mg", "TestDrug 500mg 10 Pills"),
            "'5' must not match inside '500'")

    def test_numeric_field_matches_with_surrounding_punctuation(self):
        self.assertTrue(
            render_qa._field_present("5 mg", "TestDrug dosage: 5, quantity: 10"))

    def test_two_word_phrase_requires_every_token_not_just_the_longest(self):
        # "Atomoxetine" (11 chars) is longer than "Generic" (7), so a
        # "longest token wins" check would score this field found whenever
        # the separately-checked active-ingredient field is on the page,
        # even though "Generic" was never printed anywhere.
        self.assertFalse(
            render_qa._field_present("Atomoxetine Generic",
                                     "Atomoxetine 40mg 10 Pills"),
            "'Generic' never appears; matching the longest token alone is a false positive")
        self.assertTrue(
            render_qa._field_present(
                "Atomoxetine Generic",
                "Atomoxetine Generic Atomoxetine 40mg 10 Pills"))

    def test_blank_expected_is_never_present(self):
        self.assertFalse(render_qa._field_present("", "anything"))
        self.assertFalse(render_qa._field_present(None, "anything"))


if __name__ == '__main__':
    unittest.main()
