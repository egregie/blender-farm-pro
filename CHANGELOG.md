# Changelog

All notable changes to **PharmaGen PRO** are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — What the marks actually are — 24 August 2026

Phase 1 of the marks question: establish what the 35 `mark` entries contain
before anyone is asked to decide about them. Read-only. Nothing reclassified, no
spec, manifest or figure changed, `print_truth.json` byte-identical in all 28
folders. Evidence in
[`00_PROJECT_STATE/MARKS_EVIDENCE.md`](00_PROJECT_STATE/MARKS_EVIDENCE.md).

### Added
- `scripts/render_mark_evidence.py` — crops every `mark` component and live
  `mark` hole out of the rectified face at magnification, plain beside the
  classified pixels tinted, and measures each region's internal structure.
  `tests/test_mark_evidence.py` pins that it writes only under its evidence
  directory, opens nothing for writing, never imports `label_print`, carries no
  verdict field in its index, and that every mark in the labelling has a crop —
  a decision may not be taken on an entry nobody was shown.
- `00_PROJECT_STATE/MARKS_DECISION.md` — the decision template, facts filled and
  **the decision column deliberately empty**. It is the owner's to complete; a
  blank is not an answer and the implementer stops on one.

### Measured
- **All eight `mark` holes are solid.** `islands = 0`, `solid_frac = 1.000` on
  every one. Since `trace_holes()` keeps no islands, a cut `mark` hole can only
  ever become a filled outline: the "Pfizer" script inside Viagra's and Ativan's
  ovals is not separated by the segmentation and would not appear in a render.
  What is being decided is whether to draw the silhouette, not whether to
  reproduce the artwork.
- 92% of the +9.937 is those two ovals — +5.290 and +3.865. The rest totals
  +0.782, and Adderall's two Shire fragments are worth −0.001 and −0.002.
- Held out of the branding question by name: `357-min`'s **C-II schedule
  symbol** (a regulatory marking, not a trademark) and `59_Cialis`'s **Lilly
  holographic oval** (an anti-counterfeiting feature, and a component, so it
  carries none of the figure).

### Not done
- Phase 3 — `design.marks[]`, the paired hole rule and the driver — is blocked on
  `MARKS_DECISION.md` being filled in by a person. No code was written against it.

## [Unreleased] — The hole ceiling — 24 August 2026

The tooling migration closed with the observation that the whole 6.8-point gap
between "outer ring only" and "every hole cut" belongs to holes, and that ten of
the group's holes are cut. This priced the rest. Nothing was reclassified; no
spec, manifest or figure changed. Full write-up in
[`00_PROJECT_STATE/HOLE_CEILING.md`](00_PROJECT_STATE/HOLE_CEILING.md).

### Added
- `scripts/measure_hole_payoff.py` — cuts each hole alone and re-scores
  `truth_agreement`, which needs no render. `behind` is computed once per part
  and each hole is then a masked substitution, so pricing all 239 costs one
  `segment()` per folder. It answers what a cut would be WORTH and never whether
  to make it: `tests/test_hole_payoff.py` pins by static scan that it writes only
  its own report, opens nothing for writing, never imports `label_print`, and
  that every class in the report is a join onto the hand-made labelling.
- `scripts/measure_face_resolution.py` and
  `TestTheFaceResolutionCeilingIsDeclared` — the real size of every reference
  face, and the six folders below 350px named. A declaration, not a gate: they
  keep their specs and go on rendering.

### Measured, and no action taken
- **The 228 filled holes are worth +10.920 points excluding `lettering`, and 91%
  of that is `mark`.** Two holes carry +5.290 and +3.865 — Viagra's and Ativan's
  Pfizer ovals — with Inderal's LCI roundel third. Cutting a `mark` hole while
  drawing nothing into it shows board through our field in the shape of another
  company's logo, which is the act contract 1.8 already refuses for another
  company's lettering. **Outside every third party's branding the reachable
  figure is +0.983 points over 22 holes**, 23 of the 29 non-lettering holes worth
  under 0.1 each. Below the threshold set before measuring, so the
  re-classification pass was not run.
- What it opens is not an engineering decision: a `mark` hole and a `mark`
  component are one decision, the 27 components are already labelled for
  `design.marks[]`, and cutting the hole *as part of drawing the mark* is
  coherent. Worth the +9.937, blocked on reproducing third-party trademarks.
- **The face resolution ceiling.** `OUT_WIDTH` is 1100 whatever the photograph,
  so `357_Adderall`'s 134x172 face is enlarged 8.21x and `SIMPLIFY_TOLERANCE`
  works out at 0.13 of a source pixel there.

### Fixed
- Three counts of the group's holes disagreed — 242 entries in the truth files,
  239 in the partition, 238 in `CLAUDE.md`. The difference is three `74_Viagra`
  holes flagged `"vanished": true`, labelled against the corners `6d37b89`
  corrected and kept rather than deleted so the disappearance stays visible.
  Stated in the report and in `CLAUDE.md` instead of being re-derived next time.

## [Unreleased] — Tooling migration — 24 August 2026

Four installed-but-unwired libraries were to be brought into the design-transfer
chain, one at a time, each with a measured delta. Three of the four are still
unwired and now for a recorded reason. Full evidence in
[`00_PROJECT_STATE/TOOLING_MIGRATION.md`](00_PROJECT_STATE/TOOLING_MIGRATION.md);
the baseline every "before" column is read from is
`00_PROJECT_STATE/baseline_2026-08-24/`.

Each bullet is one measuring event, and the negative results are kept
deliberately — the cost of this work was mostly in establishing what does *not*
help, and deleting that leaves the next attempt to pay it again.

### Added
- **The Cycles compute device is stated rather than inherited.**
  `setup_render()` never assigned `scene.cycles.device`, so the device was
  whatever the process started with — and Blender accepts more than one
  `--python`, so a script running ahead of the driver could move an entire
  render onto the GPU with nothing in the log to say so. New
  `blender.device` / `device_backend` / `denoising_device` in `config.yaml`,
  a `setup_device()` that raises `SystemExit` on an unavailable back-end rather
  than falling back, and a `device` block in `--dump-scene` read back off the
  scene rather than echoed from the flags. **Pixel-neutral: `max_channel_delta
  = 0`** against the baseline render, confirmed three ways.
- `scripts/probe_render_device.py` — measures whether a device change moves the
  picture. `scripts/probe_partition_shift.py` — measures whether a segmentation
  change invalidates the hand-made labelling. Both kept as instruments.
- `src/vectorise.py` and 18 tests — the rejected tracer, kept unwired as the
  only implementation of two SVG parsing traps, and now guarded by tests that
  fail if anything imports it.

### Measured and rejected
- **GPU rendering.** OptiX sampling 1.17–1.45× faster and up to 43 levels apart
  on 0.2–0.9% of pixels; CUDA 1.18–1.45× and up to 23 levels on 0.2–0.7%; GPU
  denoising up to **5.4×** and up to 43 levels on **14–18%** of pixels. None
  reproduces the CPU image, so none was enabled. The cheap win and the expensive
  change are the same setting.
- **vtracer as the design tracer.** Wired in, it took the group's
  `truth_agreement` **95.36% → 94.19%**, with `304_Sonata` −17.4 and
  `155_Imovane` −5.7 points. **The premise did not reproduce**: the "0.954
  against 0.888" that motivated the work is the *same polyline* scored two ways
  — every hole cut (0.9536) against the outer ring alone (0.8855). Like for
  like vtracer is worse on both footings (0.8649 and 0.9236), on 75 of 75
  components, at every one of eight parameter settings tried. The 0.954 is
  unreachable regardless: it needs every hole cut, which contract 1.8 forbids.
- **Perceptual colour in the segmentation — both events.** Replacing the
  lightness estimator (`rgb.max(-1)` is V of HSV, not a lightness) moved the
  partition on **21 of 28** folders; clustering in OKLab instead of sRGB moved
  it on **27 of 28**. Neither reached a figure, because both fail the
  precondition every figure rests on: `print_truth.json` keys 661 hand-made
  classifications to `role#i`, and both halves of that key are outputs of the
  partition. **The segmentation is frozen by its labelling**, and improving it
  costs a deliberate manual re-classification of 28 folders, not a code change.

### Fixed
- **`render_calibration.json` carried one stale row.** It was written at
  `68961a6` and `74_Viagra`'s face corners changed at `6d37b89`, after it — so
  its chart was built from a carton that no longer existed. Re-measured:
  `colour_residual_median` 0.0230 → 0.0149, worst 0.0585 → 0.0406, and in
  `design_qa` that carton's second field went from matching its own photograph
  on 0.312 of its pixels to 0.806. The other 27 rows came back byte-identical.
- **`00_PROJECT_STATE/design_qa.json` retaken** against the current driver and
  the fresh calibration. One row of 28 moved — the same `74-min`.

### Known gaps, named not fixed
- `calibrate_render.driver_fingerprint()` hashes the driver file plus the render
  settings, but **not the manifest the chart is built from**, so a carton
  reshape or a corner re-set leaves it matching while the curve goes stale. This
  is how the row above went unnoticed. Repairing it means covering the design
  spec's own `verification` block or the manifest hash.
- `config.yaml`'s three device keys are welded to the driver's flag defaults by
  a test rather than passed on the command line; wiring them through needs one
  line in `src/blender_renderer.py`.

## [v1.0.1] — Patch — June 2026

### Fixed
- **Declared the missing `pydantic` runtime dependency** in `requirements.txt`.
  `pydantic` is required by Stage 1 (`schemas/common.py`, via `pharma_pkg`
  routing) but was absent from the dependency list, so a from-scratch install
  per the README would fail Stage 1 with `ModuleNotFoundError`. Found by a
  clean-machine reproducibility test. No pipeline/architecture/logic change — a
  pure packaging fix (SemVer patch).

## [v1.0.0] — Initial Production Release — June 2026

**PharmaGen PRO — Version 1.0 — Production Release.**

### Highlights
- **391 SKU rendered** to PNG; **389 delivered** as final WEBP assets (`output/`).
- **Unified Pipeline** — one entry point (`main.py`) over three stages (passports → render → final images).
- **Resume** — interruption-safe; re-running continues without duplicating work.
- **QA** — rule-based verifier plus a unit-test suite.
- **WEBP** — final assets at 1600×1600, ≤500 KB.
- **CLI** — `--full` / `--passports-only` / `--render-only` / `--process-images-only` with `--resume`, `--limit`, `--from`, `--headless`, `--debug`, `--config`.
- **Documentation** — architecture, ADRs, audits, deployment, operations, disaster recovery, backup, dependency inventory, acceptance test, design rationale, and a business/CRM brief.
- **Production Ready.**

### Release composition
This release groups four hardening phases (see the corresponding commits):
1. **Architecture Unification** — `main.py` + `config.yaml` + `src/` package + back-compat shims; stale absolute paths fixed.
2. **Repository Cleanup** — `scripts/`, archival `trash/`, bilingual README, Mermaid diagrams, repo audit.
3. **Production Hardening** — Bus Factor / Production Readiness / CRM Readiness audits, ADR-001..006, project history.
4. **Operations Documentation** — deployment, operations, disaster recovery, backup, dependency inventory, acceptance test, design rationale, business value & integration.

### Known limitations
- Rendering is browser-driven (Gemini RPA): requires a logged-in session, runs non-headless, and is single-threaded.
- Rendered images are **non-deterministic**; `output/` is the system of record (not reproducible by re-running).

## [0.x] — Pre-release development — May–June 2026

Foundational development (squashed into a single baseline commit): OCR/CV
groundwork, the passport compiler, the template system, renderer experiments,
the Gemini RPA renderer, and catalogue work (P20–P22) that rendered all 391 SKU.
See [PROJECT_HISTORY.md](PROJECT_HISTORY.md) for the full narrative.
