"""Does moving Cycles onto the GPU change the pixels? Measure before deciding.

    python scripts/probe_render_device.py
    python scripts/probe_render_device.py --sku 1-min --sku 64-min
    python scripts/probe_render_device.py --keep      # leave the PNGs on disk

Renders the same SKU under several device configurations and compares the
results **against the CPU render byte for byte**, not by eye and not by
stopwatch alone. The rule this exists to serve, from the migration brief: a
configuration that reproduces the current pixels exactly can be switched on
without being a measuring event, and one that does not must wait for a phase of
its own with a full re-measure behind it.

WHY THIS DOES NOT EDIT THE DRIVER, and could not honestly be written any other
way. `setup_render()` sets the engine, the sample count and `use_denoising` and
**never assigns `scene.cycles.device`** — so the device is whatever the process
already had, which under `--factory-startup` is CPU. That omission is the seam:
Blender accepts more than one `--python`, so a prelude running before the driver
can set the device and the driver will inherit it without a line of it changing.

The alternative — edit `setup_render()` first, then measure — would compare the
new driver against itself. It would also change `driver_fingerprint()`, which is
the SHA-256 of the whole driver file, invalidating `render_calibration.json`
before there was any decision to justify the re-measure.

WHAT A DIFFERENCE HERE MEANS. OptiX is a different intersection back-end, not a
different quality setting: it can disagree with the CPU in the last bit of a
float without either being wrong. So `max channel delta` is reported in 8-bit
levels beside the byte comparison, because "not identical" and "not the same
picture" are different findings and this project has been bitten by a report
that could not tell them apart.

READ `max_channel_delta`, NOT `identical_bytes`. Measured on this build: two
runs of the SAME driver on the same job produce **bit-identical pixels and
different files** — `64-min` re-rendered against its baseline gives
`max_channel_delta = 0` over 0.0000% of pixels while the PNG bytes differ,
because the encoder stamps metadata into the file. A byte comparison of PNGs
therefore answers a question about the container, and the brief's rule about
"byte-identical output" has to be read as being about the image. `identical_bytes`
is kept because it is cheap and because a reader will look for it; it is not the
figure any decision here rests on.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils import load_config, resolve_path  # noqa: E402

_CFG = load_config()
_BL = _CFG["blender"]
MANIFEST_DIR = resolve_path(_CFG["paths"]["passports_manifests"])
SCRATCH = PROJECT_ROOT / "02_processing" / "device_probe"

#: The SKU the brief names: a plain carton, a design carton, and the one whose
#: design carries the group's largest polygon count.
DEFAULT_SKU = ["1-min", "64-min", "357-min"]

#: Each configuration is a prelude executed before the driver. `None` is the
#: control: no prelude at all, so the bytes compared against are produced by
#: precisely the command `blender_renderer` issues today.
CONFIGS: dict[str, str | None] = {
    "cpu": None,
    "optix": "OPTIX,False",
    "optix+gpudenoise": "OPTIX,True",
    "cuda": "CUDA,False",
}

_PRELUDE = '''
import bpy, sys
backend, gpu_denoise = {backend!r}, {gpu_denoise!r}
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = backend
prefs.refresh_devices()
enabled = []
for d in prefs.devices:
    # Only the accelerator. Leaving the CPU device enabled as well makes this a
    # hybrid render, which is a third thing to measure rather than the one asked
    # about.
    d.use = (d.type == backend)
    if d.use:
        enabled.append(d.name)
if not enabled:
    raise SystemExit("[probe] no %s device; refusing to fall back to CPU" % backend)
sc = bpy.context.scene
sc.cycles.device = "GPU"
sc.cycles.denoising_use_gpu = gpu_denoise
print("[probe] backend=%s devices=%s denoising_use_gpu=%s"
      % (backend, enabled, gpu_denoise))
'''


def _prelude_file(spec: str, out: Path) -> Path:
    backend, gpu_denoise = spec.split(",")
    out.write_text(
        _PRELUDE.format(backend=backend, gpu_denoise=(gpu_denoise == "True")),
        encoding="utf-8")
    return out


def render(stem: str, config: str, dest: Path) -> tuple[Path, float, str]:
    """Render *stem* under *config*. Returns (png, wall seconds, stderr tail)."""
    png = dest / f"{stem}.{config}.png"
    for stale in (png, png.with_suffix(".view.json")):
        stale.unlink(missing_ok=True)

    cmd = [str(resolve_path(_BL["executable"])), "--background", "--factory-startup"]
    spec = CONFIGS[config]
    if spec is not None:
        cmd += ["--python", str(_prelude_file(spec, dest / f"_prelude.{config}.py"))]
    cmd += ["--python", str(resolve_path(_BL["driver_script"])), "--",
            "--job", str(MANIFEST_DIR / f"{stem}.json"),
            "--out", str(png),
            "--engine-type", str(_BL["engine_type"]),
            "--samples", str(_BL["samples"]),
            "--res-x", str(_BL["resolution"][0]),
            "--res-y", str(_BL["resolution"][1])]

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=int(_BL.get("render_timeout", 300)) * 3)
    dt = time.perf_counter() - t0
    if not png.exists():
        raise SystemExit(f"{stem}/{config}: no PNG.\n{proc.stdout[-800:]}\n"
                         f"{proc.stderr[-1500:]}")
    return png, dt, proc.stderr[-400:]


def compare(a: Path, b: Path) -> dict:
    """Byte identity first, then how far apart the pixels are in 8-bit levels."""
    same_bytes = a.read_bytes() == b.read_bytes()
    ia = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16)
    ib = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    if ia.shape != ib.shape:
        return {"identical_bytes": False, "shape_mismatch": [ia.shape, ib.shape]}
    d = np.abs(ia - ib)
    return {
        "identical_bytes": same_bytes,
        "identical_pixels": bool(d.max() == 0),
        "max_channel_delta": int(d.max()),
        "mean_channel_delta": round(float(d.mean()), 5),
        "pixels_differing_pct": round(100 * float((d.max(-1) > 0).mean()), 4),
        "pixels_over_2_levels_pct": round(100 * float((d.max(-1) > 2).mean()), 4),
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sku", action="append", help="repeatable; default is three")
    p.add_argument("--config", action="append",
                   help=f"repeatable; default is all of {list(CONFIGS)}")
    p.add_argument("--keep", action="store_true", help="leave the PNGs on disk")
    p.add_argument("--out", help="write the findings as JSON here")
    args = p.parse_args()

    stems = args.sku or DEFAULT_SKU
    configs = args.config or list(CONFIGS)
    if configs[0] != "cpu":
        raise SystemExit("the first config must be `cpu`: it is the control "
                         "everything else is compared against")

    SCRATCH.mkdir(parents=True, exist_ok=True)
    rows = []
    for stem in stems:
        control = None
        for config in configs:
            png, dt, err = render(stem, config, SCRATCH)
            row = {"sku": stem, "config": config, "seconds": round(dt, 1)}
            if control is None:
                control = png
            else:
                row.update(compare(control, png))
            rows.append(row)
            flag = ("control" if row.get("identical_bytes") is None else
                    "IDENTICAL" if row["identical_bytes"] else
                    f"differs, max {row['max_channel_delta']} level(s) on "
                    f"{row['pixels_differing_pct']}% of pixels")
            print(f"{stem:10s} {config:18s} {dt:7.1f}s   {flag}")

    if args.out:
        Path(args.out).write_text(json.dumps({"rows": rows}, indent=2),
                                  encoding="utf-8")
        print(f"\nwrote {args.out}")
    if not args.keep:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
