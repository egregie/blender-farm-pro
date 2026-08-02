# Change Log

> Running history of what was done in this fork, most recent first. Not a
> replacement for git history (this project is git-initialized) — a
> human-readable narrative alongside it.

## 2026-08-02 (later) — A sweep, a cleanup, and a review that caught both

- **Swept a 30-SKU priority group** with a new `scripts/catalogue_sweep.py`. The
  group came back clean, but the sweep's second pass — reading the built scene
  through the driver's `--dump-scene` rather than the pixels — found the real
  defect: **the driver fits a long label row by shrinking it, and nothing puts a
  floor under the type size.** Overflow is impossible; illegibility is not.
  Measured on `357-min`, the row's width stays pinned at 101.2mm while a
  37-character ingredient sets at 4.64mm, 70 characters at 1.73mm and 140 at
  0.77mm. Across the catalogue's 15 longest strings, **9 fall below the 4.0mm
  floor the references imply, worst at 2.42mm** — and the risk tracks characters
  per face width, not raw length, so `393-min` (35 characters on a 50mm
  `T_VERT_INHALER` face) is worse than `348-min` (61 characters on 110mm).
- **Gave every file one home.** `verification_agent.py` was made config-driven,
  which removed the last reason for the 1.3 MB `SSOT/` mirror of
  `03_knowledge_graph/`; 24 duplicated documentation files were deleted from
  `docs/` in favour of `00_governance/` and `ops/`; root `DEPLOYMENT.md` and
  `OPERATIONS.md` went as byte-identical copies of the `ops/` pair. Every
  markdown link in the repository now resolves — including seven that had been
  broken since before the cleanup.
- **Remapped the operations runbooks** onto this fork's actual layout. They had
  never been updated after the fork and still told an operator to restore
  `SSOT/`, `pipeline/` and `render_output/` — a disaster-recovery procedure
  pointing at three directories that do not exist.
- **Deleted three dead maintenance scripts** (`sync_p23_palette.py`,
  `sync_passports_refined.py`, `update_dosages.py`). All read `pipeline/passports`,
  which this fork has never had; one read a CSV that has never existed here at all.
- **Code review caught two things worth recording.** First, the committed sweep
  report was a three-SKU trial that a `--limit` smoke check had silently written
  over the real 30-SKU run — the run now writes partial results to their own
  filenames so a trial cannot masquerade as a full pass. Second,
  `generate_architecture_snapshot.py` was a genuine casualty of the `SSOT/`
  deletion: root-anchored, so it had worked before and afterwards reported the
  SKU registry as simply absent. Both fixed, and `tests/test_verifier.py` gained
  three guards so a future path remap fails loudly instead of silently.

## 2026-08-02 — Audit, and the packshot becomes recognisable

- **Full project audit.** Re-rendered all nine reference SKU from current code and
  measured them against `01_input_raster/reference/`; inventoried code, tests,
  dependencies and documentation. Findings folded into `CURRENT_STATE.md` and
  `NEXT_STEPS.md`, both of which had gone three weeks stale.
- **Found the project's main open question.** The vertical family and T3 render
  markedly narrower and flatter than their references (`T_VERT_VIAL` 38% of frame
  width against 67%). Traced to a real asymmetry rather than a bug: the Gemini prompt
  carries no dimensions on the common path, so every reference proportion is
  invented, while Blender uses the catalogue's real dimension strings. Which of the
  two is authoritative is a human decision and now blocks further tuning.
- **Audit findings recorded**: no post-render verification exists for either engine;
  the full catalogue has never been rendered (18 PNG of 391); Stage 3 still cannot
  consume Blender output without a manual `--config`; one Blender process per SKU
  costs ~2 h of pure startup across a pass; `ops/` never mentions Blender; the
  Blender roadmap still claims "Phase 0 complete"; `numpy` is imported by the tests
  but undeclared in `requirements.txt`.
- **Process finding.** Parallel background sessions produced two independent
  implementations of the same packshot features, reconciled by hand in `badc8b7`.
  Scope parallel agents to disjoint files or run them in sequence.

## 2026-07-31 → 2026-08-02 — From a coloured box to a packshot

Delivered across several sessions; see git history from `3f4cf31` to `badc8b7`.

- **The render manifest became the Stage 1 → Stage 2 contract.**
  `schemas/render_manifest.schema.json` is now the one authoritative description of
  what a renderer receives, with `src/render_manifest.py` as its only implementation.
  Plain JSON Schema, because the driver runs inside Blender's own interpreter where
  pydantic and project modules are unavailable. Version reached **1.2**; both bumps
  added *required* fields deliberately, so a stale manifest fails loudly instead of
  quietly rendering something incomplete.
- **Fixed carton dimensions reaching Blender at all.** `primary_package` is `null` in
  every stored passport, so the driver had been falling back to a guessed aspect
  ratio for the entire catalogue. Not one SKU was within 10% of its guess; 104 were
  off by more than 50%. Also corrected the semantic error underneath it — the driver
  had been reading the *primary* package to build the *carton*, which is a different,
  smaller object on permuted axes.
- **Established that orientation comes from the template, not the dimension string.**
  The same `115x55x48mm` is landscape for T1 and portrait for T_VERT_INHALER.
- **Rebuilt camera framing.** The old fixed distance only worked while every box was
  the same nominal size; with real dimensions it cropped tall cartons outright.
  Distance now solves from the bounding sphere and the lens, and the camera is aimed
  by explicit rotation rather than a `TRACK_TO` constraint whose deferred evaluation
  left the carton riding high in frame.
- **Printed the front panel** — brand, ingredient, dosage and unit count as real text
  objects on a grid measured off the references, with fonts vendored into
  `assets/blender/fonts/` so a render cannot change on a machine missing a font.
- **Printed the side panel** — a genuine Code 128 of `sku_id` that a test decodes back
  out of the built geometry, deliberately empty LOT/EXP fields, and a data block of
  manifest strings only.
- **Matched the packshot to the references** — white body, corner badge, bottom
  accent stripe, matte throughout, emissive backdrop, one light rig for all 391 SKU
  with power scaling as the square of size, exposure metered per carton shape.
- **Made an unavailable render engine fatal** rather than silently substituted, and
  calibrated samples from 64 to 16 on measured PSNR.
- **Fixed `UnicodeEncodeError` killing successful runs** on legacy Windows codepages.
- Tests grew from 18 to **146**.
- Published to `github.com/egregie/blender-farm-pro` (private).

## 2026-07-12 — Fork created

- Created `Blender Farm Pro` as a standalone sibling folder of `pharma_v2`
  (not a git branch — an actual filesystem fork), from
  `feature/blender-renderer-experiment` @ `79553d9`.
- Built the requested numbered folder structure; documented every
  interpretive assumption (no reference screenshots were available) in
  `CURRENT_STATE.md`.
- Copied: SSOT (6 files), 391 JSON passports, 391 Markdown passports, 391 raw
  PNG, 389 final WEBP, 389 source photos, full `src/`/`pharma_pkg/`/`schemas/`,
  `verification_agent.py`, shims, `config.yaml`, `requirements.txt`, all docs,
  tests, scripts, and the Blender renderer experiment.
  Deliberately **not** copied: `venv/`, `.env` (secrets — see PharmaGen's own
  Bus Factor audit finding that these keys are unused by the pipeline anyway),
  PharmaGen's `trash/` (2600 legacy files — see `06_archive/README.md`).
- Remapped `config.yaml` paths onto the new structure and set
  `render.engine: blender` as this fork's default.
- **Found and fixed a real bug**: `verification_agent.py` hardcodes
  `Path("SSOT/SKU.csv")` outside the centralized config system. After moving
  SSOT to `03_knowledge_graph/`, every passport's CHECK 12 silently started
  failing (confidence 1.0 → 0.9 on all 391 SKU). Caught by diffing regenerated
  Stage 1 output against the source project's committed Markdown — not
  assumed to work. Fixed with a physical `SSOT/` compatibility mirror.
- **Discovered a pre-existing data quirk** (not introduced by this fork):
  `output/*.webp` uses bare numeric stems while `render_output/raw/*.png` uses
  `-min`-suffixed stems. Documented; worked around for reference selection.
- Validated: `main.py --help`, Stage 1 byte-identical regeneration (391/391,
  0-line diff after the SSOT fix), 18/18 unit tests — all from the fork's own
  directory.
- Completed the first requested task: copied 9 representative reference
  images (one per template ID that has SKU data — T2 has none in this
  catalogue), directly viewed 7 of them, wrote
  `01_input_raster/reference_analysis.md` with grounded, specific findings
  (composition, camera/lens, lighting, material, color system, typography,
  and a genuine AI-text-hallucination finding with a real Blender-advantage
  implication).
- `git init` — this fork now has its own independent git history, starting
  clean.
