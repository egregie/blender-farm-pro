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

`carton.source` records provenance (`passport_secondary` / `derived_from_primary` /
`template_ratio`) so guessed geometry is visible rather than silent. All 391 SKU currently
resolve to `passport_secondary`, and a test fails if any regresses to a guess.

**Contract version is `1.2`.** Both bumps so far added *required* fields — deliberately not
additive-optional changes, so a manifest written before them fails validation loudly instead
of quietly producing a packshot with something missing. `manifest_version` is pinned by
`const` in the schema, so stale files on disk are rejected until Stage 1 regenerates them.

- `1.1` — `label_content.active_ingredient_display`. Also the one field the builder cannot
  read off the passport's `label_content` like its siblings: the passport keeps the
  ingredient at its **top level**, as `active_ingredient`.
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
Cost was 67 s vs 167 s per SKU, i.e. ~7 h vs ~18 h for a full 391-SKU pass. Roughly 45 s of
each render is fixed cost (startup, BVH build, denoiser) and Cycles' adaptive sampling
already stops converged pixels early, so cutting samples further buys little. Re-measure
after any change that adds glass, metal, or real global illumination to the scene.

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
Hard constraints derived from that analysis:

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
- **Light size has no lower clamp.** A clamp makes small cartons relatively softer-lit than
  big ones — a per-template style difference, which is what the rig exists to avoid.

Exposure is a **film** setting, kept strictly separate from those energies: pin
`FILM_VIEW_TRANSFORM = "Standard"` and meter per carton shape —
`FILM_EXPOSURE_LANDSCAPE = -2.76`, `FILM_EXPOSURE_PORTRAIT = -2.84`, measured under
CYCLES on the true-scale carton. The lighting is
bit-identical for both; a wide front face simply sits ~2 face-widths from the key across its
width and reads ~0.13 stops darker than a narrow one, which is geometry rather than a defect
(see `reference_analysis.md` §9). This is what a photographer does anyway — re-read the
meter, don't touch the strobes.

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
