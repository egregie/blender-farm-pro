"""The reference-template folders must describe their own contents truthfully.

`metadata.json` is declared a machine-readable contract for downstream agents --
the Blender driver, the SVG generator, the UV builder all read it rather than the
photographs. Its `quality_gate` block reports `"status": "complete"`.

Both benchmark folders shipped with a `reference_images` list naming
`raw_01_angle_left.png`, `raw_02_front.png` and `raw_03_angle_right.png`, and
neither folder contained a single one of those files -- the intersection with
what was on disk was empty. A consumer following that contract would have found
nothing and had no way to tell whether the reference set was missing or the
manifest was wrong.

That is the same defect the verification barrier exists to remove, one layer up:
a record asserting something nothing checked. These tests check it.
"""
import json
import unittest
from pathlib import Path

from src.utils import PROJECT_ROOT

TEMPLATES_DIR = PROJECT_ROOT / "Reference Templates"
IMAGE_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg"}

# The owner's cap: no template folder may hoard more than this. Recorded here
# rather than only in the ТЗ, so exceeding it fails rather than merely
# contradicting a document.
MAX_IMAGES_PER_TEMPLATE = 7


def _template_dirs():
    if not TEMPLATES_DIR.exists():
        return []
    return sorted(d for d in TEMPLATES_DIR.iterdir() if d.is_dir())


def _images_in(directory):
    return sorted(p.name for p in directory.iterdir()
                  if p.suffix.lower() in IMAGE_SUFFIXES)


class TestMetadataMatchesDisk(unittest.TestCase):
    def test_at_least_one_template_carries_metadata(self):
        # Without this the suite below passes vacuously the day the folders are
        # emptied, reporting success having checked nothing.
        #
        # But "the reference material is not in this checkout" and "it is here
        # and unchecked" are different states and must not share an outcome:
        # `Reference Templates/` is currently untracked, so a clean clone has no
        # such directory at all. Absent -> skip; present but silent -> fail.
        if not TEMPLATES_DIR.exists():
            self.skipTest(
                f"{TEMPLATES_DIR.name}/ is not in this checkout -- it is "
                f"untracked, so a clean clone has none. Nothing to verify here; "
                f"that is not the same as verifying nothing.")
        with_metadata = [d for d in _template_dirs() if (d / "metadata.json").exists()]
        self.assertTrue(with_metadata,
                        f"{TEMPLATES_DIR.name}/ exists with "
                        f"{len(_template_dirs())} folders but not one has a "
                        f"metadata.json; the checks below would inspect nothing")

    def test_every_listed_reference_image_exists(self):
        for d in _template_dirs():
            meta = d / "metadata.json"
            if not meta.exists():
                continue
            # The photographs are gitignored while the metadata is tracked, so a
            # clean clone has the folder and its contract but none of its
            # pictures. A folder with no images at all is that state, not a
            # false manifest. A folder with SOME images and a listed one absent
            # is the defect this guards.
            if not _images_in(d):
                continue
            with self.subTest(template=d.name):
                listed = json.loads(meta.read_text(encoding="utf-8")).get(
                    "reference_images", [])
                missing = [f for f in listed if not (d / f).exists()]
                self.assertEqual(
                    missing, [],
                    f"{d.name}/metadata.json lists files that are not on disk: "
                    f"{missing}. A downstream agent reading this contract would "
                    f"find nothing and could not tell which side is wrong.")

    def test_every_image_on_disk_is_listed(self):
        for d in _template_dirs():
            meta = d / "metadata.json"
            if not meta.exists():
                continue
            with self.subTest(template=d.name):
                listed = set(json.loads(meta.read_text(encoding="utf-8")).get(
                    "reference_images", []))
                unlisted = [f for f in _images_in(d) if f not in listed]
                self.assertEqual(
                    unlisted, [],
                    f"{d.name} holds images its metadata does not mention: "
                    f"{unlisted}. An unlisted reference is invisible to every "
                    f"consumer that reads the contract rather than the folder.")


class TestImageBudget(unittest.TestCase):
    def test_no_template_exceeds_the_image_cap(self):
        for d in _template_dirs():
            with self.subTest(template=d.name):
                images = _images_in(d)
                self.assertLessEqual(
                    len(images), MAX_IMAGES_PER_TEMPLATE,
                    f"{d.name} holds {len(images)} images, over the cap of "
                    f"{MAX_IMAGES_PER_TEMPLATE}: {images}")


class TestNoDuplicateImages(unittest.TestCase):
    """Two files of the same picture in different formats are one reference, not
    two, and both count against the cap. The Kamagra benchmark shipped with two
    such pairs -- `.webp` copies of its `.png` files, pixel-identical.
    """

    def test_no_two_images_in_a_folder_share_pixels(self):
        try:
            import numpy as np
            from PIL import Image
        except ImportError as e:  # pragma: no cover - environment, not logic
            self.skipTest(f"Pillow/numpy unavailable: {e}")
        import hashlib

        for d in _template_dirs():
            images = _images_in(d)
            if len(images) < 2:
                continue
            with self.subTest(template=d.name):
                seen = {}
                for name in images:
                    with Image.open(d / name) as im:
                        digest = hashlib.sha256(
                            np.asarray(im.convert("RGB")).tobytes()).hexdigest()
                    self.assertNotIn(
                        digest, seen,
                        f"{d.name}: {name} and {seen.get(digest)} are the same "
                        f"picture in different files")
                    seen[digest] = name


class TestEveryPhotographedFolderIsInTheBarrier(unittest.TestCase):
    """A folder with reference photography must name the SKU it documents.

    The OCR barrier over the template sample
    (tests/test_render_qa.py::TestOCRBarrierOverTheTemplateSample) is defined by
    `TEMPLATE_SAMPLE` in scripts/make_ocr_fixtures.py -- a hand-resolved map,
    because folder names do not identify a SKU on their own: `15_T1_Xanax` and
    `24_T1_Xanax_Pfizer` are two catalogue entries whose names contain each
    other. A hand-resolved map is exactly the kind that falls behind the folders
    it describes, and nothing would say so: acquiring a reference for a twelfth
    product and leaving it unmapped simply means the barrier keeps covering
    eleven while the repository looks like it covers twelve.

    This test was written after the map was first built with a folder in it that
    holds no photograph at all.
    """

    def test_no_photographed_folder_is_missing_from_the_sample(self):
        if not TEMPLATES_DIR.exists():
            self.skipTest(f"{TEMPLATES_DIR.name}/ is not in this checkout")
        from scripts.make_ocr_fixtures import TEMPLATE_SAMPLE

        photographed = {d.name for d in _template_dirs() if _images_in(d)}
        unmapped = sorted(photographed - set(TEMPLATE_SAMPLE))
        self.assertFalse(
            unmapped,
            f"these folders hold reference photography but name no SKU: "
            f"{unmapped}. Add them to TEMPLATE_SAMPLE and rebuild the fixtures, "
            f"or the barrier silently keeps its old coverage.")

    def test_the_sample_names_no_folder_without_a_photograph(self):
        if not TEMPLATES_DIR.exists():
            self.skipTest(f"{TEMPLATES_DIR.name}/ is not in this checkout")
        from scripts.make_ocr_fixtures import TEMPLATE_SAMPLE

        photographed = {d.name for d in _template_dirs() if _images_in(d)}
        on_disk = {d.name for d in _template_dirs()}
        phantom = sorted(set(TEMPLATE_SAMPLE) - photographed)
        self.assertFalse(
            phantom,
            f"the sample names folders with no reference photograph: {phantom} "
            f"({[p for p in phantom if p not in on_disk]} are not on disk at "
            f"all). A reference folder with no image is a reference to nothing.")


if __name__ == "__main__":
    unittest.main()


class TestARowBoxedAsItsBlock(unittest.TestCase):
    """`ink_within` recovers the glyphs when the reader returns the shape.

    Tesseract binarises per region, so a colour block with type reversed out of
    it is one blob and the word box comes back as the BLOCK. On our own Cialis
    render "20mg" was returned at exactly the block's outline, v 0.2948-0.4292
    against glyphs at 0.3165-0.4133, which read back as a row 38% oversized and
    0.02 high -- the worst type figures in the group, on a carton the scene dump
    says is built exactly right.

    Synthetic rather than fixture-driven: the property is about a filled shape
    with lighter marks inside it, and stating it in twenty lines of pixels is
    clearer than pointing at a render.
    """

    def _face(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (200, 100), "#E0DCD0")
        d = ImageDraw.Draw(img)
        d.rectangle([40, 20, 159, 79], fill="#204020")      # the block
        d.rectangle([60, 35, 139, 64], fill="#FFFFFF")      # the reversed type
        return img

    def _block_outline(self):
        return [[40 / 200, 20 / 100], [160 / 200, 20 / 100],
                [160 / 200, 80 / 100], [40 / 200, 80 / 100]]

    def test_a_box_around_the_block_is_pulled_back_to_the_glyphs(self):
        from scripts.measure_type_rows import ink_within
        row = {"text": "20mg", "u0": 40 / 200, "u1": 160 / 200,
               "v0": 20 / 100, "v1": 80 / 100, "cap_frac": 0.6,
               "words": [{"text": "20mg", "u0": 40 / 200, "u1": 160 / 200,
                          "v0": 20 / 100, "v1": 80 / 100}]}
        got = ink_within(self._face(), row, [("#204020", self._block_outline())])
        self.assertAlmostEqual(got["u0"], 0.300, delta=0.02)
        self.assertAlmostEqual(got["u1"], 0.700, delta=0.02)
        self.assertAlmostEqual(got["v0"], 0.350, delta=0.02)
        self.assertAlmostEqual(got["v1"], 0.650, delta=0.02)

    def test_the_words_come_back_with_it(self):
        """Everything downstream rebuilds a row from its words.

        `_unclaimed` does it before scoring and `narrow_to_string` inside it, so
        leaving the reader's word boxes in place quietly restores the block's own
        rectangle and the correction never reaches the figures. It did exactly
        that on the first attempt.
        """
        from scripts.measure_type_rows import ink_within
        row = {"text": "20mg", "u0": 40 / 200, "u1": 160 / 200,
               "v0": 20 / 100, "v1": 80 / 100, "cap_frac": 0.6,
               "words": [{"text": "20mg", "u0": 40 / 200, "u1": 160 / 200,
                          "v0": 20 / 100, "v1": 80 / 100}]}
        got = ink_within(self._face(), row, [("#204020", self._block_outline())])
        self.assertEqual(len(got["words"]), 1)
        for key in ("u0", "u1", "v0", "v1"):
            self.assertEqual(got["words"][0][key], got[key])

    def test_a_row_that_is_not_a_block_is_untouched(self):
        from scripts.measure_type_rows import ink_within
        row = {"text": "Tadalafil", "u0": 0.30, "u1": 0.70,
               "v0": 0.35, "v1": 0.65, "cap_frac": 0.30, "words": []}
        self.assertEqual(
            ink_within(self._face(), row, [("#204020", self._block_outline())]),
            row, "a row whose box is not the shape must be returned unchanged")
