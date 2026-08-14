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

# A field is a share of the FACE, not a pixel count: the rectified faces differ
# in size and a fixed count means a different thing on each. 0.8% keeps the
# Cialis dosage block (2.0% of its face) and drops every letterform, which is the
# distinction that matters -- when type fails to separate into its own cluster,
# its strokes land in a colour field and get traced as though they were design.
# They are not: the renderer draws type from the manifest's strings, and a spec
# carrying letter outlines would print the reference's words instead.
MIN_REGION_FRAC = 0.008
LARGE_FIELD_FRAC = 0.03     # past this share of the face, shape stops mattering
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


def is_design_field(outline, w, h) -> bool:
    """Is this component a colour field, or a letter that landed in one?

    Area alone cannot tell them apart -- Cialis's "C" and "a" are larger than its
    dosage block. Two properties can:

    A colour field either RUNS OFF THE FACE (the olive bands enter from the
    edges), or is LARGE, or is a RECTANGLE (the dosage block). A glyph is none of
    those: it floats inside the face, covers about a hundredth of it, and fills
    little of its own bounding box.

    This matters more than tidiness. Type is drawn from the manifest's strings,
    and a spec carrying letter outlines would print the REFERENCE's words on
    every carton built from it -- the exact failure the text-as-geometry rule
    exists to prevent, arriving through the back door.
    """
    xs = [p[0] for p in outline]
    ys = [p[1] for p in outline]
    margin = 0.01 * max(w, h)
    if (min(xs) <= margin or min(ys) <= margin
            or max(xs) >= w - 1 - margin or max(ys) >= h - 1 - margin):
        return True
    area = _area(outline)
    # Size alone is not the test, but past a point it settles the question: no
    # glyph covers a twentieth of a face, and the Cialis white swoosh -- a deeply
    # concave crescent that stops just short of the edge -- covers a quarter of
    # one. Requiring convexity of it dropped it and took the agreement from 88.6%
    # to 73.5%.
    if area >= LARGE_FIELD_FRAC * w * h:
        return True
    # Rectangularity, not convexity. The tracer follows an outer boundary and
    # ignores holes, so a round letter comes back looking convex -- "a" scored
    # 0.85 solidity and survived. How much of its BOUNDING BOX a shape fills
    # separates them cleanly: a printed colour block is a rectangle (0.95+), a
    # letter is not (~0.6).
    bbox = (max(xs) - min(xs)) * (max(ys) - min(ys))
    return bool(bbox > 0 and area / bbox >= 0.85)


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
    substrate_label = None
    order = []
    for role in ("substrate", "brand", "highlight", "type"):
        g = named.get(role)
        if g is None:
            continue
        # recover which k-means label this group is, by matching its pixel count
        for j in range(4):
            if int((lab == j).sum()) == g["n"]:
                if role == "substrate":
                    substrate_label = j
                else:
                    order.append((role, j, g))
                break

    fields = []
    dropped = 0
    dropped_mask = np.zeros((h, w), bool)
    tol = SIMPLIFY_TOLERANCE * w
    min_region = int(MIN_REGION_FRAC * w * h)
    for role, j, g in order:
        mask = lab == j
        if mask.sum() < min_region:
            continue
        parts = []
        for part in components(mask, min_region):
            outline = trace_outline(part)
            if len(outline) < 8:
                continue
            pts = simplify(outline, tol)
            if not is_design_field(pts, w, h):
                dropped += 1
                dropped_mask |= part
                continue
            parts.append({
                "kind": part_kind(pts),
                "area_pct": round(100 * part.sum() / (w * h), 1),
                "smoothness": round(_smoothness(pts), 2),
                "outline": [[round(x / w, 4), round(y / h, 4)] for x, y in pts],
            })
        if not parts:
            continue
        fields.append({
            "role": role,
            "fill": _hex(g["colour"]),
            "coverage_pct": round(100 * mask.sum() / (w * h), 1),
            "parts": parts,
        })

    spec = {
        "spec_version": "0.1",
        "sku": meta.get("sku_id"),
        "source_image": source,
        "face_aspect": round(h / w, 4),
        "coordinates": "u across, v down, both 0..1 of the FRONT FACE",
        "substrate": _hex(substrate["colour"]),
        "fields": fields,
        "glyph_components_dropped": dropped,
        "excluded": ("manufacturer logos and holographic elements are not "
                     "represented: the owner's decision, so the substrate shows "
                     "through where they sit on the reference"),
    }

    agreement = verify(spec, lab, substrate_label, order, w, h, preview_dir, folder,
                       dropped_mask)
    spec["verification"] = agreement
    (folder / "design_spec.json").write_text(
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


def verify(spec, lab, substrate_label, order, w, h, preview_dir, folder,
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
    for n, (role, j, _g) in enumerate(order):
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
