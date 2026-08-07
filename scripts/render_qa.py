"""
PHARMAGEN PRO — Render QA (OCR Post-Render Quality Assurance)
Version: 2.0 (2026-08-07) — P8.0

PURPOSE:
    Non-blocking diagnostic module. Runs after image generation.
    For each PNG in the processed-images directory, extracts text via OCR
    and cross-references the corresponding RENDER MANIFEST -- the contract
    the renderer actually consumed, not the passport it was built from -- to
    check that each of `label_content.brand_name_display`,
    `active_ingredient_display`, `dosage_display` and `unit_count_display` is
    recognisable in the rendered pixels.

    Deskews the carton's front face first when the renderer left a
    `{stem}.view.json` sidecar (see src/deskew.py): raw OCR on the
    27.5-35 degree rotated carton misses almost everything, so scoring the
    skewed frame would report false failures on correct packshots. Falls
    back to the raw frame, flagged, when no sidecar exists or deskewing
    fails.

    All directories default from config.yaml (--dir, --manifests, --report
    all override it). --dir in particular follows render.engine: the
    blender engine's own output directory when engine is "blender", Gemini's
    raw-render directory otherwise -- the two engines' output is segregated on
    disk, so this script picks the one matching the configured engine rather
    than a single hardcoded folder.

    Outputs a Markdown report to 06_docs/RENDER_QA_REPORT.md by default.
    A diagnostic, never a gate: status is one of OK / WARN / UNAVAILABLE /
    NO_MANIFEST. There is no failing status that blocks the pipeline.

USAGE:
    python scripts/render_qa.py
    python scripts/render_qa.py --dir 02_processing/blender_test_renders
    python scripts/render_qa.py --manifests 04_passports/render_manifests
    python scripts/render_qa.py --limit 20

DEPENDENCIES:
    pip install pytesseract Pillow
    Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")

import json
import re
import os
import argparse
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

# Resolved through the config, not hardcoded: this fork remapped every path onto
# numbered folders, and a stale default does not fail loudly -- it finds no
# images and reports a clean run over nothing.
# `python scripts/render_qa.py` puts scripts/ (not the project root) at
# sys.path[0], so src wouldn't be importable without this -- the same pattern
# scripts/catalogue_sweep.py and scripts/generate_architecture_snapshot.py use.
_SCRIPT_ROOT = Path(__file__).resolve().parent.parent
if str(_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_ROOT))

from src.utils import load_config, get_path, resolve_path, PROJECT_ROOT  # noqa: E402

_CFG = load_config()
# Source follows the selected engine. Blender writes to its own directory
# precisely so resume and Stage 3 cannot confuse the two engines' output.
_ENGINE = (_CFG.get("render") or {}).get("engine", "gemini")
DEFAULT_PROCESSED_DIR = (resolve_path(_CFG["blender"]["output_dir"])
                         if _ENGINE == "blender"
                         else get_path(_CFG, "renders_raw"))
DEFAULT_MANIFESTS_DIR  = get_path(_CFG, "passports_manifests")
DEFAULT_REPORT_PATH    = PROJECT_ROOT / "06_docs" / "RENDER_QA_REPORT.md"

# Minimum OCR text length to consider extraction valid
MIN_OCR_TEXT_LENGTH = 20

# ─────────────────────────────────────────────────────────────────────────────
# OCR BACKEND
# ─────────────────────────────────────────────────────────────────────────────

_TESSERACT_AVAILABLE = False
_TESSERACT_ERROR = ""

try:
    import pytesseract
    from PIL import Image
    import shutil

    # Quick check if tesseract is in PATH, if not try default Windows paths
    if not shutil.which("tesseract"):
        possible_paths = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("LocalAppData", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ]
        for p in possible_paths:
            if p.exists():
                pytesseract.pytesseract.tesseract_cmd = str(p)
                break

    # Quick sanity check
    pytesseract.get_tesseract_version()
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_ERROR = "pytesseract not installed. Run: pip install pytesseract"
except Exception as e:
    _TESSERACT_ERROR = f"Tesseract binary not found or not configured: {e}"


def extract_text(image) -> tuple[bool, str]:
    """Run OCR on a path or an already-loaded image.

    Returns (success, text_or_error).
    """
    if not _TESSERACT_AVAILABLE:
        return False, _TESSERACT_ERROR
    try:
        # Imported locally on purpose. render_qa.py imports PIL.Image inside the
        # same try block as pytesseract, so on a machine without pytesseract the
        # module-level name never exists -- and isinstance(image, Image.Image)
        # would raise NameError instead of reporting "OCR unavailable".
        from PIL import Image as _Image
        img = image if isinstance(image, _Image.Image) else _Image.open(image)
        # Use --psm 6 (uniform text block) for better coverage on a label grid
        text = pytesseract.image_to_string(img, config="--psm 6")
        return True, text
    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# MANIFEST + VIEW LOADERS
# ─────────────────────────────────────────────────────────────────────────────

def load_manifest(sku_stem: str, manifests_dir: Path) -> dict | None:
    """The render manifest for a SKU -- the contract the renderer consumed.

    Checking against the passport instead would compare the pixels to a
    document the renderer never read; where the two disagree, that is a false
    alarm rather than a finding.
    """
    path = manifests_dir / f"{sku_stem}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def load_view(image_path: Path) -> dict | None:
    """The renderer's sidecar saying where the printed faces landed."""
    path = image_path.with_suffix(".view.json")
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# QA CHECKS
# ─────────────────────────────────────────────────────────────────────────────

def extract_numeric(s: str) -> str:
    """Extract the first numeric value (including decimals) from a string."""
    m = re.search(r"\d+(?:[.,]\d+)?", s or "")
    return m.group(0).replace(",", ".") if m else ""


# Which manifest fields are checked, and what OCR has to contain for a hit.
# A display string may carry punctuation or a unit the recogniser mangles, so
# the significant token is matched rather than the whole string.
CHECKED_FIELDS = ("brand_name_display", "active_ingredient_display",
                  "dosage_display", "unit_count_display")


def _field_present(expected: str, text: str) -> bool:
    """Is *expected* recognisable in *text*?

    Numeric fields match on a DIGIT boundary, not a \\b WORD boundary --
    '(?<!\\d)40(?!\\d)', never '\\b40\\b'. Every dosage/unit value in this
    catalogue glues its unit straight onto the number ("40mg", "0.025%"),
    and '\\b' cannot separate a digit from a following letter: '0' and 'm'
    are both word characters, so '\\b40\\b' finds no boundary inside "40mg"
    and never matches it, even though "40mg" is right there on the page.
    A digit boundary keeps the property a plain substring match would lose:
    '5' must not match inside '500', nor '10' inside '100'.

    Word fields require EVERY significant token (length >= 3), not just the
    longest one. Matching only the longest token is a false-positive trap
    whenever two checked fields share a word -- e.g. brand_name_display
    "Atomoxetine Generic" and active_ingredient_display "Atomoxetine": the
    longest token of the brand field is "Atomoxetine" itself, so the brand
    field would read as "found" purely because the separately-checked
    ingredient field put "Atomoxetine" on the page, even if "Generic" was
    never printed at all.
    """
    expected = (expected or "").strip()
    if not expected:
        return False
    num = extract_numeric(expected)
    if num and num == expected.split()[0].rstrip("mgMG%"):
        return re.search(rf"(?<!\d){re.escape(num)}(?!\d)", text) is not None
    tokens = [t for t in re.split(r"[^\w.%-]+", expected) if len(t) >= 3]
    if not tokens:
        return expected.lower() in text.lower()
    if all(t.lower() in text.lower() for t in tokens):
        return True
    if num:
        return re.search(rf"(?<!\d){re.escape(num)}(?!\d)", text) is not None
    return False


def check_image(image_path: Path, manifest: dict, view: dict | None = None) -> dict:
    """OCR one render and score it against the manifest that produced it.

    Deskews first when the renderer supplied face corners: on a 27.5-35 degree
    carton, raw OCR misses almost everything (measured 2026-08-03), so scoring a
    skewed frame would report false failures on correct packshots.

    Never returns a hard failure. This is a diagnostic; the module's contract is
    that it does not block the pipeline.
    """
    label = (manifest.get("label_content") or {})
    expected = {f: str(label.get(f, "") or "") for f in CHECKED_FIELDS}
    result = {
        "sku": image_path.stem,
        "ocr_ok": False, "ocr_error": "", "deskewed": False,
        "fields": {}, "found": 0,
        "expected": sum(1 for v in expected.values() if v),
        "confidence": None, "status": "UNKNOWN", "flags": [],
    }

    source = image_path
    corners = (view or {}).get("front_face_px")
    if corners:
        try:
            from src.deskew import flatten_face
            source = flatten_face(image_path, corners)
            result["deskewed"] = True
        except Exception as e:
            result["flags"].append(f"deskew failed, reading the raw frame: {e}")
    else:
        result["flags"].append(
            "no {stem}.view.json; reading the raw frame, where a rotated "
            "carton reads poorly")

    ok, text = extract_text(source)
    result["ocr_ok"] = ok
    if not ok:
        result["ocr_error"] = text
        result["status"] = "UNAVAILABLE"
        result["flags"].append(f"OCR unavailable: {text[:80]}")
        return result

    result["fields"] = {f: _field_present(expected[f], text) if expected[f] else None
                        for f in CHECKED_FIELDS}
    hits = sum(1 for v in result["fields"].values() if v)
    result["found"] = hits
    result["confidence"] = round(hits / result["expected"], 2) if result["expected"] else None

    for field, present in result["fields"].items():
        if present is False:
            result["flags"].append(f"not recognised: {field}={expected[field]!r}")
    if len(text) < MIN_OCR_TEXT_LENGTH:
        result["flags"].append(
            "OCR returned very little text; the image may be blank")
    result["status"] = "OK" if hits == result["expected"] else "WARN"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# REPORT WRITER
# ─────────────────────────────────────────────────────────────────────────────

def write_report(results: list[dict], report_path: Path):
    """Write a Markdown QA report."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    total = len(results)
    by_status = {s: sum(1 for r in results if r["status"] == s)
                 for s in ("OK", "WARN", "UNAVAILABLE", "NO_MANIFEST")}
    scored = [r for r in results if r["confidence"] is not None]
    mean_conf = round(sum(r["confidence"] for r in scored) / len(scored), 3) if scored else None
    raw_frames = [r for r in results if r["ocr_ok"] and not r["deskewed"]]

    lines = [
        "# RENDER QA REPORT",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "Diagnostic, never blocking. Checks that each label string the render "
        "manifest specifies is actually READABLE in the rendered pixels — which "
        "`--dump-scene` cannot tell you, since it sees the text object rather "
        "than the image.",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Images checked | {total} |",
        f"| All fields read (OK) | {by_status['OK']} |",
        f"| Some field unread (WARN) | {by_status['WARN']} |",
        f"| OCR unavailable | {by_status['UNAVAILABLE']} |",
        f"| No render manifest | {by_status['NO_MANIFEST']} |",
        f"| Mean confidence | {mean_conf if mean_conf is not None else '—'} |",
        "",
    ]

    if not _TESSERACT_AVAILABLE:
        lines += ["> [!WARNING]",
                  f"> Tesseract is not available: {_TESSERACT_ERROR}",
                  "> Install with: winget install --id UB-Mannheim.TesseractOCR",
                  ""]

    if raw_frames:
        lines += [
            "> [!WARNING]",
            f"> {len(raw_frames)} image(s) were read WITHOUT deskewing, having no "
            "`{stem}.view.json` beside them. A rotated carton reads very poorly "
            "raw, so treat those scores as unreliable rather than as findings. "
            "Re-render them to produce the sidecar.",
            "",
        ]

    lines += [
        "## Results",
        "",
        "| SKU | Deskewed | Brand | Ingredient | Dosage | Count | Confidence | Status |",
        "|---|---|---|---|---|---|---:|---|",
    ]
    mark = lambda v: "—" if v is None else ("OK" if v else "MISS")
    for r in results:
        f = r.get("fields") or {}
        conf = "—" if r["confidence"] is None else f"{r['confidence']:.2f}"
        lines.append(
            f"| {r['sku']} | {'yes' if r['deskewed'] else 'RAW'} "
            f"| {mark(f.get('brand_name_display'))} "
            f"| {mark(f.get('active_ingredient_display'))} "
            f"| {mark(f.get('dosage_display'))} "
            f"| {mark(f.get('unit_count_display'))} "
            f"| {conf} | {r['status']} |")

    flagged = [r for r in results if r["flags"]]
    if flagged:
        lines += ["", "## Flagged", ""]
        for r in flagged:
            lines.append(f"### {r['sku']} ({r['status']})")
            lines += [f"- {flag}" for flag in r["flags"]]
            lines.append("")

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[DONE] Report written to: {report_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="OCR post-render QA for PharmaGen PRO. Non-blocking diagnostic."
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=DEFAULT_PROCESSED_DIR,
        help=f"Directory of processed PNG images (default: {DEFAULT_PROCESSED_DIR})",
    )
    parser.add_argument(
        "--manifests",
        type=Path,
        default=DEFAULT_MANIFESTS_DIR,
        help=f"Directory of render manifests (default: {DEFAULT_MANIFESTS_DIR})",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"Output report path (default: {DEFAULT_REPORT_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of images to check (default: all)",
    )
    args = parser.parse_args()

    if not _TESSERACT_AVAILABLE:
        print(f"[WARN] {_TESSERACT_ERROR}")
        print("[WARN] Proceeding — report will mark all as UNAVAILABLE.")

    if not args.dir.exists():
        print(f"[WARN] Processed images directory not found: {args.dir}")
        print(f"       No images to check. Writing empty report.")
        write_report([], args.report)
        return

    images = sorted(args.dir.glob("*.png"))
    if not images:
        print(f"[WARN] No PNG files found in {args.dir}")
        write_report([], args.report)
        return

    if args.limit:
        images = images[:args.limit]

    print(f"\n[START] Render QA — checking {len(images)} images in {args.dir}")
    print(f"        OCR backend: {'pytesseract OK' if _TESSERACT_AVAILABLE else 'UNAVAILABLE'}")
    print(f"        Manifests:   {args.manifests}")
    print(f"        Report:      {args.report}\n")

    results = []
    ok_count = 0

    for img_path in images:
        sku_stem = img_path.stem
        manifest = load_manifest(sku_stem, args.manifests)

        if manifest is None:
            result = {"sku": sku_stem, "ocr_ok": False,
                      "ocr_error": "Render manifest not found",
                      "deskewed": False, "fields": {}, "found": 0, "expected": 0,
                      "confidence": None, "status": "NO_MANIFEST",
                      "flags": [f"No manifest at {args.manifests / sku_stem}.json"]}
        else:
            result = check_image(img_path, manifest, load_view(img_path))

        status = result["status"]
        icon = "[OK]       " if status == "OK" else f"[{status}]"
        flags_display = " | ".join(result["flags"][:2]) if result["flags"] else ""
        print(f"  {icon} {sku_stem:20s} {flags_display}")

        if status == "OK":
            ok_count += 1

        results.append(result)

    warn_count = sum(1 for r in results if r["status"] == "WARN")
    unavail_count = sum(1 for r in results if r["status"] == "UNAVAILABLE")
    no_manifest_count = sum(1 for r in results if r["status"] == "NO_MANIFEST")
    print(f"\n  Total: {len(results)} | OK: {ok_count} | WARN: {warn_count} "
          f"| UNAVAILABLE: {unavail_count} | NO_MANIFEST: {no_manifest_count}")
    write_report(results, args.report)


if __name__ == "__main__":
    main()
