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

    #: Photographed, deliberately unmapped, and named here so the omission is
    #: a statement rather than a gap. `21_Valium_Brand` and `24_Xanax_Pfizer`
    #: needed no entry because their folders left the disk with them; these
    #: keep their photography, so nothing else records that they are out.
    UNMEASURABLE = {
        # 107 components in the highlight cluster, largest holding 60% of the
        # mask; the boundary walk crosses itself 136 times before any
        # simplification, and the even-odd fill of that ring is three disjoint
        # pieces (74/14/10%). No simple ring can represent it -- see the
        # reason recorded beside TEMPLATE_SAMPLE in src/design_group.py.
        "107_Tramadol",
    }

    def test_no_photographed_folder_is_missing_from_the_sample(self):
        if not TEMPLATES_DIR.exists():
            self.skipTest(f"{TEMPLATES_DIR.name}/ is not in this checkout")
        from scripts.make_ocr_fixtures import TEMPLATE_SAMPLE

        photographed = {d.name for d in _template_dirs() if _images_in(d)}
        unmapped = sorted(photographed - set(TEMPLATE_SAMPLE)
                          - self.UNMEASURABLE)
        self.assertFalse(
            unmapped,
            f"these folders hold reference photography but name no SKU: "
            f"{unmapped}. Add them to TEMPLATE_SAMPLE and rebuild the fixtures, "
            f"or name them in UNMEASURABLE with the measurement that puts them "
            f"there; otherwise the barrier silently keeps its old coverage.")

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
        got = ink_within(self._face(), row, [("#204020", self._block_outline(), [])])
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
        got = ink_within(self._face(), row, [("#204020", self._block_outline(), [])])
        self.assertEqual(len(got["words"]), 1)
        for key in ("u0", "u1", "v0", "v1"):
            self.assertEqual(got["words"][0][key], got[key])

    def test_a_row_that_is_not_a_block_is_untouched(self):
        from scripts.measure_type_rows import ink_within
        row = {"text": "Tadalafil", "u0": 0.30, "u1": 0.70,
               "v0": 0.35, "v1": 0.65, "cap_frac": 0.30, "words": []}
        self.assertEqual(
            ink_within(self._face(), row, [("#204020", self._block_outline(), [])]),
            row, "a row whose box is not the shape must be returned unchanged")


if __name__ == "__main__":
    unittest.main()


class TestAPartIsItsOutlineMinusItsHoles(unittest.TestCase):
    """Contract 1.8, on the measuring side.

    `part_region` is the one implementation of what a part covers, and every
    figure the design group is judged by reads it: the spec's own raster, the
    QA target `design_qa` compares a render against, and `design_coverage`'s
    agreement. A second idea of it is how this project has twice been bitten,
    and a hole existing in one of them and not the others is the same defect
    wearing a new coat.

    Synthetic, for the reason the block test above is: the property is about a
    shape with a window in it, and twenty lines of pixels state it more clearly
    than a fixture does.
    """

    SQUARE = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    WINDOW = [[0.4, 0.4], [0.6, 0.4], [0.6, 0.6], [0.4, 0.6]]

    def _covered(self, part):
        import numpy as np
        from scripts.fit_design_spec import part_region
        return np.asarray(part_region(part, 100, 100))

    def test_a_hole_is_removed_from_what_the_part_covers(self):
        solid = self._covered({"outline": self.SQUARE, "holes": []})
        holed = self._covered({"outline": self.SQUARE, "holes": [self.WINDOW]})
        # PIL fills the boundary, so a 0.2-0.8 square on a 100px grid is 61x61
        # and its 0.4-0.6 window 21x21. The point of stating both is that the
        # difference is the window and nothing else.
        self.assertAlmostEqual(solid.mean(), 0.3721, delta=0.002)
        self.assertAlmostEqual(holed.mean(), 0.3721 - 0.0441, delta=0.002)
        self.assertFalse(holed[50, 50], "the middle of the window is still covered")
        self.assertTrue(holed[25, 50], "the part outside its window was dropped")

    def test_a_missing_or_empty_holes_key_covers_the_whole_outline(self):
        """The key is required by the contract; the raster must not guess at it.

        Refusing here as well would put the contract's enforcement in two places
        and this one cannot say which manifest it is reading. The schema rejects
        the missing key on write and on load, and the driver raises SystemExit
        rather than build the part -- that is where it is caught.
        """
        for holes in ([], None):
            part = {"outline": self.SQUARE}
            if holes is not None:
                part["holes"] = holes
            self.assertAlmostEqual(self._covered(part).mean(), 0.3721, delta=0.002)

    def test_ink_inside_a_hole_is_not_the_shapes_own(self):
        """`ink_within` measures the glyphs inside a filled shape, so the shape
        it measures inside has to be the region, not the ring."""
        from PIL import Image, ImageDraw
        from scripts.measure_type_rows import ink_within
        img = Image.new("RGB", (200, 100), "#E0DCD0")
        d = ImageDraw.Draw(img)
        d.rectangle([40, 20, 159, 79], fill="#204020")      # the block
        d.rectangle([60, 35, 139, 64], fill="#FFFFFF")      # type reversed out
        d.rectangle([20, 20, 39, 79], fill="#FFFFFF")       # a window beside it
        outline = [[20 / 200, 20 / 100], [160 / 200, 20 / 100],
                   [160 / 200, 80 / 100], [20 / 200, 80 / 100]]
        window = [[20 / 200, 20 / 100], [40 / 200, 20 / 100],
                  [40 / 200, 80 / 100], [20 / 200, 80 / 100]]
        row = {"text": "20mg", "u0": 20 / 200, "u1": 160 / 200,
               "v0": 20 / 100, "v1": 80 / 100, "cap_frac": 0.6,
               "words": [{"text": "20mg", "u0": 20 / 200, "u1": 160 / 200,
                          "v0": 20 / 100, "v1": 80 / 100}]}
        got = ink_within(img, row, [("#204020", outline, [window])])
        self.assertGreater(
            got["u0"], 0.25,
            "the window's white counted as the row's ink, so the box was pulled "
            "left onto board the shape does not cover")


class TestAReconstructedVertexLandsOnThePixelItWasTracedFrom(unittest.TestCase):
    """`part_region(..., snap_to_trace=True)` is the inverse of the normalisation.

    The spec stores an integer pixel index as `round(x / w, 4)`. Multiplying it
    back gives a value up to 0.0826 px either side of that integer, and PIL
    TRUNCATES a float polygon coordinate -- so half of every ring in every spec
    was rebuilt a WHOLE pixel off the pixel it was traced from. The gap between
    a fortieth of a pixel and a whole one is the entire defect, and these pin it
    from both ends: that the snap removes it, and that the default still has it,
    because three other readers are on that default.

    The grid is 1100x700 and not something round, deliberately. `x / 200` is
    exact in four decimals for every integer `x`, so on a tidy fixture the
    defect cannot appear at all -- the first draft of this class was written on
    one and passed while the bug was live. 1100 is the width these faces are
    actually rectified to.
    """

    W, H = 1100, 700
    #: The traced polygon, in the pixel indices `trace_outline` returns. Three
    #: of its four edges do not survive the round trip and y=91 does, which is
    #: the point: the displacement is signed per coordinate, not a global shift.
    TRACED = [(137, 91), (742, 91), (742, 508), (137, 508)]

    def _stored(self, pts):
        """What `fit()` writes to disk for these vertices."""
        return [[round(x / self.W, 4), round(y / self.H, 4)] for x, y in pts]

    def _mask(self, ring, **kw):
        import numpy as np
        from scripts.fit_design_spec import part_region
        return np.asarray(part_region({"outline": ring, "holes": []},
                                      self.W, self.H, **kw))

    def _drawn(self, pts):
        """The polygon rasterised straight from its integer vertices."""
        import numpy as np
        from PIL import Image, ImageDraw
        im = Image.new("1", (self.W, self.H), 0)
        ImageDraw.Draw(im).polygon([tuple(q) for q in pts], fill=1)
        return np.asarray(im)

    def test_the_snap_reproduces_the_traced_polygon_exactly(self):
        got = self._mask(self._stored(self.TRACED), snap_to_trace=True)
        want = self._drawn(self.TRACED)
        self.assertTrue(
            (got == want).all(),
            f"{int((got != want).sum())} pixels differ from the polygon as "
            f"traced; the reconstruction is not the inverse of the storage")

    def test_without_the_snap_the_edge_moves_a_whole_pixel(self):
        """The defect itself, so a revert cannot pass unnoticed.

        Stated as the edge rather than as an area: the shape keeps very nearly
        its size and MOVES, which is why it cost agreement without costing
        coverage and so stayed invisible in every figure but this one.
        """
        import numpy as np
        plain = self._mask(self._stored(self.TRACED))
        want = self._drawn(self.TRACED)
        self.assertFalse((plain == want).all(),
                         "expected the unsnapped reconstruction to be displaced")
        left_plain = int(np.nonzero(plain.any(0))[0].min())
        left_want = int(np.nonzero(want.any(0))[0].min())
        self.assertEqual(left_want - left_plain, 1,
                         "the displacement is one whole pixel, not a fraction")

    def test_the_default_is_the_unsnapped_reconstruction(self):
        """Pinned, because `rasterise()` and `verify()` are on this default.

        Turning the snap on for every caller moves the `pixel_agreement` a
        future fit would write and the target `design_qa` scores a render
        against. Both are published figures; moving them is a decision someone
        has to take, not something a keyword default should take for them.
        """
        import numpy as np
        stored = self._stored(self.TRACED)
        self.assertTrue(np.array_equal(self._mask(stored),
                                       self._mask(stored, snap_to_trace=False)))
        self.assertFalse(np.array_equal(self._mask(stored),
                                        self._mask(stored, snap_to_trace=True)))

    def test_the_snap_is_an_inverse_and_not_a_general_improvement(self):
        """A vertex that genuinely sits between two pixels is MOVED by it.

        The distinction the whole change rests on. Snapping is right here
        because the forward map's domain is the integers, so it removes a
        round-trip artefact. Handed a shape whose corners really do fall
        between pixels it displaces them instead -- it is not a switch that can
        be thrown anywhere to make a number go up.
        """
        import numpy as np
        between = [(x + 0.7, y + 0.7) for x, y in self.TRACED]
        ring = [[x / self.W, y / self.H] for x, y in between]
        self.assertFalse(
            np.array_equal(self._mask(ring), self._mask(ring, snap_to_trace=True)),
            "a genuinely fractional outline must be moved by the snap, not left "
            "alone -- otherwise the snap is not doing what it claims")

    def test_the_rounding_rule_is_pinned_and_real_data_never_reaches_it(self):
        """Python rounds a tie to even. Named, and shown to be unreachable.

        `round(0.5) == 0` where half-up would give 1. The rule only bites for a
        vertex exactly between two pixels, and the storage puts every real one
        within 0.0826 px of an integer -- so it is documented rather than
        depended on.
        """
        self.assertEqual((round(0.5), round(1.5), round(2.5)), (0, 2, 2))

    def test_every_vertex_the_group_stores_snaps_without_ambiguity(self):
        """Real data: nothing in the 28 specs is anywhere near a tie.

        Face width is `measure_reference_face.OUT_WIDTH`, height follows from
        the spec's own `face_aspect`, so this reads the specs and no images.
        """
        from src.design_group import FOLDER_BY_STEM, TEMPLATES_DIR
        from scripts.measure_reference_face import OUT_WIDTH
        worst, worst_at, n = 0.0, None, 0
        for stem, folder in FOLDER_BY_STEM.items():
            spec = json.loads((TEMPLATES_DIR / folder / "design_spec.json")
                              .read_text(encoding="utf-8"))
            w = OUT_WIDTH
            h = round(w * float(spec["face_aspect"]))
            for field in spec.get("fields") or []:
                for part in field.get("parts") or []:
                    rings = [part.get("outline") or []]
                    rings += list(part.get("holes") or [])
                    for ring in rings:
                        for u, v in ring:
                            for val, size in ((u, w), (v, h)):
                                d = abs(val * size - round(val * size))
                                n += 1
                                if d > worst:
                                    worst, worst_at = d, (stem, val, size)
        self.assertGreater(n, 5000, "the group's specs went missing")
        self.assertLess(
            worst, 0.25,
            f"a stored coordinate is {worst:.4f} px from the nearest pixel "
            f"({worst_at}); the snap is the inverse of the trace only while "
            f"every vertex is unambiguously one pixel")
