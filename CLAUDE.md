# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A standalone fork of **PharmaGen PRO**, created to develop headless-Blender rendering as
the packshot engine. It turns a per-SKU JSON "passport" (brand, dosage, palette, packaging
geometry) into a rendered pharmaceutical-packaging image. 391 SKU in the catalogue.

The fork carries the *whole* original pipeline forward (Gemini RPA engine included) — the
Blender engine is an alternative Stage 2, not a replacement of the codebase.

Read [`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md) for status and
[`docs/experiments/BLENDER_RENDERER_ROADMAP.md`](docs/experiments/BLENDER_RENDERER_ROADMAP.md)
for the Blender-engine design rationale and its phase plan.

## Commands

No venv is checked in. Python 3.10.11 is on PATH and the suite passes against it.

```bash
# Tests — stdlib unittest, NOT pytest (pytest is not a dependency)
python -m unittest discover -s tests          # all 18 tests
python -m unittest tests.test_verifier        # one module
python -m unittest tests.test_verifier.TestVerifier.test_name   # one test

# Full pipeline (Stage 1 -> 2 -> 3), stages run as isolated subprocesses
python main.py --full
python main.py --full --resume                # skip already-completed work

# Individual stages
python main.py --passports-only               # JSON passports -> Markdown prompts
python main.py --render-only --limit 5        # render 5 unprocessed SKU
python main.py --render-only --from 50-min    # start at a given passport stem
python main.py --process-images-only --resume # raw PNG -> final WEBP

# Engine selection (this fork defaults to blender via config.yaml)
python main.py --render-only --render-engine blender
python main.py --render-only --render-engine gemini

# Stage 2 directly, bypassing main.py's orchestration
python -m src.render_stage --engine blender --limit 5
python -m src.blender_renderer --estimate     # dry run: how many SKU remain
python -m src.blender_renderer --all
```

`--debug` forces DEBUG logging. `--config <path>` overrides `config.yaml`.

### Code graph

A Tree-sitter graph is built for this repo (`code-review-graph`). Prefer it over reading
large files whole — `src/passport_generator.py` is 70 KB and `src/rpa_orchestrator.py` 76 KB.

```bash
CRG="C:/lil_projects/_ecc-skills/_tools/crg-venv/Scripts/code-review-graph.exe"
"$CRG" impact --files src/blender_renderer.py    # blast radius before editing
"$CRG" search <symbol>
"$CRG" update                                     # incremental, after edits
```

## Architecture

### Three stages, subprocess-isolated

`main.py` is an orchestrator only — it adds logging, resume, retries and a summary report,
then runs each stage as its own subprocess so behaviour matches invoking the stage script
directly. Stages are sequential because each consumes the previous one's output.

| Stage | Module | In → Out |
|---|---|---|
| 1 passports | `src.passport_generator` | JSON passports → Markdown prompts **+ render manifests** |
| 2 render | `src.render_stage` (facade) | → raw PNG |
| 3 process-images | `src.image_processor` | raw PNG → final WEBP (1600², ≤500 KB) |

### The render manifest is the Stage 1 → Stage 2 contract

`schemas/render_manifest.schema.json` is the one authoritative description of what
Stage 2 receives; `src/render_manifest.py` is its only implementation, used by the
provider to emit and by consumers to load. Stage 1 writes one manifest per SKU to
`04_passports/render_manifests/`. If none exists, `blender_renderer` builds it in-process
through the same builder, so `--render-only` still works standalone.

Plain JSON Schema rather than pydantic, because `render_driver.py` runs inside Blender's
bundled interpreter where neither pydantic nor project modules are importable. Validation
therefore happens twice on the project side — on write and on load — and the driver trusts
the shape.

Two things the manifest exists to get right:

- **It carries the carton, i.e. the SECONDARY packaging.** The primary package (blister,
  bottle, syringe) is a smaller object, and for elongated primaries `resolve_secondary()`
  permutes the axes. The driver used to read `primary_package` dimensions and build the
  carton from them — wrong in scale and sometimes orientation. That bug was dormant only
  because `primary_package` is always `null` on disk, so it always fell through to a guess.
- **Orientation comes from the template, not the dimension string.** The same
  `115x55x48mm` is landscape for `T1` and portrait for `T_VERT_INHALER`; the same
  `110x50x18mm` is landscape for `T_MULTIPACK` and portrait for `T_VERT_DROPPER`.
  `orient_for_template()` stands the longest edge up for the vertical family and leaves
  every other template in the passport's own order.

`carton.source` records provenance (`passport_secondary` / `derived_from_primary` /
`template_ratio`) so guessed geometry is visible rather than silent. All 391 SKU currently
resolve to `passport_secondary`, and a test fails if any regresses to a guess.

### Stage 2 is a two-engine facade

`MODULE[STAGE_RENDER]` points at `src/render_stage.py`, never at an engine directly. The
facade skims `--engine` off argv, rebuilds `sys.argv`, and delegates to an **unmodified**
engine module:

```
main.py --render-engine blender
  └─ build_cmd() → python -m src.render_stage --engine blender ...
       └─ src/blender_renderer.py  (or src/rpa_orchestrator.py for gemini)
            └─ subprocess: blender.exe --background --python assets/blender/render_driver.py
```

Neither engine knows the other exists. Keep it that way — engine-specific behaviour belongs
in the engine, engine *selection* belongs in the facade.

**The two engines deliberately read different inputs.** Gemini consumes the compiled
Markdown prose (an LLM prompt); Blender consumes the structured JSON passports — Stage 1's
*input*, not its output — because a 3D renderer needs `{palette, primary_package,
label_content, template_id}`, not prose. This is intentional, not an inconsistency.

**Output directories are segregated by engine** (`01_input_raster/gemini_renders_raw` vs
`02_processing/blender_test_renders`). Resume logic scans the output dir for existing PNGs
and cannot tell which engine produced a file, so mixing them would corrupt both resume and
Stage 3. Stage 3 still sources from the Gemini dir by default — feeding Blender output into
it currently needs a manual `image_processor.source_dir` override via `--config`.

Blender runs as an **external executable**, never imported. `import bpy` appears only in
`assets/blender/render_driver.py`, which executes inside Blender's own bundled interpreter.
There is no pip-installable Blender dependency.

### Template routing has one owner

`agent_1_router()` in `src/passport_generator.py` decides `(template_id, is_bottle_override)`
for every SKU. `src/blender_renderer.py` **imports and calls it** rather than
re-implementing the decision — do not duplicate routing logic into a renderer.

Routing precedence: SKU.csv-driven vertical-container check first (→ `T_VERT_VIAL` /
`T_VERT_DROPPER` / `T_VERT_INHALER` / `T_BOTTLE_BOX`), then sachet/tube/pen → `T3`, then the
`pharma_pkg/geometry_mapping.py` family table, then a pill-count refinement splitting `T1`
into `T1_SMALL` (≤10) / `T1` / `T1_LARGE` (>60).

Two things that mislead on first read:
- The `T_VERT_*` templates render the **secondary carton, not the bottle itself** — a box is
  the correct geometry there, not a placeholder.
- `is_bottle_override` is reachable only through the family-table fallback and is
  effectively never `True` in current data.

`T2` has zero SKU in this catalogue.

### `verification_agent.py` does not look at images

Despite the name, `agent_2_verifier()` is a **pre-render JSON linter**: 12 consistency checks
over the passport dict (palette vs SSOT registry, dosage contains a digit, SKU present in
the registry, …) producing a confidence score, gated at 0.75. It runs *before* rendering and
annotates the Markdown prompt. It never opens a PNG, for either engine.

There is currently **no post-render image verification anywhere in the project**. The
`ROADMAP_ONLY`-marked Pydantic models in `schemas/` (`ObservedZone`, `ObservedPalette`,
`UVBox`) are unused scaffolding intended for that future step.

The closest thing to an output check is a guard in `main.py`: Stage 2 exiting 0 while
producing zero PNGs is forced to a failure, because per-SKU render errors are logged rather
than fatal.

## Fork-specific gotchas

**`config.yaml` is required here, not optional.** The built-in defaults in `src/utils.py`
still point at the *original* PharmaGen PRO layout (`SSOT/`, `pipeline/`, `render_output/`,
`output/`). This fork remapped every path onto numbered folders, so deleting or bypassing
`config.yaml` silently resolves paths to the wrong places.

**`SSOT/` is a deliberate compatibility mirror of `03_knowledge_graph/`.** It exists because
`verification_agent.py` hardcodes `Path("SSOT/SKU.csv")` and `Path("SSOT/master.json")` and
does not read config. Without the mirror, CHECK 12 silently fails and every passport's
confidence drops 1.0 → 0.9. If you make that module config-driven, the mirror can go.

**`primary_package` is `null` in the stored JSON passports.** It is computed at runtime by
`get_primary_package()` / `resolve_secondary()` in `src/passport_generator.py` and never
persisted. Anything reading passports off disk for dimensions gets nulls. Use the render
manifest instead — it resolves carton dimensions from `secondary_packaging.dimensions`,
which every SKU in the catalogue has.

**`render.engine` defaults to `blender`** in this fork's `config.yaml`; the source project
defaults to `gemini`.

**Filename convention is `-min` stems** (`1-min.json` → `1-min.png`). The legacy
`output/*.webp` in the source project used bare numeric names; don't reintroduce that.

**Root-level `pass_tomd.py`, `webp_converter.py`, `gemini_image_generator.py` are
compatibility shims** re-exporting from `src/`. Edit the `src/` module, not the shim.

**`docs/` and `00_governance/` are near-duplicates** — `00_governance/` holds the forked
ADR/audit/release docs, `docs/` is the full safety-net copy of the source project's docs.
The Blender roadmap exists only in `docs/experiments/`, despite a stale cross-reference in
`NEXT_STEPS.md` claiming otherwise.

## Reference-matching constraints

Blender output is judged against the curated reference renders in `01_input_raster/reference/`,
analysed in [`01_input_raster/reference_analysis.md`](01_input_raster/reference_analysis.md).
Hard constraints derived from that analysis:

- **White carton body always**, regardless of `palette.primary`. Brand colour appears in
  exactly two places: a bottom accent stripe on the front face (~8–12% of face height) and a
  square badge in the top-right corner. Never elsewhere.
- **Matte cardboard**, roughness ~0.6–0.8 — not semi-gloss.
- **Near-shadowless high-key lighting** ("product floating on white"); a visible contact
  shadow is a mismatch.
- **No depth-of-field.** References read as fully sharp; DOF is deliberately disabled in the
  driver even though an f/8 aperture value is set.

Light energies in `render_driver.py` are studio-strobe scale (25 W key / 8 W fill) because
room-scale wattages blow out the frame at this macro object scale — a real bug that was
found and fixed; don't "correct" them back up.
