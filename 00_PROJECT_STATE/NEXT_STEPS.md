# Next Steps

> Queue for whoever (or whichever Claude session) picks this up next. Move
> items to [CHANGE_LOG.md](CHANGE_LOG.md) as they're completed, and update
> [CURRENT_STATE.md](CURRENT_STATE.md).

**Ordering rule:** item 1 blocks items 2 and 3. Everything under Housekeeping is
independent and can be done at any time, including in parallel.

## Blocking decision

1. **Settle whether the passport dimensions or the reference renders define carton
   proportions.** Measured on 2026-08-02, the vertical family and T3 render markedly
   narrower and flatter than their references — `T_VERT_VIAL` fills 38% of frame
   width against the reference's 67%. The cause is understood and is not a geometry
   bug: the Gemini prompt carries no dimensions on the common path, so every
   reference proportion is invented, while our renders use the catalogue's real
   `secondary_packaging.dimensions`. See `CURRENT_STATE.md` §"The one open question".

   Do not tune framing, dimensions or the reference band until this is answered —
   "match the reference" and "trust the data" are opposite fixes for the same
   measurement.

## Once that is settled

2. **Run the catalogue and look at the results.** No full pass has ever been made;
   18 of 391 PNG exist and only nine come from current code. Budget ~7 h at 67 s per
   SKU. This is the step that finds the layout failures the nine curated templates
   cannot show — the existing correction passes in the driver all exist because
   earlier sweeps found real breakage.

3. **Add post-render verification.** There is none today, for either engine. Take
   the rendered PNG plus its manifest and check that the label strings are actually
   present (OCR), that the dominant colours match `palette`, and that the image is
   not blank. The unused `ObservedZone` / `ObservedPalette` / `UVBox` models in
   `schemas/` were scaffolded for exactly this. Treat mismatches as a confidence
   score with warnings, mirroring `agent_2_verifier`, rather than a hard failure —
   OCR misreads small stylised type, which is the same failure class that produced
   the reference set's "Datels".

## Throughput, when it starts to hurt

4. **Keep one Blender process alive for a batch.** About 20 s of each 67 s render is
   fixed startup, roughly 2 h wasted across a full pass. Worth doing before the
   catalogue is rendered repeatedly, not before it is rendered once.

5. **Let Stage 3 consume Blender output.** `image_processor.source_dir` still points
   at the Gemini directory, so producing final WEBP from Blender renders needs a
   manual `--config`. Make the source follow the engine.

## Housekeeping

6. **Declare `numpy`.** `tests/test_blender_carton.py` imports it; `requirements.txt`
   does not list it. A clean install passes and then fails that test.

7. **Refresh `ops/`.** Six of seven documents never mention Blender.
   `ACCEPTANCE_TEST.md` calls `src.rpa_orchestrator` directly, bypassing the facade
   and contradicting the architecture; `DEPENDENCY_INVENTORY.md` has no row for the
   Blender executable despite it being this fork's default engine.

8. **Rewrite `docs/experiments/BLENDER_RENDERER_ROADMAP.md`.** It still claims
   "Phase 0 complete, Phase 1 foundation in place" and describes Phases 2–4 as not
   started, when most of Phase 2 has shipped.

9. **Write ADR-007 for the Blender engine.** `00_governance/DECISIONS/` stops at
   ADR-006 and has nothing on why this fork exists.

10. **Commit a repeatable catalogue sweep.** The sweeps that caught the wrapping and
    collision bugs were ad-hoc; nothing in `scripts/` reproduces them, so the next
    person cannot re-run the check that the layout constants were fitted against.

## Deliberately not doing

- **`T2`** — zero SKU in this catalogue.
- **A fake DataMatrix.** The passports declare a `DataMatrix_Zone` and the module
  width is below scanner tolerance on panels shorter than ~90 mm. A real symbol is
  worth adding later; a decorative one is not.
- **Hand-authored `.blend` templates.** The loader still honours them if they appear
  in `assets/blender/scenes/`, but procedural generation is the chosen path and that
  directory is empty on purpose.
