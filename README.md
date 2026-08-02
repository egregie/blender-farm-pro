# Blender Farm Pro

> A standalone fork of **PharmaGen PRO**, created to develop headless-Blender
> rendering as a photorealistic-packshot engine — without touching the source
> project. Forked from `pharma_v2` branch `feature/blender-renderer-experiment`
> at commit `79553d9`.

**Start here:** [`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md)
for what's done and what's next. The original PharmaGen PRO README (business
context, pipeline stage docs, bilingual EN/RU) is preserved unchanged at
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

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
├── input/                ← original 389 source product photos
├── ops/                  ← deployment & operations docs
├── memory/               ← session/agent memory for this fork
├── src/, pharma_pkg/, schemas/, tests/, scripts/, assets/  ← code (forked, functional)
├── docs/                 ← architecture, design rationale, the Blender roadmap
├── config.yaml, requirements.txt, main.py, pass_tomd.py, ...  ← forked, paths remapped
```

Each documented subject has exactly one home. `00_governance/` holds the ADRs,
audits and release-engineering records; `ops/` holds the deployment and
operations runbooks; `docs/` holds architecture, design rationale and the
Blender roadmap. Copies of the first two also lived under `docs/` when the fork
was created, 24 files of them byte-identical, and were removed once the fork
started editing the governance copies — a reader following a link should not
have to guess which of two identical files is the live one.

## ⚠️ Important: this fork is not a 1:1 copy — paths were remapped

`config.yaml` was edited so the forked pipeline actually runs against the new
numbered folders (SSOT → `03_knowledge_graph/`, passports → `04_passports/`,
renders → `01_input_raster/`, logs/state → `00_PROJECT_STATE/`). This was
**verified functional**, not just copied and hoped: Stage 1 was re-run from
this fork's own directory and its regenerated Markdown passports are **byte-
identical** to the source project's.

**A compatibility mirror used to be required, and no longer is.**
`verification_agent.py` hardcoded `Path("SSOT/SKU.csv")` and
`Path("SSOT/master.json")` outside the config system, so a duplicate `SSOT/`
directory had to exist alongside the real data in `03_knowledge_graph/` purely
to satisfy those two lookups. Without it CHECK 8 and CHECK 12 fell through their
"no entry, not a failure" branches and every passport quietly lost confidence,
with nothing in the log to say why. Both paths now resolve through
`src/utils.get_path`, the 1.3 MB mirror is gone, and the module no longer
depends on the working directory it happens to be invoked from. Stage 1's output
is byte-identical across the change and the confidence distribution is unchanged
at 380 × 1.0 and 11 × 0.85.

`render.engine` defaults to **`blender`** here (the source project defaults to
`gemini`) — this fork's whole purpose is the Blender engine.

## Assumptions made without the referenced screenshots

The requesting instructions referenced two screenshots (a numbered-folder
structure, and "other useful folders") that were not available when this fork
was created. Folder purposes were inferred from context and are documented,
with reasoning, in
[`00_PROJECT_STATE/CURRENT_STATE.md`](00_PROJECT_STATE/CURRENT_STATE.md) — redirect
anything that doesn't match what was actually intended.
