# Blender Farm Pro

> A standalone fork of **PharmaGen PRO**, created to develop headless-Blender
> rendering as a photorealistic-packshot engine — without touching the source
> project. Forked from `pharma_v2` branch `feature/blender-renderer-experiment`
> at commit `79553d9`.

**Start here:** [`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md)
for what's done and what's next. The original PharmaGen PRO README (business
context, pipeline stage docs, bilingual EN/RU) is preserved unchanged at
[`docs/README.md`](docs/README.md).

## What was forked, and why

Everything needed to keep the underlying pipeline (SSOT → passport → render →
final image) running and understandable: `main.py`, `src/` (including the
Blender render engine already built on the source branch), `pharma_pkg/`,
`schemas/`, `verification_agent.py`, the shims, `config.yaml`,
`requirements.txt`, the full documentation set, and the full image/data
catalogue (391 SKU: JSON + Markdown passports, raw PNG, final WEBP).

## Structure

```
Blender Farm Pro/
├── 00_PROJECT_STATE/     ← progress tracking (read this first)
├── 00_governance/        ← ADRs, audits, release-engineering docs (forked)
├── 01_input_raster/      ← reference images for Blender scene design (see reference_analysis.md)
├── 02_processing/        ← legacy CV/OCR code, Blender's own test-render output, Stage-2 failure logs
├── 03_knowledge_graph/   ← SSOT (SKU.csv, master.json, design specs)
├── 04_passports/         ← JSON + Markdown passports (391 SKU)
├── 05_output_svg/        ← reserved, currently unused (see its README)
├── 06_archive/           ← this fork's own archive (empty at creation — see its README)
├── 07_output_3mf/        ← reserved, currently unused (see its README)
├── input/                ← original 389 source product photos
├── ops/                  ← deployment & operations docs (forked)
├── memory/               ← session/agent memory for this fork
├── src/, pharma_pkg/, schemas/, tests/, scripts/, assets/  ← code (forked, functional)
├── docs/                 ← full copy of PharmaGen PRO's docs/ (safety net — nothing lost)
├── SSOT/                 ← COMPATIBILITY MIRROR of 03_knowledge_graph/ (see note below)
├── config.yaml, requirements.txt, main.py, pass_tomd.py, ...  ← forked, paths remapped
```

## ⚠️ Important: this fork is not a 1:1 copy — paths were remapped

`config.yaml` was edited so the forked pipeline actually runs against the new
numbered folders (SSOT → `03_knowledge_graph/`, passports → `04_passports/`,
renders → `01_input_raster/`, logs/state → `00_PROJECT_STATE/`). This was
**verified functional**, not just copied and hoped: Stage 1 was re-run from
this fork's own directory and its regenerated Markdown passports are **byte-
identical** to the source project's.

**One compatibility fix required:** `verification_agent.py` hardcodes
`Path("SSOT/SKU.csv")` / `Path("SSOT/master.json")` — it does **not** read
`config.yaml`. A physical `SSOT/` folder (mirroring `03_knowledge_graph/`) was
added purely so that hardcoded path resolves. Without it, every passport's
verification confidence silently dropped from 1.0 to 0.9 (CHECK 12 failing to
find the SKU registry) — caught by diffing the regenerated output against the
source project, not assumed. Full details:
[`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md).

`render.engine` defaults to **`blender`** here (the source project defaults to
`gemini`) — this fork's whole purpose is the Blender engine.

## Assumptions made without the referenced screenshots

The requesting instructions referenced two screenshots (a numbered-folder
structure, and "other useful folders") that were not available when this fork
was created. Folder purposes were inferred from context and are documented,
with reasoning, in
[`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md) — redirect
anything that doesn't match what was actually intended.
