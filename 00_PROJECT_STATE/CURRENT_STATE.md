# Blender Farm Pro — Current State

> Update this file after every major step. See [NEXT_STEPS.md](NEXT_STEPS.md)
> for what's queued and [CHANGE_LOG.md](CHANGE_LOG.md) for the running history.

**Last updated:** 2026-07-12 · **Status:** Fork created, structure populated,
first task (reference analysis) complete.

## What this project is

A standalone fork of PharmaGen PRO (`C:\lil_projects\pharma_v2`, branch
`feature/blender-renderer-experiment`, commit `79553d9`), created to develop
Blender-based rendering further, isolated from the source project. The source
project's own `feature/blender-renderer-experiment` branch remains the
authoritative record of the *original* Blender-engine work (facade design,
`src/blender_renderer.py`, `assets/blender/render_driver.py`) — this fork
carries a copy of that work forward for further, independent iteration.

## Assumptions made (no screenshots were available)

The fork request referenced two screenshots — a numbered-folder structure and
"other useful folders from the second screenshot" — that were **not attached
and not visible to Claude**. Rather than block on them, defensible
interpretations were made and are recorded here explicitly so they can be
corrected:

| Folder | Assumption made | Confidence |
|---|---|---|
| `01_input_raster/` | Raster reference material for Blender scene design: `reference/` (curated subset + analysis), `gemini_renders_final/` (full 389 WEBP), `gemini_renders_raw/` (full 391 PNG) | Medium — the user's own instructions explicitly suggested this location for the images |
| `02_processing/` | Legacy CV/OCR code (`cv/`), Blender's own render attempts (`blender_test_renders/`), Stage-2 failure artifacts | Low-medium — reasonable but not confirmed |
| `03_knowledge_graph/` | SSOT (SKU.csv, master.json, design specs) — the structured "knowledge" backing routing decisions | Medium — not literally a graph DB, labeled per the requested name |
| `04_passports/` | JSON + Markdown passports | High — directly named in the request |
| `05_output_svg/` | **Left empty.** Nothing in this pipeline produces SVG. See its own README. | N/A — honest placeholder, not fabricated |
| `06_archive/` | **Left empty at creation.** PharmaGen's own 2600-file `trash/` was deliberately NOT copied (would contradict "clean fork"); this folder is for the fork's *own* future archive | Medium — a judgment call, reasoning documented |
| `07_output_3mf/` | **Left empty.** 3MF is a 3D-print mesh format; nothing here produces one. See its own README. | N/A — honest placeholder, not fabricated |
| `input/` | Flat copy of the original 389 source photos (distinct from the curated `01_input_raster/`) | High — literally listed in the request |
| `ops/` | DEPLOYMENT.md, OPERATIONS.md, docs/ops/* | High |
| `memory/`, `00_PROJECT_STATE/active_tasks/` | Left empty as requested | High |

**If any of these don't match what you intended (especially `05_output_svg`,
`06_archive`, `07_output_3mf`, or `02_processing`), say so and they'll be
corrected** — nothing here is load-bearing on code, only on documentation and
folder placement, so redirecting is cheap.

## What was done

1. **Directory structure created** — full tree per the request, including all
   folders explicitly asked for as empty scaffolding.
2. **Data copied** — SSOT (6 files), 391 JSON passports, 391 Markdown
   passports, 391 raw PNG, 389 final WEBP, 389 source photos, all source code
   (`src/`, `pharma_pkg/`, `schemas/`, `verification_agent.py`, shims, `main.py`,
   `config.yaml`, `requirements.txt`), all documentation, tests, scripts, and
   the Blender renderer experiment (`src/blender_renderer.py`,
   `src/render_stage.py`, `assets/blender/render_driver.py`).
3. **`config.yaml` remapped** to the new folder structure (source project's
   default paths would not have resolved here) — see README.md's "Important"
   section for the full explanation.
4. **A real compatibility bug was found and fixed**: `verification_agent.py`'s
   hardcoded `SSOT/` path (not config-driven) silently broke SKU-registry
   lookups after the SSOT move — caught by diffing regenerated Stage-1 output
   against the source project (not assumed to work). Fixed with a physical
   `SSOT/` mirror. Details in [CHANGE_LOG.md](CHANGE_LOG.md).
5. **Functional validation performed** (not just file-copy verification):
   - `main.py --help` runs from the fork's own directory.
   - Stage 1 (`--passports-only`) re-run from the fork: **391/391 converted,
     byte-identical** to the source project's Markdown output after the SSOT
     fix.
   - `python -m unittest discover` — 18/18 tests pass from the fork.
6. **Reference image analysis completed** (first requested task) —
   [`01_input_raster/reference_analysis.md`](../01_input_raster/reference_analysis.md),
   grounded in direct visual inspection of 7 of 9 curated reference images
   across the template family (T1, T1_LARGE, T3, T_BOTTLE_BOX, T_MULTIPACK,
   T_VERT_VIAL, T_VERT_DROPPER). Key findings: consistent 3/4-isometric
   composition, near-shadowless high-key lighting, matte (not glossy)
   material, a strict white-body + two-accent-color rule, a consistent label
   grid, and — genuinely useful — a confirmed example of AI-text-hallucination
   ("Datels" instead of "Details" on one label) that argues Blender's
   guaranteed-correct text rendering is a real advantage, not just a
   nice-to-have.
7. **A data naming quirk was discovered and documented** (pre-existing in the
   source project, not introduced here): `output/*.webp` uses bare numeric
   filenames (`1.webp`) while `render_output/raw/*.png` and the passports use
   `-min`-suffixed stems (`1-min.png`). Worked around during reference
   selection; noted so future Blender output in this fork uses the `-min`
   convention consistently (already the case — `blender_renderer.py`'s job
   stems come from the JSON filename).

## Known limitations of this fork right now

- No local Python virtual environment was set up here (intentionally — `venv/`
  is never copied between projects). Validation above used PharmaGen PRO's own
  venv pointed at this directory. First real step for anyone continuing here:
  `python -m venv venv && venv\Scripts\python -m pip install -r requirements.txt`.
- `ops/` documents (Acceptance Test, Dependency Inventory) still describe the
  *original* PharmaGen PRO paths/defaults, not this fork's remapped structure
  or its `blender`-default engine — not yet updated.
- Only 7 of the 10 template IDs have a viewed reference image analyzed (T2 has
  zero SKUs in this catalogue and was correctly skipped; T1_SMALL and
  T_VERT_INHALER were copied but not yet visually reviewed).
