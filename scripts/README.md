# scripts/ — Auxiliary & Maintenance Tools

Operator tools that are **not** part of the three-stage production pipeline
(`main.py`). Run them from the **repository root** so relative paths resolve.

| Script | Purpose |
|---|---|
| `catalogue_sweep.py` | Renders a named group of SKU and measures each result — silhouette, framing, front-face brightness, and a scene-level check of every label row against the face edges. `--legibility-scan N` instead measures printed type size for the N longest label strings in the catalogue. Diagnostic only; changes nothing about how anything renders. |
| `render_qa.py` | OCR-based QA diagnostic over rendered images (requires Tesseract + `pytesseract`). |
| `image_postprocessor.py` | Alternative post-processor (2048px WEBP). Non-canonical — the canonical final stage is `src/image_processor.py`. |
| `generate_architecture_snapshot.py` | Generates an architecture snapshot from the live code. |
| `download_last_image.py` | Manual debug helper to pull the last generated image from the Gemini UI. |

Examples:

```bash
python scripts/catalogue_sweep.py                    # the group, resuming
python scripts/catalogue_sweep.py --limit 5          # trial, writes sweep_report.partial.*
python scripts/catalogue_sweep.py --legibility-scan  # type size across the catalogue
python scripts/render_qa.py
python scripts/generate_architecture_snapshot.py
```

Three maintenance scripts — `sync_p23_palette.py`, `sync_passports_refined.py`
and `update_dosages.py` — were removed. They were one-off data migrations
carried over from the source project and had stopped working long before: all
three read `pipeline/passports`, which this fork does not have, and
`update_dosages.py` also read `SSOT/percent_skus.csv`, a file that has never
existed in this repository. Their history is in git if a future migration wants
them as a starting point.
