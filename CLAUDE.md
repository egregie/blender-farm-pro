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

**Contract version is `1.10`.** Bumps up to 1.3 and again at 1.5, 1.6, 1.7, 1.8, 1.9 and
1.10 added or
repurposed *required* fields — deliberately not additive-optional changes, so a manifest
written before them fails validation loudly instead of quietly producing a packshot with
something missing. `manifest_version` is pinned by `const` in the schema, so stale files on
disk are rejected until Stage 1 regenerates them.

- `1.10` — **`design.marks[]`, the third-party and regulatory marks a PERSON approved by
  name.** 22 marks across 12 of the 28 folders: 8 holes and 14 components listed `yes` in
  [`00_PROJECT_STATE/MARKS_DECISION.md`](00_PROJECT_STATE/MARKS_DECISION.md), and nothing
  else. Required and usually empty — a 1.9 manifest read as 1.10 is not a carton with no
  marks, it is a carton whose marks were never decided, and that is not a default any
  producer may supply. Each mark carries the `print_truth` key that permitted it, so a
  drawn mark can be put back against the row that allowed it. Write-up in
  [`00_PROJECT_STATE/MARKS_DRAWN.md`](00_PROJECT_STATE/MARKS_DRAWN.md).

  **`src/marks_decision.py` makes the decision file's own rule executable.** That file
  says no code may run until its Purpose, Basis and Scope are written by the owner, and
  the loader raises `MarksNotDecided` when any is blank. `yes` is the only value that
  permits anything — tested against `no`, `n/a`, empty, `maybe`, `YES?` and
  `yes, but only in print`. No class name is special-cased: the Lilly holographic oval is
  refused because its row says `n/a`, and a test asserts the loader does not name it in
  code so a reclassification cannot quietly re-open it. An ABSENT file raises rather than
  returning an empty set, because "no to everything" is a valid signed outcome that looks
  identical to one.

  **The pairing rule holds in three places.** `fit()` cuts a mark hole and emits its mark
  from ONE loop, so the unpaired case is unreachable in the producer;
  `parts[].mark_holes` records which cut rings are marks, without which the rule is
  unverifiable on a manifest at all; and `_reject_unpaired_marks` refuses BOTH directions
  on write and on read, because a manifest is a file and a rule only the producer keeps is
  a rule the artefact does not carry.

  **The index-based figures cannot judge a mark and now say so.** `verify()`,
  `design_coverage` and `design_qa` compare region IDENTITY against a vocabulary of
  FIELDS, and a mark is deliberately neither a field nor the board. Scored anyway it is a
  category error, measured as one: `230_Slimex`, whose only spec content is two approved
  marks, read **0.00%** and `272_Valium_Brand` 54.31%, because every pixel they draw met a
  ground truth that says substrate. Widening that truth to admit approved marks was tried
  and recovered 0.20 points. So a mark's area leaves the scored set in all three, on BOTH
  sides — cutting and drawing is neutral there rather than banking what cutting alone
  earns, which is what the decision file meant by *"the +9.937 is not carried forward"*.
  In `design_qa` there is a sharper reason: **a mark's colour is not in the palette**, so
  every mark pixel would classify to whichever field entry happened to be nearest.
  `region_colour_gap` does judge them — its regions come from `spec_index`, which gives a
  mark its own index — and it is the right instrument because it needs no word for one.

  **`_substrate_core` had to exclude marks.** A mark can be the colour of the board:
  `74_Viagra`'s oval is `#D8D9D5` against a substrate of `#DDDEDB`, **0.0364 apart**, so
  it classified as substrate and the illumination plane was fitted through a region the
  spec paints separately.

  **Five marks were painted solid where the carton prints an OUTLINE**, and that is the
  largest defect this contract introduced. `holes: []` was written on the strength of
  `MARKS_EVIDENCE.md` measuring every approved region solid — true of the eight holes,
  which fill 0.9–1.0 times the ink they describe, and false of the components:
  `230_Slimex`'s `brand#9` filled **9.5×** its ink, `272_Valium_Brand`'s `brand#1` 9.0×,
  `157_Valium`'s Roche hexagon 8.4×. That is a worse reproduction than the carton's own
  rather than a lesser one — it invents a filled logo where the pack prints a line — and
  it was measurable: `157-min` declared `#022E99` while the photograph inside that same
  region read `#B8BEC3`. A mark now carries its own holes, traced **without** consulting
  `print_truth.json`, and that is not a relaxation of 1.8: that rule protects a printed
  FIELD from showing board in the shape of the reference's lettering, while here the ring
  is the mark's own interior and leaving it filled is the invention. After: all 22 fill
  0.9–1.4× their ink, and `157-min`'s mark colour gap falls 0.585 → **0.093**.

  **The label grid printed across a mark, and the fix was reverted on a misread
  measurement.** `_prepared_parts` read `design["fields"]` alone, so `157_Valium` set
  "30 Pills" straight over the Roche hexagon and `152_Artvigil` "150mg" over its
  signature swash. Adding marks cleared both and was reverted, on the grounds that
  **"eight OCR rows lost against three gained"** and that `221_Inderal`'s legible white
  "40mg" had been walked off its band.

  **That figure was the cost of DRAWING the marks, not of moving the rows**, and the two
  runs of that attempt are still on record to prove it: with the mover blind the gate lost
  **nine** against the same three, so the grid fix was worth exactly **one row and cost
  none**. `221_Inderal` never moved — none of its rows so much as touches one of its marks.
  Filing the marks' price against the mover is the same error as reading a codec
  disagreement as a carton defect, and it cost this feature a contract phase.

  Retaken over all 28 design cartons plus a generic one, off `--dump-scene` rather than
  off pixels: a seeing mover relocates **exactly three rows and no others**, all
  horizontally, with cap height, size, condensation and ink untouched — `157-min`'s unit
  count 0.170 of the face left off the hexagon, `230-min`'s dosage 0.070 out of the
  Neptune mark's frame, `152-min`'s dosage 0.085 off the swash. **+1 OCR row, none lost**,
  and `TestNoGridRowIsPrintedInInkItsOwnBackgroundHides` goes from two straddling rows to
  **zero**. The other 26 scenes are bit-identical.

  Two of the three gain nothing a reader can score and are still right, which is where
  the guard's own limit shows: it compares the ink's lightness against the surface's, so
  `230-min`'s ORANGE mark on a white board passes while its rule visibly cuts through the
  digits of "15mg". The guard understates; the contact sheet decides.

  **The ink and the move are separate questions with separate warrants**, and that is
  worth keeping even though they got the same answer. The ink's is a principle — a row
  stands on a surface and a mark is one. The mover's is contingent on the cartons in
  front of it, so it was split behind a parameter, measured apart, and the parameter
  removed once nothing took the other branch: an unused value that decides where type
  goes is the objection this file already records against the joint two-axis search.
  If a carton ever enters the group whose mark moves a row somewhere worse, the seam is
  one flag away.

  **What a mark draws is measured, not remembered.** `MARKS_EVIDENCE.md`'s `islands = 0`
  was read as "the wordmark is not carried", and that is false twice: a glyph TOUCHING the
  boundary is a notch rather than an island and survives the trace, and a silhouette of a
  wordmark IS the wordmark. `scripts/measure_mark_shapes.py` reports each emitted
  polygon's **solidity**; 11 of the 22 carry letterform geometry, `152_Artvigil`'s swash
  at **0.190** and `74_Viagra`'s oval at 0.918 with the "fi" ligature notched out of it.
  The owner was shown the drawn shapes, withdrew `59_Cialis brand#9` — which reads "Lilly"
  and turned out to be **the lettering OF the holographic sticker**, its bounding box
  wholly inside the sticker's — and confirmed the rest. **A security feature is refused
  whole, lettering included.**

  Result over fresh renders of all 28: `render~ref` 0.9382 → **0.9398** with 8 up and none
  down, `render~spec` 0.9943 → 0.9946 with none down, `field_iou_worst` 0.9691 → 0.9706,
  and index side `pixel_agreement` 99.18 → **99.27%**, `print_agreement` 52.79 →
  **53.14%**, `truth_agreement` 95.36 → **95.76%**, drawn-off-print 0.76 → **0.72%**.
  **All 16 cartons carrying no mark moved by exactly zero on every figure.**

- `1.9` — **`design.fields[].parts[].fill`, because a colour is a statement about a
  SURFACE and a field is not one.** A field's fill is `np.median(raw_px[cluster])`,
  the median of the whole cluster `segment()` found; a part is one region of it.
  Measured with `scripts/measure_fit_colour.py`, which takes no render and whose own
  floor is **exactly zero on all 28 cartons**, **33 of the group's 75 printed parts sat
  at or beyond `SAME_SURFACE_MAX` from the colour they were painted**, across 20 of the
  28 — `152_Artvigil`'s `brand#1` declared `#E05506` and `#2D3336` in the photograph,
  over 6.47% of the face, at a spread of **0.0000**. Required and often equal to the
  field's: a 1.8 part read as 1.9 is not a part painted its field's colour, it is a part
  whose colour is unknown. Full write-up in
  [`00_PROJECT_STATE/SURFACE_COLOUR.md`](00_PROJECT_STATE/SURFACE_COLOUR.md).

  This is the second attempt. The first went in whole and came out whole (`PART_FILL.md`)
  and closed by naming what a future one would need: an estimator that knows where a
  part's rim is, and a comparison that survives the palette moving under it. Both were
  built first — `PART_COLOUR.md`, `FIT_COLOUR.md` — and **the difference between the two
  attempts is three rules in `_part_fills()`, each added because a measurement demanded
  it**:

  1. **Merge first.** Parts whose own colours lie within `SAME_SURFACE_MAX` are one
     surface, by the constant `segment()` merges clusters at. Without it the threshold
     below splits a single surface: **ten pairs across four cartons**, worst
     `64_Kamagra`'s `highlight#1` and `highlight#3` at **0.0039** apart in the photograph
     and painted differently. Merging takes those ten to two, and the two left are the
     full-region median and the eroded estimate disagreeing at the boundary — where they
     do, this believes the one measured to be better by a factor of four.
  2. **Then threshold against the field.** Emitting every part's own colour regardless is
     what the rolled-back attempt did, and it sends **eight of the 28 cartons** to
     "palette not separable" — measured twice, once by that attempt and once here.
  3. **And never emit a colour the vocabulary cannot hold.** A candidate within
     `SAME_SURFACE_MAX` of the substrate or of another field's colour is refused and the
     part keeps its field's value **even though that value is known to be wrong for it**.
     It fires on exactly two cartons: `59_Cialis`'s highlight lands 0.0761 from its own
     SUBSTRATE, `64_Kamagra`'s 0.0335 from its own brand. The price was measured before
     it was paid — emitting Kamagra's anyway bought **0.0032** of `region_colour_gap` and
     took that carton's `render~spec` IoU from 0.975 and 0.959 to **0.633 and 0.340**.

  **Kamagra says where the real defect is, and it is not here.** Its brand and highlight
  sit **0.0251 apart in the photograph and 0.1221 apart in the spec** — by this project's
  own constant they are ONE surface that the segmentation split and the spec inherited.
  No choice of fill repairs a partition, and `segment()` is frozen by its labelling.

  Target side **33 → 8 of 75** parts beyond the threshold, mean gap 0.1377 → 0.0319; six
  of the eight left are mixed regions with no single colour to estimate (predicted from
  the 1.8 measurement before the producer was switched, and it held), two are what rule 3
  withheld. Render side, over fresh renders of all 28: `region_colour_gap` **0.1958 →
  0.1489 with not one carton rising**, `render~spec` unchanged at 0.9943, `field_iou_worst`
  0.9694 → 0.9691, `render~ref` 0.9395 → 0.9382, and **zero cartons not separable**.

  **One carton loses beyond 0.02 and the acceptance criterion did not anticipate why.**
  `362-min` falls 0.942 → 0.885 on `render~ref` while its palette stays separable, so the
  criterion as written was not met — it was extended after the fact, on this evidence: the
  scored area is bit-identical at 1 335 854 px, `render~spec` is unchanged, its field's
  colour gap improves **0.2493 → 0.0855**, and the share of the PHOTOGRAPH classified as
  that field rises **15.69% → 21.33%**. Its small part is genuinely near-black, so the
  palette gains a dark entry — and a dark entry is a word for the reference's printed
  TYPE, which the spec deliberately does not represent. That is the property already
  recorded here (*a dark pixel where the spec draws the substrate cannot be told from
  type*), reached by a new carton rather than a new defect.

  **The plumbing landed separately and is provably neutral**, so "did the wiring change
  anything" is answered apart from "did the measurement change anything": with every part
  carrying its field's colour, **28 of 28 specs and 391 of 391 manifests are identical**
  once the version and that one key are stripped, `design_coverage` does not move on any
  column, and `157-min` re-renders with **every IDAT chunk byte-identical** — only the
  `tEXt` date and timing chunks differ. Across all three re-fits the specs stay identical
  to their 1.8 selves once `part.fill` is stripped: geometry, `type_rows` and
  `verification` are all untouched.

  Two things fell out of the guards rather than the plan. **The calibration chart is
  itself a design block and its patches carried no fill**, so the driver's new
  `SystemExit` refused it and `calibrate_render.py` stopped producing a curve — caught
  because `driver_fingerprint()` then refused to let `design_qa` run on a stale one; the
  re-measured curve's `rows` are numerically identical. And **`_surface_fill` now reports
  the PART's colour**, so a measured row reversed out of a recoloured part is set against
  what is actually printed under it: eleven such surfaces exist and all eleven stay on the
  same side of `_reverse_ink`'s 0.5 threshold, closest `308-min`'s `brand#1` at 0.426 →
  0.465.

  **The OCR gate moved one row each way, from one cause.** `149-min`'s
  `dosage_display` started reading and `149-min`/`344-min`'s `unit_count_display`
  stopped — the band under both is `brand#1`, taken from its field's `#C84569` to its
  own `#7333B8`, i.e. **0.390 perceived luma to 0.291**. Darker helps white type set ON
  a band and hurts dark type set ACROSS it. Filed as the reader on the two checks this
  file requires rather than on the OCR return: looked at on the rectified face at native
  scale (on `344-min` the row is ENTIRELY on the board beside a small square — the
  `365-min` abutting-edge pattern), and `TestNoGridRowIsPrintedInInkItsOwnBackgroundHides`
  passes on all 28, which judges the cap band. Fixtures rebuilt afterwards rather than
  instead.

  `design_qa`'s palette is now **one entry per painted colour** rather than one per field,
  with `to_field` mapping each entry back before any figure is reported — that is what
  keeps `field_iou_worst` a statement about fields while the classifier works in colours.
  `colour_error_by_region` is consequently keyed by painted colour, and `palette_entries`
  names each index so a reader can tell that two of them are one field.

- `1.8` — **`design.fields[].parts[].holes`, because a part is a REGION and not a ring.**
  A Moore-neighbour trace of a shape with holes in it is a correct boundary and a wrong
  region. Measured over the group's 74 printed parts, the traced rings enclose **1.192 times
  the ink they describe**; `357_Adderall`'s `brand#1` encloses **9.07 times** its own, filling
  53.48% of a face it inks 5.90% of, at an IoU of 0.110 against the component it claims.
  Subtracting *every* hole takes the group to 0.999 and 0.9817 — that is the geometry of the
  primitive, not what ships; see below for which holes are actually cut and why. Required and
  possibly empty: a 1.7 part carries no such key, and read as 1.8 it is not a part with no
  holes but a part whose holes are unknown.

  **Only ten of the group's 238 holes are cut, and which ten is a hand-made judgement.** A
  hole in a printed field is board, and there are exactly two reasons for that: the carton
  leaves it unprinted, or the carton reverses its own TYPE out of the field. Both are the
  same pixels. Three instruments were built to separate them and all three were measured
  failing — the share of the hole lying in a component already classified `type` separates 45
  and misses Cialis's "1", one stroke of "10 mg" that lands in the never-enumerated substrate
  cluster; the reference's own OCR word boxes cover 131 and read **nothing** on
  `344_Modafinil_Generic`, whose ten holes spell "Modalert ® 200" reversed out of a purple
  band; size is the escape this project already removed once. So `print_truth.json` gained a
  second population with its own five-class vocabulary (`window` / `lettering` / `mark` /
  `object` / `blend`), `label_print.py --aid --holes` draws it, and **`window` is the only
  class the fitter cuts**.

  The stake is the invariant rather than the number. `59-min` is a 20 mg Cialis whose
  photograph is a 10 mg pack; `344-min` is Modafinil Generic whose photograph is Modalert 200;
  `404_Ritalin`'s 72 holes are "Ritalin® 10 mg Tabletten" and "50 Tabletten/N2". Cutting them
  shows board through our field in the shape of another package's brand and dose — the same
  act as printing a plausible LOT, which the driver already refuses. Declining costs **0.12
  points** of `truth_agreement`, because letterform holes fall outside the scored area anyway
  — the one figure in this bullet still measured under the truncating reconstruction (see
  the `design_coverage.py` note below), and the only one that cannot be retaken: the fitter
  emits the ten `window` rings and no others, so the remaining 228 exist nowhere but in a
  re-run of the tracer.

  `truth_agreement` over the group goes **91.70% → 95.59%** with nothing regressing on any
  carton: Sonata +45.51, Adderall +45.11, Kamagra +5.22, Valium +1.49, the other 21 unchanged.
  The holes that matter are few and large. (Recorded as 90.62% → 94.20% when 1.8 landed.
  Both ends were retaken once the reconstruction was made an inverse, and the shape of the
  answer — four cartons move, twenty-one do not, none regresses — is unchanged. The
  geometric figures above survive it too: a filled ring gains 0.083% of its area across the
  group's 74, and Adderall's `brand#1` reads 53.48% of the face either way.)

  **The 228 that stay filled were priced, and only two of them are worth anything.**
  `scripts/measure_hole_payoff.py` cuts each hole ALONE and re-scores, without rendering:
  `truth_agreement` is a spec-against-reference figure, so a hole costs one masked
  substitution rather than a render. Full write-up in
  [`00_PROJECT_STATE/HOLE_CEILING.md`](00_PROJECT_STATE/HOLE_CEILING.md).

  By class, in points of group `truth_agreement`: `lettering` 199 holes **+44.433**,
  `mark` 8 holes **+9.937**, `blend` 10 holes +0.847, `object` 12 holes +0.136. Excluding
  lettering the total is +10.920, which passes any threshold worth setting — and **91% of
  it is `mark`**, two holes carrying +5.290 and +3.865: Viagra's and Ativan's Pfizer ovals,
  with Inderal's LCI roundel third at +0.631. Cutting a `mark` hole while drawing nothing
  into it shows board through our field in the shape of another company's logo, which is
  the same act as cutting Ritalin's lettering. **Outside every third party's branding the
  reachable figure is +0.983 points over 22 holes, 23 of the 29 non-lettering holes worth
  under 0.1 each** — below the threshold, so no re-classification pass was run and nothing
  was reclassified.

  What it does open is not an engineering decision: a `mark` hole and a `mark` component
  are ONE decision. Cutting the hole *as part of drawing the mark* is coherent — the hole
  is then a window onto the logo the carton actually prints — and the group's 27 `mark`
  components are already labelled for `design.marks[]`. That path is worth the +9.937 and
  is blocked on reproducing third-party trademarks, which is the owner's call.

  **Looked at, and it changes what is being decided: all eight `mark` holes are SOLID.**
  `islands = 0` and `solid_frac = 1.000` on every one, and `trace_holes()` traces an outer
  boundary and keeps no islands — so what a cut `mark` hole can ever become is a filled
  outline. Measured on the two largest: Viagra's mask is 13 071 px and 13 071 px with holes
  filled, cut as a 47-vertex ring. **The "Pfizer" script is not separated by the
  segmentation, is not carried by the hole, and would not appear in the render.** What would
  appear is the ellipse — the mark's silhouette in its printed position. 92% of the +9.937
  is those two ovals; everything below them is +0.782 and the two Shire fragments are worth
  less than nothing. Evidence and the full 35-entry table in
  [`00_PROJECT_STATE/MARKS_EVIDENCE.md`](00_PROJECT_STATE/MARKS_EVIDENCE.md);
  `scripts/render_mark_evidence.py` regenerates the crops.

  The 27 `mark` COMPONENTS are the other case and carry none of the +9.937: sixteen are
  solid, and a solid mark component is the mark's own printed silhouette rather than a
  container — drawing `133_Ambien`'s eight Hemofarm wordmarks as flat fills would reproduce
  those shapes.

  **Two entries are not branding and are held out of that question by name.**
  `357-min`'s `highlight#0/hole#0` is the **C-II schedule symbol** — a regulatory marking US
  law requires on a controlled substance, not a trademark. `59_Cialis`'s `secondary_1#0` is
  the **Lilly holographic oval**, an anti-counterfeiting feature; it is a component so it
  carries none of the figure, and it is named here so nobody later picks it up by class
  name alone. Reproducing a security element is the act this driver already refuses for
  LOT, EXP, a product code and a 2D symbol.

  Three counts that do not match, so nobody re-derives them: the truth files carry **242**
  hole entries, the partition has **239**, and this file said 238 before the Viagra corner
  fix. The difference is three `74_Viagra` holes flagged `"vanished": true` — labelled
  against the corners `6d37b89` corrected, and KEPT rather than deleted so the
  disappearance is visible. And "239" means holes above `MIN_HOLE_FRAC`: Kamagra's
  `brand#0` mask holds 593 enclosed regions and six clear the floor.

  **The face a spec is traced from is often very small, and that is now declared.**
  `OUT_WIDTH` is 1100 whatever the photograph, so `357_Adderall`'s 134x172 face is enlarged
  **8.21x** and `151_Provigil`'s 147x248 **7.48x**. `SIMPLIFY_TOLERANCE` is a thousandth of
  the rectified width, which on Adderall is 0.13 of a SOURCE pixel — finer than the grid the
  evidence is on. `scripts/measure_face_resolution.py` reports every folder;
  `TestTheFaceResolutionCeilingIsDeclared` names the six below 350px and fails in both
  directions. It is a declaration, not a gate — those folders keep their specs and go on
  rendering; the threshold comes from the one real gap in the distribution, the 20% step
  between 322 and 387 where every neighbouring step above is under 8%.

  **Blender cuts a hole by NESTING, so a hole is another cyclic spline of the same curve.**
  Measured on 5.1.2: a unit square with a 0.5 inner square fills 0.7500 whichever way either
  ring is wound, and the extrude walls the hole too. Two objects would each fill and the hole
  would be painted rather than cut. `--dump-scene` reports `splines` and `fill_area_m2` per
  design part because the bounding box is identical whether a hole was cut or filled in, and
  a test compares that area against the shoelace of outline-minus-holes.

  1.7 and 1.8 compose in that order, and had to: a hole is a window onto whatever is BEHIND
  the part, so it shows the right thing only once the fields stand at different depths.
  `_surface_fill` follows — a measured row inside a hole is printed against what shows
  through, which is what took `64-min`'s dosage from white-on-teal to dark on the board window
  the real carton leaves for its salmon badge.

- `1.7` — **`design.fields[].z`, the paint order, which the contract never stated.** The field
  list has always BEEN ordered — `rasterise()` fills it front to back and every
  `verification.pixel_agreement` was measured against that — but `build_design_fields()` read
  the same list into ONE plane, `location = (0, front_y, 0)` for every part, where nothing is
  on top of anything and Cycles resolves an overlap arbitrarily. Two readings of one record:
  on `357-min` the teal block was erased outright in the target and z-fought in the render.
  Emitted as the index the list already has, so nothing moves; what changes is that the order
  is a value the driver can obey rather than a convention it cannot see. The driver raises
  `SystemExit` on a field without one.

- `1.6` — **`product_code`, separating what is PRINTED from what KEYS the row.**
  `SKU.csv`'s first column is named `picture` and holds the source image's filename. That
  value became the SSOT registry's key, then the passport's `sku_id`, then the manifest's —
  and the side panel prints the identifier under the barcode and encodes it into the Code
  128. So **all 391 cartons carried `.jpg` on them, as a scannable product code.** No single
  step was wrong: `sku_id` really is the catalogue's key and the barcode really should carry
  the SKU. The two questions had never been separated, so the answer to one was used for the
  other. `src/utils.product_code()` is the single implementation (`design_group._stem`
  delegates to it), the schema rejects a `product_code` that ends in an image or `.json`
  extension, and the driver raises `SystemExit` rather than falling back to `sku_id` — a
  silent fallback is how the filename got onto the carton in the first place. It is
  deliberately **not** a GTIN, PZN or national drug code: the project holds none, and
  inventing one is the act it already refuses for LOT and EXP. **`sku_id` keeps its
  extension** and stays the registry key; a test asserts that too, so a later tidy-up cannot
  break every lookup.

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
  direction and render a plausible carton in the wrong colours. A test asserts every member of
  the group carries it. Where the block is present `carton.source` reads `design_spec` and the
  carton is built to the reference's **front-face** aspect — a different quantity from
  `TARGET_SILHOUETTE_ASPECT`, which is the whole visible silhouette; the spec's `u,v` are
  normalised to the printed face, so matching the wrong one puts every outline somewhere else.
  `reshape_to_design()` keeps the long edge and assigns it by orientation, so Ativan's portrait
  1.540 gives 75×115 rather than inflating the passport's 115×55 carton to carry a proportion.
  (This was Lexotanil's 2.026 → 57×115 until the reference swap; its new photograph is
  landscape at 0.398, so the test that pins the property moved to Ativan with it.)

  **Two scripts write `design_spec.json` and neither may erase the other.**
  `scripts/fit_design_spec.py` owns `fields`, `scripts/measure_type_rows.py` owns
  `type_rows`, and the fitter runs first. It used to rewrite the file wholesale, so
  re-running it deleted every measured row and all eleven manifests came back with
  `"type_rows": {}` — every design carton silently back on the generic grid, nothing
  raised. The fitter now carries the block forward and a test compares each manifest's
  `type_rows` against its spec's.

  **A component enters the spec because a PERSON classified it `print`, and every geometric
  admission rule has been removed.** This paragraph used to describe them — runs off the
  face, reads as a block, fills its own bounding box with hairlines removed — and each was
  a proxy for a judgement nobody had made, and each was measured failing: Kamagra's pouch
  entered through "runs off the face", Xanax Pfizer's shaded board through a 0.090 contrast,
  Provigil's box lid and the table under it through both. Size had to go with them, and
  Imovane is the case that proves it — its ONLY printed field is a blue rule covering 0.67%
  of its face, below the old 0.8% floor, so the threshold kept that carton at zero fields
  while a person could see exactly what was there.

  `Reference Templates/*/print_truth.json` now states, once per component, whether it is
  printed design, an object lying in front of the carton, a letterform, a logo, something
  this vocabulary cannot hold, or one surface counted twice — **664 components across the
  28 folders, and since contract 1.8 a second population of 238 holes.**
  `scripts/label_print.py` enumerates, draws the aid, records the labels and verifies that
  none is missing; `fit()` hard-fails without a truth file or against stale face corners, and
  emits the `print` set and nothing else. A label is only valid for the corners it was made
  against, and `verify()` refuses when they have moved.

  What is given up, stated rather than glossed: a person could still call a wordmark `print`,
  and no test catches that. What catches it is `label_print.py --aid`, which tints every
  component by its class over the rectified face, so a wordmark labelled as design is visible
  at a glance. The guarantee moved from a proxy to a judgement, and the judgement is recorded
  per component with its area and its bounding box.

  **`scripts/design_coverage.py` is the figure to read, and `verification.pixel_agreement` is
  not.** That field scores the whole face, and the substrate covers 87–96% of these cartons,
  so it is very nearly a statement about the BOARD: `155-min`, `304-min` and `308-min` each
  scored a perfect 1.0000 while carrying zero fields against photographs whose printed design
  covers 7.0% to 11.6% of the face. `truth_agreement` scores the union of "the reference
  prints something here" and "the spec draws something here", over what a person classified,
  and `spec_off_print_pct` reports what the spec draws where the reference prints nothing.
  Both are added BESIDE the old field, never in place of it — other records cite it.

  **The instrument was rebuilding half of every ring a WHOLE PIXEL off the pixel it was
  traced from.** A spec stores an integer pixel index out of `trace_outline` as
  `round(x / w, 4)` — Douglas-Peucker and `simple_ring` both DROP vertices rather than move
  them, so every coordinate on disk is one — and `part_region` multiplied it back. That
  lands within **0.0826 px** of the integer and falls on either side of it, and **PIL
  truncates a float polygon coordinate**: measured on Pillow 12.2.0, a vertex at `x − 0.02`
  fills as though it were at `x − 1`. A fortieth of a pixel of storage became a whole pixel
  of displacement, signed differently vertex by vertex, across 94.52% of the 9912
  coordinates this group holds. Rounding the product recovers the traced integer exactly,
  with 0.417 px of margin before the choice could be ambiguous. The region keeps its size
  while it moves, which is why this cost agreement without costing coverage and was
  invisible in every other figure. `truth_agreement` 94.20% → **95.59%**, gained on all 25
  cartons that carry a field and lost on none; `print_agreement` 50.46% → 50.84%;
  `spec_off_print_pct` 0.79% → 0.75%.

  **It recovers the TRACE and not the component**, and the difference is worth stating so
  the fix is not read as more than it is. Against the 37 printed fields a person labelled,
  the snapped reconstruction means an IoU of 0.9184 and **none of the 37 reaches 1.0000** —
  worst `155-min`'s highlight at 0.678. That residue belongs to Douglas-Peucker, which
  throws vertices away deliberately, and to `_despeckle`; it is not the storage's, and this
  change neither repairs nor disturbs it.

  **It ships for all three readers, and the switch that let them differ is gone.** It landed
  first on `design_coverage` alone, with `rasterise()` and `verify()` left on the old
  reconstruction so that two published figures would not move inside a commit about a third.
  Both were then retaken deliberately. A default that rebuilds a region somewhere other than
  where it was measured is not a default anyone should be able to take by accident, and a
  reader holding its own idea of what a part covers is the defect `part_region` exists to
  prevent.

  **A re-fit was measured before it was run, and it changes the `verification` block and
  nothing else.** `fit()` rewrites `design_spec.json` wholesale, which is how
  `measure_type_rows`' work was once silently deleted, so the dry run compared every key of
  a fresh spec against the one on disk across all 28: outlines, holes, fields, `type_rows`,
  `face_aspect`, `substrate` — identical on every carton, with only `pixel_agreement` and
  `iou_by_field` moving. The real run then changed 62 lines in 25 files and no others.
  `pixel_agreement` +0.00 to +0.38, mean +0.131, monotone up, group **99.10% → 99.23%**;
  the three cartons with no field were already at 1.0000 and stay there.

  This is the one place the rule "never rewrite `verification.pixel_agreement`" is set
  aside, and the reason is that the rule protects a RECORD OF A MEASUREMENT — while what
  stood in those 25 files was the record of a broken one. `iou_by_field` mattered more than
  the headline: `design_coverage.print_iou` is built from it, so that figure was being
  computed from displaced regions too, and it moved on **every one of the 25**, group
  **67.08% → 67.96%**, nothing regressing — `304-min` +5.09, `134-min` +2.90, `155-min`
  +2.54.

  **`design_qa` moved least of the three, and the one carton it cost was named in advance.**
  Its figures were retaken twice over the SAME renders — once with the old reconstruction
  restored — because `design_qa.json` was written on 2026-08-19 and five driver commits, a
  re-measured calibration curve and this re-fit all landed after it, so a single fresh report
  attributes nothing. Holding the pixels fixed, the reconstruction is worth a mean of +0.06
  on `render~spec`, +0.34 on `field_iou_worst` and +0.03 on `render~ref`, and it costs
  `365-min` **1.30 points** of its worst field, 0.996 → 0.983. That is the carton the
  seam-band measurement had already picked out: of the pixels a face moves, 0.0% survive
  `design_qa`'s own exclusion on 25 of the 28, 31.4% on `365-min` and 8.9% on `404-min` —
  and `404-min` came out at +0.00 on every field, so the prediction was right about which
  cartons were exposed and pessimistic about the second. `59-min` gains 2.60 and 6.30 on its
  two fields, `304-min` 1.60, `150-min` 1.00.

  **`spec_vs_reference` is not a `design_qa` computation at all** and moves by exactly zero
  here: it is the stored `verification.pixel_agreement` read back off the spec, so it
  carries the re-fit's number and never touches `part_region`. Worth stating because the
  column sits in the same table as three figures that do.

  And the rest of what a fresh report shows is NOT this change: `357-min` gains 80.30 points
  of worst field and `362-min` 88.10 against the August file, which is the clearing search
  and contract 1.8 becoming visible in a report that had not been run since before either.
  The two runs separate the reconstruction from everything else; they do not separate the
  driver from the curve from the re-fit, and nothing here claims they do.

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
Stage 3.

**Stage 3 follows the selected engine on its own** — `image_processor.source_dir` and
`output_dir` are both `auto`, resolved through `src.render_stage`, so with
`render.engine: blender` Stage 3 reads `02_processing/blender_test_renders` and writes
`02_processing/blender_renders_final`. A real path in either key is a live override and
wins. No `--config` is needed. (This paragraph used to say the opposite, and was stale: the
constant pointing at the Gemini directory was replaced by `_engine_aware()`, whose comment
records the bug it removed — `main.py --full` rendering with Blender, converting Gemini's
renders, and reporting success.)

**Resume in Stage 2 is unconditional and there is no force flag.** `load_progress()` calls a
SKU done if `{stem}.png` exists in the output dir, so re-rendering the catalogue means
moving the existing PNGs aside first. Stage 3 is the other way round: it overwrites unless
`--resume` is passed.

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

**`design_qa`'s headline agreement is area-weighted, and a substrate is 55–99.9% of these
faces. Read `field_iou_worst`.** **Thirteen of the 25 cartons that carry a field round to
100.0% agreement**, and their worst fields run from 93.3% to 100.0%: `155-min` reads 99.96%
while the field it matches worst reaches 93.3%, twentieth of the 25. Agreement is largely a
statement about the board.

(Illustrated until 2026-08-23 with Ritalin the best carton by agreement and Cialis the
worst, measured on the eleven-carton group and the previous photography. Neither survives
the move to 28 cartons: Ritalin now ranks nineteenth by agreement and Cialis twenty-third,
and the worst is `357-min` at 93.1%. The reading the paragraph exists for is unchanged.)

**The four hand-set corners are an INPUT nothing checks, and every figure below
them inherits whatever they enclose.** `74_Viagra`'s `front_face_px` bounded the
right two thirds of its front face — the navy Pfizer band, a quarter of the
carton, fell outside — and the render came out a white box with a small square.
Every instrument called it healthy: `truth_agreement` 99.47%, `spec~ref` 100.0%,
`render~spec` 100.0%, `field_iou_worst` 99.4%. They all compare our render with
what the corners produced; the corners themselves are compared with nothing.

It reached that state twice over. The second time the corners followed the
carton's physical edge, which put the CREASE inside the face: between the band
and the edge lay a strip 0.95% of the face, 57.4% shading and 42.2% blown-out
substrate, and the tracer walked round it — 75 of that ring's 110 segments under
10px, every one on that edge. Moving the left corners in by the crease width
(p90, 18px along the edge's own normal) took the outline to 34 vertices, and the
`highlight` cluster stopped separating at all: it WAS the crease. The corners
bound the printed FACE, not the box.

**`truth_agreement` fell from 99.47% to 94.18% as that carton was fixed**, and
that is the clearest statement of what it cannot see. It scores the union of
"the reference prints here" and "the spec draws here" over what a person
classified — so where the classification writes the design off, both sides agree
on emptiness and the figure reads near-perfect. `print_agreement` moved the
right way, 19.41% → 73.98%, and so did the ratio the report already prints
side by side:

    print% / truth%   12.71 / 2.48 = 5.1x   →   28.27 / 21.74 = 1.3x

That ratio is the cheap screen for "the labelling wrote the design off", and
across the group it ranked `340-min` worst at 8.2x. A second screen catches the
corner error itself: the rectified face's aspect against the aspect our own
carton is built to. Seven of the 28 sit at 2.20–3.70 and the other twenty-one at
1.60 and below, with nothing in between — but it only screens. The photograph
may legitimately show a different pack, and only the contact sheet decides which.

**Two protections against a corner change are asymmetric, and the gap is what
carried the stale rows.** `print_truth.json` records the corners it was made
against and `verify()` refuses when they move. `type_rows` records nothing, and
`fit()` deliberately carries it forward — the mechanism that stops
`measure_type_rows`' work being silently deleted is exactly what carried
`74_Viagra`'s four rows, measured on the old crop, onto the new face. Three of
the four then printed in ink their own background hides, and
`_clear_of_design` never touched them because it is grid-rows-only and these
are measured. Re-measuring put all four right of the band, as the reference has
them. Note also that `label_print --init` MERGES old classes onto new components
while rewriting the corners it validates against; after a corner change every
component has to be classified again by hand, not trusted to the merge.

**A rule that straightens a ring segment lying on the face boundary was built,
tested and discarded.** Three synthetic properties held — a notch is closed, a
region with a clean margin does not move, a corner-only contact does not fill a
whole side — and on real data it was both too weak and too strong: `74-min`
unchanged, because the band does not reach the edge in the ragged region at all,
and `150-min` 1.06% → 9.57%, filling the full width from contacts scattered
across it. The raggedness was never the tracer's; it was the crease being inside
the face.

**Named and not fixed: the pale blue strip.** `74_Viagra` prints `#ADC5DE`
between the band and the substrate, u 0.233–0.269, 3.6% of the face width. The
segmentation is k-means at k=4 and all four clusters are spent on substrate,
brand, highlight and type; a fourth printed colour does not fit the model. Raising
k changes every published figure for all 28 cartons, so this is a decision rather
than an oversight.

**A figure that was never taken must not print as a figure that came out zero.**
`render_vs_reference` needs the rectified photograph on disk, and `design_qa` keys it by
FOLDER NAME — so when `aa28834` renamed `64_Kamagra_Template_Reference` and
`74_Viagra_Template_Reference`, two previews were orphaned and the report went on printing
**0.0%** for both. A render matching its own photograph on no pixel at all is a startling
number, and nothing was startled by it, because the same cell prints 0.0% whether the
measurement failed or the file was never there. `64-min` reads **89.0%** and `74-min`
**94.4%**.

Four columns did this, with the right idiom already on the same line — `resid` has printed
a dash for a missing residual since contract 1.5. `worst fld` was the other live one:
`151-min`, `230-min` and `346-min` carry **no field at all**, and the report said their worst
field matched 0.0%. All four print `--` now, `render_vs_reference` is always present and
`null` when unmeasurable, and `design_qa` names the missing file on stderr instead of
scoring it.

**The same directory had gone stale a second way, and that one had no name to lose.** Its
files are keyed by folder and were all written on 2026-08-18 18:18; `304_Sonata`'s
`metadata.json` was committed at 00:07 the following morning, so its rectified face had been
six hours out of date ever since. Regenerating moved `304-min`'s `render~ref` 93.37% →
93.80% and its second region's IoU 0.000 → 0.013, and moved **nothing else on the other 25**
— exactly one preview was silently stale, and nothing was watching that either. It is the
failure with no symptom: nothing looks wrong until someone regenerates and watches a number
move.

**So `design_qa` stopped reading the file.** `measure_reference_face.rectified_face()` is the
rectification, `segment()` calls it, and `design_qa` calls it too — the face is a perspective
warp of one JPEG (`flatten_face`, no k-means, nothing clustered) and there was never anything
worth caching. Both ways of going stale are gone rather than guarded: a rename cannot orphan
what is not stored, and a corner set at midnight is read the next time anything asks.
`design_qa` produces its figures with `02_processing/reference_measurement/` deleted
entirely, and the report is unchanged to the last digit by the switch. The project already
argued this on the other side of the same comparison — `render_fresh` deletes and re-renders
our own PNG every run because a stale one makes the comparison worthless.

That the switch is safe rests on the segmentation being deterministic (`_kmeans` seeds from
luminance quantiles, not random points): regenerated twice into different directories, all 56
files come back byte-identical.

`tests/test_design_qa.py` pins six things about this — that `segment` and `rectified_face`
return the same pixels, that `design_qa` never reads a `.flat.png` again, that a folder with
no corners is refused by name, and, over the committed report, that every carton carries
`render_vs_reference`, that the report and `FOLDER_BY_STEM` agree about who is in the group,
and that an absent figure is null rather than 0.0.

**Every figure reads `scored_mask()`, and adding a fourth caller was the fix.** The dark
cut drops any pixel under 0.30 so printed TYPE stays out — our render prints it, the spec
does not carry it. Eight of eleven cartons have a *field* that dark, and the cut took those
too, dropping each one **exactly where our render painted it correctly**: what was left to
score was the misses. Ritalin held the group's best agreement, 99.87%, on an IoU of 0.043
over its only field. Contract 1.5 had already fixed this for ΔC and `_response` — "whether
a pixel is scored depends on what the SPEC expects there, not on how bright the pixel is" —
and `_agreement`, the figure the report is read by, was left on the bare cut. Ritalin 0.043
→ 0.926, Xanax's brand 0.024 → 0.955, mean field IoU 0.601 → 0.791, and **every field the
cut could not reach unchanged to three decimals**. Kamagra's agreement falls 96.9% → 84.0%,
which is the honest number: 53% of its face was being dropped before it could disagree.

Two properties of that mask, both asserted in `tests/test_design_qa.py` rather than assumed:
the cut tests the pixel's MAX channel and the restore tests the fill's LUMA, which is safe
only because luma ≤ max, so no fill the cut reaches goes unrestored; and a dark pixel where
the spec draws the substrate cannot be told from type, so it is dropped either way and a
**dark field's IoU degenerates to recall** — the figure catches a field placed short, never
one placed wide.

**A part's colour is broken by THINNESS, not by smallness, and `render~ref` cannot
see either.** Two instruments were built for the question contract 1.9 failed on
(`00_PROJECT_STATE/PART_COLOUR.md`), and neither is wired into `fit()`.

`scripts/measure_part_colour.py` holds four estimators and a bench that composites a
KNOWN colour against a KNOWN neighbour at `RIM_PX = 2.0`, then assigns each blurred
pixel to the nearer paint as k-means would. Eroding by **0.35 of the part's own
thickness** (`2*area/perimeter`) beats the median 0.0020 to 0.0076 mean error and
0.0047 to 0.0453 worst. Every one of this project's five existing erosions —
`ERODE_PX` 11 on a chart patch, 19 on the substrate, 3 in a type block — is applied
to a LARGE region, which is why a constant could not serve a 0.16% sliver.

The bench fails the median in exactly one place: 0.0018 on a 0.16% blob and **0.0453
on a 6px strip**. Measured thickness on the real parts agrees — erosion moves
`60_Cialis_Professional`'s 3.4px part and `404_Ritalin`'s 5.4px one, and leaves its
own 60.2px and `152_Artvigil`'s 65.6px alone, because those have almost no rim and
their distance from the cluster is a real difference in paint. **This corrects
`PART_FILL.md`**, which read that as erosion "half working": it was reading closeness
to the cluster as correctness. It also means the rim explanation is too small to
carry the 1.9 regression, which is therefore **not established**.

**`region_colour_gap` is a colour comparison with no vocabulary.** `render~ref` is an
agreement between two maps BOTH produced by classifying against the palette, so it
moves whenever a fill does — which is why 1.9's before and after were two
instruments. The new figure takes its regions from `spec_index`, i.e. from OUTLINES,
and differences the two sides inside them. `tests/test_region_colour_gap.py` shows
`spec_index` unmoved when a fill is brought within 0.001 of another while the
classified map falls below 95% agreement with the geometry — through deterministic
noise, because on a CLEAN raster nearest-colour separates a thousandth perfectly and
the demonstration proves nothing.

It inherits the fit error (regions are the spec's, `spec~ref` 95-100%). **What it does
NOT do is measure paint, and it was published as if it did.** It compares OUR RENDER
against the photograph in raw values, so it carries three terms and only the last is
the fit's: the exposure difference between render and photograph, the rig's measured
black lift, and the fit error. Split off the best neutral scale and `230_Slimex`'s
headline 0.3652 is **0.0187** — the photograph is 1.29× darker and nothing else; every
substrate gap in the group above 0.26 is a level difference, while `151-min` carries
zero fields too and reads 0.0713. `64_Kamagra`'s 0.128 chromatic residual is the lift,
red at 0.131 against a spec that says 0.000. This is the reading already recorded here
for ΔC — *a neutral scale is an exposure, not a colour* — arriving at a figure that
shipped without it. As a BEFORE/AFTER the exposure term cancels and the figure stands;
as the ranking it was presented as, it misleads.

Levelling it away is not the fix, because a gain cannot represent a lift: referred to
its own substrate `357-min`'s second field goes 0.0096 → **0.4951**. Two findings do
survive and come out stronger — `157_Valium` at 0.549 and `272_Roche` at 0.512, and on
both **our render is four times closer to the spec than the spec is to the
photograph**, so the renderer obeyed and the fitter chose wrong.

**`fit_colour` is the figure that takes the render out**, and it is what a fresh
contract-1.9 attempt should be judged by. A field's `fill` is
`np.median(raw_px[cluster])` off the rectified photograph, so the declared paint and
the photograph are one measurement in one space — nothing to level, no curve, no lift,
no render, 20 seconds for the group. `part_index()` is `spec_index` kept per PART and
in paint order, because 1.9 is a statement about parts. **Its floor is measured and is
exactly zero on all 28**: measuring the substrate cluster back returns
`spec["substrate"]`, and every spec carries exactly the rectification's own aspect so
nothing is resampled.

That floor is what an earlier version of this figure did not have, and the check that
found it is worth keeping: **a part that IS its own cluster has to read zero.** Against
the illumination-flattened face `64-min`'s `brand#0` — 32.6% of the face — read 0.0039
raw against 0.0950 levelled, and `59-min`'s `highlight#0` 0.0068 against 0.2052,
because the plane is fitted over *wherever the spec draws no field*, which on those
cartons is the board plus everything the labelling wrote off. Kept as `gap_levelled`
beside the headline so the illumination term stays visible.

**Read against contract 1.8 it found 33 of 75 parts at or beyond `SAME_SURFACE_MAX`, on
20 of the 28 cartons** — the threshold reused deliberately, since 0.08 is the distance at
which `segment()` merges two clusters as one surface. That reading is what contract 1.9
was built on and it is now history: the same instrument over the shipped specs reads
**8 of 75**, and the report on disk is the current one. `gap_field` beside `gap` keeps
the 1.8 number visible per part rather than losing it.

`spread` beside each gap splits the failures into two the contract would otherwise treat
alike: **25 were uniform and simply wrong** (`152-min`'s `brand#1` has a spread of
**0.0000** over 6.47% of the face, declared orange and charcoal in the photograph), and
**5 have a spread at or above their own gap** — `404-min`, `304-min`, `357-min`,
`155-min` `highlight`, `157-min` `type#1` — where no fill is right however it is
estimated. The first group is what 1.9 fixed and the second is what it cannot. Write-up
in [`00_PROJECT_STATE/FIT_COLOUR.md`](00_PROJECT_STATE/FIT_COLOUR.md).

**`149_Modalert` and `344_Modafinil_Generic` are one photograph**, byte for byte under
two names, with the same corners and the same spec — which is why their rows match to
four decimals. `344`'s metadata says so (`"product_name": "Modalert 200 (Sun Pharma)"`)
and this file already records that its photograph is a Modalert pack; what was not
recorded is that **the 28 folders are 27 distinct references** and every group mean
counts that carton twice.

**`design_qa.py --sku` no longer writes the report.** A single-SKU run used to rewrite
`design_qa.json` with one row, discarding the other ten. Merging would be worse — the rows
would then come from different revisions of the script with nothing in the file saying so.

**`design_qa` classifies against a MEASURED transfer curve, and the palette is mapped
forward into the render's space rather than the render corrected back.** Comparing a render
against PRINT colours is wrong in a way a substrate gain cannot reach: the transfer has a
lift. Kamagra's `#00463B` and `#002F26` are 0.122 apart, our render separates them by 0.089
— it builds both — but both arrive with a red near 0.135 against a spec that says 0.000,
because a lit surface does not return black. That shared 0.145 displacement is larger than
the gap it has to preserve, so 89% of the darker field classified as the lighter one:
**0.084, the group's worst field by a factor of five, on a carton built correctly.**

`scripts/calibrate_render.py` renders each carton a second time with its design replaced by
a chart of 19 known patches — same geometry, same rig, same exposure, no design — and reads
the curve off it. Three measured facts hold it up: the transfer is **per channel and
independent of the others** (`#400000` renders `(0.251, 0.133, 0.133)`), so one curve
suffices; it is **not affine** (a line leaves 0.046 residual, the interpolated ramp 0.013);
and the **black lift is a rig constant**, 0.133–0.141 across all eleven, sd 0.0024. Kamagra's
field goes **0.084 → 0.907** and its agreement 84.0% → 97.8%.

**A curve fitted across the group's own regions also works and was deliberately not
shipped** — leave-one-carton-out, it classifies 30/30 region medians correctly against 29/30
for nearest-paint. It is still a transform fitted to the regions being judged, which can
absorb a build error as calibration. The chart costs one render per carton and removes the
objection. `render_calibration.json` carries a driver+settings fingerprint and `load_curve()`
exits rather than applying a stale curve or falling back silently.

**Both halves are load-bearing: the curve gives the shape, the substrate the level.** The
curve alone breaks Imovane — worst field 91.9% → 76.2%, swing ±0.1 → ±2.9 — because the
chart is read on the face as it comes while the classified frame has had its illumination
divided out, and `flatten_on_substrate` renormalises to the estimate's mean. That 0.02–0.03
is a third of Imovane's 0.086 gap. `_refer_to_substrate()` fixes it and Imovane returns to
91.9% / ±0.1.

Kamagra's brand also stops being over-claimed: 36.15% of the face by spec, **50.90% under
the anchor**, 37.00% under the curve. Each field's median sits 0.004–0.028 from its
predicted appearance against 0.34–1.00 from the substrate's.

**The dark cut takes the ink's RIM with it, one pixel wide.** A pixel straddling a glyph
edge is a mixture of ink and board — evidence about neither, and where some palette entry
sits on the line between the two, evidence *for* that entry. Xanax is the case: `#968974` is
a **44% blend of its substrate `#E8DCB4` and its brand `#2C1F2A` to within 0.013**, so every
antialiased glyph edge on the carton read as that field. **99.8% of its false highlight
pixels lay within two pixels of dropped ink**, totalling 0.80% of the face against a field
that is 0.93% of it, and the field read 49.8% at 93.0% recall and 51.8% precision.

**The width is measured, not chosen**: r=1 takes the group's mean field 80.1% → 90.1%, r=2
reaches 90.3%, r=3 no further. It saturates at the resampling width, which is all it is —
the face is rectified to 1100px from a 2048 render. Costs 0.5–1.7% of scored pixels,
reported as `edge_dropped`. Xanax 49.8% → 82.7%, Modafinil 75.8% → 98.4%, Valium 81.8% →
97.3%, Ritalin 86.8% → 97.0%, Viagra 88.1% → 98.8%, and **nothing regressed on any column**
— three cartons now read 100.0% against their spec. It corrects an earlier reading too: the
four cartons recorded as losing IoU to the transfer curve were losing it to glyph rim.

**A design outline that crosses itself is not a region, and one reached the packshot.** The
only defect in this sequence that was in the RENDER rather than in the instrument. Xanax SR's
brand outline has eight points and one of them — `[0.980, 0.707]` — sits far below the other
seven, the one-pixel-thread artefact `fills_its_box` already guards against. `rasterise()`
fills with PIL's even-odd scanline, which is what every spec's `verification.pixel_agreement`
was measured against, and drops the sliver; the driver hands the same points to a Blender
curve with `fill_mode = BOTH`, which tessellated them and **filled the triangle back to the
panel — 1.33% of the face**. Our packshot carried a magenta wedge the real carton does not
have, the field read 75.2% at 100.0% recall, and nothing said so: the renderer was obeying
the contract and the contract was ambiguous. **13 parts across 8 of the 28 cartons**
are tangled this way.

`simple_ring()` in `src/design_group.py` drops the fewest vertices that untangle the ring,
preferring the smallest area change, with only vertices on a crossing edge as candidates —
one to four per part, and the repaired rings score **0.972–0.9999 IoU against the original's
even-odd raster**, so the verified region is preserved rather than redrawn. It runs inside
`load_design()`, the single loader, so the manifest builder and the QA raster see the same
rings; **the spec on disk stays as traced**, because it is a measurement and the repair
belongs at the contract boundary. A repaired part carries `simplified_from`.
`validate_manifest()` rejects a tangled outline by name on write and on load — JSON Schema
cannot express "does not cross itself", and a stale manifest would render the wedge again in
silence. Xanax SR: worst field 75.2% → **96.8%**, render~ref 97.2% → **98.6%**, the best in
the group.

**The same cut drops the SEAM where two spec regions meet, one pixel either side.** Ativan
is that case: `#8E9DA0` is a 42% blend of its substrate and its `secondary_1`, its four
regions and 175 vertices put **6.9% of its face within two pixels of a boundary**, and
**94.0% of its false highlight pixels lay in that band** — the field read 63.8%. The
asymmetry is structural: `rasterise()` fills polygons hard-edged and our render arrives
through a Lanczos rectification, so the target has a step where we have a ramp. Ativan 63.8%
→ **94.3%**, Xanax 82.7% → 91.6%, Kamagra 90.7% → 96.4%, and **five cartons now read 100.0%**.
Width measured the same way: r=1 takes the mean field 90.1% → 95.2%, r=2/3/4 give
95.3%/95.2%/95.1% — saturates, then decays.

**Two things were checked before throwing those pixels away, and both are pinned by tests.**
A one-pixel exclusion does not hide a two-pixel error — shift the classification and Ativan
goes 94.4% → 59.5%, Modafinil 100.0% → 65.2%. And it does not hollow a field out: every
field keeps ≥68.9% of itself, reported as `field_kept_min`. A **softer target** was tried
instead — the spec rasterised at 4× and averaged down, so no pixels are discarded — and is
much worse (Ativan 70.4% against 94.4%), because a box-filtered 4× raster is not the ramp a
Lanczos rectification leaves.

**`palette_closest_pair` cannot see the condition that actually breaks these cartons.** It
asks whether two entries are distinguishable; Xanax has the group's *second-widest* closest
pair at 0.522. What matters is an entry lying **on the segment between two others**, which
is what every boundary pixel between them averages to. `palette_on_line` reports it and the
evidence has a gap: Xanax 0.013, Imovane 0.015, Ativan 0.017, then Cialis at 0.064. Not a
gate — the colours are the carton's and the renderer cannot do anything about them — so it
exists to make Ativan's 63.8% and Xanax's 82.7% read as the palette, not as the build.

**`_anchor()` still takes a per-channel gain off the
substrate — a region the spec draws and whose paint it states, so a grey card the picture
contains — and the row reads 98.4% at ±4.3, with nine of eleven swings falling to zero and
nothing regressing.

Do **not** extend that anchor to `colour_error_by_region`: that figure asks whether the
renderer painted the colour it was told to, and anchoring the frame to the spec is how you
erase its answer. An earlier attempt put the gain in front of both and was reverted for
costing Kamagra fourteen points — the lesson was where it belongs, not that it was wrong.
The same rule is why the curve is applied to the PALETTE and never to the frame.
**Which illumination model the classifier uses is chosen per carton, on the substrate.**
Neither is right everywhere and the gap is not small: on `59-min` the plane leaves a
residual of 0.085 against a blur's 0.066 and classifies 28.9% of the face as the white
swoosh where the spec draws 21.1% — 88.6% against the blur's 98.1%; on `155-min` it is the
other way round. `_substrate_residual()` decides, judged only on the surface the spec draws
and states the paint for, so the choice never sees a field. `illumination` and
`illumination_residual` travel in the report so it can be checked.

**The swing perturbs the CHOSEN model, not the rejected one** — the erosion the plane is
fitted through, or the radius the blur is taken at. Differencing against a model the
substrate already showed to be worse is not uncertainty: it read ±9.5 on `59-min` for
exactly that, against ±1.1 now. And note the narrow blur (a sixth of the face) is not a
candidate at all — it follows the design, the defect recorded against Kamagra's colour
error.

**ΔC reports the picture's response as well as the paint, because it was reporting it
INSTEAD.** The two worst colour errors in the design group are both a substrate, and both
substrates render at exactly **0.87× their spec on all three channels** — a neutral scale
is an exposure, not a colour. The darks go the other way: Kamagra's `#00463B` has a red
channel of zero on the spec and 0.128 in our render, because a lit surface does not return
black. `_response()` fits gain and lift per channel across the regions and reports what is
left: Kamagra's worst region goes **0.189 → 0.024**. Both figures stand — ΔC keeps a
systematic exposure error visible, which the residual hides, and the residual answers what
ΔC was being read as. An earlier attempt put a grey-card gain *in front of* ΔC and erased
its answer; naming the response does not.

**Fitting it needs three regions and four cartons do not have them.** Two points determine
a line exactly, so Viagra, Lexotanil, Modafinil and Ritalin report a dash rather than a
residual of zero they did not earn — Viagra matters, since it holds the group's largest ΔC
at 0.191 with the same 0.87 neutral scale on its substrate. At three regions the fit has
one degree of freedom and the residual is correspondingly optimistic.

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

**The design group's photography was REPLACED on 2026-08-18, and most figures below it are
therefore historical.** An acquisition run re-searched the catalogue and swapped the reference
photograph in eight of the eleven folders — not re-encodes of the same picture but *different
packaging*: `08_Ativan` went from a Polish "Lorazepam Orion, 30 tabletek" to a Mexican Pfizer
"Ativán, 80 tabletas"; `23_Lexotanil` from a lime "Lexomil Roche 6 mg" to a cream "Lexotanil
3 mg, 70 tablets"; `30_Ritalin` from a 20/N1 pack to a 50/N2 one. Only Cialis, Kamagra and
Viagra kept theirs. **The originals were never tracked** — `Reference Templates/` holds no
images in git — so nothing reproduces the old measurements, and the old `design_spec.json` and
`design_measurement` for those eight describe cartons no photograph on disk contains.

Six were rebuilt end to end (passport, corners, D-1, D-2, type rows) against the new frames.
Two left the group: `21_Valium_Brand` is shot from above with a blister lying across its
printed face, and `24_Xanax_Pfizer`'s frame holds two cartons on a wooden table. They are out
of `TEMPLATE_SAMPLE`, which puts them on the generic art direction — a SKU left *in* the map
without a spec does not fall back, `load_design` raises and it stops rendering at all.

So: **every number quoted below against Ativan, Imovane, Xanax, Lexotanil, Modafinil, Ritalin,
Valium or Xanax SR was measured on the previous photograph.** The reasoning those passages
record is why each instrument is built the way it is and still governs; the figures are a log,
not a current reading. Cialis's, Kamagra's and Viagra's numbers are live.

The same run also acquired photography for **seventeen further folders**, which for a time named
no SKU and made `test_no_photographed_folder_is_missing_from_the_sample` fail by design. The group
was extended to them instead of dropping them: `TEMPLATE_SAMPLE` now holds **28** folders.
Two folders on disk are outside it and for different reasons: `input pp`, which holds no
image at all and so is not a reference to anything, and `107_Tramadol`, which keeps its
photography but whose highlight segmentation is speckle no outline can represent -- it is
named in `UNMEASURABLE` in `tests/test_reference_templates.py`, so its absence is a
statement rather than a gap.

**Two of these constraints are now conditional, and which is which matters.** The **28** SKU
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
of the nine real cartons have a coloured board (Kamagra teal, Ritalin orange) — it fails
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

**The segmentation is FROZEN by its own labelling, and that is the binding
constraint on every improvement to it.** `print_truth.json` keys 661 hand-made
component classes (and 239 hole classes) to `role#i` — and *both halves of that key
are outputs of the partition*: `role` is the name `segment()` gave a cluster, `i` is
the index a component takes after `components()` sorts by descending area. Move the
partition and the keys address different surfaces. `fit()` stops on a key it has
never seen; it cannot stop on a key that still exists and now means something else,
and `label_print --verify` cannot either — it asks whether every component *has* a
class, not whether it is the *right* one.

Two changes to `measure_reference_face.py` were built and measured against this,
both of them defensible on their own terms, and **both rejected**:

- **the lightness estimator.** `_flatten_illumination` uses `rgb.max(-1)`, which is
  V of HSV and not a lightness by any model — it calls `#0000FF` and `#FFFFFF`
  equally bright and ignores two thirds of the pixel, and the image is then
  *divided* by a blur of it. Replacing it with the Rec.709 luma this project
  already uses in four other places moved the partition on **21 of 28** folders:
  `362_Hydrocodone` gained 55 keys and lost 51, `357_Adderall` drifted 28.9 points
  of area, `64_Kamagra`'s `highlight` role vanished entirely.
- **the clustering space.** `_kmeans` measures Euclidean distance in the corrected
  sRGB values, so it partitions the encoding rather than the appearance. OKLab
  instead moved the partition on **27 of 28** — only `134_Atarax` survived.

Neither change *can* avoid this: `_flatten_illumination` divides every pixel by a
function of the estimator and `_kmeans` groups by distance in the space, so both
touch every pixel by construction. **The cost of improving the segmentation is a
deliberate manual re-classification of 28 folders**, not a code change — and it must
be deliberate, because `label_print --init` MERGES old classes onto new components,
which is exactly how stale labels once survived a corner change.
`scripts/probe_partition_shift.py` is the instrument that answers "does this change
invalidate the labelling?" and should be run before any edit to `segment()`.

**A curve fitter was measured against the tracer and lost — and the figure that
motivated it was measuring something else.** `vtracer` (`mode="spline"`, per
component mask) was wired into `fit()` and took the group's `truth_agreement`
**95.36% → 94.19%**, with `304_Sonata` −17.4 and `155_Imovane` −5.7 points; both are
cartons whose printed field is a sliver, 0.12% and 0.67% of the face, and a spline
rounds a sliver's ends. Rolled back whole.

The premise did not reproduce. "0.954 against 0.888" is **the same polyline scored
two ways** — every hole cut against the outer ring alone:

| what is filled | mean IoU over the 75 printed components |
|---|---|
| polyline, outer ring only — what ships | **0.8855** |
| polyline, EVERY hole cut | **0.9536** |
| vtracer, outer ring only | 0.8649 |
| vtracer, EVERY hole cut | 0.9236 |

So the gain belonged to the holes, not to the vectoriser — and it is unreachable
anyway, because cutting every hole is what contract 1.8 forbids. Like for like
vtracer is worse on both footings, on 75 of 75 components, at every one of eight
parameter settings tried (the whole space runs 0.8588–0.8649). A half-pixel
edge-vs-index offset was ruled out too: vtracer writes pixel EDGES, and correcting
for it makes matters slightly *worse*.

`SIMPLIFY_TOLERANCE`'s own comment reached this conclusion first, about a hand-built
cubic fit — *"these outlines are boundaries of RASTER regions … Douglas-Peucker's
home ground and a cubic's worst case"*. This is the same verdict from a different
fitter. `src/vectorise.py` survives unwired as the only implementation of two SVG
parsing traps (a path command repeating implicitly; `transform="translate"` written
*after* the `d` attribute), with tests that fail if anything imports it.

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
- the small print is capped at 0.12 of face height so it cannot crowd a shallow T3;
- a GRID row is moved until one ink can serve all of its capitals — `_clear_of_design`,
  which judges the CAP BAND rather than the bounding box, indents along the row's own
  baseline first and then moves it up or down the face;
- the brand is re-fitted where it stands over a design's dosage block, which is the same
  rule as its right limit stopping at the badge — on a design carton no generic badge is
  drawn, so nothing stopped it: `62-min`'s "Cialis Super Active" wrapped and its second line
  lay across the amber bar the design sets "20mg" in, the brand's box covering **68.3%** of
  the block. The reference shows what that column is for — "Cialis" on one line with "10 mg"
  in the bar BESIDE it.

Re-run that sweep after touching the grid. The unit suite covers the cases we know about;
the sweep is what finds the ones we don't.

**That clearing search only ever moved a row DOWN, and three rows in the design group were
unreadable for as long as it did.** Its own field is often BELOW the row, and a row escapes
a field by moving away from it: `357-min` printed 10.0% of "Amphetamine / Dextroamphetamine
Salts" and 28.7% of "30mg" in an ink those surfaces hide, and `149-min` 13.7% of its unit
count. Every offset that serves any of the three lies UP the face — 0.015, 0.115 and 0.235
of it. The ingredient shows why indenting could not save them: it runs 88% of the face wide,
so no horizontal offset fits between the margins at all.

Three things were measured and NOT shipped, each because the evidence refused it. A cap on
total travel — it would have thrown away the 0.240 the search already uses to clear
`64-min`. A tolerance below which a mixed band is not a defect — across the group's 81 grid
rows, 20 carry one at home and they run from 0.250% to 49.729% with no gap anywhere. And a
joint search over both axes, which is genuinely cheaper on a diagonal boundary (`357-min`'s
dosage clears at dx +0.090, dz −0.005 against 0.115 straight up) but never fires once the
axes are tried first.

Two things about that correction are worth keeping. It is applied to the BUILT row and not
by narrowing the brand's right limit up front, because that limit is also the clearing
search's, and narrowing it took away the +0.184 indent that lifts `59-min`'s brand out of
its green swoosh — 0.0% hidden straight back to 31.0%. And it is judged on the BOX rather
than the cap band, which is the one place in this file where the box is the right instrument:
what runs into a block is a row's descenders and the space its second line takes. On
`62-min` the cap bands clear each other by **0.1mm** while the box covers two thirds of the
block, and the render shows "Active" lying across the bar.

**It cost an OCR row, and that is the honest price.** `62-min`'s "Tadalafil" did not move and
did not change size, and it reads in every page-segmentation mode from a crop of its own
band — but the whole-face read loses it now that the brand beside it is a different size.
The row is in `KNOWN_OCR_MISSES` with that evidence. A packshot that no longer prints its
brand across its dosage bar is worth one row the reader stops segmenting.

**The guard for this covers every design SKU, not nine.** `TestNoGridRowIsPrintedInInkItsOwn
BackgroundHides` had a hand-written list of nine and the three broken rows were all outside
it; it now reads `FOLDER_BY_STEM`, so a SKU entering the design group enters the guard with
it, and `MIN_SKU` stops the count shrinking quietly. It costs about two minutes — 28 Blender
launches at 2.8s, and 20s for `357-min`, whose design carries the group's largest polygons.

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

**A measured row's INK follows the surface under it, and the test for "dark" is perceived
luminance.** The reference puts a row wherever it likes, and on these cartons that is often
on the design: Kamagra sets its dosage inside a teal field and our render printed "100mg"
near-black on it — right position, right size, invisible, and the one measured row the
reader could not find. `_surface_fill()` point-tests the row's centre against the design's
own polygons (last part wins) and every measured row goes through it. Two traps here:

- the label must sit at **twice** the standoff, because design fields straddle the face
  plane and their front surface lands at exactly one — with the ink corrected the dump read
  `(1.0, 1.0, 1.0)` and the render still came back dark, the block winning the depth test;
- `_reverse_ink` judges in **sRGB, not the linear values Blender is fed**. sRGB 0.5 is
  linear 0.21, so a linear bar calls almost everything dark. It never bit while it only ran
  on blocks (both genuinely dark) and flipped three of five surfaces wrongly once measured
  rows could land anywhere — Imovane's light grey `#BCBCB2` sits at 0.734 perceived and
  0.499 linear.

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

**A row reversed out of a filled shape is boxed as the SHAPE.** Tesseract binarises per
region, so a colour block with type inside it is one blob and the word box comes back as the
block: on our Cialis render "20mg" was returned at the block's own outline to four decimal
places, reading as a row 38% oversized on a carton the scene dump says is built exactly
right. `ink_within()` measures the glyphs instead, and needs both of its details — it fires
only where the box IS the shape, and it measures inside the shape's **eroded polygon**,
because a sliver of board along the box's edge is as far from the fill as white glyphs are.
Whatever it corrects must also be written back into the row's `words`: everything
downstream rebuilds a row from those, so the first version was silently undone.

`scripts/type_qa.py` is the instrument for all of this — the type axis D-6 explicitly does
not cover, since every figure there excludes dark pixels.

### The side panel prints only what it was given

The visible side panel is the carton's local **−X** face: the camera looks along +Y and the
carton is rotated +35° (or +27.5°) about Z, which turns the −X normal toward the camera and
to the left of frame. The +X face is never seen.

Magnify the reference side panel before trusting it. Its 2D code is a blob of noise with no
finder pattern; its LOT/EXP values read `SLAQF FDЯT`; its microprint is not text. **That
panel is evidence of layout, not of content.** What the driver builds instead:

- **A real Code 128** subset B of **`product_code`, never `sku_id`**, encoded by
  `encode_code128b()`, with the same string printed under it as the human-readable line. A
  test decodes it back out of the built *geometry* — recovering spaces from the gaps between
  bars, the way a scanner does — and re-derives the modulo-103 checksum, so "it is a real
  barcode" is a fact rather than a claim. Do not replace it with a decorative bar pattern.
  Until contract 1.6 it encoded `sku_id`, which is a filename, so **every carton in the
  catalogue carried `.jpg` in print and in a scannable symbol**; a second test now asserts
  the decoded string is neither a filename nor equal to `sku_id`.
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

**The compute device is STATED, and a GPU render is not the same picture.**
`setup_render()` never assigned `scene.cycles.device`, so the device was whatever the
process started with — CPU under `--factory-startup`, and therefore correct by
accident. Blender accepts more than one `--python`, so a script running ahead of the
driver could move an entire render onto the GPU with nothing in the log to say which
device drew it; `scripts/probe_render_device.py` does exactly that on purpose, and it
is why `setup_device()` now exists. `blender.device` / `device_backend` /
`denoising_device` in `config.yaml` are welded to the driver's flag defaults by a
test — nothing passes them on the command line yet, so changing one fails the suite
rather than changing a render.

CPU is not a placeholder. Measured on an RTX 2060 SUPER at 16 samples against the CPU
render of `1-min`, `64-min` and `357-min`: **OptiX sampling** 1.17–1.45× faster and up
to 43 levels apart on 0.2–0.9% of pixels; **CUDA** 1.18–1.45× and up to 23 levels on
0.2–0.7%; **GPU denoising** up to **5.4×** and up to 43 levels on **14–18%** of
pixels. The cheap win and the expensive change are the same setting — the denoiser is
more than half of every render, and it is also where the pixels move. Enabling any of
them means re-taking the calibration curve, every `design_qa` row and the OCR
fixtures, all of which were measured on CPU pixels. An unavailable back-end is
`SystemExit`, never a silent fall back to CPU.

Related: **`driver_fingerprint()` guards the wrong half.** It is the SHA-256 of the
driver file plus `engine_type`/`samples`/`resolution`, so any driver edit invalidates
`render_calibration.json` and `load_curve()` exits — but it does **not** cover the
manifest the calibration chart is built from. A carton reshape or a corner re-set
leaves the fingerprint matching while the curve goes stale, which is precisely what
happened: `74-min`'s row was measured before `6d37b89` moved its face corners and was
silently wrong until a re-run moved its `render~ref` second field from 0.312 to 0.806.

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
`tests.test_render_qa.TestOCRAgainstAFreshRender`, which re-renders **the whole 28-SKU
sample** (and `1-min` beside it) and re-runs the OCR barrier against the new pixels, so the
committed fixtures under `tests/fixtures/ocr/` cannot silently drift from what the renderer
actually produces.

**That gate is the only thing that noticed the fixtures had gone four contract phases
stale**, and it noticed it late because nobody ran it. The standard suite stayed green
throughout: it reads the fixtures, and a stale fixture set is perfectly self-consistent with
itself. When the set was finally rebuilt at contract 1.8, six rows had started missing
unnoticed and **ten rows that used to miss had started reading** — the renderer had got
better and worse in places, and neither was being watched. Run this gate in any phase that
changes what the renderer draws, and rebuild with `python scripts/make_ocr_fixtures.py`
rather than editing a fixture.

**The fixtures are LOSSLESS WEBP, and every lossy quality has now been measured
failing.** The set's one claim is that it reads the same as the render it came from —
so it is re-measured whenever the pixels change, and it has been falsified twice. At
contract 1.9 q92 disagreed with the PNG on one of the sample's 112 rows and q98 on
none, so 98 was chosen. Contract 1.10's marks put three rows on Tesseract's boundary
and **q98 disagrees on all three, in BOTH directions** — `230-min`'s ingredient and
`357-min`'s brand are read by the render and lost by the encode, while `357-min`'s
ingredient is missed by the render and *recovered* by it. Quality is not the dial:
**q100 disagrees on three as well, a different three**. Lossless disagrees on none, and
costs 2.82 → **31.97 MB**.

The cost is worth naming against the other rule in `make_ocr_fixtures`' own docstring,
that renders "do not belong in a repository that deliberately tracks no renders". The
two pull opposite ways and this is the side that was chosen, because the alternative is
an exception list about libwebp rather than about a carton — unjudgeable by looking,
and different after every rebuild.

**While the two sources disagreed, no ratchet list could satisfy both barriers**, and
that is the sharpest thing the equality assertion has done: `test_the_known_miss_list_
is_not_stale` reads the fixture and demanded `357-min`'s ingredient be REMOVED, while
`test_the_template_sample_fixtures_still_match_a_fresh_render` reads the render and
demanded it STAY. Two rows were briefly entered on the fixture's answer before that was
seen. All 28 fixtures were verified to reproduce byte-for-byte from the renders on disk
first, so the disagreement was known to be the codec and not staleness.

`KNOWN_OCR_MISSES` and `ROWS_THE_RENDER_HIDES` are deliberately two lists. The first is the
reader: the string is printed and legible to a person and Tesseract returns something else.
The second is the RENDER: a glyph is not legible. Filing one as the other is exactly how a
fixture regeneration hides a regression, and the two are told apart by looking at the
rectified face — not by the OCR return:

```bash
PHARMAGEN_SLOW_TESTS=1 python -m unittest tests.test_blender_carton
PHARMAGEN_SLOW_TESTS=1 python -m unittest tests.test_render_qa.TestOCRAgainstAFreshRender
```
