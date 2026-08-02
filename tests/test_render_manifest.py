"""Tests for the Stage 1 -> Stage 2 render-manifest contract.

Both sides of the boundary are checked against the SAME artifact
(schemas/render_manifest.schema.json) rather than against each other's
expectations, which is the point of the contract.
"""
import json
import unittest
from pathlib import Path

from src.render_manifest import (
    MANIFEST_VERSION,
    build_manifest,
    load_schema,
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
        # package, which is lossy.
        m = build_manifest(_passport("1-min"))
        self.assertEqual(m["carton"]["source"], "passport_secondary")
        self.assertAlmostEqual(m["carton"]["width_mm"], 115.0)
        self.assertAlmostEqual(m["carton"]["height_mm"], 55.0)
        self.assertAlmostEqual(m["carton"]["depth_mm"], 48.0)

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
        self.assertEqual(m["carton"]["source"], "derived_from_primary")
        self.assertGreater(m["carton"]["width_mm"], 0)

    def test_missing_secondary_packaging_still_yields_dimensions(self):
        m = build_manifest(dict(self.BASE))
        validate_manifest(m)
        self.assertIn(m["carton"]["source"],
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

    def test_every_vertical_family_sku_renders_portrait(self):
        for f in sorted(PASSPORTS.glob("*.json")):
            m = build_manifest(json.loads(f.read_text(encoding="utf-8")))
            if m["template_id"] in ("T_BOTTLE_BOX", "T_VERT_VIAL",
                                    "T_VERT_DROPPER", "T_VERT_INHALER"):
                c = m["carton"]
                self.assertGreaterEqual(
                    c["height_mm"], max(c["width_mm"], c["depth_mm"]),
                    f"{f.stem} ({m['template_id']}) is not upright",
                )


class TestContractRejectsDrift(unittest.TestCase):
    """A contract that accepts anything is not a contract."""

    def setUp(self):
        self.valid = build_manifest(_passport("1-min"))

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
                if m["carton"]["source"] == "template_ratio":
                    guessed.append(f.stem)
            except Exception as e:  # noqa: BLE001 - report all, not just the first
                failures.append(f"{f.stem}: {type(e).__name__}: {e}")
        self.assertEqual(failures, [], f"{len(failures)} passports failed the contract")
        # Not an assertion about correctness, but a guard against silently
        # regressing to guessed geometry for the whole catalogue.
        self.assertEqual(guessed, [], "these SKU fell back to guessed dimensions")


class TestManifestPaths(unittest.TestCase):
    def test_path_uses_the_min_stem_convention(self):
        p = manifest_path_for("1-min", Path("/tmp/manifests"))
        self.assertEqual(p.name, "1-min.json")


if __name__ == "__main__":
    unittest.main()
