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
**1.2**) is the single authoritative description of what a renderer receives.
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

## Verified on 2026-08-02

All nine reference SKU were re-rendered from the current merged code and compared
against `01_input_raster/reference/`. The renders read as real packshots: white body,
correct badge, correct stripe, legible text on the correct rows.

Measured silhouette fill, reference versus render, dominant axis:

| Template | ref w/h | render w/h |
|---|---|---|
| T1 | 78/60 | 74/48 |
| T1_LARGE | 84/74 | 74/48 |
| T1_SMALL | 76/59 | 74/48 |
| T3 | 88/57 | 74/37 |
| T_BOTTLE_BOX | 48/80 | 51/80 |
| T_MULTIPACK | 83/60 | 69/48 |
| T_VERT_DROPPER | 57/79 | 36/75 |
| T_VERT_INHALER | 58/76 | 43/79 |
| T_VERT_VIAL | 67/77 | 38/79 |

## The one open question that needs a decision

**The reference renders and the passport dimensions disagree about carton
proportions, and only a human can say which wins.**

The table above shows the vertical family and T3 rendering markedly narrower or
flatter than their references — `T_VERT_VIAL` occupies 38% of frame width against the
reference's 67%, `T_VERT_DROPPER` 36% against 57%.

This is not a bug in the geometry. It follows from a fact about how the references
were made: the Gemini prompt carries **no dimensions at all** on the common path, so
every proportion in the reference set is Gemini's invention. Our renders use the
catalogue's real `secondary_packaging.dimensions`. Where the two disagree, the
question is which is authoritative:

- If the passport data is the source of truth, the current renders are correct and
  the reference set is simply wrong about shape for those templates.
- If the reference set defines the desired art direction, then proportions are a
  styling decision and should not be driven off the dimension strings for the
  vertical family.

Nothing downstream should be tuned until this is settled, because both "fix the
framing" and "fix the dimensions" are plausible responses to the same measurement and
they lead in opposite directions.

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
- **The full catalogue has never been rendered.** 18 PNG exist out of 391; the nine
  above are the only ones produced by current code. At roughly 67 s per SKU that is a
  ~7 h pass, and no such pass has been run.
- **Stage 3 cannot consume Blender output without a manual override.**
  `image_processor.source_dir` still points at the Gemini directory; feeding Blender
  renders through to WEBP needs `--config`.
- **One Blender process per SKU.** Roughly 20 s of every render is fixed startup
  cost, about 2 h of pure overhead across the catalogue. A persistent instance
  processing a batch was proposed and is still not built.
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
