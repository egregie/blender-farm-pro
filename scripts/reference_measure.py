"""Measure what a reference photograph actually shows.

Why this exists
---------------
The two benchmark passports that shipped with this project describe a carton
neither photograph contains. Their bounding boxes are identical to each other to
three decimals -- logo at 0.060,0.060, brand at 0.060,0.220, accent stripe at
0.000,0.920 -- across two packages from different manufacturers, which cannot
happen by measurement. Checked against the pixels, the Viagra passport's
full-width bottom stripe in #004B87 is not there: 86% of that colour sits in the
left third of the frame, where the side panel is, and the bottom strip the
passport claims is 4% covered. The layout they describe -- white body, bottom
accent band, top-right badge -- is the layout this project's own Blender driver
renders, so the "ground truth" was a description of the renderer rather than of
the photograph.

Every one of those values carried a `[Measured]` tag. SAAT's Section 2 exists to
forbid exactly that, so the fix is not a better guess but an actual measurement.

What can honestly be measured, and what cannot
----------------------------------------------
This tool reports only what it derives from pixels:

* the carton's extent, from the alpha channel where the source has one;
* every text token OCR can read, with its box and its confidence;
* the dominant colours over the carton and the share of area each covers.

It does NOT reconstruct the front face's quadrilateral, so the boxes it returns
are normalised to the carton's **image bounding box**, not to the face's own
coordinates. Those differ whenever the carton is photographed at an angle, which
is all of them. A passport built from this output must say so rather than quietly
present one as the other.

Two things about these images that cost an hour to notice, recorded so they cost
nobody else one. The PNGs carry an alpha channel and no background; converting
straight to RGB turns transparent into black, which destroys the contrast OCR
needs and makes the backdrop read as luma 0. And Tesseract's default page
segmentation finds only the small print -- the brand title, the dosage and the
manufacturer mark all come back at `--psm 3`.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

# Page segmentation that actually reads these packshots. The default mode
# recovers the small print and misses every headline element.
OCR_PSM = 3
MIN_CONFIDENCE = 40
# Colours closer than this in RGB are one zone. Chosen so a printed ink and its
# shaded side do not split into two, and reported alongside the result so the
# number can be argued with rather than trusted.
COLOR_MERGE_DISTANCE = 60.0
MIN_ZONE_SHARE_PCT = 1.0


def load_flat(path: Path):
    """The image composited onto white, plus the carton's mask.

    Where the source has alpha, the mask is the alpha -- exact, and free. Where
    it does not, fall back to a luma difference from the corner colour and say
    so, because that fallback is an inference and the alpha is not.
    """
    im = Image.open(path)
    if im.mode in ("RGBA", "LA"):
        alpha = np.asarray(im.split()[-1])
        flat = Image.new("RGB", im.size, (255, 255, 255))
        flat.paste(im, mask=im.split()[-1])
        return flat, alpha > 16, "alpha"
    flat = im.convert("RGB")
    grey = np.asarray(flat.convert("L")).astype(float)
    corner = np.concatenate([grey[:10, :10].ravel(), grey[:10, -10:].ravel()]).mean()
    return flat, np.abs(grey - corner) > 12, "luma-vs-corner"


def carton_bbox(mask):
    ys, xs = np.nonzero(mask)
    if ys.size == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def read_text(flat, bbox):
    """Every token Tesseract reads, boxed in carton-relative coordinates.

    The binary is not on PATH on this machine, and `scripts/render_qa.py`
    already owns the probe that locates it. Importing that module runs the probe
    and sets `pytesseract.pytesseract.tesseract_cmd` as a side effect, which is
    why the import is here rather than a second copy of the search logic --
    this project has been bitten before by two places knowing the same thing.
    """
    import sys
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts import render_qa  # noqa: F401 -- imported for its side effect
    import pytesseract

    if not render_qa._TESSERACT_AVAILABLE:
        raise SystemExit(
            f"[reference_measure] Tesseract is unavailable: "
            f"{render_qa._TESSERACT_ERROR}\nText cannot be measured, and "
            f"reporting boxes without it would be the invention this tool "
            f"exists to replace. Install it and re-run.")

    x0, y0, x1, y1 = bbox
    span_x, span_y = max(1, x1 - x0), max(1, y1 - y0)
    data = pytesseract.image_to_data(flat, config=f"--psm {OCR_PSM}",
                                     output_type=pytesseract.Output.DICT)
    out = []
    for i, raw in enumerate(data["text"]):
        token = raw.strip()
        conf = int(data["conf"][i])
        if not token or conf < MIN_CONFIDENCE:
            continue
        out.append({
            "text": token,
            "confidence": conf,
            "x": round((data["left"][i] - x0) / span_x, 4),
            "y": round((data["top"][i] - y0) / span_y, 4),
            "w": round(data["width"][i] / span_x, 4),
            "h": round(data["height"][i] / span_y, 4),
        })
    return out


def colour_zones(flat, mask):
    """Dominant colours over the carton, with the share of it each covers."""
    pixels = np.asarray(flat).astype(float)[mask]
    if pixels.size == 0:
        return []
    # Coarse quantisation first so the merge below compares populated bins
    # rather than every distinct pixel value.
    keys, counts = np.unique((pixels // 16).astype(int), axis=0, return_counts=True)
    order = np.argsort(-counts)
    zones = []
    for idx in order:
        centre = keys[idx] * 16 + 8
        for zone in zones:
            if np.linalg.norm(centre - np.array(zone["_centre"])) < COLOR_MERGE_DISTANCE:
                zone["_count"] += int(counts[idx])
                break
        else:
            zones.append({"_centre": centre.tolist(), "_count": int(counts[idx])})
    total = float(mask.sum())
    result = []
    for zone in zones:
        share = 100.0 * zone["_count"] / total
        if share < MIN_ZONE_SHARE_PCT:
            continue
        r, g, b = (int(v) for v in zone["_centre"])
        result.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "rgb": [r, g, b],
                       "area_pct": round(share, 2)})
    return result


def measure(path: Path) -> dict:
    flat, mask, mask_source = load_flat(path)
    width, height = flat.size
    bbox = carton_bbox(mask)
    if bbox is None:
        return {"image": path.name, "error": "no carton found against the backdrop"}
    x0, y0, x1, y1 = bbox
    return {
        "image": path.name,
        "image_size": [width, height],
        "mask_source": mask_source,
        "carton_bbox_px": [x0, y0, x1, y1],
        "carton_share_of_frame_pct": round(100.0 * mask.sum() / (width * height), 2),
        "carton_bbox_aspect": round((x1 - x0) / max(1, y1 - y0), 4),
        "text_tokens": read_text(flat, bbox),
        "colour_zones": colour_zones(flat, mask),
        "coordinate_space": (
            "Boxes are normalised to the carton's IMAGE bounding box, not to the "
            "front face's own coordinates. The face is photographed at an angle, "
            "so the two are not the same and must not be presented as such."),
        "settings": {"ocr_psm": OCR_PSM, "min_confidence": MIN_CONFIDENCE,
                     "colour_merge_distance": COLOR_MERGE_DISTANCE,
                     "min_zone_share_pct": MIN_ZONE_SHARE_PCT},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--json", type=Path, help="write the full measurement here")
    args = ap.parse_args()

    results = [measure(p) for p in args.images]
    for r in results:
        print(f"\n=== {r['image']}")
        if "error" in r:
            print(f"    {r['error']}")
            continue
        print(f"    {r['image_size'][0]}x{r['image_size'][1]}, mask from {r['mask_source']}, "
              f"carton covers {r['carton_share_of_frame_pct']}% of frame, "
              f"bbox aspect {r['carton_bbox_aspect']}")
        print(f"    text tokens read: {len(r['text_tokens'])}")
        for t in r["text_tokens"]:
            print(f"      {t['text']:24} conf {t['confidence']:>3}  "
                  f"x={t['x']:.3f} y={t['y']:.3f} w={t['w']:.3f} h={t['h']:.3f}")
        print(f"    colour zones (>= {MIN_ZONE_SHARE_PCT}% of carton):")
        for z in r["colour_zones"]:
            print(f"      {z['hex']}  {z['area_pct']:5.2f}%")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
