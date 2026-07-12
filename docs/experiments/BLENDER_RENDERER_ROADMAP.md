# Blender Renderer — Experimental Stage 2 Engine

> **Branch:** `feature/blender-renderer-experiment` · **Status:** Phase 0 complete,
> Phase 1 foundation in place · **Date:** 2026-06-28
>
> Goal: an alternative, deterministic Stage 2 (Markdown→PNG becomes
> JSON→PNG) using headless Blender instead of Gemini browser RPA — **without
> touching Stage 1, Stage 3, or the Gemini engine's code paths.**

---

## 1. Analysis — how the current pipeline works and where it extends

### 1.1 Stage 2's real contract (what a new engine must satisfy)

`main.py` treats Stage 2 as an opaque subprocess: `python -m <module> [--all|--limit N] [--from STEM] [--estimate]`,
judged only by **exit code** and **artifact count** (`main.py:331-334` — a render
that exits 0 but writes 0 PNGs is now treated as failure, a fix from the
Production Hardening phase). Whatever the module is, it must:

1. Read the stage's declared input dir (`paths.passports_md` today).
2. Write one PNG per SKU stem into its declared output dir.
3. Skip already-done SKUs when re-run (resume).
4. Exit non-zero on a genuine failure; exit 0 with per-SKU failures logged is
   acceptable (the existing Gemini engine does this).

This contract is engine-agnostic — nothing in `main.py` assumes Selenium/Chrome.
That is the extension point: **Stage 2 is already swappable if the module name
is swappable.** `MODULE = {STAGE_RENDER: "src.rpa_orchestrator"}` (`main.py:44-48`)
is the single hardcoded coupling, and `build_cmd()` (`main.py:94-104`) is the
single place that constructs its argv.

### 1.2 Why the Gemini engine reads Markdown but Blender should read JSON

`src/rpa_orchestrator.py` consumes **`pipeline/passports.markdown/*.md`** — a
compiled natural-language prompt (art direction as prose) meant for an LLM.
Blender needs none of that prose; it needs **structured fields**:
`branding.palette.{primary,accent,background}`, `label_content.{brand_name_display,
dosage_display,unit_count_display}`, `primary_package.{type,geometry,width_mm,
height_mm,depth_mm}`, `packaging_geometry`. All of this already lives in
**`pipeline/passports/*.json`** (Stage 1's *input*, not its output) — see e.g.
`pipeline/passports/1-min.json`. **Conclusion: the Blender engine reads the JSON
passport directly, not the Markdown.** This is a deliberate, documented deviation
from "read the same input as Gemini" — it is the *correct* input for a
structured 3D renderer and avoids re-parsing prose.

### 1.3 The one real integration gap: template routing is not persisted as data

The template decision (`T1`, `T1_SMALL/LARGE`, `T2`, `T3`, `T_BOTTLE_BOX`,
`T_MULTIPACK`, `T_VERT_VIAL/DROPPER/INHALER` — 10 IDs, `src/passport_generator.py:947-958`)
is computed by `agent_1_router(data)` (`src/passport_generator.py:178`) and baked
straight into the Markdown text. It is **never written to disk as data** — no
renderer other than "read the English sentence" can know which template a SKU
routed to. **Resolution used here:** import and call `agent_1_router` directly
from `src/blender_renderer.py` (already a supported import surface — the root
shim proves `pass_tomd.agent_1_router` is public API). This is a **read-only
reuse**, zero duplication, zero risk to Stage 1's behavior or its
byte-identical-Markdown invariant.
**Recommended for Phase 2 (not done here):** have Stage 1 additionally emit a
small structured **render manifest** (`{template_id, is_override, palette,
primary_package, label_content}`) per SKU, so *any* future renderer (Blender or
otherwise) has a stable, versioned data contract instead of importing an
internal function from another engine's module.

### 1.4 Fallback dimensions already exist and were reused, not re-invented

`get_primary_package()` (`src/passport_generator.py:237+`) falls back to fixed
mm dimensions when `primary_package` fields are null: **85×55×8** (blister/flat),
**15×120×15** (slender/vertical), **35×95×35** (bottle) — see
`src/passport_generator.py:286-290`. The Blender driver reuses these exact
numbers so geometry is consistent between engines even when SSOT data is sparse.

### 1.5 Optical language is already documented and was reused

The Gemini prompt templates hardcode `25° pitch, box rotated 35°, 85mm lens, f/8`
for most templates and `20° pitch, 25–30° rotation` for the vertical family
(`src/passport_generator.py:570+`, cataloged in
[DESIGN_RATIONALE.md](../DESIGN_RATIONALE.md) §1). The Blender camera rig uses
the **same angles**, so a side-by-side comparison isolates rendering quality,
not art-direction drift.

### 1.6 Files studied (for the record)

`main.py`, `src/utils.py`, `src/rpa_orchestrator.py`, `src/passport_generator.py`,
`src/image_processor.py`, `pharma_pkg/geometry_mapping.py`,
`schemas/common.py`, `verification_agent.py`, `config.yaml`, one representative
JSON passport (`pipeline/passports/1-min.json`), `docs/ARCHITECTURE.md`,
`docs/DESIGN_RATIONALE.md`, `docs/DECISIONS/ADR-001..006`.

---

## 2. Architecture decision: output segregation (not in the original ТЗ, required for correctness)

Gemini and Blender **must not write to the same `render_output/raw/` directory.**
If they did, resume (`load_progress()` scans the raw dir for existing PNGs)
could not tell which engine produced a given file, Stage 3 could silently mix
Gemini and Blender assets in one WEBP batch, and re-running with a different
`--render-engine` would think work is "already done."

**Decision:** `render_output/raw/` stays Gemini's dir (`paths.renders_raw`,
**unchanged** — 100% backward compatible, zero risk to the 391 existing PNGs).
Blender gets its own directory, `blender.output_dir` (default
`render_output/raw_blender/`), and its own progress bookkeeping scoped to that
directory. Feeding Blender output into Stage 3 today requires pointing
`image_processor.source_dir` at `render_output/raw_blender/` via `--config`
(documented limitation, §6 Risks — a clean per-engine Stage-3 source is Phase 2).

---

## 3. Branch

```bash
git checkout -b feature/blender-renderer-experiment
```

Created from `master` at the `v1.0.1` tip. All work for this experiment lives on
this branch; `master` is untouched until a merge decision is made (§7).

---

## 4. Road Map

### Phase 0 — Facade & wiring (✅ done, this commit)

| Item | File | Notes |
|---|---|---|
| `render.engine` + `blender.*` config | `config.yaml`, `src/utils.py` | New sections; defaults preserve current behavior (`engine: gemini`). |
| `--render-engine {gemini,blender}` CLI flag | `main.py` | Optional; `None` → facade uses config default. Forwarded via `build_cmd`, not an env var (Stage-2-only concern). |
| Stage 2 facade | `src/render_stage.py` (new) | `main.py`'s `MODULE[STAGE_RENDER]` now points here; it dispatches to `src.rpa_orchestrator` or `src.blender_renderer` by rebuilding `sys.argv` and delegating — **neither engine module is modified**. |
| Engine-aware pre-flight | `main.py` `preflight()` | Chrome-profile check only fires for `engine=gemini`; a new Blender-executable check fires for `engine=blender`. |

**Complexity: Low.** Pure plumbing; no rendering logic. Verified: `gemini`
remains the default and every existing command/test is unaffected (§8).

### Phase 1 — Blender pipeline foundation (✅ vertical slice done, this commit)

| Item | File | Notes |
|---|---|---|
| CLI orchestrator mirroring `rpa_orchestrator`'s surface (`--limit/--all/--from/--estimate`) | `src/blender_renderer.py` (new) | Reads **JSON** passports; resume via PNG-exists scan of `blender.output_dir`. |
| Template resolution reuse | same file | Calls `agent_1_router()` from `src.passport_generator` (§1.3) — no re-implementation. |
| Per-SKU render job | same file | Serializes a small `{template_id, palette, primary_package, label_content, packaging_geometry}` JSON "job" and shells out to headless Blender. |
| bpy scene driver | `assets/blender/render_driver.py` (new) | Runs **inside** Blender's Python (`blender --background --python render_driver.py -- --job ... --out ...`). Builds a **procedural** primary form (box or cylinder, sized from `primary_package` mm / fallback dims), applies `palette.primary`/`palette.accent` materials, sets up camera/lighting matching the documented optical calibration, renders one PNG. |
| Real smoke test | — | Rendered SKU `1-min` end to end through the real, installed Blender 5.1.2 on this machine (§9). |

**Design choice — procedural scenes, not static `.blend` template files.** The
original ТЗ envisioned a library of hand-authored `.blend` scene templates per
geometry family. Those are binary assets that must be modeled inside Blender's
GUI by a person — they cannot be authored by this tool. The driver instead
**builds geometry procedurally from passport data** (box/cylinder primitives,
data-driven dimensions and materials), which is more consistent with the rest of
this pipeline's config/data-driven philosophy and requires no asset-authoring
step to get a working render. `blender.scenes_dir` is still wired up as an
**optional** override: if a hand-authored `{template_id}.blend` exists there,
Phase 2 can load it via `bpy.ops.wm.open_mainfile` instead of building
procedurally — both paths can coexist.

**Complexity: Medium** (done as a working slice; production-grade shading and
composition is a Phase 2/3 concern, see below).

### Phase 2 — Full template & branding integration (not started)

| Item | Business value | Effort | Dependencies |
|---|---|---|---|
| Cover all 10 template IDs (currently: generic box + generic cylinder; multipack/blister-card/tube geometries not yet modeled) | Full catalogue coverage | M | Phase 1 driver |
| Label text rendering (brand name, dosage, unit count) as real 3D text/decals, not just color blocks | Visual parity with Gemini's labeled output | M–L | Font asset, text-wrap logic |
| Accent-stripe geometry (Row 6 front-face rule, from `DESIGN_RATIONALE.md` §1) | Brand-rule parity | S–M | material UV mapping |
| Optional hand-authored `.blend` templates per family, loaded when present | Higher art-direction ceiling than procedural-only | M | artist time (out of engineering scope) |
| Structured render-manifest emitted by Stage 1 (§1.3) | Decouples future renderers from importing `agent_1_router` directly | S | Stage 1 (additive, non-breaking) |

### Phase 3 — Quality & production readiness (not started)

| Item | Business value | Effort | Dependencies |
|---|---|---|---|
| Render settings tuning (samples, denoiser, GPU device selection) for speed/quality balance | Throughput | S–M | Phase 2 |
| Batch + resume hardening (retry/backoff parity with `rpa_orchestrator`) | Reliability parity | S | Phase 1 (foundation present) |
| `verification_agent.py` integration for Blender output (reuse existing checks; add render-specific ones, e.g. non-blank-image check) | QA parity | S–M | — |
| Comparative test: Blender vs Gemini on a fixed sample (quality, speed, consistency, determinism) | Go/no-go evidence | M | Phase 2 |

### Phase 4 — Polish & merge strategy (not started)

| Item | Notes |
|---|---|
| Docs: README addition, new `ADR-007-blender-renderer.md` | Follows the existing ADR format |
| Tests for `src/render_stage.py` dispatch logic | Facade is small and unit-testable without Blender installed |
| Parallel-use support (`--render-engine` per run, already true today) | Already satisfied by the facade design |
| Merge strategy | Recommend: keep as a long-lived feature branch until Phase 3's comparative test produces a quality verdict; only then decide merge-to-`master` vs. permanent-experiment. **Do not merge before Phase 3.** |

---

## 5. New/changed files (this commit)

```
config.yaml                          # + render:, blender: sections
src/utils.py                         # + matching _DEFAULTS
main.py                              # MODULE[render]->render_stage, --render-engine flag, engine-aware preflight
src/render_stage.py                  # NEW — Stage 2 facade (engine dispatch)
src/blender_renderer.py              # NEW — Blender engine (CLI, job building, subprocess driver)
assets/blender/render_driver.py      # NEW — bpy scene builder, runs inside Blender
docs/experiments/BLENDER_RENDERER_ROADMAP.md   # this file
```

`src/rpa_orchestrator.py`, `src/passport_generator.py`, `src/image_processor.py`,
`verification_agent.py`, `pharma_pkg/`, `schemas/` — **unchanged**.

---

## 6. Risks & mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| **Blender learning curve** for whoever extends Phase 2 (materials, shader nodes, UV text) | Slows Phase 2 | Procedural approach keeps Phase 1 approachable Python, not GUI-modeling; Phase 2 can be scoped incrementally per template. |
| **`.blend` file management** (binary, hard to diff/review in git) | If Phase 2 adopts hand-authored templates | Keep them **optional** (procedural is the default/fallback); if adopted, store via Git LFS, not plain git. |
| **Text rendering quality** (3D text vs. Gemini's photoreal label rendering) | Visual gap on label-heavy SKUs | Explicitly scoped to Phase 2; Phase 1 intentionally ships without polished text to prove the pipeline plumbing first. |
| **Output collision with Gemini** | Data corruption / ambiguous resume | Solved now via segregated output dirs (§2) — not deferred. |
| **Stage 3 doesn't know which engine to source from** | Manual `--config` override needed today | Documented limitation; Phase 2 candidate: per-engine Stage 3 source selection. |
| **Render time** (Cycles path-tracing is slower than a cloud LLM per image at high sample counts) | Throughput vs. Gemini | `blender.samples`/`engine_type` are config-tunable (EEVEE for speed, Cycles for quality); benchmark in Phase 3. |
| **Per-SKU Blender process startup cost** — `render_one()` launches a fresh `blender.exe --background` subprocess per SKU. Measured: 26.4s first render vs. 5.1s second (same scene complexity) — the ~20s delta is Blender's own boot time, paid **on every image**. At 391 SKU sequential, that alone is ~2h of pure startup overhead. | Batch throughput; likely the dominant cost, not the render itself | Not fixed in Phase 1 (out of scope — plumbing-proof only). Phase 3 fix: keep one Blender instance alive for the whole batch (e.g. drive `bpy` in-process from a persistent Blender, or a job-queue server inside one long-lived `--background` session) instead of one subprocess per SKU. |
| **GPU/CPU render backend variability across machines** | Non-reproducible performance (not visual output — Blender rendering is deterministic given the same scene/seed, unlike Gemini) | Config exposes `engine_type`; document minimum hardware expectations in Phase 3. |
| **Headless Blender environment issues** (missing GPU drivers, `--background` quirks) | Render failures | `blender_renderer.py` treats a missing executable or non-zero Blender exit as a hard pre-flight/per-SKU failure, mirroring the Gemini engine's failure handling. |

---

## 7. Explicit non-goals of Phase 0/1

- No changes to Stage 1, Stage 3, `verification_agent.py`, or the Gemini engine.
- No merge to `master` proposed yet — this stays an experiment until Phase 3
  produces a quality/throughput verdict (§4, Phase 4).
- No hand-authored `.blend` assets (binary, out of this tool's reach) — the
  procedural path is the Phase 1 deliverable; `.blend` support is wired as an
  optional Phase 2 path.
- No label-text rendering polish, no multipack/blister-specific geometry yet —
  Phase 1 proves the plumbing with a generic box/cylinder primitive.

---

## 8. Validation performed for Phase 0/1

- `python main.py --help` — new `--render-engine` flag present; unaffected otherwise.
- `python -m unittest discover -s tests -p "test_*.py"` — unchanged, still green (no test touches Stage 2).
- Default behavior (`--render-engine` omitted) resolves to `engine=gemini` and
  invokes `src.rpa_orchestrator` exactly as before — verified via
  `src/render_stage.py`'s delegation logic.
- Real end-to-end Blender smoke test — see §9.

## 9. Smoke test result

Rendered `1-min` (Atomoxetine Generic → routed to `T1`, `packaging_geometry:
BLISTER`, `primary_package` fields null → falls back to the template's
documented 2:1:1 aspect ratio) through the real installed **Blender 5.1.2** on
this machine:

```
python -m src.blender_renderer --from 1-min --limit 1
```

**First attempt found a real bug, not just a stub success.** The initial
lighting rig used AREA-light wattages sized for room-scale Blender scenes
(800W/300W); at this pipeline's macro object scale (~0.05–0.3m, camera ~0.3m
away) that overexposed the entire frame to solid white (verified: all RGB
channels clipped to 254–255). Caught by actually opening the rendered image,
not just checking "PNG file exists." **Fixed** by reducing to studio-strobe-scale
wattages (25W key / 8W fill) and pinning the world background explicitly
(`assets/blender/render_driver.py::setup_lighting`) — the smoke test was
re-run and produces a correctly exposed, clearly visible carton: pink body
(`palette.primary #DDA7A5`), magenta accent stripe (`palette.accent #6B2D5C`),
3/4 isometric framing, soft shadow, white background.

**Determinism verified empirically** (not merely claimed): the same SKU was
rendered twice independently; the two PNGs are **pixel-identical**
(`ImageChops.difference` → zero-extent diff). This is a genuine, checked
advantage over the Gemini engine, which is non-deterministic by design (see
[RELEASE_CERTIFICATION.md](../release/RELEASE_CERTIFICATION.md) and
[TECHNICAL_DEBT.md](../release/TECHNICAL_DEBT.md) TD-H1) — Blender's
determinism claim in §6 Risks is scoped to *same machine, same render settings*;
cross-hardware (GPU vs. CPU Cycles backend) reproducibility was not tested here.

This proves the full chain (facade → engine selection → JSON read → template
routing reuse via `agent_1_router` → Blender subprocess → procedural
scene/material/camera/lighting → PNG output → resume bookkeeping) works end to
end, produces a correct and legible image, and is reproducible.

**Not yet covered by this slice:** label text (brand name/dosage/unit count are
in the job data but not yet rendered as visible text/decals — Phase 2), and
only `T1`'s proportions were exercised (the other 9 template IDs use the same
code path with different ratios, untested beyond code review).
