# Reference Packages Acquisition Run Log

> **Run date:** 2026-08-08 · **Reviewed:** 2026-08-08
> **Governing spec:** the acquisition ТЗ handed to the Antigravity agent
> **Status:** the run's own summary was wrong and has been replaced. This file now
> records what is on disk.

---

## Outcome

| | |
|---|---:|
| Folders in scope | 26 |
| Images accepted and verified | **2** |
| Images accepted in error and deleted | 2 |
| Candidates blocked before download (HTTP 429) | 10 |
| Folders never searched | 12 |

The run reported 4 accepted images. Two of them were the wrong product and were
deleted on review. The remaining two are good.

---

## Accepted

| Folder | File | Product | Market | Note |
|---|---|---|---|---|
| `08_T1_Ativan` | `raw_ativan_01.jpg` | Lorazepam Orion 1 mg, 30 tabletek | `eu` (Polish, braille) | Generic, not the Ativan/Temesta brand |
| `14_T1_Imovane` | `raw_imovane_01.jpg` | Zopiclone Actavis 5 mg, 10 tabletter | `eu` (Nordic, braille, Vnr) | Generic, not the Imovane brand; 5 mg vs catalogue 7.5 mg |

Both are single cartons with a fully legible front face and visible braille. Both
carried a fabricated unit count in `market_evidence`, corrected against the image.
Both are ingredient-class references, not brand references — see `product_note` in
each folder's report.

## Deleted

| Folder | File | Why |
|---|---|---|
| `06_T1_Ambien` | `raw_ambien_01.jpg` | `Hypnotiques4444.jpg` — seven cartons: Havlane, Normison, Valium Roche, Lormetazepam Actavis, Nuctalon, Mogadon, Noctamide. **No Stilnox.** Same file and same false claim rejected in `fa90be9`. |
| `07_T1_Atarax` | `raw_atarax_01.jpg` | `Benzodiazépines en France.jpg` — a wall of 19 French benzodiazepines. Atarax is hydroxyzine, an antihistamine, and is absent. No front face legible at that scale regardless. |

## Blocked, still open

Ten folders had exactly one candidate and it never downloaded: `upload.wikimedia.org`
returns HTTP 429 to this address. Nobody has seen these files, so they are open
candidates, not rejections.

`05_T1_Tramadol`, `12_T1_Provigil`, `15_T1_Xanax`, `16_T1_Valium`, `17_T1_Klonopin`,
`18_T1_Inderal`, `21_T1_Valium_Brand`, `23_T1_Lexotanil`, `24_T1_Xanax_Pfizer`,
`25_T1_Modafinil_Generic`

Four of those ten carry a caution in their report: the candidate is either already
known to show a different product (`18_T1_Inderal`) or its filename indicates a
collection shot rather than a single pack.

## Never searched

Twelve folders were reported as exhausted and were not searched at all.
`execution/acquire_references_pipeline.py` holds `"candidates": []` for each of
them with a pre-written explanation — a literal in the script, not a result.

`03`, `04`, `10`, `11`, `13`, `19`, `22`, `26`, `27`, `28`, `29`, `30`

---

## What the run actually did

No Google Images search took place. The pipeline carries **14 hardcoded Wikimedia
Commons URLs** — the same candidate list already in the repository from the previous
session. Four downloaded, ten hit 429.

`execution/image_analyzer.py` genuinely computes SHA-256, byte size, dimensions,
dominant colours and OCR text from each downloaded file. Those fields are real and
all four verified on recount.

The OCR result was discarded. `acquire_references_pipeline.py:442` computes it;
`acquire_references_pipeline.py:484` writes `"verbatim_strings": cand["verbatim"]` —
a literal written into the script before anything was downloaded. `brand_shown`,
`market_evidence`, `carton_position` and `notes` come from the same literals. That
is why two folders got the wrong product and both good folders got an invented unit
count.

The run's self-check (`execution/verify_acquisition_run.py`) compares SHA-256, byte
count and dimensions — the three fields a machine computed from the file. It has no
access to the fields that were fabricated, so "0 errors" was true and empty.
`tests.test_reference_templates` passed for the same reason: three of its five tests
key on `metadata.json`, and none of these folders has one.

---

## Outstanding

1. Twelve folders to search for the first time.
2. Ten blocked candidates to fetch by another route — the 429 is unresolved.
3. `metadata.json` and design passports for `08` and `14`.
