"""D-6 — how far a rendered carton is from the packaging it copies.

    python scripts/design_qa.py                 # measure every design SKU
    python scripts/design_qa.py --sku 59-min --preview

Rectifies our own render with the corners the driver publishes, classifies it
into the design spec's own colours, and compares. Two distances are reported and
kept apart, because they fail for different reasons and one can hide the other:

  spec vs reference   how much of the real carton the spec captured   (D-2)
  render vs spec      how faithfully the renderer built that spec     (D-4)

A high second number with a low first is a renderer building a bad spec
perfectly. The composite -- render against the rectified photograph -- is
reported too, but the two components are what a fix acts on.

Classification is by NEAREST SPEC COLOUR on the illumination-flattened frame,
not by re-clustering. Two independent k-means runs give two partitions with no
guaranteed correspondence, so the clusters would have to be matched up before
anything could be compared, and that matching is exactly where a wrong answer
would hide.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.deskew import flatten_face  # noqa: E402
from src.design_group import FOLDER_BY_STEM, TEMPLATES_DIR, load_design  # noqa: E402
from src.utils import load_config, resolve_path  # noqa: E402
from scripts.fit_design_spec import rasterise  # noqa: E402
from scripts.measure_reference_face import _flatten_illumination  # noqa: E402

_CFG = load_config()
_BL = _CFG["blender"]
RENDER_DIR = resolve_path(_BL["output_dir"])
MANIFEST_DIR = resolve_path(_CFG["paths"]["passports_manifests"])
PREVIEW_DIR = PROJECT_ROOT / "02_processing" / "reference_measurement"

OUT_WIDTH = 1100
DARK_V = 0.30      # type: ours prints it, the spec does not carry it
# The gradient estimate this comparison uses, as a divisor of the face's long
# edge. Wider than the segmentation's, and deliberately: clustering only asks
# which pixels resemble each other, while this asks how a rendered field compares
# with the colour the driver was told to paint. A narrow estimate follows the
# design itself, so on a carton that is half dark it divides the light half by a
# low local value AND a low global mean -- Kamagra's cream board measured 0.413
# from its own fill on a render that was correct.
FLATTEN_RADIUS_DIV = 2.0

# Two spec colours closer than this cannot be told apart by a nearest-colour
# classifier once a render and a photograph have each added their own noise, so
# the agreement figure stops measuring fidelity and starts measuring which side
# of a coin flip each pixel landed. Modafinil's substrate #A09C9D and highlight
# #A9A5A7 are four levels apart and scored 19.4% against a render that looks
# nearly identical to its spec. A number that cannot discriminate has to say so
# rather than be read as a failure.
SEPARABLE_MIN = 0.08


def _hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def flatten_on_substrate(rgb: np.ndarray, substrate_core: np.ndarray) -> np.ndarray:
    """Divide out the lighting gradient, estimated ONLY where the board is one colour.

    A blur of the whole face cannot separate shading from design. At a narrow
    radius it follows the artwork -- Kamagra's cream measured 0.48 from the fill
    it was painted -- and at a wide one it stops removing the gradient that a
    near-degenerate palette needs removed. Fitting a plane over the SUBSTRATE
    region, which the spec draws and is therefore known exactly, lets no design
    structure into the estimate at all; and a lighting gradient across a flat
    card is very nearly a plane.

    Measured against both blurs, worst colour error: Kamagra 0.482 / 0.252 /
    **0.187**, Imovane 0.133 / 0.091 / **0.060**, and the two cartons with wide
    palettes unchanged at 0.060.
    """
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    lum = rgb.max(-1)
    sel = substrate_core & (lum > 0.05)
    if sel.sum() < 500:
        return _flatten_illumination(rgb, FLATTEN_RADIUS_DIV)
    A = np.stack([xx[sel], yy[sel], np.ones(int(sel.sum()))], 1).astype(float)
    coef, *_ = np.linalg.lstsq(A, lum[sel], rcond=None)
    est = np.maximum(coef[0] * xx + coef[1] * yy + coef[2], 1e-3)
    return np.clip(rgb / est[..., None] * float(est.mean()), 0.0, 1.0)


def _substrate_core(spec_idx: np.ndarray, erode: int = 19) -> np.ndarray:
    """The substrate, eroded clear of its own boundaries."""
    from PIL import ImageFilter
    return np.asarray(
        Image.fromarray(((spec_idx == 0) * 255).astype("uint8"))
        .filter(ImageFilter.MinFilter(erode))) > 0


def _substrate_residual(frame: np.ndarray, core: np.ndarray) -> float:
    """How flat a model left the one surface known to be a single colour.

    The illumination estimate's own error, judged where the answer is not in
    doubt: the spec draws the substrate and states its paint, so anything left
    varying inside it is the model failing, not the carton. Nothing about the
    FIELDS enters, which is what keeps this from being a choice made by looking
    at the result.
    """
    sel = core & (frame.max(-1) >= DARK_V)
    if sel.sum() < 500:
        return float("inf")
    return float(np.linalg.norm(frame[sel].std(axis=0)))


def _nearest(frame: np.ndarray, palette: np.ndarray) -> np.ndarray:
    return ((frame[:, :, None, :] - palette[None, None, :, :]) ** 2).sum(-1).argmin(-1)


def _anchor(frame: np.ndarray, substrate_core: np.ndarray,
            substrate_rgb: np.ndarray) -> np.ndarray:
    """Put the frame on the spec's own level, using the one region it knows.

    A nearest-colour classifier compares a RENDER against PRINT colours, with
    nothing holding the two at the same level -- and our renders sit 5-15% below
    their spec, which is a photograph of paint at an exposure rather than the
    paint. Where the palette is wide that costs nothing, because the nearest
    entry is still the right one. Where two entries are 0.086 apart it decides
    everything: Imovane's highlight was classified over **0.3%** of the face
    against a spec that draws it over 14.3%, the whole band falling to the
    substrate side of a boundary a 5% shift had moved past it. 85.1% -> 98.4%.

    The gain is read off the SUBSTRATE, eroded clear of its own edges: the spec
    draws that region and states its paint, so this is a grey card the picture
    actually contains rather than a fitted correction.

    Deliberately NOT applied to `colour_error_by_region`. That figure asks
    whether the renderer painted the colour it was told to, and anchoring the
    frame to the spec is precisely how you erase its answer. An earlier attempt
    put the gain in front of both and was reverted for costing Kamagra fourteen
    points; the lesson was where it belongs, not that it is wrong.
    """
    sel = substrate_core & (frame.max(-1) >= DARK_V)
    if sel.sum() < 500:
        return frame
    gain = substrate_rgb / np.maximum(np.median(frame[sel], axis=0), 1e-3)
    return np.clip(frame * gain, 0.0, 1.0)


def _classify(img: Image.Image, palette: np.ndarray,
              substrate_core: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Nearest-colour index per pixel, plus a mask of pixels worth scoring.

    Dark pixels are dropped: our render prints the label and the reference
    carries type the spec deliberately does not represent. Scoring them would
    measure the type grid, which is a different piece of work, and would move
    this number every time a string changed length.
    """
    a = _flatten_illumination(np.asarray(img.convert("RGB")).astype(float) / 255.0,
                              FLATTEN_RADIUS_DIV)
    mask = a.max(-1) >= DARK_V
    if substrate_core is not None:
        a = _anchor(a, substrate_core, palette[0])
    return _nearest(a, palette), mask


def _agreement(a_idx, b_idx, mask, n) -> dict:
    match = float((a_idx == b_idx)[mask].mean()) if mask.any() else 0.0
    iou = {}
    for k in range(n):
        x, y = (a_idx == k) & mask, (b_idx == k) & mask
        union = (x | y).sum()
        iou[k] = round(float((x & y).sum() / union), 3) if union else None
    return {"agreement": round(match, 4), "iou": iou}


# A render is a photograph of paint, and a photograph has an exposure and a black
# level. Fitting both needs more regions than parameters: two points determine a
# line exactly, so a two-region carton would report a residual of zero and mean
# nothing by it.
MIN_RESPONSE_REGIONS = 3


def _response(ours: np.ndarray, spec_idx: np.ndarray, palette: np.ndarray,
              mask: np.ndarray):
    """The picture's own response: what gain and black level map paint to pixels.

    Measured because ColourError was reporting it as colour error. The two worst
    figures in the group are both a SUBSTRATE, and both render at exactly 0.87
    times their spec on all three channels -- a neutral scale, which is an
    exposure and not a colour. The dark regions go the other way: Kamagra's
    `#00463B` has a red channel of zero on the spec and 0.128 in our render,
    because a lit surface in a studio does not return black.

    Neither is the renderer painting the wrong colour, and neither is a defect:
    they are what a picture of paint does. Reported separately so the figure
    beside them can be read as what it claims to be. Removing them takes
    Kamagra's worst region from 0.189 to 0.024.

    Per channel, least squares over the region means. At three regions this has
    one degree of freedom, so the residual is correspondingly optimistic; at two
    it has none and is not attempted.
    """
    obs, want = [], []
    for k in range(len(palette)):
        sel = (spec_idx == k) & mask
        if sel.sum() < 50:
            continue
        obs.append(ours[sel].mean(0))
        want.append(palette[k])
    if len(obs) < MIN_RESPONSE_REGIONS:
        return None, {}
    obs, want = np.array(obs), np.array(want)
    gain, lift = np.zeros(3), np.zeros(3)
    for ch in range(3):
        A = np.stack([obs[:, ch], np.ones(len(obs))], 1)
        gain[ch], lift[ch] = np.linalg.lstsq(A, want[:, ch], rcond=None)[0]
    residual, n = {}, 0
    for k in range(len(palette)):
        sel = (spec_idx == k) & mask
        if sel.sum() < 50:
            residual[k] = None
            continue
        residual[k] = round(float(np.linalg.norm(obs[n] * gain + lift - want[n])), 4)
        n += 1
    return {"gain": [round(float(g), 3) for g in gain],
            "lift": [round(float(v), 3) for v in lift]}, residual


def _colour_error(ours: np.ndarray, spec_idx: np.ndarray, palette: np.ndarray,
                  mask: np.ndarray) -> dict:
    """Did the renderer paint the right colour where the spec said to?

    Survives a palette a classifier cannot separate, which six of the eleven
    have. The regions come from the SPEC, which is known exactly, so nothing has
    to be inferred from our pixels: they are only sampled. Two fills four levels
    apart make "which region is this pixel in" unanswerable while leaving "is
    this region the colour it should be" perfectly well posed.
    """
    out = {}
    for k in range(len(palette)):
        sel = (spec_idx == k) & mask
        if sel.sum() < 50:
            out[k] = None
            continue
        out[k] = round(float(np.linalg.norm(ours[sel].mean(0) - palette[k])), 4)
    return out


def render_fresh(stem: str) -> Path:
    """Render this SKU now. The comparison is worthless against a stale PNG.

    Same reasoning as the sweep's provenance check, applied at its strictest: a
    design render is being compared with the design it was supposed to build, so
    "which driver drew it" is not a detail.
    """
    out = RENDER_DIR / f"{stem}.png"
    for stale in (out, out.with_suffix(".view.json")):
        if stale.exists():
            stale.unlink()
    proc = subprocess.run(
        [str(_BL["executable"]), "--background", "--factory-startup",
         "--python", str(resolve_path(_BL["driver_script"])), "--",
         "--job", str(MANIFEST_DIR / f"{stem}.json"), "--out", str(out),
         "--engine-type", _BL.get("engine_type", "CYCLES"),
         "--samples", str(_BL.get("samples", 16)),
         "--res-x", str(_BL.get("resolution", [2048, 2048])[0]),
         "--res-y", str(_BL.get("resolution", [2048, 2048])[1])],
        capture_output=True, text=True, timeout=900)
    if not out.exists():
        raise SystemExit(f"{stem}: no render produced\n{proc.stderr[-1500:]}")
    return out


def measure(stem: str, preview: bool = False) -> dict:
    spec = load_design(stem)
    folder = TEMPLATES_DIR / FOLDER_BY_STEM[stem]

    palette = np.stack([_hex_rgb(spec["substrate"])]
                       + [_hex_rgb(f["fill"]) for f in spec["fields"]])
    gaps = [float(np.linalg.norm(palette[i] - palette[j]))
            for i in range(len(palette)) for j in range(i + 1, len(palette))]
    closest = min(gaps) if gaps else 1.0
    aspect = float(spec["face_aspect"])
    size = (OUT_WIDTH, max(1, round(OUT_WIDTH * aspect)))

    # The spec, drawn at the comparison size. This is the target both sides are
    # measured against, in its own colours.
    target = rasterise(spec, *size)
    t_idx, _ = _classify(target, palette)

    png = render_fresh(stem)
    view = json.loads(png.with_suffix(".view.json").read_text(encoding="utf-8"))
    ours = flatten_face(png, view["front_face_px"], out_width=OUT_WIDTH, aspect=aspect)
    ours_raw = np.asarray(ours.convert("RGB")).astype(float) / 255.0
    core = _substrate_core(t_idx)
    # ColourError always reads the PLANE. It asks whether a region is the colour
    # it should be, so its illumination estimate must not be able to absorb the
    # design -- a blur can, which is the defect recorded against Kamagra below.
    ours_flat = flatten_on_substrate(ours_raw, core)
    o_mask = ours_flat.max(-1) >= DARK_V

    # The CLASSIFIER takes whichever model leaves the substrate flattest. Neither
    # is right everywhere and the difference is not small: on `59-min` the plane
    # leaves a residual of 0.085 against the blur's 0.066 and classifies 28.9% of
    # the face as highlight where the spec draws 21.1%, reading 88.6% against the
    # blur's 98.1%; on `155-min` it is the other way round, 0.030 against 0.036
    # and 98.4% against 94.1%. On the other nine the two agree to a tenth of a
    # point, so this changes nothing where nothing needed changing.
    #
    # Chosen on the SUBSTRATE, never on the fields -- see _substrate_residual.
    candidates = {"plane": ours_flat, "blur": _flatten_illumination(ours_raw, 2.0)}
    anchored = {k: _anchor(v, core, palette[0]) for k, v in candidates.items()}
    residual = {k: _substrate_residual(v, core) for k, v in anchored.items()}
    chosen = min(residual, key=residual.get)
    o_idx = _nearest(anchored[chosen], palette)

    # The swing is what the figure does under the same model with a different
    # arbitrary knob -- the erosion the plane is fitted through, the radius the
    # blur is taken at. Differencing against the REJECTED model instead reports
    # the cost of a estimate the substrate already showed to be worse, which is
    # not the figure's uncertainty: it read +-9.5 on `59-min` for exactly that.
    variant = (flatten_on_substrate(ours_raw, _substrate_core(t_idx, 9))
               if chosen == "plane" else _flatten_illumination(ours_raw, 2.5))
    alt_idx = _nearest(_anchor(variant, core, palette[0]), palette)

    # The dark cut is there to keep printed TYPE out of the score. It must not
    # also cut dark FIELDS, which the spec does carry: inside Xanax's near-black
    # brand it left only the lit fringe, whose mean sits nowhere near the fill,
    # and reported 0.600 against a render measured at 99.4% agreement. Whether a
    # pixel is scored now depends on what the SPEC expects there, not on how
    # bright the pixel happens to be.
    dark_fill = (palette * np.array([0.2126, 0.7152, 0.0722])).sum(1) < DARK_V
    scored = o_mask | dark_fill[t_idx]
    colour_err = _colour_error(ours_flat, t_idx, palette, scored)
    response, colour_residual = _response(ours_flat, t_idx, palette, scored)

    ref_path = PREVIEW_DIR / f"{folder.name}.flat.png"
    ref_idx = ref_mask = None
    if ref_path.exists():
        ref = Image.open(ref_path).resize(size, Image.LANCZOS)
        ref_idx, ref_mask = _classify(ref, palette, core)

    result = {
        "sku": stem,
        "folder": folder.name,
        "palette_closest_pair": round(closest, 4),
        "separable": closest >= SEPARABLE_MIN,
        "illumination": chosen,
        "illumination_residual": {k: round(v, 4) for k, v in residual.items()},
        "render_vs_spec": _agreement(o_idx, t_idx, o_mask, len(palette)),
        # The figure's own uncertainty, measured rather than assumed.
        "agreement_spread": round(abs(
            _agreement(o_idx, t_idx, o_mask, len(palette))["agreement"]
            - _agreement(alt_idx, t_idx, o_mask, len(palette))["agreement"]), 4),
        "colour_error_by_region": colour_err,
        "colour_error_worst": (max([v for v in colour_err.values() if v is not None],
                                   default=None)),
        # What is left once the picture's own exposure and black level are taken
        # out -- see _response. None where there are too few regions to fit them.
        "response": response,
        "colour_residual_by_region": colour_residual,
        "colour_residual_worst": (max([v for v in colour_residual.values() if v is not None],
                                      default=None)),
        "spec_vs_reference": (spec.get("verification") or {}).get("pixel_agreement"),
    }
    if ref_idx is not None:
        both = o_mask & ref_mask
        result["render_vs_reference"] = _agreement(o_idx, ref_idx, both, len(palette))

    if preview:
        PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        strip = Image.new("RGB", (size[0], size[1] * 3 + 24), (255, 255, 255))
        strip.paste(Image.open(ref_path).resize(size) if ref_path.exists() else target, (0, 0))
        strip.paste(target, (0, size[1] + 12))
        strip.paste(ours, (0, 2 * size[1] + 24))
        strip.save(PREVIEW_DIR / f"{folder.name}.qa.png")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sku", help="one SKU stem; default is every design SKU")
    p.add_argument("--preview", action="store_true",
                   help="write reference / spec / render as one strip")
    args = p.parse_args()

    stems = [args.sku] if args.sku else sorted(
        FOLDER_BY_STEM, key=lambda s: int(s.split("-")[0]))

    rows = []
    print(f"{'SKU':9s} {'folder':32s} {'spec~ref':>9s} {'render~spec':>12s} "
          f"{'render~ref':>11s} {'worst dC':>9s} {'residual':>8s} {'swing':>6s}")
    for stem in stems:
        r = measure(stem, args.preview)
        rows.append(r)
        sr = r["spec_vs_reference"]
        flag = "" if r["separable"] else "  (palette not separable)"
        # A dash, not a zero: too few regions to fit the picture's response is
        # not the same as nothing left after fitting it.
        resid = r["colour_residual_worst"]
        resid_txt = "--" if resid is None else f"{resid:.3f}"
        print(f"{stem:9s} {r['folder']:32s} "
              f"{(100 * sr if sr else 0):8.1f}% "
              f"{100 * r['render_vs_spec']['agreement']:11.1f}% "
              f"{100 * r.get('render_vs_reference', {}).get('agreement', 0):10.1f}% "
              f"{(r['colour_error_worst'] if r['colour_error_worst'] is not None else 0):8.3f} "
              f"{resid_txt:>8s} "
              f"+-{100 * r['agreement_spread']:4.1f}{flag}")

    out = PROJECT_ROOT / "00_PROJECT_STATE" / "design_qa.json"
    out.write_text(json.dumps({"rows": rows}, indent=2), encoding="utf-8")
    print(f"\n{out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
