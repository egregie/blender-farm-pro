"""Tests for the Stage 1 -> Stage 2 render-manifest contract.

Both sides of the boundary are checked against the SAME artifact
(schemas/render_manifest.schema.json) rather than against each other's
expectations, which is the point of the contract.
"""
import json
import re
import unittest
from pathlib import Path

from src import silhouette
from src.render_manifest import (
    MANIFEST_VERSION,
    TARGET_SILHOUETTE_ASPECT,
    build_manifest,
    load_schema,
    orient_for_template,
    reshape_to_art_direction,
    resolve_carton,
    validate_manifest,
    manifest_path_for,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PASSPORTS = PROJECT_ROOT / "04_passports" / "passports_json"


def _passport(stem: str) -> dict:
    return json.loads((PASSPORTS / f"{stem}.json").read_text(encoding="utf-8"))


def _all_passport_stems() -> list:
    return sorted(p.stem for p in PASSPORTS.glob("*.json"))


class TestManifestSchema(unittest.TestCase):
    """The artifact itself must be a well-formed, self-consistent schema."""

    def test_schema_loads_and_is_valid(self):
        from jsonschema import Draft202012Validator
        Draft202012Validator.check_schema(load_schema())

    def test_schema_pins_the_manifest_version(self):
        self.assertEqual(
            load_schema()["properties"]["manifest_version"]["const"],
            MANIFEST_VERSION,
            "module constant and schema disagree on the contract version",
        )


class TestBuildManifest(unittest.TestCase):
    """Provider side: what Stage 1 emits must satisfy the contract."""

    def test_real_passport_produces_valid_manifest(self):
        m = build_manifest(_passport("1-min"))
        validate_manifest(m)          # raises on any contract violation
        self.assertEqual(m["manifest_version"], MANIFEST_VERSION)
        self.assertEqual(m["sku_id"], _passport("1-min")["sku_id"])

    def test_carton_comes_from_the_passports_own_secondary_dimensions(self):
        # 1-min declares "115x55x48mm"; those exact numbers must survive to
        # the manifest rather than being round-tripped through the primary
        # package, which is lossy. Since contract 1.3 they survive in
        # passport_dimensions -- the geometry beside them is art-directed and is
        # deliberately NOT these numbers.
        m = build_manifest(_passport("1-min"))
        real = m["carton"]["passport_dimensions"]
        self.assertEqual(real["source"], "passport_secondary")
        self.assertAlmostEqual(real["width_mm"], 115.0)
        self.assertAlmostEqual(real["height_mm"], 55.0)
        self.assertAlmostEqual(real["depth_mm"], 48.0)

    def test_the_printed_size_is_never_the_rendered_size_by_accident(self):
        # The one mistake contract 1.3 exists to prevent: printing art-directed
        # measurements on pharmaceutical packaging. If a reshape ever silently
        # stops happening, this catches it before a packshot carries a number
        # that is real by coincidence rather than by construction.
        m = build_manifest(_passport("1-min"))
        self.assertEqual(m["carton"]["source"], "art_direction")
        self.assertNotAlmostEqual(m["carton"]["height_mm"],
                                  m["carton"]["passport_dimensions"]["height_mm"],
                                  places=3)

    def test_template_id_matches_the_router(self):
        from src.passport_generator import agent_1_router
        for stem in ("1-min", "192-min", "293-min"):
            data = _passport(stem)
            expected_tid, expected_override = agent_1_router(data)
            m = build_manifest(data)
            self.assertEqual(m["template_id"], expected_tid, stem)
            self.assertEqual(m["is_bottle_override"], expected_override, stem)

    def test_label_content_is_carried_verbatim(self):
        data = _passport("1-min")
        m = build_manifest(data)
        for field in ("brand_name_display", "dosage_display", "unit_count_display"):
            self.assertEqual(m["label_content"][field], data["label_content"][field])

    def test_active_ingredient_comes_from_the_passports_top_level(self):
        """The one label row the passport does NOT keep in label_content.

        It lives at the passport's top level as `active_ingredient`, so it is the
        one field build_manifest cannot read off `label` like its siblings, and
        the one most likely to be silently dropped.
        """
        data = _passport("1-min")
        m = build_manifest(data)
        self.assertEqual(m["label_content"]["active_ingredient_display"],
                         data["active_ingredient"])
        self.assertTrue(m["label_content"]["active_ingredient_display"],
                        "ingredient row is empty; the front face would render "
                        "without it and the packshot would be wrong, not merely "
                        "plain")

    def test_every_sku_has_an_ingredient_to_print(self):
        """All 391 carry one today. If that ever stops being true the renderer
        needs a documented fallback, so fail here rather than discover it as a
        blank row in a finished packshot."""
        empty = [stem for stem in _all_passport_stems()
                 if not (_passport(stem).get("active_ingredient") or "").strip()]
        self.assertEqual(empty, [], f"{len(empty)} SKU have no active_ingredient")

    def test_carton_carries_the_declared_construction_features(self):
        """Real per-SKU data, and the side panel is drawn from it: 370 of 391
        cartons declare Braille / DataMatrix_Zone / Tamper_Evident_Seal and 21
        declare nothing. A renderer that assumes every carton is identical gets
        the 21 wrong."""
        data = _passport("1-min")
        m = build_manifest(data)
        self.assertEqual(m["carton"]["features"],
                         data["secondary_packaging"]["features"])
        self.assertEqual(m["carton"]["material"],
                         data["secondary_packaging"]["material"])

    def test_features_survive_the_dimension_fallbacks(self):
        """Construction data is independent of whether the dimension string
        parsed, so it must travel on the derived and ratio paths too."""
        data = _passport("1-min")
        data["secondary_packaging"] = dict(data["secondary_packaging"],
                                           dimensions="not a size")
        m = build_manifest(data)
        self.assertNotEqual(m["carton"]["passport_dimensions"]["source"],
                            "passport_secondary",
                            "test premise: this should have left the happy path")
        self.assertEqual(m["carton"]["features"],
                         data["secondary_packaging"]["features"])
        self.assertTrue(m["carton"]["material"])

    def test_carton_is_the_secondary_not_the_primary_package(self):
        """The rendered object is the printed box, so the manifest must carry
        the carton. The blister inside is strictly smaller."""
        from src.passport_generator import get_primary_package
        data = _passport("1-min")
        primary = get_primary_package(data)
        m = build_manifest(data)
        self.assertGreater(m["carton"]["width_mm"], primary.width_mm)
        self.assertGreater(m["carton"]["depth_mm"], primary.depth_mm)


class TestCartonFallbacks(unittest.TestCase):
    """Dimensions must always be present; only their provenance varies."""

    BASE = {
        "sku_id": "synthetic-min.jpg",
        "product_name": "Synthetic Test Product",
        "packaging_geometry": "BLISTER",
        "minimal_package": 30,
        "branding": {"palette": {"primary": "#003366",
                                 "accent": "#0D5FB8",
                                 "background": "#FFFFFF"}},
        "label_content": {"brand_name_display": "Synthetic",
                          "dosage_display": "20mg",
                          "unit_count_display": "30 Pills"},
    }

    def test_unparseable_dimensions_fall_back_to_derivation(self):
        data = dict(self.BASE, secondary_packaging={"dimensions": "medium sized"})
        m = build_manifest(data)
        validate_manifest(m)
        self.assertEqual(m["carton"]["passport_dimensions"]["source"],
                         "derived_from_primary")
        self.assertGreater(m["carton"]["width_mm"], 0)

    def test_missing_secondary_packaging_still_yields_dimensions(self):
        m = build_manifest(dict(self.BASE))
        validate_manifest(m)
        self.assertIn(m["carton"]["passport_dimensions"]["source"],
                      ("derived_from_primary", "template_ratio"))
        self.assertGreater(m["carton"]["height_mm"], 0)

    def test_dimensions_are_never_null(self):
        """The whole reason the driver could silently guess was a null here."""
        for payload in ({}, {"dimensions": ""}, {"dimensions": "115x55"}):
            m = build_manifest(dict(self.BASE, secondary_packaging=payload))
            for axis in ("width_mm", "height_mm", "depth_mm"):
                self.assertIsNotNone(m["carton"][axis])
                self.assertGreater(m["carton"][axis], 0)


class TestOrientation(unittest.TestCase):
    """The dimension string supplies three extents but not which way is up;
    the template decides. Each expectation below is anchored to a curated
    reference render in 01_input_raster/reference/."""

    def test_vertical_family_stands_the_longest_edge_up(self):
        from src.render_manifest import orient_for_template
        # T_VERT_VIAL_144 (HUCOG-2000) reads "170x80x35mm" and renders portrait.
        self.assertEqual(orient_for_template((170.0, 80.0, 35.0), "T_VERT_VIAL"),
                         (80.0, 170.0, 35.0))
        # T_VERT_DROPPER_229 (Lumigan) reads "110x50x18mm", also portrait.
        self.assertEqual(orient_for_template((110.0, 50.0, 18.0), "T_VERT_DROPPER"),
                         (50.0, 110.0, 18.0))

    def test_horizontal_family_keeps_the_passport_order(self):
        from src.render_manifest import orient_for_template
        # T1_1 (Atomoxetine) reads the same "115x55x48mm" as the inhaler below
        # but renders landscape.
        self.assertEqual(orient_for_template((115.0, 55.0, 48.0), "T1"),
                         (115.0, 55.0, 48.0))
        # T_MULTIPACK_347 reads "110x50x18mm" and renders landscape, unlike the
        # dropper with the identical string.
        self.assertEqual(orient_for_template((110.0, 50.0, 18.0), "T_MULTIPACK"),
                         (110.0, 50.0, 18.0))

    def test_identical_string_diverges_by_template(self):
        """The whole reason orientation cannot be read off the string."""
        from src.render_manifest import orient_for_template
        dims = (115.0, 55.0, 48.0)
        self.assertNotEqual(orient_for_template(dims, "T1"),
                            orient_for_template(dims, "T_VERT_INHALER"))

    def test_already_upright_string_is_left_alone(self):
        from src.render_manifest import orient_for_template
        # T_BOTTLE_BOX_10 (Revia) reads "55x100x55mm" — the height is already
        # the largest extent, so reorienting must be a no-op.
        self.assertEqual(orient_for_template((55.0, 100.0, 55.0), "T_BOTTLE_BOX"),
                         (55.0, 100.0, 55.0))

    def test_every_vertical_family_sku_stands_upright_before_reshaping(self):
        for f in sorted(PASSPORTS.glob("*.json")):
            m = build_manifest(json.loads(f.read_text(encoding="utf-8")))
            if m["template_id"] in ("T_BOTTLE_BOX", "T_VERT_VIAL",
                                    "T_VERT_DROPPER", "T_VERT_INHALER"):
                c = m["carton"]["passport_dimensions"]
                self.assertGreaterEqual(
                    c["height_mm"], max(c["width_mm"], c["depth_mm"]),
                    f"{f.stem} ({m['template_id']}) is not upright",
                )

    def test_every_vertical_family_sku_still_PHOTOGRAPHS_portrait(self):
        # The claim worth holding is about the picture, and after reshaping it
        # is no longer the same claim as "the box is taller than it is wide".
        # T_VERT_VIAL solves to 172x170x35: wider than tall, and still a portrait
        # photograph at 0.9224 because the camera looks down a portrait carton.
        # Asserting on the box edges here would fail on a correct reshape.
        for f in sorted(PASSPORTS.glob("*.json")):
            m = build_manifest(json.loads(f.read_text(encoding="utf-8")))
            if m["template_id"] in ("T_BOTTLE_BOX", "T_VERT_VIAL",
                                    "T_VERT_DROPPER", "T_VERT_INHALER"):
                c = m["carton"]
                dims = (c["width_mm"], c["height_mm"], c["depth_mm"])
                self.assertLess(
                    silhouette.visible_faces_aspect(dims, m["template_id"]), 1.0,
                    f"{f.stem} ({m['template_id']}) photographs landscape",
                )


class TestContractRejectsDrift(unittest.TestCase):
    """A contract that accepts anything is not a contract."""

    def setUp(self):
        self.valid = build_manifest(_passport("1-min"))

    def test_a_1_2_manifest_is_rejected_rather_than_read_as_1_3(self):
        """The bump that must not be forgiving.

        1.3 repurposed carton.width_mm/height_mm/depth_mm from the carton's real
        size to art-directed scene geometry. A 1.2 file has the old meaning in
        the new field names and no passport_dimensions at all, so a consumer that
        accepted it would build the box from real dimensions -- merely wrong --
        and print whatever it could find -- not merely wrong. Both failure modes
        are silent, which is why the version is a const and not a minimum.
        """
        from jsonschema import ValidationError
        legacy = json.loads(json.dumps(self.valid))
        legacy["manifest_version"] = "1.2"
        real = legacy["carton"].pop("passport_dimensions")
        legacy["carton"].update({k: real[k] for k in
                                 ("width_mm", "height_mm", "depth_mm")})
        legacy["carton"]["source"] = real["source"]
        with self.assertRaises(ValidationError):
            validate_manifest(legacy)

    def test_a_manifest_without_the_real_dimensions_is_rejected(self):
        from jsonschema import ValidationError
        bad = json.loads(json.dumps(self.valid))
        bad["carton"].pop("passport_dimensions")
        with self.assertRaises(ValidationError):
            validate_manifest(bad)

    def test_unknown_field_is_rejected(self):
        from jsonschema import ValidationError
        bad = dict(self.valid, surprise_field="drift")
        with self.assertRaises(ValidationError):
            validate_manifest(bad)

    def test_missing_carton_is_rejected(self):
        from jsonschema import ValidationError
        bad = {k: v for k, v in self.valid.items() if k != "carton"}
        with self.assertRaises(ValidationError):
            validate_manifest(bad)

    def test_negative_dimension_is_rejected(self):
        from jsonschema import ValidationError
        bad = json.loads(json.dumps(self.valid))
        bad["carton"]["width_mm"] = -1
        with self.assertRaises(ValidationError):
            validate_manifest(bad)

    def test_malformed_hex_colour_is_rejected(self):
        from jsonschema import ValidationError
        bad = json.loads(json.dumps(self.valid))
        bad["palette"]["accent"] = "0D5FB8"      # missing the leading hash
        with self.assertRaises(ValidationError):
            validate_manifest(bad)

    def test_unknown_template_id_is_rejected(self):
        from jsonschema import ValidationError
        bad = dict(self.valid, template_id="T_NOT_A_TEMPLATE")
        with self.assertRaises(ValidationError):
            validate_manifest(bad)


class TestWholeCatalogue(unittest.TestCase):
    """Every SKU in the catalogue must satisfy the contract, not just samples."""

    def test_all_passports_produce_valid_manifests(self):
        files = sorted(PASSPORTS.glob("*.json"))
        self.assertGreater(len(files), 0, "no passports found")
        failures = []
        guessed = []
        for f in files:
            try:
                m = build_manifest(json.loads(f.read_text(encoding="utf-8")))
                validate_manifest(m)
                if m["carton"]["passport_dimensions"]["source"] == "template_ratio":
                    guessed.append(f.stem)
            except Exception as e:  # noqa: BLE001 - report all, not just the first
                failures.append(f"{f.stem}: {type(e).__name__}: {e}")
        self.assertEqual(failures, [], f"{len(failures)} passports failed the contract")
        # Not an assertion about correctness, but a guard against silently
        # regressing to guessed geometry for the whole catalogue.
        self.assertEqual(guessed, [], "these SKU fell back to guessed dimensions")


class TestReshapeToArtDirection(unittest.TestCase):
    """Geometry solved to the reference proportion, with the product kept upright.

    The targets are measurements, recorded in 01_input_raster/reference_analysis.md
    section 10; the solver is checked against the model that produced them, so a
    wrong constant and a wrong solve cannot cancel out.
    """

    def test_every_reshaped_carton_lands_on_its_template_target(self):
        for template_id, target in TARGET_SILHOUETTE_ASPECT.items():
            with self.subTest(template=template_id):
                base = orient_for_template((115.0, 55.0, 48.0), template_id)
                dims, reshaped = reshape_to_art_direction(base, template_id)
                self.assertTrue(reshaped, f"{template_id} refused a plain carton")
                self.assertAlmostEqual(
                    silhouette.visible_faces_aspect(dims, template_id), target, places=4)

    def test_the_target_is_matched_on_the_visible_faces_not_the_whole_box(self):
        # The distinction is worth a test of its own because getting it wrong is
        # silent: both quantities exist, both look plausible, and the wrong one
        # reports T1 as already correct when it is 14% out.
        base = orient_for_template((115.0, 55.0, 48.0), "T1")
        dims, _ = reshape_to_art_direction(base, "T1")
        target = TARGET_SILHOUETTE_ASPECT["T1"]
        self.assertAlmostEqual(silhouette.visible_faces_aspect(dims, "T1"), target,
                               places=4)
        self.assertNotAlmostEqual(silhouette.silhouette_aspect(dims, "T1"), target,
                                  places=2)

    def test_the_vial_becomes_the_squat_box_its_reference_shows(self):
        # 80x170x35 is a tall pen-shaped carton; T_VERT_VIAL_144.webp is a squat
        # 10-vial box, and the measurement says so at +77%. Solving lands on
        # 172x170x35 -- wider than tall as a box, still a portrait PICTURE at
        # 0.9224, which is why the flip guard reads the silhouette rather than
        # the edges.
        #
        # The ТЗ predicted 159x170 from an earlier measurement of the same
        # reference. That measurement is superseded, not reconciled: it paired a
        # reference's full silhouette against a model of our printed faces, which
        # are different quantities.
        base = orient_for_template((80.0, 170.0, 35.0), "T_VERT_VIAL")
        dims, reshaped = reshape_to_art_direction(base, "T_VERT_VIAL")
        self.assertTrue(reshaped)
        self.assertAlmostEqual(dims[1], 170.0, places=6, msg="height is the anchor")
        self.assertAlmostEqual(dims[2], 35.0, places=6, msg="depth is never solved")
        self.assertAlmostEqual(dims[0], 172.0, delta=2.0)
        self.assertLess(silhouette.visible_faces_aspect(dims, "T_VERT_VIAL"), 1.0,
                        "the picture must stay portrait")

    def test_the_anchor_is_the_larger_face_edge_and_the_depth(self):
        for dims_in, template_id in (((115.0, 55.0, 48.0), "T1"),
                                     ((140.0, 35.0, 25.0), "T3"),
                                     ((80.0, 170.0, 35.0), "T_VERT_VIAL")):
            with self.subTest(template=template_id):
                base = orient_for_template(dims_in, template_id)
                out, _ = reshape_to_art_direction(base, template_id)
                self.assertAlmostEqual(out[2], base[2], places=6, msg="depth moved")
                keep = 0 if base[0] >= base[1] else 1
                self.assertAlmostEqual(out[keep], base[keep], places=6,
                                       msg="the anchored edge moved")

    def test_a_carton_that_would_flip_keeps_its_passport_shape(self):
        # 55x100x55 and 45x80x45 are upright vials that routed to a landscape
        # template. Solving for T1's proportion would stretch them past three
        # times their width and stand the product on its side.
        for dims_in in ((55.0, 100.0, 55.0), (45.0, 80.0, 45.0)):
            with self.subTest(dims=dims_in):
                out, reshaped = reshape_to_art_direction(dims_in, "T1")
                self.assertFalse(reshaped)
                self.assertEqual(out, dims_in)

    def test_an_unknown_template_is_left_alone_rather_than_guessed(self):
        out, reshaped = reshape_to_art_direction((100.0, 50.0, 20.0), "T2")
        self.assertFalse(reshaped)
        self.assertEqual(out, (100.0, 50.0, 20.0))

    def test_reshaping_is_idempotent(self):
        base = orient_for_template((115.0, 55.0, 48.0), "T1")
        once, _ = reshape_to_art_direction(base, "T1")
        twice, _ = reshape_to_art_direction(once, "T1")
        for a, b in zip(once, twice):
            self.assertAlmostEqual(a, b, places=6)

    def test_scale_does_not_change_the_answer_but_shape_does(self):
        # The camera frames from the bounding sphere, so only proportion is
        # art-directable. A carton twice the size must reshape to twice the size.
        small, _ = reshape_to_art_direction((115.0, 55.0, 48.0), "T1")
        big, _ = reshape_to_art_direction((230.0, 110.0, 96.0), "T1")
        for a, b in zip(small, big):
            self.assertAlmostEqual(2.0 * a, b, places=4)

    def test_every_catalogue_carton_either_reshapes_or_says_why(self):
        if not PASSPORTS.exists():
            self.skipTest("passports are not in this checkout")
        from src.passport_generator import agent_1_router

        refused = []
        for f in sorted(PASSPORTS.glob("*.json")):
            passport = json.loads(f.read_text(encoding="utf-8"))
            template_id, _ = agent_1_router(passport)
            if template_id not in TARGET_SILHOUETTE_ASPECT:
                continue
            carton = resolve_carton(passport, template_id)
            dims = (carton["width_mm"], carton["height_mm"], carton["depth_mm"])
            out, reshaped = reshape_to_art_direction(dims, template_id)
            if reshaped:
                self.assertAlmostEqual(
                    silhouette.visible_faces_aspect(out, template_id),
                    TARGET_SILHOUETTE_ASPECT[template_id], places=3,
                    msg=f"{f.stem} missed its target")
            else:
                refused.append((f.stem, template_id, dims))
        # The two known upright vials in a landscape template, and nothing else.
        # A third refusal is a new shape the rule has not been thought about for.
        self.assertLessEqual(
            len(refused), 2,
            f"{len(refused)} SKU refused reshaping, expected at most 2: {refused}")


class TestManifestsOnDisk(unittest.TestCase):
    """What Stage 2 will actually open, not what build_manifest would produce.

    Those are the same thing only while the files are current, and a stale
    manifest is precisely the failure the version const exists to make loud. So
    these read the files.
    """

    MANIFESTS = PROJECT_ROOT / "04_passports" / "render_manifests"

    def setUp(self):
        if not self.MANIFESTS.exists():
            self.skipTest("render manifests have not been generated in this checkout")
        self.files = sorted(self.MANIFESTS.glob("*.json"))
        self.assertTrue(self.files, "manifest directory exists but is empty")

    def test_every_manifest_on_disk_satisfies_the_current_contract(self):
        # A partial migration is the worst of the three states: it renders, and
        # it renders some SKU one way and some another.
        stale = []
        for f in self.files:
            m = json.loads(f.read_text(encoding="utf-8"))
            if m.get("manifest_version") != MANIFEST_VERSION:
                stale.append(f"{f.stem}={m.get('manifest_version')}")
                continue
            validate_manifest(m)
        self.assertEqual(stale, [],
                         f"{len(stale)} manifests predate {MANIFEST_VERSION}; "
                         f"regenerate Stage 1 rather than migrate them by hand")

    def test_the_printed_dimensions_still_match_the_passport(self):
        # The reshape must not have leaked into the numbers that get printed.
        # Checked against the passport's own string rather than against
        # build_manifest, so a bug shared by both would not cancel out.
        if not PASSPORTS.exists():
            self.skipTest("passports are not in this checkout")
        checked = 0
        for f in self.files:
            m = json.loads(f.read_text(encoding="utf-8"))
            passport_file = PASSPORTS / f.name
            if not passport_file.exists():
                continue
            declared = (json.loads(passport_file.read_text(encoding="utf-8"))
                        .get("secondary_packaging") or {}).get("dimensions")
            numbers = re.findall(r"\d+(?:\.\d+)?", str(declared or ""))
            if len(numbers) != 3:
                continue
            real = m["carton"]["passport_dimensions"]
            with self.subTest(sku=f.stem):
                self.assertEqual(
                    sorted(float(n) for n in numbers),
                    sorted(real[k] for k in ("width_mm", "height_mm", "depth_mm")),
                    "the printed size is not the size the passport declares")
            checked += 1
        self.assertGreater(checked, 300, "too few SKU checked to mean anything")

    def test_every_reshaped_manifest_hits_its_template_target(self):
        declined = []
        for f in self.files:
            m = json.loads(f.read_text(encoding="utf-8"))
            carton, tid = m["carton"], m["template_id"]
            dims = (carton["width_mm"], carton["height_mm"], carton["depth_mm"])
            if carton["source"] == "art_direction":
                with self.subTest(sku=f.stem):
                    self.assertAlmostEqual(
                        silhouette.visible_faces_aspect(dims, tid),
                        TARGET_SILHOUETTE_ASPECT[tid], places=3)
            elif carton["source"] == "art_direction_declined_orientation":
                declined.append(f.stem)
                real = m["carton"]["passport_dimensions"]
                with self.subTest(sku=f.stem):
                    self.assertEqual(
                        dims, (real["width_mm"], real["height_mm"], real["depth_mm"]),
                        "a declined reshape must leave the geometry alone")
        # The two upright vials that routed to a landscape template. A third is a
        # shape nobody has looked at yet.
        self.assertEqual(len(declined), 2,
                         f"expected 2 declined reshapes, got {len(declined)}: {declined}")


class TestManifestPaths(unittest.TestCase):
    def test_path_uses_the_min_stem_convention(self):
        p = manifest_path_for("1-min", Path("/tmp/manifests"))
        self.assertEqual(p.name, "1-min.json")


if __name__ == "__main__":
    unittest.main()
