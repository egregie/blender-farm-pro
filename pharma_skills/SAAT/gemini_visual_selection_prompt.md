# Prompt for the visual-selection agent (Gemini / Antigravity)

> Hand this whole file to an agent that has **browser access and vision**. It does
> the one step this project cannot: looking at pictures and judging them.
> Everything downstream — download, deduplication, measurement, market
> determination, passports, metadata, logs — is handled here afterwards.
>
> Copy everything below the line.

---

## Your task

Find photographs of pharmaceutical **cartons** (folding boxes) for a list of
products, judge them by eye, and return a structured list of image URLs. You are
doing visual selection only. Do not write documentation, do not analyse the
designs in depth, do not download anything — just find, judge, and report URLs.

## What makes an image acceptable

**One criterion decides it: is the front face of the carton legible?**

Legible means someone could read off it, without guessing: the colour scheme, the
brand name, where the dosage and the active ingredient sit, and the shape of the
graphic elements.

- **Camera angle does not matter.** Straight-on, three-quarter, tilted — all fine.
- **Image type does not matter.** A studio packshot, a press photo, a snapshot on
  a table, a flat label scan. All acceptable.
- **Reject** anything where the front face is obscured: a hand across it, a price
  sticker, blowout glare, heavy blur, a watermark over more than ~20% of the pack.

## What is NOT acceptable

- **Blister strips alone.** Foil with tablets showing, no box.
- **Bottle labels.** A wrap-around strip label, or a photo of a plastic bottle.
- **Loose tablets or capsules** with no packaging.
- **Illustrations, renders, mock-ups.** Photographs of real boxes only.
- Anything where you cannot tell whether it is a carton.

If a photo shows a carton *and* loose tablets beside it, that is fine — the
carton is what matters.

## Market matters, and the domain does not tell you

We want **European** packaging. A grey pharmacy site can host a photo of a
genuine European box; a European pharmacy site can host a photo of an Indian one.
So judge the market from the **box itself**:

| What you see on the pack | Market |
|---|---|
| Braille dots embossed on the front face | **Europe** — mandatory there since EU Directive 2004/27/EC |
| "film-coated tablets", multilingual panels, small counts (4, 14, 20, 28) | **Europe** |
| EAN/GTIN barcode and no NDC number | **Europe** |
| An "NDC" number, "Rx only", counts of 30/90/100 | **United States** |
| "IP" printed after the ingredient name (Indian Pharmacopoeia) | **India** |
| "Mfd. by" with an Indian address | **India** |

Record what you saw, not what you assume. If you cannot tell, say `unknown`.

**Prefer European. Accept non-European if nothing European exists**, and mark it —
we would rather have a marked Indian pack than an empty folder.

## Where to look, in order

1. **Manufacturer sites** — usually show no box for prescription drugs, but check.
2. **European pharmacies and distributors** — note that German ones legally cannot
   show prescription packs and serve placeholders.
3. **National formularies and regulators** — usually text and tablet photos only.
4. **News, editorial, clinical and encyclopedic publishers.** This tier works well.
   **Wikimedia Commons is the single best source found so far** — see
   `Category:Benzodiazepines packaging`, where French filenames using
   `boite`/`boites` mark European cartons.
5. **Grey or unofficial pharmacy sites — as a visual reference only.**

On tier 5: take the image and nothing else. Do not evaluate the seller, do not
read prices or availability, do not report anything about the site's business.
**We reproduce the appearance of a package, not the activity of the site.**

Running out of options in tiers 1–4 is a reason to go to tier 5, not to stop.

## Search under LOCAL brand names

A European pack will not be found under a US name. Verified equivalents:

| Catalogue name | Search instead for |
|---|---|
| Xanax | **Xanor** (Nordic), Xanax (Italy, Belgium, France) |
| Ambien | **Stilnox** |
| Klonopin | **Rivotril** |
| Ativan | **Temesta**, **Tavor** (Germany) |
| Tapentadol | **Palexia** |
| Provigil | **Modiodal** (France, Nordic) |
| Lexotanil | **Lexomil** (France) |

For the rest, try the catalogue name first, then the generic ingredient name.

## Per-product limits

- **Maximum 7 images per product.** Never more.
- **When two candidates look equally good, take both** — within the limit. Final
  selection happens later.
- **Fewer is fine.** One good image beats seven mediocre ones. If only one exists,
  return one. If none passes, say so — do not lower the bar to fill the list.

## The products

Dosage and unit count come from our catalogue and are what the product should
ideally show — but **a different strength is acceptable**, just record which one
you found. Package design rarely changes between strengths; only the colour does,
and we track that separately.

| # | Folder | Product | Search as | Catalogue dosage / count |
|---|---|---|---|---|
| 03 | `03_T1_SMALL_Cialis_Professional` | Cialis Professional | Cialis (tadalafil) | 20mg |
| 04 | `04_T1_SMALL_Cialis_Super_Active` | Cialis Super Active | Cialis (tadalafil) | 20mg |
| 05 | `05_T1_Tramadol` | Tramadol | Tramadol, Contramal, Topalgic | 50mg / 60 |
| 06 | `06_T1_Ambien` | Ambien | **Stilnox** (zolpidem) | 10mg / 30 |
| 07 | `07_T1_Atarax` | Atarax | Atarax (hydroxyzine) | 25mg / 30 |
| 08 | `08_T1_Ativan` | Ativan | **Temesta**, **Tavor** (lorazepam) | 1mg / 30 |
| 10 | `10_T1_Modalert` | Modalert | Modalert (Sun Pharma) | 200mg / 30 |
| 11 | `11_T1_Waklert` | Waklert | Waklert (Sun Pharma) | 150mg / 30 |
| 12 | `12_T1_Provigil` | Provigil | **Modiodal**, Provigil | 200mg / 30 |
| 13 | `13_T1_Artvigil` | Artvigil | Artvigil (HAB Pharma) | 150mg / 30 |
| 14 | `14_T1_Imovane` | Imovane | Imovane (zopiclone) | 7.5mg / 30 |
| 15 | `15_T1_Xanax` | Xanax | **Xanor**, Xanax (alprazolam) | 0.5mg / 30 |
| 16 | `16_T1_Valium` | Valium | Valium (Roche, diazepam) | 5mg / 30 |
| 17 | `17_T1_Klonopin` | Klonopin | **Rivotril** (clonazepam) | 1mg / 30 |
| 18 | `18_T1_Inderal` | Inderal | Inderal (propranolol) | 40mg / 30 |
| 19 | `19_T1_Slimex` | Slimex | Slimex, Reductil (sibutramine) | 15mg / 30 |
| 21 | `21_T1_Valium_Brand` | Valium (brand) | Valium (Roche) | 5mg / 30 |
| 22 | `22_T1_Sonata` | Sonata | Sonata, Zerene (zaleplon) | 10mg / 30 |
| 23 | `23_T1_Lexotanil` | Lexotanil | **Lexomil**, Lexotanil (bromazepam) | 3mg / 30 |
| 24 | `24_T1_Xanax_Pfizer` | Xanax by Pfizer | **Xanor**, Xanax (Pfizer/Upjohn) | 0.5mg / 30 |
| 25 | `25_T1_Modafinil_Generic` | Modafinil generic | Modafinil (any maker) | 200mg / 30 |
| 26 | `26_T1_Modvigil` | Modvigil | Modvigil (HAB Pharma) | 200mg / 30 |
| 27 | `27_T1_Adderall` | Adderall | Adderall — **US only, no EU version** | 30mg / 30 |
| 28 | `28_T1_Hydrocodone` | Hydrocodone | Hydrocodone — **US only** | 10mg / 30 |
| 29 | `29_T1_Tapentadol` | Tapentadol | **Palexia** (Grünenthal) | 50mg / 30 |
| 30 | `30_T1_Ritalin` | Ritalin | Ritalin (Novartis) | 10mg / 30 |

**Known-difficult entries, so you do not waste effort:**

- **27 Adderall, 28 Hydrocodone** — no European product exists. Take US packs and
  mark them `us`.
- **19 Slimex** — sibutramine was withdrawn in the EU in 2010. Historic photos or
  grey-market packs only.
- **10, 11, 13, 25, 26** (Modalert, Waklert, Artvigil, Modafinil generic,
  Modvigil) — Indian export generics. No European packaging exists and the
  manufacturers publish no consumer photography. Expect tier 5, mark them `in`.
- **03, 04** (Cialis Professional / Super Active) — these are not licensed
  products but online-pharmacy variants. They may have no distinct packaging at
  all. If you find only standard Cialis packs, say so rather than substituting.

## What to return

A JSON array. One object per image. Nothing else — no commentary, no summary
prose around it.

```json
[
  {
    "folder": "15_T1_Xanax",
    "image_url": "https://upload.wikimedia.org/wikipedia/commons/7/7f/example.jpg",
    "page_url": "https://commons.wikimedia.org/wiki/File:example.jpg",
    "source_tier": 4,
    "brand_shown": "Xanor",
    "dosage_shown": "1 mg",
    "packaging_market": "eu",
    "market_evidence": "braille visible on front face; text in Swedish; pack of 20",
    "front_face_legible": true,
    "notes": "three-quarter view, slight glare on the upper right but the brand and dosage read clearly"
  }
]
```

Field rules:

- `image_url` — **direct link to the image file**, not to the page containing it.
  This is the single most important field; without it nothing downstream works.
- `source_tier` — 1 to 5, per the ladder above.
- `packaging_market` — `eu`, `us`, `in`, or `unknown`.
- `market_evidence` — what you actually saw that decided it. If you wrote
  `unknown`, say why you could not tell.
- `notes` — anything a person choosing between candidates would want to know.

For a product where you found nothing acceptable, return one object with
`"image_url": null` and a `notes` field explaining what you searched and why
nothing passed. **A recorded failure is useful; a silent omission is not.**

## What not to do

- Do not download files. Return URLs.
- Do not write passports, analyses or design descriptions. That happens later.
- Do not judge sellers, legality or availability of any drug.
- Do not invent a URL. If you cannot get a direct image link, return the page URL
  in `page_url`, leave `image_url` null, and note it.
- Do not exceed 7 images for any product.
- Do not lower the legibility bar to fill a slot.
