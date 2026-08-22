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


def _pair_crosses(poly, n, i, j) -> bool:
    if (j + 1) % n == i or (i + 1) % n == j:
        return False
    return _crosses(poly[i], poly[(i + 1) % n], poly[j], poly[(j + 1) % n])


#: An edge spanning more than this many grid cells is tested against everything
#: rather than indexed. Without it a single long edge across a finely divided
#: ring is inserted into thousands of cells and the index costs more than the
#: quadratic loop it replaces.
_GRID_SPAN_CAP = 16


def ring_crossings(poly) -> list:
    """Which pairs of this closed ring's edges cross each other.

    Same answer as testing every pair, reached through a uniform grid over the
    ring's own bounding box so that only edges sharing a cell are compared.

    The index is not an optimisation for its own sake. `simple_ring` re-runs
    this once per candidate vertex per iteration, so a quadratic scan is paid
    tens of times per tangled ring: measured across the group at a 0.001 face
    width, `load_design` took 61.6s, nearly all of it here. Rings traced round a
    printed shape are spatially local, which is exactly the case a grid serves.

    Falls back to the full scan when the index would not be cheaper -- a ring
    whose edges nearly all share cells gains nothing, and paying for the index
    as well would be strictly worse.
    """
    n = len(poly)
    if n < 4:
        return []
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    side = max(w, h)
    if side <= 0:
        return []
    import math
    div = max(1, int(math.sqrt(n)))
    cell = side / div
    x0, y0 = min(xs), min(ys)

    cells: dict = {}
    long_edges = []
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        cx0, cx1 = sorted((int((a[0] - x0) / cell), int((b[0] - x0) / cell)))
        cy0, cy1 = sorted((int((a[1] - y0) / cell), int((b[1] - y0) / cell)))
        if (cx1 - cx0 + 1) * (cy1 - cy0 + 1) > _GRID_SPAN_CAP:
            long_edges.append(i)
            continue
        for cx in range(cx0, cx1 + 1):
            for cy in range(cy0, cy1 + 1):
                cells.setdefault((cx, cy), []).append(i)

    if len(long_edges) * 4 > n:            # the index would not pay
        out = []
        for i in range(n):
            for j in range(i + 1, n):
                if _pair_crosses(poly, n, i, j):
                    out.append((i, j))
        return out

    seen = set()
    for bucket in cells.values():
        for a in range(len(bucket)):
            for b in range(a + 1, len(bucket)):
                i, j = bucket[a], bucket[b]
                if i > j:
                    i, j = j, i
                if (i, j) in seen:
                    continue
                seen.add((i, j))
    for i in long_edges:                   # a long edge may cross anything
        for j in range(n):
            if i == j:
                continue
            seen.add((min(i, j), max(i, j)))
    return sorted((i, j) for i, j in seen if _pair_crosses(poly, n, i, j))


def _filled(poly, size: int = 192):
    """The ring's EVEN-ODD fill, rasterised inside its own bounding box.

    The quantity `simple_ring` has to preserve, and the one it used to ignore.
    Rasterised in the ring's own box rather than in face coordinates so a sliver
    covering a thousandth of the face still gets a few hundred pixels to be
    judged on.

    A raster quantises, and on rings that were already fine the tie-break is
    therefore slightly noisier than the exact-but-wrong sum it replaced: of the
    nine tangled rings in the group, two now drop a different vertex, and their
    fidelity to the raw trace moves by 0.0001 -- Inderal 0.9996 to 0.9996,
    Kamagra 0.9999 to 0.9998. That is the price of measuring the right quantity
    approximately instead of the wrong one exactly, and it is paid where it
    cannot matter: among candidates that are all but identical, either will do.
    """
    from PIL import Image, ImageDraw

    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    w = max(xs) - min(xs)
    h = max(ys) - min(ys)
    if w <= 0 or h <= 0 or len(poly) < 3:
        return None
    img = Image.new("1", (size, size), 0)
    ImageDraw.Draw(img).polygon(
        [((p[0] - min(xs)) / w * (size - 1), (p[1] - min(ys)) / h * (size - 1))
         for p in poly], fill=1)
    return img


def _fill_iou(a_img, b_poly, box) -> float:
    """How much of the original region a candidate ring still describes."""
    from PIL import Image, ImageDraw

    x0, y0, w, h = box
    size = a_img.size[0]
    img = Image.new("1", (size, size), 0)
    ImageDraw.Draw(img).polygon(
        [((p[0] - x0) / w * (size - 1), (p[1] - y0) / h * (size - 1))
         for p in b_poly], fill=1)
    a = a_img.tobytes()
    b = img.tobytes()
    inter = union = 0
    for byte_a, byte_b in zip(a, b):
        inter += bin(byte_a & byte_b).count("1")
        union += bin(byte_a | byte_b).count("1")
    return inter / union if union else 0.0


class RingRepairFailed(RuntimeError):
    """A tangled outline could not be untangled without redrawing its region.

    Loud on purpose, and the precedent is `107_Tramadol`: where a repair cannot
    reach the region, the honest outcome is that the SKU leaves the group, not
    that a shape nobody measured is printed on a carton.
    """


#: How much of the original fill a repair must keep. The nine tangled rings in
#: the group today score 0.987 to 1.000, so this refuses only a catastrophe --
#: and one exists: at a 0.001 face width Ritalin's `highlight#1` repaired from
#: 0.36% of the face to 11.87%, an IoU of 0.005, because the objective below
#: used to be the SHOELACE area, which on a self-crossing ring is a signed
#: cancellation and not what an even-odd fill covers.
RING_REPAIR_MIN_IOU = 0.90


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
    removal that keeps the most of the ORIGINAL EVEN-ODD FILL. Only vertices
    belonging to a crossing edge are candidates, which is what keeps this cheap.

    THE OBJECTIVE USED TO BE THE SHOELACE AREA, and that was the wrong quantity
    for exactly the rings this function exists for. On a ring that crosses
    itself the shoelace sum is a signed cancellation: the two lobes of a figure
    eight subtract. An even-odd fill covers both. So the repair was scoring
    itself on a number that has no relation to what gets painted, and the two
    agreed only because the group's tangles happened to be mild.

    They do not stay mild. At a 0.001 face width -- three times finer than the
    committed 0.004 -- Ritalin's `highlight#1` repaired from 0.36% of the face
    to 11.87%, an IoU of 0.005 against the original. The repair did not lose the
    region, it INVENTED one thirty-three times larger and put it on the carton.
    Nothing failed; it showed up as that SKU dropping 6.68 points.

    A repair that cannot keep `RING_REPAIR_MIN_IOU` of the fill raises rather
    than returning a shape nobody measured.

    Done at LOAD, not on disk: the spec file is a measurement of a photograph
    and stays as traced. What every consumer receives is a region.
    """
    poly = [(float(p[0]), float(p[1])) for p in poly]
    if not ring_crossings(poly):
        return poly

    target = _filled(poly)
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    box = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))

    while len(poly) > 3:
        hits = ring_crossings(poly)
        if not hits:
            break
        n = len(poly)
        candidates = sorted({k % n for i, j in hits
                             for k in (i, i + 1, j, j + 1)})
        best = None
        for i in candidates:
            cand = poly[:i] + poly[i + 1:]
            # Crossings first, because the repair has to terminate; the fill is
            # what decides between the removals that make equal progress.
            iou = 0.0 if target is None else _fill_iou(target, cand, box)
            key = (len(ring_crossings(cand)), -iou)
            if best is None or key < best[0]:
                best = (key, cand)
        poly = best[1]

    if target is not None:
        kept = _fill_iou(target, poly, box)
        if kept < RING_REPAIR_MIN_IOU:
            raise RingRepairFailed(
                f"untangling this outline kept only {kept:.3f} of the region it "
                f"described ({len(poly)} vertices left). Drawing it would print "
                f"a shape nobody measured; the outline needs re-tracing, or the "
                f"SKU needs to leave the design group the way 107_Tramadol did.")
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
            if len(outline) >= 4:
                fixed = simple_ring(outline)
                if len(fixed) != len(outline):
                    part["outline"] = [list(p) for p in fixed]
                    # Recorded rather than done quietly: a repaired outline is
                    # not what the tracer measured, and the manifest carries
                    # this.
                    part["simplified_from"] = len(outline)
            # Contract 1.8: a part is a region, its outline minus its holes, and
            # a hole that crosses itself is no more a region than an outline
            # that does. Same repair, same place -- the boundary -- and the spec
            # on disk stays as traced.
            holes, repaired = [], []
            for i, ring in enumerate(part.get("holes") or []):
                if len(ring) >= 4:
                    fixed = simple_ring(ring)
                    if len(fixed) != len(ring):
                        repaired.append([i, len(ring)])
                        holes.append([list(q) for q in fixed])
                        continue
                holes.append([list(q) for q in ring])
            if part.get("holes") is not None:
                part["holes"] = holes
            if repaired:
                part["holes_simplified_from"] = repaired
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
