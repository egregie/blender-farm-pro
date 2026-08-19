# Blender Farm Pro — Current State

> Update this file after every major step. See [NEXT_STEPS.md](NEXT_STEPS.md)
> for what's queued and [CHANGE_LOG.md](CHANGE_LOG.md) for the running history.

**Last updated:** 2026-08-07 · **Status:** The Blender engine produces recognisable
pharmaceutical packshots — geometry, branding and printed text all driven by real
per-SKU data. Not yet run across the full catalogue. A post-render verification
barrier now exists (OCR + pixel + scene checks) but it runs on one committed
fixture SKU plus whatever the opt-in slow gate re-renders — not a catalogue-wide
guarantee.

## Where the code lives

| | |
|---|---|
| Remote | `github.com/egregie/blender-farm-pro` (**private**) |
| Working branch | `correct-brand-books-for-target-template`, carries this verification-barrier round's work; not pushed. |
| Default branch | `master` at `ad72dea` — the fork baseline plus the skills cheatsheet |
| Commits since fork | Grows with every commit on this branch, so not recorded as a static number here — run `git rev-list --count ad72dea..HEAD` for the current count. |
| Tests | **200 pass, 2 skipped** (`python -m unittest discover -s tests`, ~90-105 s) |

The two skipped tests are both opt-in via `PHARMAGEN_SLOW_TESTS=1`: the pixel-level
calibration gate (renders real packshots) and the fresh-render OCR gate (re-renders
the fixture SKU to confirm the committed fixture hasn't drifted from what the
renderer actually produces).

`master` deliberately does not carry the Blender work yet. Everything below is on
this branch.

## What actually works today

**The Stage 1 → Stage 2 contract.** `schemas/render_manifest.schema.json` (version
**1.3**, which carries the art-directed scene geometry and the carton's real
`passport_dimensions` as two separate blocks — build from the first, print only the
second) is the single authoritative description of what a renderer receives.
`src/render_manifest.py` is its only implementation — Stage 1 emits through it,
`blender_renderer` loads through it, and both validate against the same artifact.
All 391 SKU produce a schema-valid manifest and every one resolves its carton from
`passport_secondary`, i.e. real dimensional data rather than a guess. A test fails
if any SKU regresses to a guessed ratio.

**Geometry from real data.** The carton is built from the passport's own
`secondary_packaging.dimensions`, oriented per template family. Before this, the
driver read `primary_package` — a different, smaller object on permuted axes — and,
because that field is `null` in every stored passport, silently fell back to a
per-template aspect ratio for the entire catalogue. Measured afterwards, not one SKU
had been within 10% of its guess and 104 were off by more than 50%.

**Printed surfaces.** The front panel carries the brand name, active ingredient,
dosage and unit count as real Blender text objects on a measured grid, plus the
corner badge and the bottom accent stripe. The visible side panel carries a genuine
Code 128 encoding of `sku_id`, empty LOT/EXP rules, and a data block built only from
manifest strings. Fonts are vendored in `05_assets/blender/fonts/` (DejaVu), never taken
from the system, so the render cannot change on a machine that lacks a font.

**One studio for all 391 SKU.** The light rig scales with the carton — power follows
the square of the size ratio — and exposure is metered per carton shape as a film
setting, kept separate from light energy.

**Engine selection.** `main.py --render-only --render-engine blender|gemini` works
end to end through the `src/render_stage.py` facade, with unit coverage for the
dispatch and for the two architectural invariants behind it.

**The whole catalogue renders, and there is a baseline.** All **391 SKU**, one
driver (`sweep_report.md` names its sha256), 0 failures, 45.5 min for the 100 that
needed rendering at 27 s each. Frame fill sits inside its template's median with
**no outliers in any of the nine**; front-face brightness runs 231.9–240.9 with a
median of 238.5; the scene check completed for all 391. **14 SKU flagged, every one
of them the same known small-print defect** — no geometry failure, no cropping, no
render error. The report is what later runs are read against, and only a
whole-catalogue run is allowed to occupy that filename.

**The pipeline is closed on both sides.** Stage 3 reads and writes wherever the
*selected* engine works: `image_processor.source_dir`/`output_dir` accept the sentinel
`auto`, resolved through `render_stage.raw_output_dir()`/`final_output_dir()` — config
only, so Stage 3 still imports no engine. Any real path there overrides the sentinel and
wins. Before this, `--full` under the blender engine rendered into one directory and
converted another, reporting success over renders it had not produced; the two engines'
finished WEBP are now segregated too (`blender.final_dir`), because both name their
output after the SKU stem. `main.py`'s summary reports the handoff itself —
`Stage 2 -> Stage 3: N produced -> M converted` — which is the number that was missing.

## Carton proportions: settled 2026-08-09

**The reference set defines the art direction.** The owner's decision, taken with the
measurements in hand. Geometry is now solved onto each template's measured reference
proportion at the manifest boundary; the carton's real size travels beside it as
`carton.passport_dimensions` and is the only size printed on the pack.

The table that used to sit here compared reference frame fill against render frame
fill. Both numbers were real, but the comparison was not: frame fill is not
reproducible under shared framing, because the camera solves from the bounding sphere
and the two axes' fills are locked together. It has been replaced by silhouette
aspect, which is framing-invariant — see `01_input_raster/reference_analysis.md` §10
for the measured table, §11 for why a threshold-derived silhouette is not a target
that can be solved onto, and §12 for the light-rig defects that search uncovered.

Where things stand:

- `reshape_to_art_direction()` in `src/render_manifest.py` solves the shape; 389 of
  391 SKU carry `carton.source = "art_direction"`, and 2 upright vials that routed to
  a landscape template are recorded as `art_direction_declined_orientation` rather
  than turned on their side.
- Contract **1.3** carries both sizes, and a 1.2 manifest is rejected.
- The side panel prints `passport_dimensions`, never the solved geometry.

**Still open, and recorded rather than hidden:** which model quantity the target should
be matched against — full silhouette, visible faces or front face — differs by 13–18%
and cannot be settled by measuring our own renders, because the top face has no edge a
threshold can find. §11a has the evidence. The vertical family sits 36–77% from its
references under every one of the three, so its direction is not in doubt.

## Known gaps

- **Post-render verification now exists, but only proves itself on one SKU.**
  `scripts/render_qa.py` runs OCR (Tesseract) against the render manifest — the
  contract the renderer actually consumed — reading `brand_name_display`,
  `active_ingredient_display`, `dosage_display` and `unit_count_display` off a
  perspective-flattened front face (`src/deskew.py`, using the `{stem}.view.json`
  corners `render_driver.py` emits). Raw OCR on the carton's native 27.5-35°
  rotation is unreliable: measured on the fixture SKU, the deskewed read recovers
  4 of 4 label fields where the raw read recovers 1 of 4, with the brand coming
  back as `Germetine`. This is proven as a barrier, not just a diagnostic —
  `tests/test_render_qa.py::TestOCRBarrier` runs against a committed fixture render
  and fails if the deskew step is removed or the fields stop being readable, and
  `PHARMAGEN_SLOW_TESTS=1` re-renders that same SKU to catch fixture drift.
  Alongside it, `scripts/catalogue_sweep.py` and `src/measure.py` already do pixel
  checks (silhouette extent, front-face brightness) and a scene-level check (every
  label row's bounds read via `--dump-scene`, against the face edges and the row
  below). **The gap that remains:** none of this checks the brand badge, drawn in
  `palette.primary` — nothing inspects colour, only text presence and layout. And
  the barrier itself is narrow: it runs on the one fixture SKU (`1-min`) committed
  under `tests/fixtures/ocr/`, plus whatever `scripts/catalogue_sweep.py --group
  top30` re-renders when run by hand — it is not a catalogue-wide guarantee, and
  the `ROADMAP_ONLY` Pydantic models in `schemas/` (`ObservedZone`,
  `ObservedPalette`, `UVBox`) remain unused scaffolding beyond it. `main.py`
  separately forces a failure when Stage 2 exits clean having written zero PNGs —
  a file count, not an inspection, and unrelated to the OCR/pixel/scene checks
  above.
- **The small print falls below its floor on 14 SKU** — the one class of defect the
  2026-08-11 catalogue baseline found, and it is a known one (R-007). Seven
  `T_BOTTLE_BOX` unit counts set at 3.50mm, five `T_MULTIPACK` ingredient rows at
  3.24–3.93mm on 50–61 characters, `177-min` failing both rows at 2.86/3.23mm, and
  `269-min`'s dosage at 3.80mm — against the 4.0mm the references hold small print
  to. The driver fits a long row by shrinking it, so the failure it produces is
  illegibility rather than overflow.
- **One Blender process per SKU, and that is the decision, not an omission.** Startup
  is 2.6 s of a 27.9 s render; an actual three-SKU batch saved 1.84 s per SKU (6.7%),
  ~12 minutes across the catalogue. **Batch mode is closed as "not doing."** The
  earlier ~20 s / ~2 h figure quoted here was never measured and is wrong by ~8×.
  More than half of every render is the denoiser (~14.9 s) — that, not the process
  boundary, is where a faster catalogue pass would come from.
- **`08_ops/` is mostly stale.** Six of its seven documents do not mention Blender
  at all, and `ACCEPTANCE_TEST.md` still calls `src.rpa_orchestrator` directly,
  bypassing the facade. `DEPENDENCY_INVENTORY.md` now has rows for the Blender
  executable and for Tesseract OCR (added alongside this verification barrier).
- **`06_docs/experiments/BLENDER_RENDERER_ROADMAP.md` is stale.** It still reads
  "Phase 0 complete, Phase 1 foundation in place", which has been untrue for weeks.
- **No ADR for the Blender decision.** `00_governance/DECISIONS/` tops out at
  ADR-006.
- **Cross-machine determinism is unverified.** Renders are pixel-identical on repeat
  on one machine; GPU-versus-CPU Cycles reproducibility has never been tested.

## Catalogue facts worth keeping in view

- 391 SKU. Template split: T1 287, T1_SMALL 37, T3 26, T_BOTTLE_BOX 12, T_VERT_VIAL
  10, T1_LARGE 6, T_MULTIPACK 5, T_VERT_DROPPER 4, T_VERT_INHALER 4. **T2 has zero**
  — do not spend effort on it.
- 370 cartons declare `["Braille", "DataMatrix_Zone", "Tamper_Evident_Seal"]`;
  **21 declare nothing**, so any renderer that assumes every carton is identical gets
  those 21 wrong.
- Only 9 distinct dimension triples across all 391 SKU. The data is per-category, not
  per-item measurement — worth remembering before treating it as precise.

## Process note

Several parallel background sessions contributed to the current state. Two of them
independently implemented the same packshot features and had to be reconciled by hand
(`badc8b7`, "reconcile two independent implementations"). Parallel agents on the same
file duplicate work; scope them to disjoint files or run them in sequence.
