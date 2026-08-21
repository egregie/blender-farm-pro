"""D-2 — turn a measured reference face into a design spec, and prove it.

    python scripts/fit_design_spec.py --folder 02_T1_SMALL_Cialis
    python scripts/fit_design_spec.py --all --preview

Reads the segmentation D-1 produced (`measure_reference_face.segment`, the same
partition, not a second implementation of it) and writes `design_spec.json` into
the folder: a substrate colour and an ordered stack of fields, each a filled
outline in FACE-NORMALISED coordinates (u across, v down, both 0..1).

WHY OUTLINES AND NOT CONICS. The plan said conics, because the Cialis fields are
arcs of large ellipses. Four of the eleven designs are built that way -- and
Lexotanil's bands are straight, Ritalin has no colour field at all, and Kamagra's
transition is five parallel rules. One primitive has to carry all of them, and a
polygon carries a conic to whatever accuracy is asked while a conic cannot carry
a rectangle without special-casing. Smoothness is recorded per outline so D-4 can
fit curves where the source really is curved rather than rebuilding stair-steps.

WHAT MAKES IT A SPEC AND NOT A TRACE. Vertices are simplified until the spec's
own rasterisation stops agreeing with the segmentation. `--verify` reports that
agreement as a percentage of face pixels, so "the spec is right" is a number.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.measure_reference_face import (  # noqa: E402
    TEMPLATES_DIR, _hex, segment,
)

#: Per-component ground truth, written by scripts/label_print.py. The name and
#: the loader live in this module rather than in that one because label_print
#: already imports `components` from here, and the reverse direction would be a
#: circular import.
TRUTH_NAME = "print_truth.json"


def load_truth(folder: Path) -> dict | None:
    """The hand-made classification for *folder*, or None if it has none."""
    path = folder / TRUTH_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


# A field is a share of the FACE, not a pixel count: the rectified faces differ
# in size and a fixed count means a different thing on each. 0.8% keeps the
# Cialis dosage block (2.0% of its face) and drops every letterform, which is the
# distinction that matters -- when type fails to separate into its own cluster,
# its strokes land in a colour field and get traced as though they were design.
# They are not: the renderer draws type from the manifest's strings, and a spec
# carrying letter outlines would print the reference's words instead.
#
# SUPERSEDED BY THE LABEL as of Phase B, and kept because it names the reasoning
# the label replaced. `fit()` now enumerates at the truth file's own floor, which
# is coarser than nothing and finer than this: Imovane's only printed field is
# 0.67% of its face and this threshold would drop it.
MIN_REGION_FRAC = 0.008
# A field has to be visibly different from the board it is printed on. Below this
# distance in RGB it is not a design element -- it is the clustering splitting one
# printed surface into two under a lighting gradient. Measured: Xanax's
# "highlight" #E9DCB6 sits TWO levels from its substrate #E8DBB2, Valium's
# #C9C8C4 two from #C9C5C0, Ritalin's #82837D two from #817F78. All three were
# emitted as fields covering a third of the face, and they are why six of the
# eleven palettes came back inseparable in D-6: a spec that names two colours a
# classifier cannot tell apart makes every later measurement of it meaningless.
#
# Set to the same figure D-6 needs to tell two colours apart
# (scripts/design_qa.SEPARABLE_MIN). The two readings agree: a field this close
# to its board is invisible to a viewer AND unmeasurable afterwards, and emitting
# one produces a spec whose own fidelity cannot be checked.
MIN_FILL_CONTRAST = 0.08
# How much of its own bounding box a component must fill to be admitted as a
# printed shape when it neither runs off the face nor reads as a block. Measured
# on the component's PIXELS with hairline filaments removed, not on its traced
# polygon: the polygon encloses holes, which is right for a block with type
# reversed out of it and wrong here.
#
# This replaced a "large enough" escape, and it had to: the escape could not be
# repaired by choosing a better size, because the thing it was letting through
# is BIGGER than the thing it was there for. Xanax's traced "XA" covers 3.4% of
# its face and Xanax Pfizer's magenta panel 3.2%. They separate on this ratio at
# 0.49 against 0.96.
BOX_FILL_MIN = 0.85
SIMPLIFY_TOLERANCE = 0.004  # Douglas-Peucker, in face widths
SMOOTH_TURN_DEG = 25.0      # a vertex turning less than this reads as a curve


def _neighbours(y, x):
    #  Moore neighbourhood, clockwise from the west. Order matters: the tracer
    #  resumes from the backtrack direction, which is what keeps it on the
    #  outline instead of cutting corners into the interior.
    return [(y, x - 1), (y - 1, x - 1), (y - 1, x), (y - 1, x + 1),
            (y, x + 1), (y + 1, x + 1), (y + 1, x), (y + 1, x - 1)]


def trace_outline(mask: np.ndarray) -> list[tuple[int, int]]:
    """Moore-neighbour boundary trace of the largest blob in *mask*.

    Written out rather than imported: skimage and scipy are not dependencies of
    this project, and adding one to draw an outline would put a compiled package
    in the way of a measurement script.
    """
    h, w = mask.shape
    padded = np.zeros((h + 2, w + 2), bool)
    padded[1:-1, 1:-1] = mask
    ys, xs = np.nonzero(padded)
    if not len(ys):
        return []
    start = (int(ys[0]), int(xs[np.nonzero(ys == ys[0])[0][0]]))

    outline = [start]
    prev = (start[0], start[1] - 1)
    cur = start
    for _ in range(4 * padded.size):
        ring = _neighbours(*cur)
        try:
            i = ring.index(prev)
        except ValueError:
            i = 0
        found = None
        for k in range(1, 9):
            cand = ring[(i + k) % 8]
            if padded[cand]:
                found = cand
                prev = ring[(i + k - 1) % 8]
                break
        if found is None:
            break
        cur = found
        if cur == start and len(outline) > 2:
            break
        outline.append(cur)
    return [(x - 1, y - 1) for y, x in outline]


def components(mask: np.ndarray, min_px: int) -> list[np.ndarray]:
    """Split *mask* into connected regions, largest first.

    A field is rarely one blob: the Cialis olive enters from the left AND sweeps
    across the bottom right, and tracing "the" outline of that mask produced a
    polygon around one half and 65% agreement. Union-find over row runs rather
    than a pixel flood fill -- a 1100x700 face is 770 000 pixels and a
    Python-level flood is slow enough to discourage re-running the fit, which is
    the one thing this step needs to be cheap.
    """
    h, w = mask.shape
    parent: dict[int, int] = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    runs_by_row: list[list[tuple[int, int, int]]] = []
    next_id = 0
    for y in range(h):
        row = mask[y]
        idx = np.flatnonzero(np.diff(np.concatenate(([0], row.view(np.int8), [0]))))
        runs = []
        for x0, x1 in zip(idx[::2], idx[1::2]):
            parent[next_id] = next_id
            runs.append((int(x0), int(x1), next_id))
            next_id += 1
        if y:
            for x0, x1, rid in runs:
                for px0, px1, pid in runs_by_row[-1]:
                    if px0 < x1 and x0 < px1:      # overlap => 4-connected
                        union(rid, pid)
        runs_by_row.append(runs)

    out: dict[int, np.ndarray] = {}
    for y, runs in enumerate(runs_by_row):
        for x0, x1, rid in runs:
            r = find(rid)
            m = out.get(r)
            if m is None:
                m = out[r] = np.zeros((h, w), bool)
            m[y, x0:x1] = True

    keep = [m for m in out.values() if m.sum() >= min_px]
    keep.sort(key=lambda m: -m.sum())
    return keep


def _perp(pt, a, b) -> float:
    (x, y), (x1, y1), (x2, y2) = pt, a, b
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** 0.5
    if n == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / n


def simplify(points, tol):
    """Douglas-Peucker, iterative so a 20 000-point outline cannot blow the stack."""
    if len(points) < 3:
        return list(points)
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        worst, wi = -1.0, i
        for k in range(i + 1, j):
            d = _perp(points[k], points[i], points[j])
            if d > worst:
                worst, wi = d, k
        if worst > tol:
            keep[wi] = True
            stack.append((i, wi))
            stack.append((wi, j))
    return [p for p, k in zip(points, keep) if k]


def _area(points) -> float:
    if len(points) < 3:
        return 0.0
    p = np.asarray(points, dtype=float)
    x, y = p[:, 0], p[:, 1]
    return float(abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / 2)


def _runs_off_face(outline, w, h) -> bool:
    """Does this outline reach the edge of the printed face?

    A colour field that enters from an edge is structural whatever its shape.
    Nothing printed as type does that.
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    margin = 0.01 * max(w, h)
    return (min(xs) <= margin or min(ys) <= margin
            or max(xs) >= w - 1 - margin or max(ys) >= h - 1 - margin)


def _despeckle(mask: np.ndarray) -> np.ndarray:
    """The component with one-pixel filaments removed: erode 1px, dilate 1px.

    A morphological opening. A printed shape loses and regains its outline; a
    thread one pixel wide does not come back, because there was nothing left of
    it to dilate.
    """
    from PIL import ImageFilter
    img = Image.fromarray((mask * 255).astype("uint8"))
    return np.asarray(img.filter(ImageFilter.MinFilter(3))
                         .filter(ImageFilter.MaxFilter(3))) > 0


def fills_its_box(mask: np.ndarray) -> float:
    """Share of its own bounding box the component's pixels occupy.

    Taken after `_despeckle`, and that is the whole point of the function.
    Xanax Pfizer's magenta panel is a clean 138x160 pixel rectangle with a
    ONE-PIXEL thread running a fifth of the face down the carton's right edge --
    an artefact of rectifying a photograph, not something printed. The thread
    carries 1% of the component's pixels and stretches its bounding box by half,
    taking this ratio from 0.96 to 0.51 and dropping a plain colour panel below
    every rectangle test in this module.
    """
    m = _despeckle(mask)
    if not m.any():
        return 0.0
    ys, xs = np.nonzero(m)
    box = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
    return float(m.sum()) / box if box else 0.0


def is_design_field(outline, w, h, mask=None) -> bool:
    """Is this component a colour field, or a letter that landed in one?

    Area alone cannot tell them apart -- Cialis's "C" and "a" are larger than its
    dosage block, and the case that settles it is Xanax, whose traced "XA" is
    LARGER than Xanax Pfizer's magenta panel: 3.4% of its face against 3.2%. Any
    threshold admitting the panel admits the letters. A component earns its place
    three ways instead:

    - it RUNS OFF THE FACE. The olive bands enter from the edges; nothing printed
      as type does that.
    - it reads as a BLOCK. `part_kind`'s polygon test, which encloses holes, and
      must: the four references that reverse the dosage out of a filled block
      leave letter-shaped holes in it, and Cialis's block fills only 0.70 of its
      box by pixels while its outline fills 0.95.
    - its PIXELS fill its own box, hairlines removed. This is what carries a
      plain colour panel that is not quite a rectangle, and it is what "XA" fails
      at 0.49.

    This matters more than tidiness. Type is drawn from the manifest's strings,
    and a spec carrying letter outlines prints the REFERENCE's words on every
    carton built from it -- the exact failure the text-as-geometry rule exists to
    prevent, arriving through the back door. Xanax shipped that way: the reader
    that measures our own type came back with "XAXa" off a carton printing
    "Xanax", because the wordmark was standing beside it as geometry.
    """
    if _runs_off_face(outline, w, h):
        return True
    if part_kind(outline) == "block":
        return True
    return mask is not None and fills_its_box(mask) >= BOX_FILL_MIN


def part_kind(outline) -> str:
    """`block` for a printed colour block, `field` for everything else.

    Named in the spec rather than re-derived by the renderer. The driver runs
    inside Blender and reads only the manifest, so a shape it has to classify
    for itself is a second implementation of a rule that already exists here --
    and this project has twice paid for two copies of "the same" logic.

    The distinction earns its keep: four of the eleven references reverse the
    dosage out of a filled block (Cialis, Ativan, Imovane, Lexotanil). A block is
    a place to put type; a field is not.
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    bbox = (max(xs) - min(xs)) * (max(ys) - min(ys))
    if bbox <= 0 or len(outline) > 12:
        return "field"
    return "block" if _area(outline) / bbox >= 0.85 else "field"


def _smoothness(points) -> float:
    """Share of vertices that turn by less than SMOOTH_TURN_DEG.

    A polygon approximating an arc turns a little at every vertex; one
    approximating a rectangle turns 90 degrees at four of them and nowhere else.
    The figure tells D-4 whether to fit a curve through these points or to build
    them as drawn.
    """
    if len(points) < 3:
        return 0.0
    pts = np.asarray(points, dtype=float)
    prev = pts - np.roll(pts, 1, axis=0)
    nxt = np.roll(pts, -1, axis=0) - pts
    dot = (prev * nxt).sum(1)
    norm = np.linalg.norm(prev, axis=1) * np.linalg.norm(nxt, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        ang = np.degrees(np.arccos(np.clip(dot / np.where(norm == 0, 1, norm), -1, 1)))
    return float(np.mean(ang < SMOOTH_TURN_DEG))


def fit(folder: Path, preview_dir: Path | None = None) -> dict:
    flat, labels, named, meta, source = segment(folder)
    w, h = flat.width, flat.height
    lab = labels.reshape(h, w)

    substrate = named["substrate"]
    substrate_label = substrate.get("label")
    # Each group carries its own label. Recovering it by matching pixel counts --
    # what this did before -- breaks the moment segment() merges two clusters of
    # one surface: the merged-away label matches nothing, and a count that
    # happens to coincide matches the WRONG group. Modafinil went to 24.2% on
    # exactly that, with a spec that was otherwise correct.
    order = [(role, named[role]["label"], named[role])
             for role in sorted(named)
             if role != "substrate" and named.get(role) is not None]

    fields = []
    # The labels of the fields ACTUALLY emitted, in the same order. verify() used
    # to index its ground truth by `order`, which lists every role considered --
    # so the moment a role was dropped the two indexings slid apart and each
    # field was scored against its neighbour's pixels. It showed up as IoU 0.0 on
    # roles that were plainly present.
    emitted = []
    dropped = 0
    dropped_by_class: dict[str, int] = {}
    kept_mask = np.zeros((h, w), bool)
    tol = SIMPLIFY_TOLERANCE * w
    # PHASE B. Where a folder carries `print_truth.json`, the hand-made label is
    # the ONLY test, and every heuristic below it is bypassed.
    #
    # Those heuristics -- MIN_REGION_FRAC, MIN_FILL_CONTRAST, is_design_field's
    # three escapes, the stricter ink test on `type` and `secondary_*` -- exist
    # because nothing had ever stated, per component, what was printed on the
    # carton and what was lying in front of it. Each is a proxy for that
    # judgement, and each was measured failing: Kamagra's pouch entered through
    # "runs off the face", Xanax Pfizer's shaded board through a 0.090 contrast,
    # Provigil's box lid and the table under it through both.
    #
    # Size has to give way with the rest, and this is the case that proves it:
    # Imovane's ONLY printed field is a blue rule covering 0.67% of its face,
    # below MIN_REGION_FRAC's 0.8%. The threshold would keep that carton at zero
    # fields while the label says exactly what is there. Letting a labelled
    # component through is not tuning a threshold to chase a number -- it is a
    # measurement overruling a proxy for it.
    #
    # Indices line up because `components()` filters then sorts by descending
    # area, so the fitter's list is a PREFIX of the labeller's whenever its
    # floor is coarser. Reading the floor out of the truth file removes even
    # that: both sides enumerate identically, and a key the truth does not carry
    # is a hard stop rather than a silent skip.
    truth = load_truth(folder)
    if truth is None:
        raise SystemExit(
            f"{folder.name}: print_truth.json is absent. Run "
            f"scripts/label_print.py --folder {folder.name} --init, classify "
            f"every component, and check with --verify. Falling back to the "
            f"heuristics is what put a blister in this spec.")
    if truth.get("front_face_px") != meta.get("front_face_px"):
        raise SystemExit(
            f"{folder.name}: print_truth.json was made against different face "
            f"corners. Re-run --init and re-classify; a stale label puts the "
            f"dropped object back in the spec with nothing in the log to say so.")
    label_of = {c["key"]: c.get("class") for c in truth["components"]}
    min_region = int(float(truth["enumerate_min_frac"]) * w * h)

    for role, j, g in order:
        mask = lab == j
        parts = []
        for i, part in enumerate(components(mask, min_region)):
            key = f"{role}#{i}"
            if key not in label_of:
                raise SystemExit(
                    f"{folder.name}: {key} has no label. The partition has moved "
                    f"under print_truth.json -- re-run --init.")
            if label_of[key] != "print":
                # Everything not printed design: an object in the photograph, a
                # letterform, the board split off by a gradient, a logo the owner
                # excluded, or something this vocabulary cannot hold. All of it
                # leaves the spec, and all of it leaves the scored area too --
                # `verify()` reads `~dropped_mask`, so a photograph is neither
                # drawn nor counted as a miss.
                dropped += 1
                dropped_by_class[label_of[key]] = dropped_by_class.get(label_of[key], 0) + 1
                continue
            kept_mask |= part
            outline = trace_outline(part)
            if len(outline) < 8:
                continue
            pts = simplify(outline, tol)
            parts.append({
                "kind": part_kind(pts),
                "area_pct": round(100 * part.sum() / (w * h), 1),
                "smoothness": round(_smoothness(pts), 2),
                "outline": [[round(x / w, 4), round(y / h, 4)] for x, y in pts],
            })
        if not parts:
            continue
        emitted.append((role, j, g))
        fields.append({
            "role": role,
            # Paint order, made explicit. The list has always BEEN ordered --
            # `rasterise()` fills it front to back and every `pixel_agreement`
            # was measured against that -- but the contract never said so, and
            # the driver read the same list into ONE plane where no order
            # exists. Two readings of one record, which is how Adderall's teal
            # block came to be erased in the target and to z-fight in the
            # render. Emitted as the index it already has, so nothing moves;
            # what changes is that the order is now a value the driver can obey
            # rather than a convention it cannot see.
            "z": len(fields),
            "fill": _hex(g["colour"]),
            "coverage_pct": round(100 * mask.sum() / (w * h), 1),
            "parts": parts,
        })

    # What `verify()` is entitled to score: the board, plus the components the
    # label calls print. Everything else in a non-substrate cluster leaves --
    # objects, letterforms, logos, photographs, the board split off by a
    # gradient, AND the residue below the enumeration floor.
    #
    # The residue is why this is computed from `kept_mask` rather than
    # accumulated as parts are dropped. `truth` in verify() marks a whole
    # CLUSTER as its field, so any pixel of that cluster which is neither
    # emitted nor explicitly dropped reads as "the spec should have drawn here"
    # and never can be. Imovane is the case: its blue rule emits correctly and
    # scored 0.145 against 2.7% of unenumerated highlight residue.
    dropped_mask = (lab != substrate_label) & ~kept_mask

    spec = {
        "spec_version": "0.1",
        "sku": meta.get("sku_id"),
        "source_image": source,
        "face_aspect": round(h / w, 4),
        "coordinates": "u across, v down, both 0..1 of the FRONT FACE",
        "substrate": _hex(substrate["colour"]),
        "fields": fields,
        # What the LABEL dropped, by class. This replaces the three counters the
        # heuristics kept (`glyph_components_dropped`, `flat_fields_dropped`,
        # `ink_components_dropped`); those counted which proxy fired, and no
        # proxy fires any more. A spec written before Phase B still carries them,
        # which is the point of keeping `design_spec.v01.json` beside it.
        "components_dropped": dropped,
        "dropped_by_class": dropped_by_class,
        "truth": TRUTH_NAME,
        "excluded": ("manufacturer logos and holographic elements are not "
                     "represented: the owner's decision, so the substrate shows "
                     "through where they sit on the reference"),
    }

    agreement = verify(spec, lab, substrate_label, emitted, w, h, preview_dir, folder,
                       dropped_mask)
    spec["verification"] = agreement

    # This module owns the FIELDS. `measure_type_rows` owns `type_rows`, writes
    # into the same file, and runs after -- so rewriting the file wholesale
    # silently deleted its work, and the eleven manifests came back carrying
    # `"type_rows": {}` the next time Stage 1 ran. Found by diffing the
    # manifests rather than by anything failing, which is the wrong way to find
    # it. Carried forward rather than re-measured: the rows are measured off the
    # same rectified face this fit reads, so re-fitting the fields cannot
    # invalidate them. Re-setting the face CORNERS invalidates both, and that is
    # a different operation.
    spec_path = folder / "design_spec.json"
    if spec_path.exists():
        previous = json.loads(spec_path.read_text(encoding="utf-8"))
        for key in ("type_rows", "type_rows_note"):
            if key in previous:
                spec[key] = previous[key]

    spec_path.write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return spec


def rasterise(spec: dict, w: int, h: int) -> Image.Image:
    """Draw the spec back out. This is what makes the spec checkable."""
    img = Image.new("RGB", (w, h), spec["substrate"])
    d = ImageDraw.Draw(img)
    for f in spec["fields"]:
        for part in f["parts"]:
            poly = [(u * w, v * h) for u, v in part["outline"]]
            if len(poly) >= 3:
                d.polygon(poly, fill=f["fill"])
    return img


def verify(spec, lab, substrate_label, emitted, w, h, preview_dir, folder,
           dropped_mask=None) -> dict:
    """Agreement between the spec's own rasterisation and the segmentation.

    Compared as REGIONS, not colours: each pixel's spec region is recovered by
    drawing the fields into an index image the same way rasterise() draws them,
    so a field whose fill happens to resemble its neighbour cannot score as a
    match it did not earn.
    """
    idx = Image.new("I", (w, h), 255)
    d = ImageDraw.Draw(idx)
    for n, f in enumerate(spec["fields"]):
        for part in f["parts"]:
            poly = [(u * w, v * h) for u, v in part["outline"]]
            if len(poly) >= 3:
                d.polygon(poly, fill=n)
    spec_idx = np.asarray(idx)

    truth = np.full((h, w), 255, dtype=int)
    for n, (role, j, _g) in enumerate(emitted):
        truth[lab == j] = n

    # Glyph pixels are excluded from the score. The spec deliberately does not
    # carry letterforms -- type is drawn from the manifest's strings -- so
    # counting them as disagreement would penalise the spec for being right, and
    # would reward a spec that traced the reference's words back into the fields.
    scored = np.ones((h, w), bool) if dropped_mask is None else ~dropped_mask
    match = float((spec_idx == truth)[scored].mean())
    per_field = {}
    for n, f in enumerate(spec["fields"]):
        t = (truth == n) & scored
        sp = (spec_idx == n) & scored
        union = (t | sp).sum()
        per_field[f["role"]] = round(float((t & sp).sum() / union), 3) if union else None

    if preview_dir is not None:
        preview_dir.mkdir(parents=True, exist_ok=True)
        rasterise(spec, w, h).save(preview_dir / f"{folder.name}.spec.png")

    return {"pixel_agreement": round(match, 4),
            "excluded_as_glyphs_pct": (round(100 * float(dropped_mask.mean()), 2)
                                       if dropped_mask is not None else 0.0),
            "iou_by_field": per_field,
            "vertices": sum(len(p["outline"]) for f in spec["fields"] for p in f["parts"])}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--folder")
    p.add_argument("--all", action="store_true")
    p.add_argument("--preview", action="store_true")
    args = p.parse_args()

    preview = (PROJECT_ROOT / "02_processing" / "reference_measurement") if args.preview else None
    if args.folder:
        folders = [TEMPLATES_DIR / args.folder]
    elif args.all:
        from scripts.make_ocr_fixtures import TEMPLATE_SAMPLE
        folders = [TEMPLATES_DIR / n for n in sorted(TEMPLATE_SAMPLE)]
    else:
        p.error("pass --folder NAME or --all")

    print(f"{'folder':32s} {'fields':>7s} {'verts':>6s} {'agreement':>10s}  IoU by field")
    for folder in folders:
        if not (folder / "metadata.json").exists():
            continue
        spec = fit(folder, preview)
        v = spec["verification"]
        ious = " ".join(f"{k}={x}" for k, x in v["iou_by_field"].items())
        print(f"{folder.name:32s} {len(spec['fields']):7d} {v['vertices']:6d} "
              f"{100 * v['pixel_agreement']:9.1f}%  {ious}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
