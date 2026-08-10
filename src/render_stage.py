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


def raw_output_dir(cfg: dict | None = None, engine: str | None = None) -> str:
    """Where the SELECTED Stage 2 engine writes its raw renders.

    Stage 3 needs this and must not learn it by importing an engine. The two
    engines write to deliberately separate directories -- resume logic scans the
    output dir for existing PNG and cannot tell which engine produced a file, so
    mixing them would corrupt both resume and Stage 3 -- and until this function
    existed Stage 3 read one of them from a constant. With `render.engine` set to
    blender that meant `main.py --full` rendered packshots nothing collected and
    still reported success.

    Reads configuration only. No engine module is imported here, so the facade
    stays the one place that knows an engine exists (BND-001), and importing this
    module does not pull Selenium or a Blender subprocess into Stage 3.
    """
    cfg = cfg or load_config()
    engine = engine or cfg.get("render", {}).get("engine", "gemini")
    if engine == "blender":
        return cfg["blender"]["output_dir"]
    return cfg["paths"]["renders_raw"]


def final_output_dir(cfg: dict | None = None, engine: str | None = None) -> str:
    """Where Stage 3 writes the finished WEBP for the SELECTED engine.

    The output side needs splitting for the same reason the raw side already was:
    both engines name their WEBP after the SKU stem, so one shared directory means
    the second engine to run silently overwrites the first one's finished
    artefacts. Discovered while wiring Stage 3 to the engine -- pointing the input
    at Blender without doing this would have overwritten 389 existing Gemini WEBP
    on the next full run.
    """
    cfg = cfg or load_config()
    engine = engine or cfg.get("render", {}).get("engine", "gemini")
    if engine == "blender":
        return cfg["blender"].get("final_dir", "02_processing/blender_renders_final")
    return cfg["paths"]["renders_final"]


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
