"""The eleven SKU rendered against real packaging, and their design specs.

`Reference Templates/` holds a folder per product with reference photography, a
measured `metadata.json` (D-1) and a `design_spec.json` (D-2). This module is the
one place that maps a catalogue SKU to its folder, and the only reader of the
spec on the project side.

It lives in `src/` rather than `scripts/` because the manifest builder needs it:
a script may import project code, project code importing a script is backwards.
`scripts/make_ocr_fixtures.py` imports the map from here.

The map is resolved by hand and not derived from names, because the names do not
identify a SKU: `15_T1_Xanax` and `24_T1_Xanax_Pfizer` are two catalogue entries
whose names contain each other, and matching on "Cialis" reaches Strips, Oral
Jelly and Black Generic before the plain one.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.utils import PROJECT_ROOT

TEMPLATES_DIR = PROJECT_ROOT / "Reference Templates"

#: folder name -> catalogue SKU stem. Folders with no reference photograph are
#: deliberately absent: there is nothing for them to be a reference OF.
TEMPLATE_SAMPLE: dict[str, str] = {
    "02_T1_SMALL_Cialis":            "59-min",
    "08_T1_Ativan":                  "135-min",
    "14_T1_Imovane":                 "155-min",
    "15_T1_Xanax":                   "156-min",
    "21_T1_Valium_Brand":            "272-min",
    "23_T1_Lexotanil":               "308-min",
    "24_T1_Xanax_Pfizer":            "340-min",
    "25_T1_Modafinil_Generic":       "344-min",
    "30_T1_Ritalin":                 "404-min",
    "31_Kamagra_Template_Reference": "64-min",
    "32_Viagra_Template_Reference":  "74-min",
}

#: catalogue SKU stem -> folder name
FOLDER_BY_STEM: dict[str, str] = {v: k for k, v in TEMPLATE_SAMPLE.items()}


class MissingDesignSpec(RuntimeError):
    """A SKU in the design group has no spec on disk.

    Loud on purpose. The design group's whole point is that these eleven are
    rendered against real packaging; falling back to the generic art direction
    would produce a plausible carton in the wrong colours and call it done, which
    is the failure mode this project keeps finding in its own history.
    """


def is_design_sku(sku_id: str) -> bool:
    return _stem(sku_id) in FOLDER_BY_STEM


def _stem(sku_id: str) -> str:
    """`59-min.jpg` and `59-min` are the same SKU.

    Manifests carry `sku_id` as it appears in the passport, which for some SKU
    still has a file extension on it.
    """
    stem = str(sku_id).strip()
    for suffix in (".jpg", ".jpeg", ".png", ".json"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
    return stem


def spec_path(sku_id: str) -> Path | None:
    folder = FOLDER_BY_STEM.get(_stem(sku_id))
    return (TEMPLATES_DIR / folder / "design_spec.json") if folder else None


def load_design(sku_id: str) -> dict | None:
    """The design spec for *sku_id*, or None when the SKU is not in the group.

    Raises :class:`MissingDesignSpec` when the SKU IS in the group and the spec
    is absent or unreadable -- the distinction between "no design intended" and
    "design intended and missing" is the reason this returns None for one and
    raises for the other.
    """
    path = spec_path(sku_id)
    if path is None:
        return None
    if not path.exists():
        raise MissingDesignSpec(
            f"{_stem(sku_id)} is in the design group ({path.parent.name}) but "
            f"{path.name} is absent. Run scripts/fit_design_spec.py --folder "
            f"{path.parent.name}, or remove the SKU from TEMPLATE_SAMPLE.")
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — an unreadable spec is a hard stop
        raise MissingDesignSpec(f"{path} could not be read: {e}") from e
    if not spec.get("face_aspect"):
        raise MissingDesignSpec(f"{path} carries no face_aspect")
    return spec


def reshape_to_design(extents, face_aspect: float):
    """Solve the carton so its FRONT FACE matches the reference's proportion.

    NOT the same quantity as `reshape_to_art_direction`, and the difference is
    the one this project has already got wrong once. That function solves the
    SILHOUETTE aspect -- the visible faces together, front plus the sliver of
    side panel the camera's rotation shows. This one solves the FRONT FACE alone,
    because that is what a design spec's coordinates are normalised to: `u` and
    `v` run 0..1 across the printed face, not across the picture.

    The longer edge is kept and assigned by orientation, so a portrait reference
    does not inflate the carton: Lexotanil measures 2.026, and solving 110x50 by
    keeping the width would give a 110x223mm box, where keeping the long edge
    gives 54x110 -- the passport's own carton, stood up.
    """
    width, height, depth = (float(e) for e in extents)
    long_edge = max(width, height)
    short_edge = long_edge * min(face_aspect, 1.0 / face_aspect)
    if face_aspect >= 1.0:
        return short_edge, long_edge, depth      # portrait face
    return long_edge, short_edge, depth          # landscape face
