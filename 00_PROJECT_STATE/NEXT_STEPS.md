# Next Steps

> Queue for whoever (or whichever Claude session) picks this up next. Move
> items to [CHANGE_LOG.md](CHANGE_LOG.md) as they're completed, and update
> [CURRENT_STATE.md](CURRENT_STATE.md).

## Immediate

1. **Confirm the folder-structure assumptions** in `CURRENT_STATE.md`
   §"Assumptions made" against the actual reference screenshots — redirect
   `05_output_svg/`, `06_archive/`, `07_output_3mf/`, `02_processing/` if they
   were meant to hold something different.
2. **Set up a local venv** — none exists yet in this fork (see
   `CURRENT_STATE.md` §Known limitations).
3. **Finish visually reviewing the remaining reference images**
   (`T1_SMALL_103.webp`, `T_VERT_INHALER_268.webp`) and extend
   `01_input_raster/reference_analysis.md` §9 accordingly.

## Blender scene work (the actual point of this fork)

4. Use `01_input_raster/reference_analysis.md` §8's concrete tuning
   recommendations (shadow, roughness, no DOF) to improve
   `assets/blender/render_driver.py`'s lighting/material setup.
5. Resolve the open question in `reference_analysis.md` §9 (filled vs. outline
   badge style) — check `branding.design_elements` fields across a larger SKU
   sample.
6. Cover the remaining template geometries in the Blender driver (currently:
   generic box with per-template aspect ratio only; see the source project's
   `docs/experiments/BLENDER_RENDERER_ROADMAP.md` Phase 2 for the full list —
   also present at `00_governance/` / `docs/experiments/` in this fork).
7. Implement label text rendering (brand name/dosage/unit count as real 3D
   text) — see reference_analysis.md §6 for the exact grid to match.

## Housekeeping

8. Update `ops/ACCEPTANCE_TEST.md` and `ops/DEPENDENCY_INVENTORY.md` for this
   fork's remapped paths and `blender`-default engine (see `ops/README.md`).
9. Consider whether the pixel/measurement-level open questions in
   `reference_analysis.md` §9 (accent-stripe height ratio) are worth a
   precise pass before building geometry against them.
