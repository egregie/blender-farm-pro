"""PharmaGen PRO — Stage 2 facade (EXPERIMENTAL, feature/blender-renderer-experiment).

Selects which render engine actually runs Stage 2 and delegates to it:

    gemini   -> src.rpa_orchestrator   (production, default — Selenium/Gemini RPA)
    blender  -> src.blender_renderer   (experimental — headless Blender)

Neither engine module is modified by this facade: it only picks one and
re-invokes its unmodified main() with the remaining CLI arguments. main.py's
default behaviour (--render-engine omitted) is therefore byte-for-byte
unchanged — it resolves to "gemini" here exactly as it always has.

Standalone usage mirrors the engines' own CLI, plus --engine:
    python -m src.render_stage --engine blender --limit 5
    python -m src.render_stage --all                       # engine from config.yaml
"""
from __future__ import annotations

import sys
import argparse

from src.utils import load_config

ENGINE_MODULES = {
    "gemini":  "src.rpa_orchestrator",
    "blender": "src.blender_renderer",
}


def _default_engine() -> str:
    cfg = load_config()
    return cfg.get("render", {}).get("engine", "gemini")


def main() -> None:
    # Only skim --engine off argv; every other flag (--all/--limit/--from/
    # --estimate/...) is left untouched for the delegate engine's own parser.
    meta = argparse.ArgumentParser(add_help=False)
    meta.add_argument("--engine", choices=sorted(ENGINE_MODULES), default=_default_engine())
    known, remaining = meta.parse_known_args()

    module_name = ENGINE_MODULES[known.engine]
    sys.argv = [sys.argv[0]] + remaining  # delegate sees its normal argv, minus --engine

    if known.engine != "gemini":
        print(f"[render_stage] EXPERIMENTAL engine selected: {known.engine} "
              f"(see docs/experiments/BLENDER_RENDERER_ROADMAP.md)", file=sys.stderr)

    if known.engine == "gemini":
        from src import rpa_orchestrator as engine
    elif known.engine == "blender":
        from src import blender_renderer as engine
    else:  # pragma: no cover — argparse `choices` already prevents this
        raise SystemExit(f"[render_stage] Unknown render engine: {known.engine}")

    engine.main()


if __name__ == "__main__":
    main()
