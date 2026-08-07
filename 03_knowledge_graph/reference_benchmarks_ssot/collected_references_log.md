# Reference Benchmarks Log

> **Target Path:** `03_knowledge_graph/reference_benchmarks_ssot/collected_references_log.md`
> **Baselines:** `02_T1_SMALL_Cialis`, `31_Kamagra_Template_Reference`, `32_Viagra_Template_Reference`
> **Updated:** 2026-08-07

The single record of what was acquired, what was rejected and why. A candidate
that is dropped without an entry here did not happen: silent discards are how a
reference set stops being reproducible.

---

## Baseline Reference Packages

### 1. Cialis 20mg Carton (`Reference Templates/02_T1_SMALL_Cialis/`)
- `raw_cialis_front.png` — 1079×810
- `raw_cialis_back.png` — 1080×810
- `raw_cialis_pills.png` — 1080×810

### 2. Viagra 100mg Carton (`Reference Templates/32_Viagra_Template_Reference/`)
- `raw_viagra_front.png` — 1080×810
- `raw_viagra_back.png` — 1080×810
- `raw_viagra_pills.png` — 1080×810

### 3. Kamagra 100mg Pack (`Reference Templates/31_Kamagra_Template_Reference/`)
- `raw_Kamagra_front_01.png` — 1536×1024
- **`single_source`** — one image only. Reconstruction of anything not visible in
  that single frame is a constraint, not an inference, and belongs in Section L
  of its passport.

---

## 2026-08-07 — Baseline audit

### Removed: duplicates

Four files were two pictures. Confirmed by hashing decoded pixels, not by
comparing filenames:

| Removed | Duplicate of | Pixel SHA-256 (16) |
|---|---|---|
| `31_Kamagra.../Kamagra-100mg.webp` | `raw_Kamagra_front_01.png` | `ee321860bfc67189` |
| `31_Kamagra.../Kamagra-100-MG.webp` | `raw_Kamagra_front_02.png` | `9e0eb51e51dda4fa` |
| `reference_benchmarks_ssot/raw_cialis_front.png` | `02_T1_SMALL_Cialis/raw_cialis_front.png` | `9097dee924879cfa` |
| `reference_benchmarks_ssot/raw_viagra_front.png` | `32_Viagra.../raw_viagra_front.png` | `2aa8817b36ec5bd3` |

### Removed: below the floor

`31_Kamagra_Template_Reference/raw_Kamagra_front_02.png` — 608×380. It failed the
quality gate it was itself supposed to define: the SAAT README demanded a minimum
of 800px on the long edge and this benchmark carried 608. The owner ruled it out
of the benchmark set rather than lowering the floor to admit it. A bounding box
measured off 608px is not reliable enough for Section B, which is the only reason
the floor exists.

### Corrected: manifests naming files that were not there

`metadata.json` in both `02_T1_SMALL_Cialis` and `32_Viagra_Template_Reference`
listed `raw_01_angle_left.png`, `raw_02_front.png`, `raw_03_angle_right.png`
under `reference_images`. Neither folder held any of them — the intersection with
disk was empty — while both reported `"status": "complete"`. Corrected to the
files actually present. `tests/test_reference_templates.py` now fails if a listed
file is absent or a present file goes unlisted.

---

## Quality floors, derived 2026-08-07

Measured across the seven surviving benchmark images, not chosen. A candidate
that is worse than the **worst benchmark** on any signal is rejected; lowering a
floor to fill a folder is forbidden.

| Signal | Floor | Set by |
|---|---|---|
| Long edge | **1079 px** | `raw_cialis_front.png` |
| Sharpness (variance of Laplacian) | **996** | `raw_viagra_front.png` |
| Subject area, share of frame | **56.5%** | `raw_Kamagra_front_01.png` |

Per-image measurements:

| File | Long edge | Sharpness | Subject % |
|---|---:|---:|---:|
| `raw_cialis_back.png` | 1080 | 4248 | 84.6 |
| `raw_cialis_front.png` | 1079 | 2599 | 84.3 |
| `raw_cialis_pills.png` | 1080 | 2434 | 59.3 |
| `raw_Kamagra_front_01.png` | 1536 | 1246 | 56.5 |
| `raw_viagra_back.png` | 1080 | 1401 | 72.8 |
| `raw_viagra_front.png` | 1080 | 996 | 81.2 |
| `raw_viagra_pills.png` | 1080 | 997 | 61.2 |

**Two cautions about the sharpness figure.** It is a Laplacian variance, so it
moves with resolution and with how much fine detail the packaging happens to
carry — it compares like with like only roughly. And it does not track "good
front reference": the sharpest image in the set is a *back* panel at 4248, while
the least sharp is `raw_viagra_front.png` at 996, which is a perfectly usable
front packshot. The floor is anchored to that front packshot deliberately, since
front-face legibility is the acquisition criterion.

The 1079 floor is one pixel below a round 1080 because `raw_cialis_front.png` is
1079 wide. It is left exact rather than rounded: rounding down to 1000 would
admit candidates worse than every benchmark, which is the opposite of what the
floor is for.
