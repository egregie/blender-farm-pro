# Changelog

All notable changes to **PharmaGen PRO** are documented here.
Format inspired by [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased] — The colour figure with the render taken out — 26 August 2026

Nothing that is painted changed: contract stays at 1.8, and no spec, manifest,
render, `print_truth.json` or `design_qa.json` was written. Write-up in
[`00_PROJECT_STATE/FIT_COLOUR.md`](00_PROJECT_STATE/FIT_COLOUR.md).

### Corrected
- **`region_colour_gap` was published as a ranking of paint and it is not one.**
  It compares OUR RENDER against the photograph in raw values, so it carries the
  exposure difference, the rig's measured black lift, and the fit error. Split
  off the best neutral scale: `230_Slimex`'s headline 0.3652 is **0.0187** and
  the rest a 1.29× level; every substrate gap in the group above 0.26 is a level
  difference, while `151-min` also carries zero fields and reads 0.0713.
  `64_Kamagra`'s 0.128 chromatic residual is the lift — red 0.131 against a spec
  that says 0.000. As a before/after the exposure term cancels and the figure
  stands; as a ranking it misleads. The reading this file already carried for ΔC,
  arriving at a figure that shipped without it.
- Two findings survive and come out stronger: `157_Valium` 0.549, `272_Roche`
  0.512 — and on both **our render is four times closer to the spec than the
  spec is to the photograph.** The renderer obeyed; the fitter chose wrong.
- `segment()`'s docstring declared three return values and returns five.

### Added
- `scripts/measure_fit_colour.py` — the fitter's declared fill against the pixels
  the part covers, with no render in the comparison. A `fill` is
  `np.median(raw_px[cluster])` off the rectified photograph, so both sides are
  one measurement in one space: nothing to level, no curve, no lift. Whole group
  in 20 seconds. `--sku` prints and writes nothing.
- `part_index()` — `spec_index` kept per PART and in paint order, since contract
  1.9 is a statement about parts and a part under a later one must be scored on
  what remains visible.
- `spread` beside each gap — whether the part is one colour at all, which splits
  "the fitter chose wrong" from "there is no single right answer here".
- `tests/test_fit_colour.py` — the zero floor over the committed report, paint
  order, null-never-zero, and that `spread` separates the two failures.

### Measured
- **The floor is exactly zero on all 28.** Measuring the substrate cluster back
  returns `spec["substrate"]` to four decimals, and every spec carries exactly
  the rectification's own aspect so nothing is resampled.
- Getting there meant dropping the illumination flattening from the headline. The
  check: **a part that IS its own cluster has to read zero.** `64-min`'s
  `brand#0`, 32.6% of the face, read 0.0039 raw against 0.0950 levelled;
  `59-min`'s `highlight#0` 0.0068 against 0.2052. The plane is fitted over
  "wherever the spec draws no field", which on those cartons is the board plus
  everything the labelling wrote off. Kept as `gap_levelled`.
- **33 of 75 parts at or beyond `SAME_SURFACE_MAX`, on 20 of 28 cartons.**
  25 are uniform and simply wrong — `152-min`'s `brand#1` has spread **0.0000**
  over 6.47% of the face, declared orange, charcoal in the photograph. 5 have a
  spread at or above their own gap, where no fill is right however estimated.
- `157-min`'s `type#0` reads `#083BC7`, the same answer `PART_COLOUR.md` reached
  by two other routes that share no code with this one.
- **`149_Modalert` and `344_Modafinil_Generic` are one photograph**, byte for
  byte under two names, same corners, same spec. The 28 folders are **27
  distinct references** and every group mean counts that carton twice.

## [Unreleased] — Two instruments for the question 1.9 failed on — 25 August 2026

Nothing that is painted changed: contract stays at 1.8, `part.fill` was not
reintroduced, no spec, manifest, render or `print_truth.json` written, and every
prior field of `design_qa.json` is byte-identical. Write-up in
[`00_PROJECT_STATE/PART_COLOUR.md`](00_PROJECT_STATE/PART_COLOUR.md).

### Added
- `scripts/measure_part_colour.py` — four part-colour estimators and a synthetic
  bench with KNOWN answers at the sizes that occur, because a real part has no
  known colour and agreement with the cluster is the thing already shown wrong.
  Winner: erode by **0.35 of the part's own thickness**, 0.0020 mean error
  against the median's 0.0076, worst 0.0047 against 0.0453.
- `region_colour_gap` in `design_qa`, beside the existing fields and replacing
  none. Regions from `spec_index` — outlines, not colours — so the figure does
  not move when paint does. Inherits the fit error and says so.
- `tests/test_region_colour_gap.py` — invariance demonstrated rather than
  asserted: `spec_index` unmoved when one fill is brought within 0.001 of
  another, while the classified map drops below 95% agreement with the geometry.

### Measured
- **Thinness breaks the median, not smallness.** 0.0018 on a 0.16% blob, 0.0453
  on a 6px strip. Real thicknesses agree: erosion moves the 3.4px and 5.4px
  parts and leaves the 60.2px and 65.6px ones, whose distance from their cluster
  is a real difference in paint.
- **This corrects `PART_FILL.md`.** Erosion was recorded as "half working" and
  unable to tell rim from real; it separates them cleanly once thickness is
  measured. The earlier reading took closeness to the cluster as correctness.
  Consequently the rim explanation is too small to carry the 1.9 regression,
  whose cause is **not established** — the palette shift is the remaining
  candidate.
- **The new figure sees what the old ones hide.** `157_Valium`'s blue bar is
  painted near-black purple, 0.583 apart, where `render~ref` reads 99.5%. And
  `346_Modvigil` and `230_Slimex` score `render~ref` **1.000** carrying zero
  fields — one palette entry, everything classifies to it — while their board
  sits 0.37 from the photograph.
- Every existing boundary erosion in the tree (11, 19, 3, 3, 1) is applied to a
  large region; none was ever asked to work on a 0.16% part.

## [Unreleased] — Contract 1.9 built, measured and rolled back — 25 August 2026

The wide per-part-fill change was implemented in full and reverted. No code,
spec, manifest or figure carries anything from it; `print_truth.json` was never
touched. Suite green at 392. Full write-up appended to
[`00_PROJECT_STATE/PART_FILL.md`](00_PROJECT_STATE/PART_FILL.md).

### Measured
- **The plumbing is provably neutral.** Landed in two stages on purpose. With
  every part's `fill` set to its field's — the value it had always been painted —
  all 29 specs are byte-identical after stripping the new key, all 391 manifests
  move only by the version string and that key, and `design_coverage` over 28
  cartons moves on **no column at all**.
- **`design_coverage` moved by zero in Stage B as well**, exactly as predicted:
  its figures are field INDICES and colour never enters them. A part went from
  orange to charcoal and `truth_agreement` did not notice.
- **`design_qa` says the change does not pass.** Mean `render~ref` **0.9395 →
  0.9346**, 5 cartons improved, **9 regressed beyond the 0.02 rule**. Best
  `64-min` **+8.8** (0.890 → 0.978); worst `59-min` −7.7, `62-min` −6.8,
  `362-min` −5.8. Rolled back whole rather than tuned.
- **Why: small parts' medians carry their antialiased rim.** Large parts barely
  moved — Ritalin's 39.1% part by 0.000, Kamagra's 32.5% by 0.004 — while
  Ritalin's 0.42% part moved 0.182 and Cialis Professional's 0.16% part 0.259.
  Eroding the mask half works and cannot tell the two causes apart: it takes
  Ritalin's sliver 0.182 → 0.059, leaves Cialis Professional's genuinely
  different `highlight#1` at 0.290 → 0.286, and moves `64_Kamagra` — the one
  carton that gained — the wrong way.
- **And the deeper problem is structural.** `design_qa`'s palette is both the set
  of colours `rasterise` paints and the vocabulary both sides are classified
  against, so changing what a part is painted changes the classifier. Before and
  after are two instruments, not two renders. Not fixable with more care.

### Solid, and worth keeping in mind
- **A per-part palette must collapse at `SEPARABLE_MIN`.** One entry per part
  regardless left eight cartons "palette not separable": `221_Inderal`'s
  `highlight#2` sits **0.002** from its `highlight#0`, taking that carton's worst
  field to **0.0%** and `357_Adderall`'s `render~ref` to **37.8%** on renders that
  had not changed. Collapsing recovered Inderal to 89.3% / 93.3%.
- `64_Kamagra` **+8.8** is the one clean signal that the diagnosis underneath is
  right: its `highlight` parts sit 0.055–0.094 from the merged cluster colour and
  are large enough to measure without rim contamination.
- `scripts/calibrate_render.py` needed the new key too, and the schema test
  caught it — the chart is a design like any other.

## [Unreleased] — A part is painted its cluster's colour — 24 August 2026

Read-only. No code changed, no spec, manifest or figure changed,
`print_truth.json` untouched in all 28 folders. Write-up in
[`00_PROJECT_STATE/PART_FILL.md`](00_PROJECT_STATE/PART_FILL.md).

Set out to recover three components misfiled `unrepresentable` because `fill`
lives on the field and a part has none. The emission threshold was to come from
the distribution of part-versus-cluster colour distance. **There is no
threshold**, and the reason is that they are not three cases.

### Measured
- Over the 75 components classified `print`, the distance between a part's own
  colour (median of its RAW pixels, exactly how `segment()` measures a cluster's)
  and the colour it is painted runs 0.000 to **0.7389** in a smooth ramp with no
  gap. The largest is `152_Artvigil brand#1`, class `print` and shipping.
- **31 of 75 shipping parts — 41% — sit further from their paint than
  `SAME_SURFACE_MAX`**, the threshold at which this project already calls two
  clusters one surface. Their summed area is 109.6% of face-equivalents against
  446.5% for all printed parts, across **18 of 25 cartons**. Roughly a quarter of
  all printed design area is painted a colour that is not its own.
- Verified by looking, not by the number: Artvigil's dark charcoal S-curve is
  painted orange, Valium's bright blue bar near-black purple, Valium Brand's blue
  Roche hexagon dark navy. All three are class `print`.
- **Why nothing caught it.** `design_coverage.py` compares field INDICES, so a
  part painted orange where the reference is charcoal still agrees. `design_qa`
  classifies the render against the SPEC's own palette, so a render told to paint
  orange and painting orange scores a colour error of zero; only `render~ref`
  disagrees, thinly, over 18 cartons.
- Eleven sites read "what colour is this region", two of them not named in the
  brief: `measure_type_rows.py` and `type_qa.py` both pair a field's fill with a
  part's outline, and three sites decide a measured row's INK from it.

### Not done
- The narrow change the brief authorised does not exist. The honest shape is
  every part carrying its own measured fill, which is a re-measurement event for
  every colour figure on 25 cartons rather than 3. That is a scoping call, not a
  measurement, and the work stopped at the brief's own edge case.

## [Unreleased] — `unrepresentable` triaged — 24 August 2026

Read-only. Nothing reclassified, no spec, manifest or figure changed. Write-up in
[`00_PROJECT_STATE/UNREPRESENTABLE_TRIAGE.md`](00_PROJECT_STATE/UNREPRESENTABLE_TRIAGE.md).

### Measured
- **The class is four problems, not one**, taken from the reasons the labelling
  already carries: 19 components are photographic inserts (54.80% summed, almost
  all `346_Modvigil` and `230_Slimex`), 3 are continuous tone or pattern (21.18%,
  almost all `362_Hydrocodone`'s gradient panel), 3 were **merged into another
  cluster**, and 1 was lost to the simplify tolerance.
- **The three merged ones are misfiled.** Nothing about them is unrepresentable:
  each is a solid region of one colour, and what blocks them is that `fill` lives
  on the FIELD and a part has none — a teal Waklert badge that k-means put in the
  orange cluster traces perfectly and cannot be painted. All three are the
  product's own design (a brand badge, a do-not-substitute pictogram, a dosage
  box), so unlike the `mark` question there is no owner decision behind them.
- **Recovering them is worth about +0.04 group points, and that is a fact about
  the instrument rather than about the change.** `unrepresentable` sits outside
  the scored area, so these cost nothing today and can earn nothing; drawing all
  three correctly moves their own cartons +1.005, +0.069 and +0.003. For a badge
  covering 5.08% of a printed face. `truth_agreement` is blind to whatever the
  labelling wrote off, the same shape of error as `pixel_agreement` being nearly
  a statement about the board.
- **Reclassifying without being able to draw costs `150_Waklert` thirty points**
  — 96.8% to 66.8%. The reclassification and the ability to draw are one change,
  the same pairing as a `mark` hole and its mark.
- The screen that does see these already exists: printed cluster against labelled
  print. The three blank cartons report `truth_agreement` as **null** and an
  infinite ratio rather than a number, which is why they are visible at all.

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
