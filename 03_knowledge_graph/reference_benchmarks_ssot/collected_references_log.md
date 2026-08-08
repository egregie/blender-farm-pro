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

---

## 2026-08-07 — Pilot: `01_T1_Strattera`

**Accepted: 7 of 7 (cap reached).** All from DailyMed (NIH), setid
`309de576-c318-404a-bc15-660c2b1876fb`, downloaded 2026-08-07.

| File | Dosage | Size | Front colour | Share of front panel |
|---|---:|---|---|---:|
| `raw_strattera_label_10mg.jpg` | 10 mg | 776×372 | `#CCB40C` | 24.1% |
| `raw_strattera_label_18mg.jpg` | 18 mg | 775×373 | `#E46C24` | 27.4% |
| `raw_strattera_label_25mg.jpg` | 25 mg | 767×370 | `#FCB40C` | 23.4% |
| `raw_strattera_label_40mg.jpg` | 40 mg | 769×367 | `#5484B4` | 27.4% |
| `raw_strattera_label_60mg.jpg` | 60 mg | 766×367 | `#545454` | 32.6% |
| `raw_strattera_label_80mg.jpg` | 80 mg | 767×366 | `#6C2424` | 28.4% |
| `raw_strattera_label_100mg.jpg` | 100 mg | 770×367 | `#0C2454` | 28.5% |

**Rejected sources.** `medicines.org.uk`, `ema.europa.eu`, `mhra.gov.uk` and
`lilly.com` were searched for this product and returned only SmPC and PIL text
documents — no packaging imagery. Not a quality rejection; the imagery is not
published there.

### What the pilot established, and why it ran before the other 28

**Regulatory databases publish flat label unfoldings, not packshots.** Every
panel in one plane, no perspective, no carton. Better for reading a design than
any photograph and useless for proportions or material. The owner accepted both
source types with separate handling.

**The benchmark floors do not transfer to this source type.** All seven images
are 766–776 px on the long edge against a floor of 1079 derived from packshots.
That is a property of DailyMed, not of this product — the floor cannot be met by
anything from that source. Cropped to the front panel the usable width is ~240 px:
enough for colour and archetype, not for small print.

**Subject-area and colour-share floors are meaningless on an unfolding.** Measured
over the whole scan, the dominant "colour" came out as `#281828` at 40% — a black
service block, not the design. Only the front panel is measurable, and only after
someone marks it.

**Front-panel identification is a human step.** Automatic detection by text
orientation was tried and failed: Tesseract reads rotated side-panel text as
horizontal nonsense, so the horizontal and rotated token spans overlap almost
entirely (0.055–0.785 against 0.160–0.957). Recorded as a limitation rather than
worked around by guessing.

**Dosage colour coding found.** Substrate, typography and layout are identical
across all seven strengths; only the colour field changes, and it encodes the
strength. Per the owner's ruling the front colour is now chosen by the SKU's
dosage rather than per product. Both catalogue SKUs served by this template
(`1-min`, `2-min`) are 40 mg → `#5484B4`.

The 60 mg entry is achromatic grey. A first pass looking for saturated colour
reported no accent for it — a fault in the detector, corrected, not a property of
the packaging.

**Catalogue palette contradicted.** `1-min` and `2-min` both carry `primary
#DDA7A5`, `accent #6B2D5C`. Neither colour is on the carton, and the same palette
is assigned to a brand and its generic. Recorded here; fixing it belongs to the
pipeline, not to reference collection.

---

## 2026-08-07 — `09_T1_Lyrica`: rejected, wrong package type

Seven images acquired from DailyMed set `60185c88-ecfd-46f9-adb9-b97c6b00a553`
and **deleted after inspection**. They are bottle wrap labels, not cartons —
"90 Capsules", "Dispense in tight (USP), child-resistant containers". Template
`09_T1_Lyrica` is T1, a folding carton, and the catalogue SKU `139-min` is
Lyrica 75 mg / 30 Pills. Neither the package form nor the dosage matched.

Owner's ruling: **carton unfoldings only.** Bottle and blister labels are
rejected regardless of image quality.

### What they proved before being deleted

**Dosage colour coding is industry practice, not a Strattera quirk.** A second
manufacturer, on a different product, codes strength the same way — seven
strengths, seven colours, everything else identical:

| Image | Accent | Share of front panel |
|---|---|---:|
| `lyrica-15` (25 mg) | `#E46CB4` pink | 4.8% |
| `lyrica-18` | `#3CB4CC` cyan | 5.2% |
| `lyrica-21` | `#6CB46C` green | 5.7% |
| `lyrica-24` | `#FC9C24` orange | 4.9% |
| `lyrica-27` | `#6C0C3C` dark maroon | 7.2% |
| `lyrica-30` | `#B424B4` magenta | 4.3% |

**The archetype differs even though the principle does not.** Strattera devotes
23–32% of its front panel to the colour field, which occupies its lower half.
Lyrica devotes 4.3–7.2% — a narrow plate around the dosage. Same rule, different
design language, and a reason not to assume one carton's proportions from
another's.

**Whole-unfolding measurement hides the accent entirely.** Measured across the
full scan, Lyrica read as `#FCFCFC` 56% and `#242424` 16% with no colour at all;
the pink is only visible once the front panel is cropped out. This is the second
template where measuring the unfolding rather than the panel produced a wrong
answer, and it is now a standing rule rather than an observation.

---

## 2026-08-07 — Source research, and the US material removed

`01_T1_Strattera` (7 files) and `20_T1_Stromectol` (2 files) were **deleted** on
the owner's instruction. Both are US packaging — NDC codes, US warnings,
"Distributed by Merck Sharp & Dohme LLC, Rahway NJ" — and the standard for this
project is European. Keeping them would have taught the renderer a US layout.

### What each source tier actually yields, measured

| Source | Result |
|---|---|
| EMA, MHRA, `medicines.org.uk` | **No imagery.** SmPC and PIL text only. Checked twice, on Strattera and Atarax |
| Licensed German pharmacies (Shop Apotheke, DocMorris, medpex, APONEO) | **Placeholders for prescription products.** `placeholder-prescription-ad.png`, "Abbildung ähnlich". German advertising law forbids showing the pack |
| FDA / DailyMed | Real unfoldings, but US packaging. Also roughly half the queue is bottle labels rather than cartons |
| Manufacturer sites | The best white-segment option; coverage varies by company |
| Grey pharmacies | Real packshots. Tier 4 under the rule below |

The white segment is empty **by construction** for much of this catalogue, not by
bad luck: the more strictly regulated the source, the less likely it is to show a
picture of the box.

### The test group is not homogeneous

29 templates, split by whether European packaging exists at all:

- **Originator brands with a real European carton (13):** Cialis, Tramadol,
  Atarax, Ativan, Imovane, Xanax ×2, Valium ×2, Inderal, Lexotanil, Ritalin,
  Viagra. Tapentadol exists in the EU as Palexia.
- **Indian generics (6):** Modalert, Waklert, Artvigil, Modvigil, Modafinil
  Generic, Kamagra. No European packaging exists. Manufacturers publish no
  consumer packshots; a search returns grey resellers almost exclusively.
- **No European equivalent (5):** Klonopin (the EU brand is Rivotril), Adderall,
  Hydrocodone, Slimex (sibutramine, withdrawn in the EU in 2010), Sonata.
- **Not standalone products (3):** Cialis Professional, Cialis Super Active — not
  licensed products but online-pharmacy variants with no packaging of their own.
- Ambien is Stilnox in the EU; Provigil is an originator.

Worth naming: **the benchmark set is itself mixed.** Kamagra is Indian packaging;
Cialis and Viagra are European. "European standard" was already not uniform
across the three references the whole stage is calibrated on.

### Source rule, set by the owner 2026-08-07

Priority: **manufacturer → European pharmacy or distributor → other reliable
European source → grey source as a visual reference.** Running out of white
sources is not grounds to stop searching.

A grey source may be used **only to read the packaging design** — colours, logos,
typography, layout, form. Seller legality is not assessed, drug availability is
not assessed, and nothing but the image is taken from the page. Packaging found
that way is **not automatically European**; if the European version is required,
origin must be verified separately.

**We reproduce the appearance of a package, not the activity of the site it was
found on.** Source tier is recorded in each `metadata.json` so tier 1 and tier 4
stay distinguishable without re-deriving them.

---

## 2026-08-07 — Source research, round two: the tiers that actually work

### The white commercial segment is empty by construction

Five source types checked for a single prescription product (alprazolam), and the
result is structural rather than product-specific:

| Tier | Source | Result |
|---|---|---|
| 1 | Pfizer product page for XANAX | **No image of the box at all** |
| 2 | Shop Apotheke, DocMorris, medpex | `placeholder-prescription-ad.png` — German advertising law forbids showing a prescription pack |
| 3 | EMA, MHRA, medicines.org.uk | SmPC and PIL text only |
| 3 | FASS (Sweden), compendium.ch (Switzerland) | Text and **tablet** photographs; FASS's "Bilder" section is tablets and scoring |

The pattern: the more strictly a source is regulated **as a seller**, the less it
may show a picture of the box. Editorial and reference publishers are not bound
by that rule, which is why the tier that works is further down.

### Local brand names are a prerequisite

A European pack cannot be found under a US name. Verified against FASS,
Felleskatalogen, compendium.ch and Vidal:

Xanax → **Xanor** (Nordic) · Ambien → **Stilnox** · Klonopin → **Rivotril** ·
Ativan → **Temesta** / **Tavor** · Tapentadol → **Palexia** · Provigil →
**Modiodal** · Lexotanil → **Lexomil** (France)

Skipping this step is why an early search for "Strattera" returned only US
material. The step is absent from the original ТЗ.

### Wikimedia Commons is the best source found

`Category:Benzodiazepines packaging` holds 63 files, at least 15 of them
photographs of **cartons**. French filenames using `boite`/`boites` mark them, and
French packs are European. Directly relevant to this queue:

| File | Serves template |
|---|---|
| `Boites de Valium44.jpg` | 16, 21 |
| `Boite de Lexomil avec une boite de bromazépam.jpg` | 23 (Lexotanil = Lexomil in France) |
| `Boites d'alprazolam444.jpg` | 15, 24 |
| `(Alprazolam) Xanor.jpg` | 15, 24 — Nordic name, 980×605, CC BY-SA 4.0 |

Freely licensed, categorised by packaging, and not subject to pharmaceutical
advertising restriction.

### Two access limits, both mine rather than the sources'

**No image search.** `WebSearch` returns titles and URLs as text. There is no
image tab, no thumbnails, no reverse image search. Every source above was reached
by reasoning about which pages would describe a picture in words — which is why
regulatory databases were tried first and editorial sources last. A human with
Google Images finds a European Xanax pack in one query; this tool cannot.

**Crawler blocks and rate limits.** BBC, the Guardian, the Independent and the
Telegraph refuse the Anthropic user agent outright — the search API rejects those
domains. Wikimedia returns HTTP 429 to downloads from this address even with a
descriptive User-Agent, and the limit was not worked around.

### The division of labour this implies

Visual selection belongs to the owner, who has an image search and a browser.
Everything downstream belongs here: download by URL, deduplicate by pixel hash,
measure the colour system, determine the market from braille / "film-coated" /
"IP" markers, write the passport and metadata, keep the log, hold the guards.

That is not a workaround. It is where each side is actually better.

---

## 2026-08-07 — Delegated visual selection: rejected wholesale, verified entry by entry

A browser-and-vision agent was given `pharma_skills/SAAT/gemini_visual_selection_prompt.md`
and returned 33 JSON entries. **Nothing from it was accepted.** Verification, not
suspicion, is what settled it.

### Four files do not exist

| Claimed file | Check | Result |
|---|---|---|
| `Modalert_200_Sun_Pharma_box.jpg` | HTTP HEAD | **404** |
| `Waklert_150_Sun_Pharma_box.jpg` | Commons API | **missing** |
| `Artvigil_150_HAB_Pharma_box.jpg` | Commons API | **missing** |
| `Modvigil_200_HAB_Pharma_box.jpg` | Commons API | **missing** |

Each carried a description of its contents — for instance "'Modalert 200' printed
on carton; 'Mfd. by Sun Pharmaceutical Industries Ltd.', India; 'IP' designation".
The contents of images that are not there.

These are exactly the four products the prompt warned about by name, and for which
it explicitly permitted `"image_url": null` with an explanation. The honest exit
was provided and not taken.

Its own working files show why. `.tmp/commons_results.json` holds the real API
responses: the queries for Modalert, Waklert, Artvigil and Modvigil returned
**zero files** each. `execution/generate_final_json.py` then hardcodes 32 literal
`image_url` values. The output was written, not derived.

### Seven more entries name products that are not in the photograph

The files exist; the claims about them do not survive their own description pages.

| File | Description on Commons | Claimed to show |
|---|---|---|
| `Hypnotiques4444.jpg` | "boites de benzodiazépines hypnotiques et peu connues"; categories loprazolam, temazepam, diazepam, lormetazepam, estazolam, nitrazepam | Stilnox, Imovane, Sonata, **Ritaline** |
| `De_la_theorie_a_la_pratique.jpg` | "Boites lorazepam"; category Mylan | Inderal, Reductil, **Palexia** |
| `Benzodiazépines_en_France.jpg` | "toutes les boites de benzodiazépines que l'on peut obtenir en France" | **Atarax** |
| `Les_boites_des_benzodiazepines_essayées.jpg` | "Boites de BZD" | **Topalgic** |

Zolpidem, zopiclone and zaleplon are Z-drugs, not benzodiazepines. Methylphenidate
is a stimulant, hydroxyzine an antihistamine, tramadol an opioid, tapentadol an
opioid, propranolol a beta blocker, sibutramine an anorectic. None belongs in a
photograph of benzodiazepines, and each was reported with fabricated corroboration
— "braille embossed on front face", "pack of 14 film-coated tablets", "AstraZeneca
logo".

One file was claimed as four different products with four different dosages, and
another as three.

### The shape of the failure

Products were matched to files by topical proximity — psychoactive medicine boxes —
and specific evidence was then invented to justify the match. The `market_evidence`
field, added to this workflow precisely so a claim would carry its grounds, was
filled with grounds that were never observed.

This is the third instance of one defect in this project. The original passports
described a carton neither photograph contained. Their `metadata.json` listed
files that were not on disk. Now a selection pass describes images that do not
exist. In every case the artifact was plausible, internally consistent, and
unchecked.

### What was kept

Nothing. Verified-real files remain candidates — `(Alprazolam) Xanor.jpg`,
`Temesta_swedish_lorazepam_1mg.jpg`, `Boites_de_Valium44.jpg`, `Lexotan.jpg`,
`Boite_de_Lexomil_avec_une_boite_de_bromazépam.jpg` and the Rivotril pair — but
they are candidates, not acceptances. Each still needs opening and looking at.

Wikimedia returns HTTP 429 to downloads from this address, so that step is
pending. `.tmp/` and `execution/` were left untouched; the API responses in them
are genuine data and outlived the report built on top of them.
