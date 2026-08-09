# Next Steps

> Queue for whoever (or whichever Claude session) picks this up next. Move
> items to [CHANGE_LOG.md](CHANGE_LOG.md) as they're completed, and update
> [CURRENT_STATE.md](CURRENT_STATE.md).

**Ordering rule:** item 1 is the one that finds unknown failures; run it before
tuning anything it might move. Housekeeping is independent throughout.

## Next

1. **Run the catalogue and look at the results.** No full pass has ever been made.
   Budget ~5 h; measured 24-48 s per SKU on 2026-08-02. This is the step that finds
   the layout failures the nine curated templates cannot show — every correction pass
   in the driver exists because an earlier sweep found real breakage. The reshape
   changed the proportions of all 391 cartons, so the label grid is now fitted to
   faces it was not measured on.

2. **Settle which model quantity the art-direction target is matched against.**
   Full silhouette, visible faces and front face differ by 13-18% and no measurement
   of our own renders can choose between them — the top face has no edge a threshold
   can find. `01_input_raster/reference_analysis.md` §10, §11 and §11a hold the
   evidence. Not blocking: the vertical family is 36-77% out under all three, so its
   direction is settled either way.

3. **Give the light rig a metering model that covers more than two shapes.** Exposure
   has landscape and portrait buckets; a carton as flat as T3 needs its own and lands
   about a level under the reference floor without it. Ratcheted in
   `TestRenderedLuminance.KNOWN_UNDER_BAND` so it cannot slip further.

4. **Close the remaining lid clipping.** 9.2% of the flat T3's lid still saturates,
   and the portrait lids sit at 0.79-0.82 of their front face against a reference band
   of 0.969-1.042. One rig cannot satisfy both shapes; a per-shape key elevation would,
   at the cost of the "one studio" invariant.

5. **Make `film_exposure()` read the picture, not the box.** It picks its shape from
   `width_mm >= height_mm`, which since contract 1.3 is art-directed geometry:
   `T_VERT_VIAL` reshapes to 172x170 and meters as landscape although it photographs
   portrait. The driver cannot import `src.silhouette` to ask.

## Throughput, when it starts to hurt

6. **Keep one Blender process alive for a batch.** About 20 s of each render is
   fixed startup, roughly 2 h wasted across a full pass. Worth doing before the
   catalogue is rendered repeatedly, not before it is rendered once.

7. **Let Stage 3 consume Blender output.** `image_processor.source_dir` still points
   at the Gemini directory, so producing final WEBP from Blender renders needs a
   manual `--config`. Make the source follow the engine.

## Housekeeping

8. **Give `08_ops/` a Blender chapter.** Its paths were remapped onto this fork's
   layout on 2026-08-02, so the runbooks no longer send an operator to
   directories that do not exist — but they still describe a Gemini-only
   pipeline. `ACCEPTANCE_TEST.md` calls `src.rpa_orchestrator` directly, bypassing
   the facade and contradicting the architecture. (`DEPENDENCY_INVENTORY.md` now
   has rows for the Blender executable and Tesseract OCR — that part is done.)

9. **Rewrite `06_docs/experiments/BLENDER_RENDERER_ROADMAP.md`.** It still claims
   "Phase 0 complete, Phase 1 foundation in place" and describes Phases 2–4 as not
   started, when most of Phase 2 has shipped.

10. **Write ADR-007 for the Blender engine.** `00_governance/DECISIONS/` stops at
   ADR-006 and has nothing on why this fork exists.

11. **Put a floor under the small print.** Delivered by the sweep on 2026-08-02
   and now the clearest open defect in the renderer. The driver fits a long
   label row by shrinking it, with no lower bound, so a long ingredient on a
   narrow face sets below legibility rather than overflowing: 9 of the
   catalogue's 15 longest strings fall under the 4.0mm the references imply,
   worst at 2.42mm on `393-min`. Reproduce with
   `python scripts/catalogue_sweep.py --legibility-scan`. Fixing it means
   deciding what gives when the string will not fit at a legible size —
   wrapping to a second line, abbreviating, or accepting a smaller floor — which
   is an art-direction call, not just a constant.

## Deliberately not doing

- **`T2`** — zero SKU in this catalogue.
- **A fake DataMatrix.** The passports declare a `DataMatrix_Zone` and the module
  width is below scanner tolerance on panels shorter than ~90 mm. A real symbol is
  worth adding later; a decorative one is not.
- **Hand-authored `.blend` templates.** The loader still honours them if they appear
  in `05_assets/blender/scenes/`, but procedural generation is the chosen path and that
  directory is empty on purpose.
