# Verification barrier — design

**Date:** 2026-08-03 · **Status:** approved, not yet implemented
**Supersedes nothing.** Feeds `00_PROJECT_STATE/NEXT_STEPS.md` item 3 (post-render
verification) and closes three defects found while auditing the repository.

## Problem

The project has no mechanism that catches a regression between sessions. Three
failures are live in `dev` right now, and they are the same class: **the
repository asserts something that nothing verifies.**

| | Failure mode | Live example |
|---|---|---|
| **F1** | A stage's `main()` breaks end to end while the unit suite stays green | `src/passport_generator.py` wrote to `Path("docs")` after the folder renumbering. All 149 tests passed. Only a live pipeline run caught it. |
| **F2** | A committed artifact contradicts itself | `00_PROJECT_STATE/sweep_report.json` says `covers_whole_group: true, total: 30`. Its `.md` sibling says "partial run — first 2 of the group only". |
| **F3** | Code exists but is unreachable in this fork's layout | `scripts/render_qa.py` defaults to `render_output/processed`, a directory from the *source* project that this fork has never had. |
| **F4** | A render is wrong in a way no current check can see | Nothing inspects a rendered pixel against the manifest that produced it. |

F2 is a repeat. A code review already caught it once (`bc44665`), the fix landed,
and it recurred within one session: [`catalogue_sweep.py:386`](../../../scripts/catalogue_sweep.py)
computes `md_path` from `report_paths(limit)` and
[`:504`](../../../scripts/catalogue_sweep.py) ignores it, hardcoding
`sweep_report.md`. `md_path` is assigned once and never read. The guard protected
the JSON and not the Markdown, so a 2-SKU verification run overwrote the real
30-SKU record, and the change rode into `dc7d8e1` as 46 lines inside a 434-file
rename commit.

**"Add more tests" does not address the class.** F2 is an artifact, not code. F1
was missed because no test invokes a stage's `main()`. F3 is a path that only
fails outside the repository root.

## Evidence gathered for this design

All measured on 2026-08-03 on the development machine.

**Stage 1 costs 3 seconds** for all 391 passports
(`00_PROJECT_STATE/logs/pharmagen_20260802_205425.log`, 20:54:25 → 20:54:28). It
is cheap enough to run inside the default test suite with no `--limit`.

**Tesseract 5.4.0.20240606 is installed** at
`C:\Program Files\Tesseract-OCR\tesseract.exe`, via winget
`UB-Mannheim.TesseractOCR`. It is **not on PATH**; `shutil.which("tesseract")`
returns `None`, which is why an earlier reading of this project concluded OCR was
unavailable. `render_qa.py` already probes that exact path in its import block, so
its backend initialises correctly today.

**OCR on the current renders is unusable.** Six real Blender renders, checked
against their manifests with the existing `--psm 6`:

| SKU | Expected brand | Tesseract read |
|---|---|---|
| `1-min` | Atomoxetine Generic | `Germetine` |
| `11-min` | Amoxil | *(empty string)* |
| `10-min` | Revia | `2 \|` |
| `103-min` | Maxalt | `maxa!` |
| `107-min` | Tramadol | `{ra m a d O` |
| `111-min` | Retin-A Cream 0.025% | `retin" cream` |

Page-segmentation mode is not the cause: modes 3, 6, 11 and 12 were all tried, and
`11-min` returns an empty string in every one.

**The typeface and size are not the cause either.** The same four strings drawn
flat with the vendored `DejaVuSans-Bold.ttf` / `DejaVuSans.ttf` at the cap heights
they occupy in a render OCR cleanly at 4/4:
`'Atomoxetine Gener Atomoxetine 40mg 10 Pills'` (the truncation is the probe's
canvas, not the recogniser).

**Therefore the carton's 35° Z-rotation is the entire problem**, and correcting
the perspective is both necessary and sufficient.

**Corners cannot be recovered from the image.** Two probes tried and failed. A
colour mask keyed on `palette.accent` conflates the accent stripe with the brand
badge whenever `primary` and `accent` are within the tolerance, and the principal
axis returned by SVD is sign-ambiguous, so the recovered angle came out as
138°–178° where the true tilt is a few degrees to −41°. The renderer already holds
the camera and the exact geometry. It should publish the answer rather than have a
consumer guess it — the same principle the render manifest is built on.

**Renders are not tracked by git.** `git ls-files 02_processing/blender_test_renders`
returns nothing, so a test cannot assume a PNG is present.

## Design

### Carrier: the existing test suite

No new command. `python -m unittest discover -s tests` is the one instruction
already in `CLAUDE.md` and the one people already trust. A second command to
remember is how a third forgotten thing gets created. The suite missed F1 because
nothing exercised `main()`, which is a gap in the vehicle, not a reason to change
vehicles.

The only piece that will not fit in a fast default run is a live Blender render;
that goes behind the existing opt-in `PHARMAGEN_SLOW_TESTS=1` gate.

### F1 — stages run end to end

New `tests/test_pipeline_smoke.py`:

- Runs `python -m src.passport_generator` as a subprocess, asserts exit 0, 391
  Markdown passports and 391 manifests present.
- Asserts **idempotence**: SHA-256 of every output before and after the run is
  unchanged. This is already a documented project invariant; the test makes it
  enforced rather than claimed.
- Runs `python -m src.render_stage --engine blender --estimate` as a dry run,
  asserting exit 0 without invoking Blender.

**The load-bearing detail: run from a temporary working directory, not the
repository root.** Running from the root would not have caught `Path("docs")` —
that is precisely why the bug survived to a live run.

### F2 — a report cannot lie about its own scope

- One-line fix: `write_reports` uses the `md_path` it already computes.
- Regenerate `00_PROJECT_STATE/sweep_report.md` from the real
  `sweep_report.json`. The 30-SKU data survived; only the rendering of it was
  lost.
- Test: a partial run leaves `sweep_report.md` untouched (mock the render, call
  `write_reports(limit=2)`, compare the canonical file's hash).
- Test: for every `*.json` / `*.md` pair in `00_PROJECT_STATE`, the Markdown
  header agrees with the JSON's `covers_whole_group` and `counts.total`.

### F3 — every script's default paths resolve

Test walks `scripts/*.py`, collects each `argparse` default that is a path, and
asserts it resolves under this fork's config. It will fail on `render_qa.py`
today, which is the correct result.

Fix: `render_qa.py` resolves paths through `src.utils.get_path`, with its source
directory following the selected engine.

### F4 — OCR proves the text is *visible*

`--dump-scene` already proves each label row carries the right string, byte for
byte. It cannot see whether that string ended up visible: a correct text object
can still fall outside the camera, sit behind another face, or render white on
white. OCR sees exactly that, and the two checks are complementary.

Four parts:

**(a) The driver publishes where the front face landed.** `render_driver.py`
computes the four corners of the front face in image pixels using
`bpy_extras.object_utils.world_to_camera_view()` scaled by the render resolution,
and writes them to a sidecar `{stem}.view.json` beside the PNG — mirroring the
existing `{stem}.job.json`. The same corners go into `--dump-scene` output. The
side panel's corners are emitted too; nothing consumes them yet, but they come
from the same call and omitting them would mean touching the driver twice.

**(b) `src/deskew.py`** — a pure function taking a PNG path plus four corners and
returning the front face as a flat, axis-aligned `PIL.Image` via an inverse
perspective transform. No Blender import, no I/O beyond reading the PNG, so it is
directly unit-testable.

**(c) `scripts/render_qa.py` reworked.** Three changes beyond the path fix:
- Deskew before OCR.
- **Check against the render manifest, not the passport.** The Blender engine
  renders from `label_content` in the manifest; QA currently reads
  `brand_name` / `label_content` off the passport. Where those differ, QA reports
  a failure against a contract the renderer never saw.
- Report a per-field confidence score with warnings, mirroring
  `agent_2_verifier`, instead of `HARD_FAIL`. Its own docstring already promises
  "never blocks the pipeline"; the current `HARD_FAIL` logic contradicts that.

**(d) The barrier test.** One real render is committed as a fixture —
`tests/fixtures/ocr/1-min.png` plus its manifest and `.view.json` — because
renders are not otherwise in git and an opt-in check is not a barrier. `1-min`
(Atomoxetine Generic, T1) is chosen because T1 is the modal template at 287 of
391 SKU and because it is already the SKU the calibration work measures against.
Two assertions:
- On the fixture, the brand name is found and at least 3 of 4 label fields are
  recovered.
- The **deskewed** image scores strictly higher than the same image OCR'd raw.
  This is what stops the deskew step from being quietly removed while the test
  stays green by luck.

Behind `PHARMAGEN_SLOW_TESTS=1`, the same SKU is re-rendered and the same
assertions run against fresh output, so fixture drift is caught.

## Not doing

- **No CI.** A GitHub runner has no Blender, so 69 of 149 tests would skip. A
  green badge over unverified geometry, lighting and text is worse than no badge.
- **No pre-commit hook.** The useful checks take minutes; a slow hook gets
  bypassed, and bypassing hooks is forbidden in this project.
- **Not touching the carton-proportions question** (`NEXT_STEPS` item 1) or the
  small-print floor (item 9). Different decisions, different session.

## How the barrier is itself verified

Mutation testing against the three bugs that actually happened. Each must fail
exactly one test and no others:

| Mutation | Must fail |
|---|---|
| Restore `Path("docs")` in `passport_generator.py` | the F1 smoke test |
| Restore the hardcoded path at `catalogue_sweep.py:504` | the F2 partial-run test |
| Restore `render_output/processed` in `render_qa.py` | the F3 path test |
| Remove the deskew call from `render_qa.py` | the F4 comparison assertion |

A test that survives its mutation is decorative and gets rewritten, not
celebrated.

## Risks

| Risk | Mitigation |
|---|---|
| A Tesseract upgrade changes recognition output and breaks the fixture test | Assert a threshold (≥3/4 fields, brand present), never exact text. Record the pinned version, 5.4.0.20240606, in `08_ops/DEPENDENCY_INVENTORY.md`. |
| Tesseract absent on another machine → OCR tests skip → not a barrier there | Skip with an explicit message, as the Blender tests already do, and add the binary to the dependency inventory. Accepted: it is a system binary, not a pip package. |
| Touching `render_driver.py` changes the rendered pixels | The addition is a read-only measurement written after the render. Assert one SKU renders byte-identically before and after the change. |
| Deskew corners wrong for the vertical family or T3, where faces are narrow | Before declaring done, run the 30-SKU group and report OCR hit rate per template. A template below threshold is a finding, not a rounding error. |
| The committed fixture goes stale as the renderer evolves | The slow gate re-renders the same SKU and runs identical assertions. |

## Cost

- Default suite: 149 → roughly 158 tests, +5 s (3 s Stage 1, the rest negligible).
- One committed PNG fixture, ~2.7 MB.
- Also in scope, because it is the same category of stale claim:
  `00_PROJECT_STATE/CURRENT_STATE.md` says `numpy` is undeclared (it is in
  `requirements.txt`), cites branch `badc8b7` (now `dc7d8e1`) and 146 tests
  (now 149).
