# Change Log

> Running history of what was done in this fork, most recent first. Not a
> replacement for git history (this project is git-initialized) — a
> human-readable narrative alongside it.

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
