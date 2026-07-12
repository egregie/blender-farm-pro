"""PharmaGen PRO — Stage 2, Blender render engine (EXPERIMENTAL).

Alternative to src/rpa_orchestrator.py (Selenium/Gemini RPA). Reads the
STRUCTURED JSON passport (pipeline/passports/*.json — the same input Stage 1
consumes, NOT the compiled Markdown prompt) because a 3D renderer needs
{palette, primary_package, label_content, template_id}, not prose. See
docs/experiments/BLENDER_RENDERER_ROADMAP.md §1.2-1.3 for the rationale.

Output is written to a SEPARATE directory (blender.output_dir, default
render_output/raw_blender/) so it never collides with Gemini's
render_output/raw/ — see the roadmap §2 for why that segregation matters.

CLI mirrors src/rpa_orchestrator.py's surface (--limit/--all/--from/--estimate)
so it is a drop-in alternative behind the src/render_stage.py facade.

    python -m src.blender_renderer --limit 5
    python -m src.blender_renderer --all
    python -m src.blender_renderer --from 217-min --limit 1
    python -m src.blender_renderer --estimate
"""
from __future__ import annotations

import os
import sys
import json
import time
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

from src.utils import load_config, get_path, resolve_path

_CFG = load_config()
_BLENDER = _CFG["blender"]

BLENDER_EXE     = _BLENDER["executable"]
DRIVER_SCRIPT   = str(resolve_path(_BLENDER["driver_script"]))
JSON_DIR        = str(get_path(_CFG, "passports_json"))      # structured input (Stage 1's input)
OUT_DIR         = str(resolve_path(_BLENDER["output_dir"]))  # segregated from Gemini's render_output/raw
ENGINE_TYPE     = _BLENDER.get("engine_type", "CYCLES")
RESOLUTION      = _BLENDER.get("resolution", [2048, 2048])
SAMPLES         = _BLENDER.get("samples", 64)
RENDER_TIMEOUT  = _BLENDER.get("render_timeout", 300)

_LOGS_DIR = get_path(_CFG, "logs")
_LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = str(_LOGS_DIR / f"blender_renderer_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    level=getattr(logging, str(_CFG["logging"]["level"]).upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


def get_passport_files() -> list[Path]:
    """Sorted *.json passports from JSON_DIR (same sort convention as other stages)."""
    jdir = Path(JSON_DIR)
    if not jdir.exists():
        raise FileNotFoundError(f"Passports JSON directory not found: {jdir}")
    files = sorted(
        jdir.glob("*.json"),
        key=lambda f: int(f.stem.split("-")[0]) if f.stem.split("-")[0].isdigit() else 999999,
    )
    log.info(f"📁 Found {len(files)} JSON passports in {jdir}")
    return files


def load_progress() -> set[str]:
    """Resume model: a SKU is 'done' if {stem}.png already exists in OUT_DIR
    (mirrors src/rpa_orchestrator.py's raw-dir-scan fallback; no separate
    progress-tracker file is needed since Blender rendering is idempotent)."""
    done = set()
    out = Path(OUT_DIR)
    if out.exists():
        for f in out.glob("*.png"):
            done.add(f.stem)
    log.info(f"Progress check: {len(done)} items already present in {OUT_DIR} and will be skipped.")
    return done


def resolve_template(passport: dict) -> tuple[str, bool]:
    """Reuse Stage 1's routing decision — do not re-implement it (see roadmap §1.3)."""
    from src.passport_generator import agent_1_router
    return agent_1_router(passport)


def build_render_job(passport_path: Path) -> dict:
    with open(passport_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    template_id, is_override = resolve_template(data)
    return {
        "sku_id":             data.get("sku_id", passport_path.stem),
        "template_id":        template_id,
        "is_bottle_override": is_override,
        "packaging_geometry": data.get("packaging_geometry", "BOX"),
        "palette":            data.get("branding", {}).get("palette", {}),
        "label_content":      data.get("label_content", {}),
        "primary_package":    data.get("primary_package", {}),
    }


def render_one(passport_path: Path, out_path: Path) -> tuple[bool, str]:
    try:
        job = build_render_job(passport_path)
    except Exception as e:
        return False, f"job-build error: {e}"

    job_path = out_path.with_suffix(".job.json")
    try:
        job_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    except Exception as e:
        return False, f"could not write job file: {e}"

    cmd = [
        BLENDER_EXE, "--background", "--factory-startup",
        "--python", DRIVER_SCRIPT, "--",
        "--job", str(job_path),
        "--out", str(out_path),
        "--engine-type", ENGINE_TYPE,
        "--samples", str(SAMPLES),
        "--res-x", str(RESOLUTION[0]),
        "--res-y", str(RESOLUTION[1]),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=RENDER_TIMEOUT)
    except subprocess.TimeoutExpired:
        return False, f"render timed out after {RENDER_TIMEOUT}s"
    except Exception as e:
        return False, f"subprocess error: {e}"

    if result.returncode != 0 or not out_path.exists():
        tail = (result.stderr or result.stdout or "")[-1500:]
        return False, f"Blender exit={result.returncode}: {tail}"
    return True, "ok"


def print_estimate() -> None:
    """Dry-run: remaining SKUs, no Blender invocation."""
    try:
        passports = get_passport_files()
    except Exception as e:
        log.error(f"Could not load passports: {e}")
        return
    done = load_progress()
    remaining = [p for p in passports if p.stem not in done]
    print(f"\n[blender] Total: {len(passports)} | Done: {len(done)} | Remaining: {len(remaining)}")
    if not remaining:
        print("All SKUs are already rendered (blender engine)!")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PharmaGen PRO — Blender render engine (Stage 2, EXPERIMENTAL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--limit", type=int, default=20,
                       help="Max number of passports to process (default: 20 for safety)")
    parser.add_argument("--all", action="store_true",
                       help="Process ALL remaining unprocessed passports (overrides --limit)")
    parser.add_argument("--from", dest="from_stem", default=None,
                       help="Start processing from a specific passport stem (e.g. '50-min')")
    parser.add_argument("--estimate", action="store_true",
                       help="Show remaining SKUs without rendering")
    args = parser.parse_args()

    if args.estimate:
        print_estimate()
        return

    log.info("=" * 70)
    log.info("  BLENDER RENDERER — EXPERIMENTAL Stage 2 engine")
    log.info(f"  Blender:  {BLENDER_EXE}")
    log.info(f"  JSON_DIR: {JSON_DIR}")
    log.info(f"  OUT_DIR:  {OUT_DIR}")
    log.info(f"  Engine:   {ENGINE_TYPE}  Samples: {SAMPLES}  Res: {RESOLUTION}")
    log.info("=" * 70)

    if not Path(BLENDER_EXE).exists():
        log.error(f"Blender executable not found: {BLENDER_EXE}")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    done = load_progress()
    passports = [p for p in get_passport_files() if p.stem not in done]

    if args.from_stem:
        idx = next((i for i, p in enumerate(passports) if p.stem == args.from_stem), None)
        if idx is not None:
            passports = passports[idx:]
            log.info(f"⏩ --from {args.from_stem}: {len(passports)} remaining from that point.")
        else:
            log.warning(f"⚠️  --from '{args.from_stem}' not found in the unprocessed list.")

    if not args.all:
        passports = passports[:args.limit]

    log.info(f"📋 Rendering {len(passports)} passport(s)"
             f"{' (ALL mode)' if args.all else f' (limit={args.limit})'}")

    if not passports:
        log.info("✅ Nothing to render — all SKUs already present.")
        return

    stats = {"success": 0, "failed": 0}
    for i, passport_path in enumerate(passports):
        stem = passport_path.stem
        out_path = Path(OUT_DIR) / f"{stem}.png"
        log.info(f"[{i + 1}/{len(passports)}] {stem}")
        start = time.time()
        ok, msg = render_one(passport_path, out_path)
        dur = time.time() - start
        if ok:
            stats["success"] += 1
            log.info(f"  ✅ SUCCESS ({dur:.1f}s) -> {out_path.name}")
        else:
            stats["failed"] += 1
            log.error(f"  ❌ FAILED ({dur:.1f}s): {msg}")

    log.info("=" * 70)
    log.info(f"  DONE — success={stats['success']}  failed={stats['failed']}")
    log.info(f"  Log: {LOG_FILE}")
    log.info("=" * 70)


if __name__ == "__main__":
    main()
