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


class TestPunctuationTolerantMultiTokenFields(unittest.TestCase):
    """`_field_present` must survive OCR re-spacing punctuation, not just
    demand every token byte-for-byte.

    Values are real `brand_name_display` strings pulled from
    04_passports/render_manifests/ (111-min: Retin-A Cream 0.025%; 351-min
    carries a hyphenated "L-VC" token; 409/411/412-min carry the
    "<ingredient words> Generic" collision shape at three tokens instead of
    two). The 111-min OCR text quoted here is the ACTUAL raw (un-deskewed)
    pytesseract output measured on this branch -- not invented -- confirming
    that even the corrected matcher does not manufacture a match where the
    OCR reading has genuinely lost a letter, only where it has mangled
    punctuation/whitespace around letters that are still there.
    """

    def test_hyphen_and_percent_respacing_still_matches(self):
        # Every punctuation mark in the field ("-", ".", "%") independently
        # re-spaced by OCR, exactly the shape reported against 04_passports/
        # render_manifests/111-min.json's brand_name_display.
        self.assertTrue(render_qa._field_present(
            "Retin-A Cream 0.025%",
            "Retin - A Cream 0.025 % Tretinoin 30 Tubes"))

    def test_percent_respacing_alone_still_matches(self):
        # 04_passports/render_manifests declares this exact string for
        # several SKU (e.g. Vaniqa Cream 13.9%, Lumigan 0.03%).
        self.assertTrue(render_qa._field_present(
            "Vaniqa Cream 13.9%", "Vaniqa Cream 13.9 % Eflornithine"))

    def test_hyphenated_token_survives_hyphen_dropped_to_a_space(self):
        # 04_passports/render_manifests/351-min.json's brand_name_display
        # ends in the hyphenated token "L-VC".
        self.assertTrue(render_qa._field_present(
            "Test Pack L-VC", "Test Pack L VC kit"))

    def test_verbatim_punctuation_still_matches(self):
        # The un-mangled case must keep working: normalisation must not
        # require noise to be present, only tolerate it when it is.
        self.assertTrue(render_qa._field_present(
            "Retin-A Cream 0.025%", "Retin-A Cream 0.025% Tretinoin"))

    def test_a_genuinely_lost_letter_is_still_a_miss(self):
        # The actual raw (un-deskewed) OCR reading measured on this branch
        # for 111-min: extract_text() on 02_processing/blender_test_renders/
        # 111-min.png returns '...retin” cream...' -- the '-A' is not
        # respaced, it is GONE, replaced by a stray quote glyph. Punctuation
        # normalisation can recover formatting noise; it cannot invent a
        # letter tesseract never read. This must stay a miss -- if it did
        # not, the matcher would have drifted from "tolerant of formatting"
        # to "tolerant of missing content," which is the too-lax failure
        # mode this task also has to avoid.
        self.assertFalse(render_qa._field_present(
            "Retin-A Cream 0.025%", "8 retin” cream Moraes p"))

    def test_three_token_generic_collision_still_requires_every_token(self):
        # 04_passports/render_manifests/409-min.json, 411-min.json and
        # 412-min.json each carry a THREE-token brand of the
        # "<ingredient words> Generic" shape, e.g. brand_name_display
        # "Nandrolone Decanoate Generic" against active_ingredient_display
        # "Nandrolone Decanoate". Punctuation tolerance must not have been
        # achieved by also relaxing which TOKENS are required: if "Generic"
        # is missing, the brand is still not found, even though two of its
        # three tokens (both shared with the separately-checked ingredient
        # field) are right there in the text.
        self.assertFalse(render_qa._field_present(
            "Nandrolone Decanoate Generic",
            "Nandrolone Decanoate 50mg 10 Vials"))
        self.assertTrue(render_qa._field_present(
            "Nandrolone Decanoate Generic",
            "Nandrolone Decanoate Generic 50mg 10 Vials"))


class TestTokenMatchAlignsToWordBoundaries(unittest.TestCase):
    """A letter-bearing token may only match text that OCR split ONE word
    across a space -- never text formed by bridging into the middle of a
    genuinely different, unrelated word.

    Round 1 of the punctuation fix flattened the WHOLE OCR text to one
    contiguous letters/digits blob (`"foo x yzoo"` -> `"fooxyzoo"`) and did a
    bare substring search. That has no boundary anchor at all, so it can
    "find" a token the text never actually contains: `"Xyz"` is not in
    `"foo x yzoo"`, but it IS a substring of the flattened
    `"fooxyzoo"`, spanning the tail of the unrelated word "x" and the head
    of the unrelated word "yzoo". Code review reproduced this directly and
    swept all 391 manifests x 4 fields for cases where it flips a real
    verdict -- none found today, but the class of bug is exactly what a
    verification barrier exists to keep out, latent or not.

    The fix requires a match to BEGIN where some original word begins and
    END where some (possibly later) word ends, with nothing but other
    complete words in between -- true for "Cream" split into "Cre am" by an
    OCR-inserted space, false for "Xyz" bridging "x" and "yzoo".
    """

    def test_intra_word_split_by_a_stray_space_still_matches(self):
        # The exact shape this whole branch exists to tolerate: OCR drops
        # one space into the middle of a single printed word.
        self.assertTrue(render_qa._field_present("Cream", "Cre am"))
        self.assertTrue(render_qa._field_present("Generic", "Gene ric"))
        self.assertTrue(render_qa._field_present("Retin-A", "Ret in A"))

    def test_bridging_into_an_unrelated_word_does_not_match(self):
        # The counter-example from code review: "Xyz" is not written
        # anywhere in "foo x yzoo" -- the flattened blob "fooxyzoo" merely
        # happens to contain the substring "xyz" by coincidence of two
        # unrelated words landing next to each other.
        self.assertFalse(render_qa._field_present("Xyz", "foo x yzoo"))

    def test_multi_token_field_still_recovers_a_genuine_intra_word_split(self):
        # Property 1 from the review: the 98 multi-token brands must not
        # regress. 111-min's brand_name_display, respaced the way OCR
        # actually respaces it, must still be a full match.
        self.assertTrue(render_qa._field_present(
            "Retin-A Cream 0.025%", "Retin - A Cream 0.025 %"))

    def test_multi_token_field_does_not_match_via_a_bridged_token(self):
        # Same shape as the Xyz counter-example, but inside a multi-token
        # field: "Cream" is genuinely there, but "Retin-A" is not -- it must
        # not be manufactured by bridging into an unrelated word.
        self.assertFalse(render_qa._field_present(
            "Retin-A Cream 0.025%", "foo x yzoo Cream"))

    def test_slash_joined_field_still_matches_when_text_has_no_space_around_it(self):
        # Regression pinned by this fix's own 391-SKU sweep. 111-min's
        # dosage_display is "0.025g/0.025%": the outer tokenizer splits it
        # on '/' into two required tokens ("0.025g", "0.025%"), but if the
        # word-boundary detector for the OCR TEXT only split on whitespace,
        # the verbatim "0.025g/0.025%" (no space around the '/') stayed ONE
        # undivided text word with no internal boundary, so the first token
        # failed its end-boundary check even though it is right there,
        # unmangled. `_TOKEN_SPLIT_RE` must be the SAME pattern on both
        # sides to avoid this.
        self.assertTrue(render_qa._field_present(
            "0.025g/0.025%", "Retin-A Cream 0.025g/0.025% Tretinoin 30 Tubes"))
        # Same shape for a word field: 239-min's active_ingredient_display.
        self.assertTrue(render_qa._field_present(
            "Caffeine/Ergotamine", "Cafergot Caffeine/Ergotamine 1mg 30 Pills"))


if __name__ == '__main__':
    unittest.main()
