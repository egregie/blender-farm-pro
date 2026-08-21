"""The 28 SKU rendered against real packaging, and their design specs.

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

from src.utils import PROJECT_ROOT, product_code

TEMPLATES_DIR = PROJECT_ROOT / "Reference Templates"

#: folder name -> catalogue SKU stem. Folders with no reference photograph are
#: deliberately absent: there is nothing for them to be a reference OF.
#:
#: `21_Valium_Brand` and `24_Xanax_Pfizer` are DELIBERATELY absent, and their
#: absence is the point. A re-acquisition replaced every photograph in the group
#: except Cialis's, Kamagra's and Viagra's, and the two it left those folders are
#: not measurable: Valium's carton is shot from above with a blister lying across
#: its printed face, and Xanax Pfizer's frame holds two cartons on a wooden table.
#: A SKU with no spec must not sit in this map -- `load_design` raises rather than
#: falling back, so leaving them here does not render them generically, it stops
#: them rendering at all. Out of the map they take the generic art direction,
#: which is the honest outcome for a carton nothing has measured.
#:
#: `107_Tramadol` left for a different reason and KEEPS its photography, so
#: its absence is not implied by an empty folder the way theirs is.
#: Its `highlight` cluster is speckle -- 107 connected components, the largest
#: holding 60% of the mask -- and a boundary walk over a blob that pinched
#: doubles back through the pinch: `trace_outline` returns a ring crossing
#: itself 136 times BEFORE any simplification, so Douglas-Peucker is not the
#: cause. The even-odd fill of that ring is THREE disjoint pieces, 74/14/10%,
#: and a ring that does not cross itself has a simply-connected interior, so
#: the best any repair can score against it is the largest piece. `simple_ring`
#: scored 0.548 where all thirteen other tangled parts score 0.988 or better.
#: The fitter had already written its own verdict into the spec: this field
#: agrees with the photograph at 0.54, and `secondary_1` at 0.539.
#:
#: Four repairs were measured and none reached the region: ranking dropped
#: vertices by IoU rather than area (0.559), splitting the ring at its
#: crossings and keeping the larger loop (0.741, and it costs `59-min` 0.999
#: -> 0.905), and cleaning the mask before tracing, which removes every tangle
#: in the group but takes THIS field to an IoU of 0.0 and turns the test green
#: by leaving it nothing to check. The spec stays on disk as measured; what
#: leaves the group is the SKU, not the measurement.
#:
#: The folder's numeric prefix is its SKU's number, so the key now carries the
#: value's number in it. The map stays explicit anyway: the number is the only
#: part of a folder name that identifies a SKU, and deriving the map from the
#: name would re-introduce exactly the matching this module refuses to do.
#: Renamed from the old sequential prefixes (`02_Cialis` and the rest) after the
#: rule was checked against every pair already in this map and reproduced all
#: eleven it then held. `64_Kamagra` and `74_Viagra` then shed a trailing
#: `_Template_Reference`, the last two folders that still carried it, so the
#: rule reads without exceptions: the numeric prefix is the SKU, the rest is
#: the product. Note `58-min` is "Cialis Brand", a different SKU with no
#: folder -- `59-min` is the plain "Cialis" this one holds.
TEMPLATE_SAMPLE: dict[str, str] = {
    "59_Cialis":                       "59-min",
    "60_Cialis_Professional":          "60-min",
    "62_Cialis_Super_Active":          "62-min",
    "64_Kamagra":                      "64-min",
    "74_Viagra":                       "74-min",
    "133_Ambien":                      "133-min",
    "134_Atarax":                      "134-min",
    "135_Ativan":                      "135-min",
    "149_Modalert":                    "149-min",
    "150_Waklert":                     "150-min",
    "151_Provigil":                    "151-min",
    "152_Artvigil":                    "152-min",
    "155_Imovane":                     "155-min",
    "156_Xanax":                       "156-min",
    "157_Valium":                      "157-min",
    "158_Klonopin":                    "158-min",
    "221_Inderal":                     "221-min",
    "230_Slimex":                      "230-min",
    "272_Valium_Brand":                "272-min",
    "304_Sonata":                      "304-min",
    "308_Lexotanil":                   "308-min",
    "340_Xanax_Pfizer":                "340-min",
    "344_Modafinil_Generic":           "344-min",
    "346_Modvigil":                    "346-min",
    "357_Adderall":                    "357-min",
    "362_Hydrocodone":                 "362-min",
    "365_Tapentadol":                  "365-min",
    "404_Ritalin":                     "404-min",
}

#: catalogue SKU stem -> folder name
FOLDER_BY_STEM: dict[str, str] = {v: k for k, v in TEMPLATE_SAMPLE.items()}


class MissingDesignSpec(RuntimeError):
    """A SKU in the design group has no spec on disk.

    Loud on purpose. The design group's whole point is that these 28 are
    rendered against real packaging; falling back to the generic art direction
    would produce a plausible carton in the wrong colours and call it done, which
    is the failure mode this project keeps finding in its own history.
    """


def is_design_sku(sku_id: str) -> bool:
    return _stem(sku_id) in FOLDER_BY_STEM


def _stem(sku_id: str) -> str:
    """`59-min.jpg` and `59-min` are the same SKU.

    Manifests carry `sku_id` as it appears in the passport, which for EVERY SKU
    has a file extension on it -- `SKU.csv`'s key column is named `picture`.
    One implementation, in utils, because the same strip decides what is printed
    on the carton; see `product_code`.
    """
    return product_code(sku_id)


def spec_path(sku_id: str) -> Path | None:
    folder = FOLDER_BY_STEM.get(_stem(sku_id))
    return (TEMPLATES_DIR / folder / "design_spec.json") if folder else None


def _orientation(a, b, c) -> int:
    v = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    return 0 if abs(v) < 1e-12 else (1 if v > 0 else 2)


def _crosses(p1, p2, p3, p4) -> bool:
    return (_orientation(p1, p2, p3) != _orientation(p1, p2, p4)
            and _orientation(p3, p4, p1) != _orientation(p3, p4, p2))


def ring_crossings(poly) -> list:
    """Which pairs of this closed ring's edges cross each other."""
    n, out = len(poly), []
    for i in range(n):
        for j in range(i + 1, n):
            if (j + 1) % n == i or (i + 1) % n == j:
                continue
            if _crosses(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n]):
                out.append((i, j))
    return out


def _ring_area(poly) -> float:
    n = len(poly)
    return abs(sum(poly[i][0] * poly[(i + 1) % n][1]
                   - poly[(i + 1) % n][0] * poly[i][1]
                   for i in range(n))) / 2


def simple_ring(poly):
    """The same region as a ring that crosses itself nowhere.

    A self-intersecting outline is not a region: it is a drawing instruction
    whose meaning depends on the fill rule, and the two sides of this project
    use different ones. `rasterise()` fills with PIL's even-odd scanline and is
    what every spec's `verification.pixel_agreement` was measured against; the
    driver hands the same points to a Blender curve, which tessellates them.

    On `340-min` they disagreed by a fifth of the field. Its brand outline has
    eight points, one of which -- `[0.980, 0.707]` -- sits far below the other
    seven, the same one-pixel thread artefact `fills_its_box` already guards
    against. Even-odd drops the sliver; Blender filled the triangle back to the
    panel, **1.33% of the face**, and our packshot carried a magenta wedge the
    real carton does not have. Measured excess: 1.07%. The field read 0.752 at
    100.0% recall and 75.2% precision -- our magenta strictly contained the
    spec's and was a third larger.

    13 parts across 8 of the 28 cartons are tangled this way.

    Repaired by dropping the fewest vertices that untangle it, preferring the
    removal that changes the enclosed area least. Only vertices belonging to a
    crossing edge are candidates, which is what keeps this cheap. Against the
    original's even-odd raster the repaired rings score 0.972 to 0.9999 IoU, so
    this preserves the region that was verified rather than redrawing it.

    Done at LOAD, not on disk: the spec file is a measurement of a photograph
    and stays as traced. What every consumer receives is a region.
    """
    poly = [(float(p[0]), float(p[1])) for p in poly]
    while len(poly) > 3:
        hits = ring_crossings(poly)
        if not hits:
            break
        n = len(poly)
        candidates = sorted({k % n for i, j in hits
                             for k in (i, i + 1, j, j + 1)})
        before = _ring_area(poly)
        best = None
        for i in candidates:
            cand = poly[:i] + poly[i + 1:]
            key = (len(ring_crossings(cand)), abs(_ring_area(cand) - before))
            if best is None or key < best[0]:
                best = (key, cand)
        poly = best[1]
    return poly


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
    for field in spec.get("fields") or []:
        for part in field.get("parts") or []:
            outline = part.get("outline") or []
            if len(outline) < 4:
                continue
            fixed = simple_ring(outline)
            if len(fixed) != len(outline):
                part["outline"] = [list(p) for p in fixed]
                # Recorded rather than done quietly: a repaired outline is not
                # what the tracer measured, and the manifest carries this.
                part["simplified_from"] = len(outline)
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
