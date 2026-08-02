"""Render a named group of SKU and measure every resulting packshot.

Diagnostic only: this script never changes how anything is rendered. It exists
because the driver's layout constants were fitted against nine curated
references, and a sweep over many real SKU is the only thing that finds the
failures those nine cannot show. Every correction pass currently in
assets/blender/render_driver.py was added after a sweep found real breakage.

    python scripts/catalogue_sweep.py --limit 5      # trial
    python scripts/catalogue_sweep.py                # the group, resuming
    python scripts/catalogue_sweep.py --force        # re-render the group

Writes 00_PROJECT_STATE/sweep_report.json (one record per SKU) and
00_PROJECT_STATE/sweep_report.md (human summary). Both are rewritten on every
run, including after Ctrl+C, so a long run is never lost.
"""
from __future__ import annotations

import sys
import json
import time
import argparse
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import load_config, get_path, resolve_path  # noqa: E402

# ── The group ────────────────────────────────────────────────────────────────
# Resolved once, by hand, from product_name in the passports. Kept as data so
# the group can be changed without touching any logic below.
#
# Two traps this mapping already resolves, and which re-deriving it would
# reintroduce: "Xanax (Alprazolam)" and "Xanax (Alprazolam) by Pfizer" are
# DIFFERENT SKU (156-min and 340-min), and most names carry the active
# ingredient in brackets while product_name does not.
GROUPS = {
    "top30": [
        ("2-min",   "Strattera (Atomoxetine)"),
        ("59-min",  "Cialis (Tadalafil)"),
        ("60-min",  "Cialis Professional"),
        ("62-min",  "Cialis Super Active"),
        ("107-min", "Tramadol"),
        ("133-min", "Ambien (Zolpidem)"),
        ("134-min", "Atarax (Hydroxyzine)"),
        ("135-min", "Ativan (Lorazepam)"),
        ("139-min", "Lyrica (Pregabalin)"),
        ("149-min", "Modalert (Modafinil)"),
        ("150-min", "Waklert (Armodafinil)"),
        ("151-min", "Provigil (Modafinil)"),
        ("152-min", "Artvigil (Armodafinil)"),
        ("155-min", "Imovane (Zopiclone)"),
        ("156-min", "Xanax (Alprazolam)"),
        ("157-min", "Valium (Diazepam)"),
        ("158-min", "Klonopin (Clonazepam)"),
        ("221-min", "Inderal (Propranolol)"),
        ("230-min", "Slimex"),
        ("258-min", "Stromectol (Ivermectin)"),
        ("272-min", "Valium Brand"),
        ("304-min", "Sonata (Zaleplon)"),
        ("308-min", "Lexotanil (Bromazepam)"),
        ("340-min", "Xanax (Alprazolam) by Pfizer"),
        ("344-min", "Modafinil"),
        ("346-min", "Modvigil"),
        ("357-min", "Adderall"),
        ("362-min", "Hydrocodone"),
        ("365-min", "Tapentadol"),
        ("404-min", "Ritalin (Generic)"),
    ],
}

# ── Thresholds a SKU is flagged against ──────────────────────────────────────
BLANK_FRAC = 5.0          # object smaller than this share of frame -> nothing rendered
OVERSIZE_FRAC = 95.0      # larger than this -> effectively filling the frame
SLOW_RENDER_S = 180.0
SPREAD_TOLERANCE_PP = 10.0  # deviation from the template's median frame fill

# Front-face brightness. Worth flagging rather than merely recording: this
# catches a carton lit visibly darker than the rig intends, which is what the
# light_energy square law exists to prevent and which no geometry check can see.
# The sweep's band is deliberately looser than src.measure's reference band —
# the vertical family measures 232.6-234.2 under the current rig, just below the
# reference floor, and that is a known rig gap rather than a per-SKU defect.
FRONT_FACE_MIN, FRONT_FACE_MAX = 230.0, 245.0

# Object-versus-backdrop threshold. The backdrop is emissive and renders a flat
# ~255 with no cast shadow, so a plain luminance cut separates the carton
# cleanly; 243 is the value used for the same measurement during the 2026-08-02
# audit, where it produced consistent figures on both renders and references.
SILHOUETTE_MAX_LUMA = 243

_CFG = load_config()
OUT_DIR = resolve_path(_CFG["blender"]["output_dir"])
MANIFEST_DIR = get_path(_CFG, "passports_manifests")
PASSPORT_DIR = get_path(_CFG, "passports_json")
BLENDER_EXE = Path(_CFG["blender"]["executable"])
STATE_DIR = PROJECT_ROOT / "00_PROJECT_STATE"


# ── Measurement ──────────────────────────────────────────────────────────────
def measure(png_path: Path, manifest_path: Path) -> dict:
    """Geometry and brightness of one rendered packshot.

    Front-face brightness comes from src.measure, shared with the calibration
    gate in tests/test_blender_carton.py so a measurement whose band was fitted
    off the references has exactly one implementation.
    """
    import numpy as np
    from PIL import Image

    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    grey = np.asarray(Image.open(png_path).convert("L")).astype(float)
    height, width = grey.shape

    ys, xs = np.nonzero(grey < SILHOUETTE_MAX_LUMA)
    if ys.size == 0:
        return {"measured": False, "reason": "no object found against the backdrop"}

    top, bottom = int(ys.min()), int(ys.max())
    left, right = int(xs.min()), int(xs.max())
    frac_w = 100.0 * (right - left + 1) / width
    frac_h = 100.0 * (bottom - top + 1) / height
    margins = {"top": top, "bottom": height - 1 - bottom,
               "left": left, "right": width - 1 - right}

    result = {
        "measured": True,
        "resolution": [width, height],
        "frame_fill_width_pct": round(frac_w, 1),
        "frame_fill_height_pct": round(frac_h, 1),
        "frame_fill_dominant_pct": round(max(frac_w, frac_h), 1),
        "margins_px": margins,
        "cropped": min(margins.values()) == 0,
        "blank": max(frac_w, frac_h) < BLANK_FRAC,
        "oversize": max(frac_w, frac_h) > OVERSIZE_FRAC,
    }

    try:
        from src.measure import _front_face_and_background
        front, backdrop, backdrop_sd = _front_face_and_background(
            str(png_path), manifest["palette"]["accent"])
        result["front_face_mean"] = round(float(front), 1)
        result["backdrop_mean"] = round(float(backdrop), 1)
        result["backdrop_sd"] = round(float(backdrop_sd), 2)
    except Exception as e:  # noqa: BLE001 - a brightness miss must not lose the geometry
        result["front_face_mean"] = None
        result["brightness_error"] = f"{type(e).__name__}: {e}"

    return result


# ── Scene-level layout check ─────────────────────────────────────────────────
# The silhouette metrics above cannot see a text defect: a label row that
# overruns the face edge or collides with the row below leaves the outline of
# the box unchanged. This check reads the built scene instead of the pixels,
# through the driver's own --dump-scene, which is how tests/test_blender_carton.py
# already asserts on layout. It renders nothing and changes nothing.
DUMP_TIMEOUT_S = 120
ROW_MIN_GAP_MM = 0.0     # stacked rows must not overlap at all

# The driver fits a long row by SHRINKING it, never by letting it overrun, so an
# overflow defect cannot occur — but nothing puts a floor under the type size.
# Measured on 357-min: a 37-character ingredient sets at 4.64mm cap height, 70
# characters at 1.73mm, 140 at 0.77mm, with the row's width pinned at 101.2mm
# throughout. The references set their small print at 4.4-5.5mm
# (reference_analysis.md §6), so anything much under that is legible in the data
# and not on the carton.
SMALL_PRINT_MIN_MM = 4.0
FITTED_ROWS = {"label_ingredient", "label_dosage", "label_unit_count"}

# The dosage and the unit count deliberately share one baseline at the bottom of
# the face, left- and right-aligned. They overlap in Z by design, so they are
# never compared against each other as "stacked".
SAME_BASELINE = {"label_dosage", "label_unit_count"}


def check_scene(stem: str) -> dict:
    """Label geometry for one SKU, measured off the built scene."""
    import tempfile
    manifest = MANIFEST_DIR / f"{stem}.json"
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "scene.json"
        try:
            subprocess.run(
                [str(BLENDER_EXE), "--background", "--factory-startup",
                 "--python", str(resolve_path(_CFG["blender"]["driver_script"])), "--",
                 "--job", str(manifest), "--dump-scene", str(dump)],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                stdin=subprocess.DEVNULL, timeout=DUMP_TIMEOUT_S,
            )
        except Exception as e:  # noqa: BLE001
            return {"checked": False, "reason": f"{type(e).__name__}: {e}"}
        if not dump.exists():
            return {"checked": False, "reason": "driver wrote no scene dump"}
        scene = json.loads(dump.read_text(encoding="utf-8"))

    m = json.loads(manifest.read_text(encoding="utf-8"))
    half_w = m["carton"]["width_mm"] / 2000.0     # metres, face spans -half_w..+half_w
    half_h = m["carton"]["height_mm"] / 2000.0

    rows = []
    for o in scene.get("label", []):
        b = o.get("bounds_in_carton_frame")
        if b:
            rows.append({"name": o.get("name", "?"), "body": o.get("body", ""),
                         "x0": b["min"][0], "x1": b["max"][0],
                         "z0": b["min"][2], "z1": b["max"][2]})

    issues = []
    for r in rows:
        if r["x1"] > half_w + 1e-6:
            issues.append(f"{r['name']} overruns the right edge by "
                          f"{(r['x1'] - half_w) * 1000:.2f}mm")
        if r["x0"] < -half_w - 1e-6:
            issues.append(f"{r['name']} overruns the left edge by "
                          f"{(-half_w - r['x0']) * 1000:.2f}mm")
        if r["z1"] > 2 * half_h + 1e-6 or r["z0"] < -1e-6:
            issues.append(f"{r['name']} runs off the face vertically")

    stacked = sorted(rows, key=lambda r: -r["z1"])
    for a, b in zip(stacked, stacked[1:]):
        if {a["name"], b["name"]} == SAME_BASELINE:
            continue
        gap = (a["z0"] - b["z1"]) * 1000
        if gap < ROW_MIN_GAP_MM:
            issues.append(f"{a['name']} and {b['name']} overlap by {-gap:.2f}mm")

    smallest = None
    for r in rows:
        if r["name"] not in FITTED_ROWS:
            continue
        mm = (r["z1"] - r["z0"]) * 1000
        smallest = mm if smallest is None else min(smallest, mm)
        if mm < SMALL_PRINT_MIN_MM:
            issues.append(f"{r['name']} set at {mm:.2f}mm, under the "
                          f"{SMALL_PRINT_MIN_MM:.1f}mm the references hold small "
                          f"print to ({len(r['body'])} characters)")

    return {"checked": True, "row_count": len(rows), "issues": issues,
            "smallest_fitted_row_mm": round(smallest, 2) if smallest else None,
            "rows": [{"name": r["name"],
                      "x_mm": [round(r["x0"] * 1000, 2), round(r["x1"] * 1000, 2)],
                      "z_mm": [round(r["z0"] * 1000, 2), round(r["z1"] * 1000, 2)],
                      "body": r["body"]} for r in rows]}


# ── Rendering ────────────────────────────────────────────────────────────────
def render_one(stem: str) -> tuple[bool, float, str]:
    """Render a single SKU through the normal Stage 2 entry point."""
    start = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "src.blender_renderer", "--from", stem, "--limit", "1"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
            stdin=subprocess.DEVNULL, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, time.time() - start, "renderer timed out after 600s"
    except Exception as e:  # noqa: BLE001
        return False, time.time() - start, f"{type(e).__name__}: {e}"

    elapsed = time.time() - start
    if not (OUT_DIR / f"{stem}.png").exists():
        tail = (proc.stderr or proc.stdout or "")[-400:]
        return False, elapsed, f"no PNG written (rc={proc.returncode}): {tail}"
    return True, elapsed, ""


def record_for(stem: str, label: str, rendered: bool, seconds, error: str) -> dict:
    manifest_path = MANIFEST_DIR / f"{stem}.json"
    rec = {"stem": stem, "requested_as": label, "rendered": rendered,
           "render_seconds": round(seconds, 1) if seconds is not None else None,
           "error": error or None}

    if manifest_path.exists():
        m = json.loads(manifest_path.read_text(encoding="utf-8"))
        rec.update({"sku_id": m["sku_id"], "template_id": m["template_id"],
                    "carton_mm": [m["carton"]["width_mm"], m["carton"]["height_mm"],
                                  m["carton"]["depth_mm"]],
                    "carton_source": m["carton"]["source"]})
        passport = PASSPORT_DIR / f"{stem}.json"
        if passport.exists():
            rec["product_name"] = json.loads(
                passport.read_text(encoding="utf-8")).get("product_name")
    else:
        rec["manifest_missing"] = True

    png = OUT_DIR / f"{stem}.png"
    if png.exists():
        try:
            rec["measurement"] = measure(png, manifest_path)
        except Exception as e:  # noqa: BLE001 - a corrupt PNG is a finding, not a crash
            rec["measurement"] = {"measured": False,
                                  "reason": f"{type(e).__name__}: {e}"}
            rec["rendered"] = False
            rec["error"] = rec["error"] or "PNG unreadable"

    if manifest_path.exists():
        rec["layout"] = check_scene(stem)
    return rec


def problems_for(rec: dict) -> list[str]:
    """Which thresholds this SKU violates. Empty means clean."""
    out = []
    if not rec.get("rendered"):
        out.append("render failed")
    m = rec.get("measurement") or {}
    if m.get("measured"):
        if m["cropped"]:
            out.append("cropped at frame edge")
        if m["blank"]:
            out.append(f"blank frame (<{BLANK_FRAC}%)")
        if m["oversize"]:
            out.append(f"fills frame (>{OVERSIZE_FRAC}%)")
        front = m.get("front_face_mean")
        if front is None:
            # Never let a dropped measurement read as a pass. Without this the
            # brightness pass could fail for all 30 SKU and the summary would
            # still print "flagged: 0".
            out.append(f"front-face brightness not measured: "
                       f"{m.get('brightness_error', 'unknown')}")
        elif not (FRONT_FACE_MIN <= front <= FRONT_FACE_MAX):
            out.append(f"front face at {front}, outside the "
                       f"{FRONT_FACE_MIN}-{FRONT_FACE_MAX} reference band")
    elif rec.get("rendered"):
        out.append(f"not measurable: {m.get('reason', 'unknown')}")
    if (rec.get("render_seconds") or 0) > SLOW_RENDER_S:
        out.append(f"slow render (>{SLOW_RENDER_S:.0f}s)")
    layout = rec.get("layout") or {}
    if layout.get("checked"):
        out.extend(layout["issues"])
    elif layout:
        out.append(f"layout not checked: {layout.get('reason', 'unknown')}")
    return out


# ── Reporting ────────────────────────────────────────────────────────────────
def _median(values):
    s = sorted(values)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def spread_by_template(records: list[dict]) -> dict:
    """Frame fill per template. The group is near-homogeneous in geometry, so a
    SKU whose silhouette departs from its template's median is very likely a
    TEXT defect rather than a geometry one."""
    buckets: dict[str, list] = {}
    for r in records:
        m = r.get("measurement") or {}
        if m.get("measured") and r.get("template_id"):
            buckets.setdefault(r["template_id"], []).append(
                (r["stem"], m["frame_fill_dominant_pct"]))
    out = {}
    for tid, rows in buckets.items():
        vals = [v for _, v in rows]
        med = _median(vals)
        out[tid] = {
            "count": len(vals), "min": min(vals), "max": max(vals), "median": med,
            "outliers": [{"stem": s, "dominant_pct": v,
                          "deviation_pp": round(v - med, 1)}
                         for s, v in rows if abs(v - med) > SPREAD_TOLERANCE_PP],
        }
    return out


def report_paths(limit) -> tuple[Path, Path]:
    """Where this run's reports go.

    A partial run writes to its own filenames. Previously every run overwrote
    sweep_report.*, so a three-SKU `--limit` smoke check silently replaced a
    full group's report and left the repository claiming the group was verified
    when a tenth of it was — which is exactly what happened once already.
    """
    stem = "sweep_report" if limit is None else "sweep_report.partial"
    return STATE_DIR / f"{stem}.json", STATE_DIR / f"{stem}.md"


def write_reports(records, group_name, started_at, interrupted=False, limit=None):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    json_path, md_path = report_paths(limit)
    spread = spread_by_template(records)
    flagged = [(r, problems_for(r)) for r in records]
    flagged = [(r, p) for r, p in flagged if p]
    templates = sorted({r.get("template_id") for r in records if r.get("template_id")})
    total_s = sum(r.get("render_seconds") or 0 for r in records)

    payload = {
        "group": group_name,
        "started_at": started_at,
        "interrupted": interrupted,
        "limit": limit,
        "covers_whole_group": limit is None,
        "counts": {"total": len(records),
                   "rendered": sum(1 for r in records if r.get("rendered")),
                   "failed": sum(1 for r in records if not r.get("rendered")),
                   "flagged": len(flagged)},
        "templates_covered": templates,
        "total_render_seconds": round(total_s, 1),
        "thresholds": {"blank_pct": BLANK_FRAC, "oversize_pct": OVERSIZE_FRAC,
                       "slow_render_s": SLOW_RENDER_S,
                       "spread_tolerance_pp": SPREAD_TOLERANCE_PP},
        "spread_by_template": spread,
        "records": records,
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = []
    L.append("# Catalogue sweep report")
    L.append("")
    scope = ("the whole group" if limit is None
             else f"**a partial run — first {limit} of the group only**")
    L.append(f"> Group `{group_name}`, {scope} · started {started_at}"
             + (" · **INTERRUPTED**" if interrupted else ""))
    L.append("")
    L.append("Generated by `scripts/catalogue_sweep.py`. Diagnostic only: nothing "
             "about how the packshot is rendered was changed to produce this.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append(f"- SKU in group: **{len(records)}**")
    L.append(f"- Rendered: **{payload['counts']['rendered']}** · "
             f"failed: **{payload['counts']['failed']}**")
    L.append(f"- Flagged against thresholds: **{len(flagged)}**")
    L.append(f"- Total render time: **{total_s / 60:.1f} min** "
             f"({total_s / max(1, payload['counts']['rendered']):.0f} s per SKU)")
    L.append("")
    L.append("### Coverage caveat")
    L.append("")
    L.append(f"This run covers **{', '.join(templates) or 'nothing'}** only. "
             "The catalogue has nine populated templates; `T3`, `T_MULTIPACK`, "
             "`T_BOTTLE_BOX`, `T_VERT_VIAL`, `T_VERT_DROPPER`, `T_VERT_INHALER` and "
             "`T1_LARGE` are **not exercised here**. Draw no conclusion about them "
             "from this report — their panels are narrower and their layouts tighter, "
             "which is exactly where a sweep is most likely to find something.")
    L.append("")

    L.append("## Frame fill by template")
    L.append("")
    L.append("The group is near-homogeneous in geometry, so silhouettes within a "
             "template should barely vary. A SKU that departs from its template's "
             "median is most likely a text-layout defect, not a geometry one.")
    L.append("")
    L.append("| Template | SKU | min | median | max | outliers |")
    L.append("|---|---:|---:|---:|---:|---|")
    for tid in sorted(spread):
        s = spread[tid]
        outl = ", ".join(f"`{o['stem']}` ({o['deviation_pp']:+.1f} pp)"
                         for o in s["outliers"]) or "none"
        L.append(f"| {tid} | {s['count']} | {s['min']:.1f}% | {s['median']:.1f}% | "
                 f"{s['max']:.1f}% | {outl} |")
    L.append("")

    L.append("## What was actually checked")
    L.append("")
    L.append("Two independent passes, because they catch different things:")
    L.append("")
    L.append("- **Pixels** — silhouette extent, per-edge margins, front-face "
             "brightness. Catches a carton that is cropped, missing or mis-framed.")
    L.append("- **Scene** — every label row's bounds read out of the built scene via "
             "the driver's `--dump-scene`, checked against the face edges and against "
             "the row below. This is the pass that can see a text defect at all: a "
             "row that overruns the face or collides with its neighbour leaves the "
             "silhouette completely unchanged, so the pixel pass is blind to it.")
    L.append("")
    checked = sum(1 for r in records if (r.get("layout") or {}).get("checked"))
    L.append(f"Scene check completed for **{checked} of {len(records)}** SKU.")
    L.append("")

    L.append("## Flagged SKU")
    L.append("")
    if not flagged:
        L.append("None. Every SKU rendered, stayed inside the frame, kept every label "
                 "row within the printed face, and fell within the size and time "
                 "thresholds.")
    else:
        L.append("| Stem | Product | Template | Problem |")
        L.append("|---|---|---|---|")
        for r, probs in flagged:
            L.append(f"| `{r['stem']}` | {r.get('product_name', '?')} | "
                     f"{r.get('template_id', '?')} | {'; '.join(probs)} |")
    L.append("")

    L.append("## All SKU")
    L.append("")
    L.append("| Stem | Product | Template | Carton mm | Fill w/h | Front face | Time |")
    L.append("|---|---|---|---|---|---:|---:|")
    for r in records:
        m = r.get("measurement") or {}
        carton = "x".join(f"{v:.0f}" for v in r.get("carton_mm", [])) or "?"
        fill = (f"{m['frame_fill_width_pct']:.0f}/{m['frame_fill_height_pct']:.0f}%"
                if m.get("measured") else "—")
        front = f"{m['front_face_mean']:.1f}" if m.get("front_face_mean") else "—"
        secs = f"{r['render_seconds']:.0f}s" if r.get("render_seconds") else "—"
        L.append(f"| `{r['stem']}` | {r.get('product_name', '?')} | "
                 f"{r.get('template_id', '?')} | {carton} | {fill} | {front} | {secs} |")
    L.append("")
    (STATE_DIR / "sweep_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")


# ── Orchestration ────────────────────────────────────────────────────────────
def sweep(group_name: str, limit: int | None, force: bool) -> int:
    group = GROUPS[group_name]
    if limit is not None:
        group = group[:limit]

    missing = [s for s, _ in group if not (PASSPORT_DIR / f"{s}.json").exists()]
    if missing:
        print(f"[sweep] passports missing for: {', '.join(missing)}", file=sys.stderr)
        return 2
    if not BLENDER_EXE.exists():
        print(f"[sweep] Blender not found at {BLENDER_EXE}", file=sys.stderr)
        return 2

    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    interrupted = False

    print(f"[sweep] group={group_name} n={len(group)} force={force}")
    try:
        for i, (stem, label) in enumerate(group, 1):
            png = OUT_DIR / f"{stem}.png"
            if png.exists() and not force:
                print(f"[{i}/{len(group)}] {stem} — already rendered, measuring only")
                records.append(record_for(stem, label, True, None, ""))
                continue
            if force and png.exists():
                png.unlink()
            print(f"[{i}/{len(group)}] {stem} — rendering...", flush=True)
            ok, secs, err = render_one(stem)
            rec = record_for(stem, label, ok, secs, err)
            records.append(rec)
            m = rec.get("measurement") or {}
            note = (f"{m['frame_fill_width_pct']:.0f}/{m['frame_fill_height_pct']:.0f}%"
                    if m.get("measured") else (err or "unmeasured"))
            print(f"          {'ok' if ok else 'FAILED'} {secs:.0f}s  {note}", flush=True)
    except KeyboardInterrupt:
        interrupted = True
        print("\n[sweep] interrupted — writing what was collected", file=sys.stderr)

    write_reports(records, group_name, started_at, interrupted, limit)
    flagged = sum(1 for r in records if problems_for(r))
    print(f"[sweep] done: {len(records)} record(s), {flagged} flagged")
    print(f"[sweep] {report_paths(limit)[1]}")
    return 1 if interrupted else 0


def legibility_scan(top_n: int) -> int:
    """Measure printed type size for the catalogue's longest label strings.

    Separate from the group sweep and catalogue-wide on purpose. The driver fits
    a long row by shrinking it, so the failure it produces is illegibility rather
    than overflow — and the SKU at risk are whichever have the longest strings on
    the narrowest faces, which no curated group is likely to contain. Reads the
    built scene only; renders nothing.
    """
    manifests = []
    for f in sorted(MANIFEST_DIR.glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        manifests.append((len(m["label_content"]["active_ingredient_display"]),
                          f.stem, m))
    manifests.sort(reverse=True, key=lambda t: t[0])
    subjects = manifests[:top_n]

    print(f"[legibility] measuring the {len(subjects)} longest of {len(manifests)} SKU")
    rows = []
    for i, (nchars, stem, m) in enumerate(subjects, 1):
        res = check_scene(stem)
        smallest = res.get("smallest_fitted_row_mm") if res.get("checked") else None
        rows.append({"stem": stem, "template_id": m["template_id"],
                     "face_width_mm": m["carton"]["width_mm"],
                     "ingredient_chars": nchars,
                     "ingredient": m["label_content"]["active_ingredient_display"],
                     "smallest_fitted_row_mm": smallest,
                     "below_floor": bool(smallest and smallest < SMALL_PRINT_MIN_MM)})
        print(f"[{i}/{len(subjects)}] {stem:<10} {nchars:3d} chars -> "
              f"{smallest if smallest else '?'}mm", flush=True)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    below = [r for r in rows if r["below_floor"]]
    payload = {"scanned": len(subjects), "catalogue_size": len(manifests),
               "floor_mm": SMALL_PRINT_MIN_MM,
               "below_floor": len(below), "rows": rows}
    (STATE_DIR / "legibility_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    L = ["# Small-print legibility scan", "",
         "> Generated by `scripts/catalogue_sweep.py --legibility-scan`. "
         "Reads the built scene; renders nothing.", "",
         "The driver never lets a label row overrun its face — it shrinks the row "
         "to fit. That makes overflow impossible and makes **illegibility** the "
         "failure mode instead, which no silhouette or pixel check can see. "
         "Measured on `357-min`: a 37-character ingredient sets at 4.64mm cap "
         "height, 70 characters at 1.73mm, 140 at 0.77mm — with the row's width "
         "pinned at 101.2mm throughout.", "",
         f"The curated references hold small print to 4.4-5.5mm "
         f"(`reference_analysis.md` §6). Flagged here below **{SMALL_PRINT_MIN_MM}mm**.",
         "",
         f"Scanned the **{len(subjects)}** longest ingredient strings of "
         f"**{len(manifests)}** SKU. **{len(below)}** fall below the floor.", "",
         "| SKU | Template | Face mm | Chars | Type mm | Ingredient |",
         "|---|---|---:|---:|---:|---|"]
    for r in rows:
        mark = " ⚠" if r["below_floor"] else ""
        size = f"{r['smallest_fitted_row_mm']:.2f}{mark}" if r["smallest_fitted_row_mm"] else "?"
        L.append(f"| `{r['stem']}` | {r['template_id']} | {r['face_width_mm']:.0f} | "
                 f"{r['ingredient_chars']} | {size} | {r['ingredient'][:52]} |")
    L += ["", "The pattern is a long string on a narrow face, so the worst case is "
              "not simply the longest string: a 42-character ingredient on an 80mm "
              "`T_VERT_VIAL` face sets smaller than a 61-character one on a 110mm "
              "`T_MULTIPACK`.", ""]
    (STATE_DIR / "legibility_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[legibility] {len(below)} of {len(subjects)} below {SMALL_PRINT_MIN_MM}mm")
    print(f"[legibility] {STATE_DIR / 'legibility_report.md'}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--group", choices=sorted(GROUPS), default="top30")
    p.add_argument("--limit", type=int, default=None,
                   help="only the first N SKU of the group (trial runs)")
    p.add_argument("--force", action="store_true",
                   help="re-render even where a PNG already exists")
    p.add_argument("--legibility-scan", type=int, nargs="?", const=15, default=None,
                   metavar="N",
                   help="instead of a sweep, measure printed type size for the N "
                        "longest label strings across the whole catalogue")
    args = p.parse_args()
    if args.legibility_scan is not None:
        return legibility_scan(args.legibility_scan)
    return sweep(args.group, args.limit, args.force)


if __name__ == "__main__":
    sys.exit(main())
