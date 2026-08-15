# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A standalone fork of **PharmaGen PRO**, created to develop headless-Blender rendering as
the packshot engine. It turns a per-SKU JSON "passport" (brand, dosage, palette, packaging
geometry) into a rendered pharmaceutical-packaging image. 391 SKU in the catalogue.

The fork carries the *whole* original pipeline forward (Gemini RPA engine included) — the
Blender engine is an alternative Stage 2, not a replacement of the codebase.

Read [`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md) for status and
[`06_docs/experiments/BLENDER_RENDERER_ROADMAP.md`](06_docs/experiments/BLENDER_RENDERER_ROADMAP.md)
for the Blender-engine design rationale and its phase plan.

## Commands

No venv is checked in. Python 3.10.11 is on PATH and the suite passes against it.

```bash
# Tests — stdlib unittest, NOT pytest (pytest is not a dependency)
python -m unittest discover -s tests          # 200 tests (69 need Blender; 2 slow gates, opt-in)
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

# Measure the built scene WITHOUT rendering — how the carton's art-direction
# invariants are tested (tests/test_blender_carton.py), since bpy can never be
# imported from the project's Python and pixel-inspecting a render is brittle.
blender --background --factory-startup --python 05_assets/blender/render_driver.py -- \
    --job 04_passports/render_manifests/1-min.json --dump-scene scene.json
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

`carton.source` records provenance so guessed geometry is visible rather than silent. Since
1.3 it describes the SCENE geometry (`art_direction` / `art_direction_declined_orientation`
/ the three raw-size values); where the real measurements came from moved to
`carton.passport_dimensions.source`. All 391 SKU resolve to `passport_secondary` there, and
a test fails if any regresses to a guess.

**Contract version is `1.5`.** Bumps up to 1.3 and again at 1.5 added or repurposed
*required* fields — deliberately not additive-optional changes, so a manifest written before
them fails validation loudly instead of quietly producing a packshot with something missing.
`manifest_version` is pinned by `const` in the schema, so stale files on disk are rejected
until Stage 1 regenerates them.

- `1.5` — **`design.type_rows.cap_frac` repurposed from an ink height to a CAP height**, with
  `cap_top_v` and `read_as` added beside it as required. An OCR box is the extent of the
  *glyphs*, so how much of it is cap height depends on which letters the reference's own
  string happens to carry — measured over the twenty rows this sample has, **1.034 to 1.384,
  mean 1.180**. Using it as a cap height set every row that much oversized, and the error was
  a property of another manufacturer's wording rather than of anything about our carton.
  `read_as` is what makes the conversion possible and is therefore required now rather than
  optional. This is a repurposing, not an addition: a 1.4 row is not a 1.5 row missing a
  field, it is the same number meaning something else, so it must fail rather than be read.
  The proxy is stated where it is taken (`ink_profile`): the reference's typeface is unknown,
  so the glyph profile is measured in the face this project prints in.

- `1.4` — **`design`, the one optional block**, and the exception is deliberate: 380 SKU have
  no reference photography to measure, so requiring it would fail the catalogue. Loudness moved
  to where it can still be enforced — `src/design_group.py` raises `MissingDesignSpec` for a SKU
  that IS in the group and has no spec, rather than letting it fall back to the generic art
  direction and render a plausible carton in the wrong colours. A test asserts all eleven carry
  it. Where the block is present `carton.source` reads `design_spec` and the carton is built to
  the reference's **front-face** aspect — a different quantity from `TARGET_SILHOUETTE_ASPECT`,
  which is the whole visible silhouette; the spec's `u,v` are normalised to the printed face,
  so matching the wrong one puts every outline somewhere else. `reshape_to_design()` keeps the
  long edge and assigns it by orientation, so Lexotanil's portrait 2.026 gives 57×115 rather
  than inflating the carton to 110×223 to carry a proportion.

  **Two scripts write `design_spec.json` and neither may erase the other.**
  `scripts/fit_design_spec.py` owns `fields`, `scripts/measure_type_rows.py` owns
  `type_rows`, and the fitter runs first. It used to rewrite the file wholesale, so
  re-running it deleted every measured row and all eleven manifests came back with
  `"type_rows": {}` — every design carton silently back on the generic grid, nothing
  raised. The fitter now carries the block forward and a test compares each manifest's
  `type_rows` against its spec's.

  **A component enters the spec by running off the face, reading as a block, or filling
  its own bounding box with hairlines removed — never by being large.** The size escape
  was removed because it could not be repaired by size: Xanax's traced "XA" covers 3.4%
  of its face and Xanax Pfizer's genuine magenta panel 3.2%. They separate on box fill,
  0.49 against 0.96, and the panel needs the despeckle because a ONE-PIXEL thread down
  the carton edge stretches its bounding box and halves the ratio. Keep the block test in
  the middle: the four references that reverse the dosage out of a filled block leave
  letter-shaped holes, so Cialis's block fills 0.70 by pixels against 0.95 by outline.

- `1.1` — `label_content.active_ingredient_display`. Also the one field the builder cannot
  read off the passport's `label_content` like its siblings: the passport keeps the
  ingredient at its **top level**, as `active_ingredient`.
- `1.3` — **repurposed** `carton.width_mm/height_mm/depth_mm` into art-directed scene
  geometry and moved the carton's real size to `carton.passport_dimensions`. Build the box
  from the first; **print only the second**. Printing solved geometry would put a
  measurement on pharmaceutical packaging that no carton has — the same act as printing a
  plausible LOT, which this driver already refuses.
- `1.2` — `carton.features` and `carton.material`, which the side panel is drawn from.
  `features` is real per-SKU data, not decoration: 370 of 391 declare
  `["Braille", "DataMatrix_Zone", "Tamper_Evident_Seal"]` and **21 declare nothing**, so a
  renderer that assumes every carton is identical gets those 21 wrong. It travels on all
  three carton-resolution paths, not just the happy one.

### Stage 2 is a two-engine facade

`MODULE[STAGE_RENDER]` points at `src/render_stage.py`, never at an engine directly. The
facade skims `--engine` off argv, rebuilds `sys.argv`, and delegates to an **unmodified**
engine module:

```
main.py --render-engine blender
  └─ build_cmd() → python -m src.render_stage --engine blender ...
       └─ src/blender_renderer.py  (or src/rpa_orchestrator.py for gemini)
            └─ subprocess: blender.exe --background --python 05_assets/blender/render_driver.py
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
`05_assets/blender/render_driver.py`, which executes inside Blender's own bundled interpreter.
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

**There is no `SSOT/` directory any more — the data lives only in `03_knowledge_graph/`.**
A mirror used to exist because `verification_agent.py` hardcoded `Path("SSOT/SKU.csv")` and
`Path("SSOT/master.json")` outside the config system. Both now go through
`src/utils.get_path`, so the duplicate is gone and the module works from any working
directory. If you see `SSOT/` referenced in an older document, it means
`03_knowledge_graph/`.

**`primary_package` is `null` in the stored JSON passports.** It is computed at runtime by
`get_primary_package()` / `resolve_secondary()` in `src/passport_generator.py` and never
persisted. Anything reading passports off disk for dimensions gets nulls. Use the render
manifest instead — it resolves carton dimensions from `secondary_packaging.dimensions`,
which every SKU in the catalogue has.

**`render.engine` defaults to `blender`** in this fork's `config.yaml`; the source project
defaults to `gemini`.

**`blender.engine_type` must be a real Blender engine identifier, and an unavailable one
is fatal.** `CYCLES`, `BLENDER_EEVEE`, `BLENDER_WORKBENCH` — *not* `EEVEE`, which Blender
rejects. `setup_render()` no longer substitutes a working engine for a missing one: it
raises `SystemExit`, matching `main.py`'s refusal to call a zero-PNG Stage 2 a success.

Do not test engine availability by introspecting
`bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items`. `engine` is a *dynamic*
enum; that expression returns only a static placeholder (`('BLENDER_EEVEE',)` on 5.1.2)
and never lists `CYCLES`, even where Cycles is enabled and rendering fine. The driver used
to do exactly this, so every Blender render silently came out of EEVEE with
`blender.samples` never applied. Assign the engine and catch the error instead.

Related: Blender exits **0** after printing an ordinary uncaught exception. A hard failure
in `render_driver.py` must be `SystemExit` (exit 1) or `blender_renderer.py` will read the
run as a success.

**`blender.samples: 16` is a measured value, not a default.** Rendering 1-min at 2048²
against a 256-sample reference: 16 samples reaches 60.6 dB PSNR, 64 reaches 63.3 dB, and
both are far past the ~40 dB point where differences stop being visible — Cycles'
denoiser, not the sample count, is doing the work. Stage 3's own LANCZOS resize and WEBP
encode shift pixels *more* than the gap between 16 and 64 does, and the resulting WEBP sits
at quality 95 / ~26 KB against a 500 KB cap, so nothing downstream is straining either.
Cost is **28.2 s vs 57.6 s** per SKU, i.e. ~3 h vs ~6 h for a full 391-SKU pass. Cutting
samples further buys little: **18.8 s of every render is fixed**, so even zero samples costs
19 s. Re-measure after any change that adds glass, metal, or real global illumination to the
scene.

**Where a render's 28 s actually goes** (measured, `00_PROJECT_STATE/R006_STARTUP_COST.md`):
the denoiser ~14.9 s, sampling ~9.7 s, Blender startup 2.6 s, scene build 0.3 s, and Cycles'
device init plus BVH build plus PNG save ~1 s between them. **The denoiser is more than half
of every render** — the one lever that would meaningfully speed up a catalogue pass is GPU
denoising, not sample count, and not a persistent batch process. Batch mode was measured at
1.84 s per SKU (6.7%) and deliberately **not built**.

EEVEE is **not** an equivalent shortcut, despite costing ~7 s. Against the same reference
it scores 28.1 dB with 28.6% of pixels off by more than two levels, and the difference map
shows the whole front face shifted — a systematic exposure/saturation change, not noise.

**Filename convention is `-min` stems** (`1-min.json` → `1-min.png`). The legacy
`output/*.webp` in the source project used bare numeric names; don't reintroduce that.

**Root-level `pass_tomd.py`, `webp_converter.py`, `gemini_image_generator.py` are
compatibility shims** re-exporting from `src/`. Edit the `src/` module, not the shim.

**`docs/` and `00_governance/` are near-duplicates** — `00_governance/` holds the forked
ADR/audit/release docs, `docs/` is the full safety-net copy of the source project's docs.
The Blender roadmap exists only in `06_docs/experiments/`, despite a stale cross-reference in
`NEXT_STEPS.md` claiming otherwise.

**OCR needs the face flattened first.** The carton is rotated 27.5-35 degrees
about Z, and Tesseract reads a skewed face very badly — measured, "Atomoxetine
Generic" comes back as "Germetine" and one render returns an empty string, in
every page-segmentation mode. The same strings drawn flat in the same vendored
font read 4 of 4. `render_driver.py` therefore emits `{stem}.view.json` with the
printed faces' corners in image pixels, and `src/deskew.py` flattens the front
face before `scripts/render_qa.py` reads it. Do not recover those corners from
the image: a colour mask keyed on `palette.accent` cannot separate the accent
stripe from the brand badge.

## Reference-matching constraints

Blender output is judged against the curated reference renders in `01_input_raster/reference/`,
analysed in [`01_input_raster/reference_analysis.md`](01_input_raster/reference_analysis.md).

**Two of these constraints are now conditional, and which is which matters.** The eleven SKU
in `src/design_group.py` are judged against *real packaging photography* instead — see
[`00_PROJECT_STATE/DESIGN_FIDELITY_PLAN.md`](00_PROJECT_STATE/DESIGN_FIDELITY_PLAN.md). For
them the measured design governs:

| constraint | 380 SKU | the design group |
|---|---|---|
| white body, brand colour in exactly two places | holds | **superseded** — the carton's own board and fields |
| matte, roughness 0.7 | holds | holds |
| near-shadowless high-key, no contact shadow | holds | holds |
| no depth of field | holds | holds |

Surface colour is superseded because it is a *design* rule fitted to nine AI renders, and two
of the eleven real cartons have a coloured board (Kamagra teal, Lexotanil lime) — it fails
inside the sample, not at its edge. Finish and lighting are **not** superseded: the design
spec carries no print finish, and the owner's brief was composition and colour. The
references are glossy and our renders are matte; that is a known, deliberate difference
rather than an oversight.

The scene tests say which path they cover, and `TestCartonSurfaceColour` asserts its own
fixture is not a design SKU — pointed at one, it would fail the renderer for obeying the
contract.

Hard constraints derived from the AI-reference analysis, i.e. the generic path:

- **White carton body always**, regardless of `palette.primary`. Brand colour appears in
  exactly two places, and the two take *different* palette entries — swapping them is the
  easy mistake:
  - a bottom stripe on the front face in **`palette.accent`**, 3–6% of face height
    (pixel-measured across all 9 references; the "8–12%" that used to be documented was
    eyeballed and roughly double the truth), full width, front face only — it does not wrap
    onto the side panel;
  - a square badge in the top-right corner of the front face in **`palette.primary`**
    (9/9 references), side ~25% of the *shorter* front-face edge, inset ~5% of face width
    from the right and ~3% of face height from the top.

  Never elsewhere.
- **Matte cardboard**, roughness ~0.6–0.8 — not semi-gloss. `MATTE_ROUGHNESS = 0.7` covers
  the body, the stripe and the badge; printed ink sits on the same matte board.
- **Near-shadowless high-key lighting** ("product floating on white"); a visible contact
  shadow is a mismatch. Measured, the references sit at 254.9 directly under the carton —
  there is no contact shadow to speak of. The driver's backdrop is therefore an **emissive**
  plane, not a diffuse floor lit by the key: it takes no cast shadow, renders a seamless
  255 with no hot spot, and is switched out of all indirect ray paths so it cannot bounce
  back and wash out the accent (a no-op under EEVEE, load-bearing under Cycles).
- **No depth-of-field.** References read as fully sharp; DOF is deliberately disabled in the
  driver even though an f/8 aperture value is set.
- **The front-panel label grid**, in the face's own coordinates (u across, v down), measured
  off the references: brand name at v 0.10, active ingredient at v 0.46, then dosage
  bold-left and unit count right-aligned sharing v 0.80. Rows start at u 0.07 and the unit
  count ends at u 0.95. Still missing versus the references: the braille row, and the side
  panel's barcode / LOT / EXP / microprint.

### Text is real geometry, and the font is vendored

Label rows are Blender text objects, not textures. That is the engine's headline advantage:
`reference_analysis.md` §7 caught the Gemini renders printing **"Datels"** — not a word — as
a side-panel label. A text object draws the string it is handed or nothing at all, so a test
compares the built `body` byte-for-byte against the manifest. Don't replace this with baked
image textures; the guarantee is the point.

Fonts live in `05_assets/blender/fonts/` (DejaVu, redistributable — see `LICENSE_DEJAVU`) and
are **not** taken from the system, because a system font silently changes the render on a
machine that lacks it and the project's determinism invariant forbids that. Sizes are set as
cap height, not Blender's `size`: the two differ by a per-font ratio (~0.49 for DejaVu) that
`_cap_ratio()` measures at runtime, so the grid constants mean what they say and swapping
the font does not resize every label in the catalogue.

**Type size follows two different laws, and using one for everything is wrong.** The brand
name scales with the carton — 6.3mm on a T3 up to 30.6mm on a T_VERT_VIAL, a 4.9× spread,
but a steady 0.131–0.209 of face height. The small print holds its size in *millimetres*:
the bottom row measures 4.4–5.5mm on eight of the nine references while varying 3.5× as a
fraction of the face. Driving the small print off face height gives 2.9mm on a T1 — half the
reference — and 8.8mm on a vial, where the bottom row's two strings then collide.

Layout is fitted by **measuring the built text**, never by trusting the nominal size, and
every one of those correction passes exists because a full 391-SKU sweep found a real
failure the nine curated templates did not show:

- the brand shrinks to clear the ingredient row when it wraps (18 SKU wrapped; all 18 ran
  into the row below);
- the brand's right limit comes from where the badge actually lands, since the badge is
  sized off the *shorter* face edge and so eats far more width on a portrait carton;
- the bottom row rises as a unit to clear the accent stripe — lifting each string
  separately moves "40mg", which has a descender, further than "10 Pills", which has none,
  and they stop sharing a baseline;
- the small print is capped at 0.12 of face height so it cannot crowd a shallow T3.

Re-run that sweep after touching the grid. The unit suite covers the cases we know about;
the sweep is what finds the ones we don't.

**Where a design spec carries a measured row, that row overrides the grid — and it is set
against its CAP LINE at both ends.** Two quantities were confused there at once, and both
depend on glyphs the reference's string happens to carry rather than on anything about our
carton:

- `align_y="TOP"` pins the top of the font's *line box*, which stands above the tallest
  glyph by the font's ascent-above-cap. Anchoring a measured row by it dropped every one
  below its target — 0.109–0.231 of a cap height, eight rows, none above. `_cap_drop()`
  measures where a capital's top sits below that origin, per unit `size`, so `_align_cap_top`
  is exact and — unlike an ink measurement — string-independent and stable across
  `_fit_width`.
- `cap_frac` was the *ink* box height used as a cap height, over-sizing every row by
  1.034–1.384. Fixed at the measuring end in contract 1.5, so the field means its name.

**A row that will not fit its measured box is NARROWED before it is reduced.** Our typeface
is wider than the printed ones — measured with the reference's own string on both sides,
DejaVu needs a median of **1.29** times the width it occupies on the photograph — so a row
set at the measured cap height often overruns the box. Of the two numbers, only the cap
height was measured; the width DejaVu needs is a property of a font nobody chose to match.
`_fit_width(condense=True)` therefore takes `scale.x` down to `CONDENSE_FLOOR = 0.80` first
and lets `size` give way only after that. Fifteen of twenty rows now keep their measured cap
height exactly, against ten before. A row built *larger* than its measurement has no such
excuse and a test forbids it.

`condense` is passed **only from `_place_measured_row`**. The 380 generic cartons' row widths
are this project's own art direction, not a measurement of anything, so there is nothing
there to protect and they build identically.

**Do not read that 1.29 as better than ±0.3.** A reference face is rectified to the quad's
own averaged edge ratio in the photograph, which under perspective is not its true aspect,
and a horizontal stretch is indistinguishable from a condensed typeface once the glyphs are
all you have. Across the ten folders, how far the photographed aspect departs from the
catalogue's correlates with how wide DejaVu looks at **+0.79**. Two other explanations were
tested and dismissed: OCR boxes are tight (box/ink median 1.02), and the 2.37 outlier was a
wrong row rather than a wide font — see `number_conflicts()`.

Two consequences worth holding on to:

- **A measured row lands anywhere, so a row still on the grid can be printed through it.**
  The reference decides where a measured row goes; the grid is fixed. On `135-min` the
  reference sets the brand at v 0.432–0.562 and the grid sets the ingredient at 0.46, so
  "Ativan" printed straight through "Lorazepam" and the OCR barrier read *nothing* off that
  face in either polarity. `_clear_below()` lowers the grid row; at the foot of the face
  there is nowhere below to go, so the bottom row instead gains a floor on `_lift_row()` and
  **rises** — `340-min` sets its unit count in the bottom-left corner the grid hangs the
  dosage in. Both guards test **both axes, and require an actual intersection**: the first
  version of the `_lift_row` floor cleared every measurement sharing a column and threw
  Kamagra's whole bottom row from v 0.81 to v 0.07, over the top of the carton.
- **`cap_frac` is the reference's ink-box height being used as our cap height**, and where
  the two strings carry different ascenders and descenders the sizes still differ — measured,
  0.55–1.34 of the reference's box. That is a question about what D-2b measured, not about
  where the driver puts it. Open; see `00_PROJECT_STATE/D7_TYPE_FIDELITY.md`.

**A measured box has to cover the string it claims to measure, at both ends.** Two ways it
does not, and `measure_type_rows` guards each:

- *Too wide.* The reader groups words by vertical centre, and a carton sets several labels
  on one line, so a row's box spans them all. `narrow_to_string()` trims a row to the words
  that spell the string being asked about, and **claims WORDS, not rows** — otherwise
  Viagra's dosage matched "50 mg" out of "50 mg film-coated tablets" and took the unit
  count's words with it. Both sides go through this one function; do not re-implement it in
  `type_qa`.
- *Too narrow.* `MATCH_MIN` guards this, and 0.5 was the wrong number for a reason worth
  keeping: `_similar` divides by the longer string, so **0.5 is very nearly the score of a
  box covering half its string**. Three rows entered there, covering 47%, 47% and 25% of the
  ink in their own band — Xanax's brand box read u 0.410–0.823 against a wordmark running
  0.113–0.822, and the renderer set our brand in the middle of the face. 0.6 is "more than
  half, with room for a misread"; the next score in the sample is 0.74, so the evidence
  fixes the floor rather than the value.

`scripts/type_qa.py` is the instrument for all of this — the type axis D-6 explicitly does
not cover, since every figure there excludes dark pixels.

### The side panel prints only what it was given

The visible side panel is the carton's local **−X** face: the camera looks along +Y and the
carton is rotated +35° (or +27.5°) about Z, which turns the −X normal toward the camera and
to the left of frame. The +X face is never seen.

Magnify the reference side panel before trusting it. Its 2D code is a blob of noise with no
finder pattern; its LOT/EXP values read `SLAQF FDЯT`; its microprint is not text. **That
panel is evidence of layout, not of content.** What the driver builds instead:

- **A real Code 128** subset B of `sku_id`, encoded by `encode_code128b()`. A test decodes it
  back out of the built *geometry* — recovering spaces from the gaps between bars, the way a
  scanner does — and re-derives the modulo-103 checksum, so "it is a real barcode" is a fact
  rather than a claim. Do not replace it with a decorative bar pattern.
- **LOT and EXP as empty labels with a rule.** No values, deliberately: the project holds no
  lot or expiry data, and a real carton carries none either — they are inkjetted at packing.
  Printing a plausible-looking value would be inventing data on pharmaceutical packaging.
- **A data block** of manifest strings only: board material, dimensions, packaging geometry,
  and the carton's declared `features`.

**Not built: any 2D symbol.** The module width measures 0.08–0.40mm across the catalogue,
below the ~0.19mm a scanner needs on every panel shorter than ~90mm, and the driver warns on
stderr when it is. That is an argument *for* a proper DataMatrix later — same payload, far
less area, which is why the passports declare a `DataMatrix_Zone` — not for faking one.

Watch the axis when adding to this panel: `object.dimensions` in Blender is the **local**
bounding box scaled, not a world AABB, so a row's reading length is always its local `.x`
however the object is rotated. Measuring the wrong axis silently disables the fit. And the
panel rotation is `(90°, 0, −90°)`; `+90°` about Z leaves the normal pointing *into* the
carton and the text renders mirrored.

### The light rig is one studio for all 391 SKU

Everything about the rig is a multiple of the carton's own `target_size = max(w, h, d)`, so
from the carton's point of view the lights always arrive from the same direction and subtend
the same angle. Only the distance scales — and therefore the power must too.

- **`KEY_ENERGY_W = 25` / `FILL_ENERGY_W = 8` are the power at `LIGHT_REF_SIZE_M = 0.115`,
  not for every carton.** They stay studio-strobe scale because room-scale wattages blow out
  the frame at this object scale — a real bug that was found and fixed; don't "correct" them
  back up. 0.115 m is both the T1 family's largest dimension and the catalogue's modal
  carton (259 of 391 SKU), so most of the catalogue is lit at literally these numbers.
- **`light_energy()` scales power with the SQUARE of the size ratio.** Distance grows
  linearly with the carton and irradiance falls as 1/d², so anything less leaves big cartons
  dark: before this, the front face ran 182–255 across templates with five of nine clipping,
  against a reference band of 235–241. After, 236–239. Don't "simplify" the square away.
- **The key is on the camera's RIGHT (+X), the fill on its LEFT.** Prose descriptions of
  this project have had it the other way round; the code is correct, the prose is not.
- **`KEY_OFFSET = (3, -3, 3)`, and the constraint is all three faces at once.** The
  references light a carton almost flat: side/front 0.995 across a 0.855–1.081 spread,
  top/front 1.020 across 0.969–1.042. The faces are separated by their edges, not by
  modelling. Two rigs failed that in opposite directions, and the front-face band was
  correct in both, which is why neither was caught by a test:
  - `(2, -2, 3)` stood the printed face almost edge-on to the key (cos 0.119 against the
    top face's 0.728) and rendered the **top face at a clipped 255.0, brighter than the
    254.96 backdrop**. The carton had no lid and read as a flat label. The *fill* was doing
    the key's job on the front face, 5.94 against the key's 2.98.
  - `(2, -4.5, 3)` fixed the lid and blew the **side panel** instead — 95.4% clipped, so
    the panel merged into the backdrop and its barcode and LOT/EXP appeared to float.
  - `(3, -3, 3)` cleared both, but its landscape lids still clipped in their brightest
    40–60%: the mean sat inside the band while the gradient's bright end saturated.
  - `(3, -3, 2)` — the key LOWERED, which is what stops that. Landscape lid clipping goes
    39.7% → 0.0% on `1-min` and 59.7% → 9.2% on `111-min`. Exposures −2.18 / −2.21.

  **The elevation has an optimum, not a direction.** Below z≈1.7 clipping starts rising
  again and the side panel climbs out of the reference spread — measured at z = 3.0, 2.4,
  2.0, 1.7 and 1.4.

  **Moving the whole rig farther away makes it worse, not better.** Tested at 1.8×, 3× and
  5× the offsets with matched angular size and compensated exposure: top/front rises 1.17 →
  1.31 because at distance the rig approaches a directional light, where the lid's
  geometric cosine (0.577) dwarfs the printed face's (0.142). Proximity was helping.

  **One rig cannot match the references on both shapes.** They are AI images and draw every
  face at nearly one tone whatever the carton's proportions; a real rig cannot, because a
  landscape carton presents a large lid to the key and an upright one presents almost none.
  Lowering the key to clear the landscape lids costs the portrait lids their tone —
  top/front 0.793–0.817 against a reference band of 0.969–1.042. That trade is deliberate:
  a dim lid still carries gradient, a clipped one carries nothing.

  **Do not estimate this from a Lambertian dot product.** That model scores the shipped-
  broken rig 2.60 and the working one 2.05 — too close to tell apart, and it says nothing
  about the side panel, which turned out to be where the light actually went.
  `test_no_face_of_the_carton_is_blown_to_white` measures pixels instead.
- **Light size has no lower clamp.** A clamp makes small cartons relatively softer-lit than
  big ones — a per-template style difference, which is what the rig exists to avoid.

Exposure is a **film** setting, kept strictly separate from those energies: pin
`FILM_VIEW_TRANSFORM = "Standard"` and meter per carton shape —
`FILM_EXPOSURE_LANDSCAPE = -2.18`, `FILM_EXPOSURE_PORTRAIT = -2.21`, measured under
CYCLES on the true-scale carton. (They were −2.76 / −2.84 for the old edge-on key. Exposure
could never have fixed that rig: metering the front face to 238 is precisely what pushed
the lid past clipping.)

**Two exposure buckets are not enough, and one shape is knowingly out of band.** `111-min`
(T3, the flattest carton at 140×55.5×25) lands at 233.2 against a reference floor of 235.0.
This is not new and not caused by the rig change — under the previous rig the case out of
band was `268-min` at 232.98 instead, one of four either way. `TestRenderedLuminance.
KNOWN_UNDER_BAND` ratchets it so it cannot quietly get worse; the fix is a metering model
covering more than landscape and portrait.
The lighting is bit-identical for both shapes; a wide front face simply sits ~2 face-widths
from the key across its width and reads ~0.1 stops darker than a narrow one, which is
geometry rather than a defect (see `reference_analysis.md` §9, §12). This is what a
photographer does anyway — re-read the meter, don't touch the strobes.

**`film_exposure()` picks its shape from `width_mm >= height_mm`, and since contract 1.3
that is the art-directed geometry, not the carton.** `T_VERT_VIAL` reshapes to 172×170 and
is metered as landscape although it photographs portrait — the same box-versus-picture
confusion the reshape's flip guard exists to avoid. Known, not yet fixed: the driver cannot
import `src.silhouette` to ask which way the picture falls.

**Never introspect the render-engine enum.** `RenderSettings.engine` is a DYNAMIC enum:
Blender builds its real item list through an RNA callback at assignment time, and
`bl_rna.properties["engine"].enum_items` returns only the static placeholder —
`('BLENDER_EEVEE',)` on 5.1.2. Code that checks availability that way declares CYCLES
missing on *every* install, including ones where it renders fine, and silently falls through
to EEVEE with `samples` never applied. Assign the engine inside `try/except` and treat
failure as fatal: a quietly swapped renderer changes sampling, denoising and light falloff,
and emits off-spec packshots with nothing in the log to say so.

Blender's default AgX rolls the highlights off far enough to hide that the scene is ~2.8
stops hot: the white body still looked plausible while the accent stripe rendered as a pale
pastel. Measure that stop count off an *unclipped* render, never off an AgX one — AgX is not
linear, and estimating from it gives ~2.0, which still clips the T1 front face.

`python -m unittest discover -s tests` asserts the rig's invariants (directions, key:fill
ratio, energy-vs-size law) from `--dump-scene`, without rendering. Two gates are opt-in
because each renders real packshots: the pixel-level calibration gate, and
`tests.test_render_qa.TestOCRAgainstAFreshRender`, which re-renders the fixture SKU
(`1-min`) and re-runs the OCR barrier against it so the committed fixture under
`tests/fixtures/ocr/` cannot silently drift from what the renderer actually produces:

```bash
PHARMAGEN_SLOW_TESTS=1 python -m unittest tests.test_blender_carton
PHARMAGEN_SLOW_TESTS=1 python -m unittest tests.test_render_qa.TestOCRAgainstAFreshRender
```
