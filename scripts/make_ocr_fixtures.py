"""Build the committed OCR fixture set from the current renders.

The barrier that proves label text reaches pixels ran on ONE SKU, `1-min`, and
the audit named that the weakest point in the product's headline claim: "a text
object draws the string it is handed or nothing at all" was verified on 1 of
391. This script builds the fixture set for the reference-template sample so the
same barrier can run over eleven.

    python scripts/make_ocr_fixtures.py            # rebuild every fixture
    python scripts/make_ocr_fixtures.py --check    # report drift, write nothing

Fixtures are full-resolution WEBP at quality 92 rather than PNG. The render
itself is 2.8 MB and eleven of those do not belong in a repository that
deliberately tracks no renders; the same frame as WEBP is ~64 KB, reads
identically under Tesseract, and keeps the deskew step real — the view sidecar's
corners are in render pixels and still apply, so the fixture exercises the whole
path instead of a pre-flattened crop. It is also the format Stage 3 delivers.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import load_config, resolve_path  # noqa: E402

# The reference-template sample: the folders under `Reference Templates/` that
# actually hold reference photography, paired with the catalogue SKU each one
# documents.
#
# Resolved by hand from the curated `top30` group in scripts/catalogue_sweep.py,
# not re-derived by string matching, because the folder names do not identify a
# SKU on their own: `15_T1_Xanax` and `24_T1_Xanax_Pfizer` are two different
# catalogue entries whose names contain each other, and a matcher keyed on
# "Cialis" pulls back Strips, Oral Jelly and Black Generic before it reaches the
# plain one. Folders with no photograph are deliberately absent — there is
# nothing for them to be a reference OF.
TEMPLATE_SAMPLE = {
    "02_T1_SMALL_Cialis":        "59-min",
    "08_T1_Ativan":              "135-min",
    "14_T1_Imovane":             "155-min",
    "15_T1_Xanax":               "156-min",
    "21_T1_Valium_Brand":        "272-min",
    "23_T1_Lexotanil":           "308-min",
    "24_T1_Xanax_Pfizer":        "340-min",
    "25_T1_Modafinil_Generic":   "344-min",
    "30_T1_Ritalin":             "404-min",
    "31_Kamagra_Template_Reference": "64-min",
    "32_Viagra_Template_Reference":  "74-min",
}

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "ocr"
WEBP_QUALITY = 92

_CFG = load_config()
RENDER_DIR = resolve_path(_CFG["blender"]["output_dir"])
MANIFEST_DIR = resolve_path(_CFG["paths"]["passports_manifests"])


def sample_stems() -> list[str]:
    """The sample's SKU stems, in catalogue order."""
    return sorted(set(TEMPLATE_SAMPLE.values()),
                  key=lambda s: int(s.split("-")[0]))


def build(stem: str, check_only: bool) -> str:
    from PIL import Image

    png = RENDER_DIR / f"{stem}.png"
    view = png.with_suffix(".view.json")
    manifest = MANIFEST_DIR / f"{stem}.json"
    for required in (png, view, manifest):
        if not required.exists():
            return f"MISSING {required}"

    webp_out = FIXTURE_DIR / f"{stem}.webp"
    if check_only:
        return "present" if webp_out.exists() else "ABSENT"

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    Image.open(png).save(webp_out, "WEBP", quality=WEBP_QUALITY, method=6)
    shutil.copy2(view, FIXTURE_DIR / f"{stem}.view.json")
    # The manifest travels WITH the fixture rather than being read from
    # 04_passports/: the barrier's subject is whether these pixels show the
    # strings the renderer was handed, and re-reading a manifest that has since
    # been regenerated would compare the render against a contract it never saw.
    shutil.copy2(manifest, FIXTURE_DIR / f"{stem}.manifest.json")
    return f"{webp_out.stat().st_size / 1024:.0f} KB"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true",
                   help="report which fixtures exist; write nothing")
    args = p.parse_args()

    stems = sample_stems()
    print(f"[fixtures] {len(stems)} SKU from {len(TEMPLATE_SAMPLE)} template folders")
    total = 0
    for stem in stems:
        note = build(stem, args.check)
        print(f"  {stem:10s} {note}")
        if note.endswith("KB"):
            total += float(note.split()[0])
    if not args.check:
        print(f"[fixtures] {total / 1024:.2f} MB in {FIXTURE_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
