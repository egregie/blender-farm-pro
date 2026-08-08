# SAAT — Searching and Analysis of Templates

> **Version:** 1.0 (design-passport architecture)
> **Governing ТЗ:** `06_docs/superpowers/specs/2026-08-07-saat-reference-acquisition-tz.md`
> **Downstream consumers:** Blender render driver, SVG vector generator, UV layout builder

Acquires pharmaceutical packaging photography for the catalogue's templates and
turns each accepted reference into a **design passport** — a description of the
carton's colour system, layout archetype and content placement, written so a
renderer can reconstruct the *design* without the photograph.

> **Кратко (RU):** SAAT ищет фотографии упаковок по трём эталонам, отбирает
> годные по измеренным порогам и превращает отобранные в **дизайн-паспорт** —
> описание цветовой системы, архетипа вёрстки и расположения содержимого.
> Камера не реконструируется: угол съёмки задаёт рендер.

---

## 1. What this version changed, and why

Version 0.2 specified a *reverse engineering passport* with twelve sections
including camera reconstruction, vanishing points, Bézier control points and
shader parameters, all to three decimals.

That specification produced fabrications. The two benchmark passports written
under it carried bounding boxes **identical to three decimals across two
packages from different manufacturers** — logo at 0.060,0.060, brand at
0.060,0.220, a full-width accent stripe at 0.000,0.920 — every value tagged
`[Measured]`. Checked against the pixels, none of it was in either photograph:
the layout they described is the one this project's own Blender driver renders.
The ground truth for reconstruction was a description of the renderer.

Three things follow, and they are the shape of this version:

- **The camera is not reconstructed.** The render chooses its own angle, so
  measuring a photograph's pitch, focal length and vanishing points spends effort
  on numbers nothing consumes. A reference is judged on whether its front-face
  design is legible, not on the angle it was shot from.
- **Content placement is approximate by intent.** A renderer needs to know the
  dosage sits beside the brand, not that its box begins at 0.3817 — especially
  when that figure lives in carton-bounding-box space rather than face space,
  which the old passports never disclosed.
- **What replaces the precision is what actually matters:** the measured colour
  system, the layout archetype, and the graphic signature that distinguishes one
  design language from another during search.

---

## 2. Observation rules

Unchanged from v0.2, because they were never the problem — they were ignored.
Every statement in a passport carries one of:

| Tag | Meaning |
|---|---|
| `[Measured]` | Derived from pixels by `scripts/reference_measure.py` or another named tool |
| `[Observed]` | Directly visible in the image and stated by eye, not computed |
| `[Estimated]` | Inferred, **with an explicit confidence** (High / Medium / Low) |
| `[Unknown]` | Not visible, not derivable. Recorded as a reconstruction constraint |

`[Measured]` means a tool produced the number. Writing it beside a value that was
reasoned out is the failure that made this rewrite necessary.

---

## 3. The three benchmarks

| Folder | Product | Substrate : colour | Where the colour lives |
|---|---|---|---|
| `Reference Templates/02_T1_SMALL_Cialis/` | Cialis 10mg | 58 : 24 | Curved fields entering from both edges, type in the corridor between |
| `Reference Templates/31_Kamagra_Template_Reference/` | Kamagra 100mg | 47 : 38 | Lower half of the face, divided by a wave |
| `Reference Templates/32_Viagra_Template_Reference/` | Viagra 50mg | 64 : 21 | A separate face — the side panel. Front face nearly bare |

The three are deliberately unalike, and that spread is what makes them useful as
a benchmark set. **None of them has an accent stripe along the bottom of the
front face**, which is worth knowing because the current Blender driver renders
one.

`31_Kamagra_Template_Reference` is `single_source` — one usable frame. Its second
image was 608×380, below the floor derived below, and was removed rather than
lower the floor to admit it.

---

## 4. Quality floors

Measured across the seven benchmark images on 2026-08-07, not chosen. Derivation
and per-image numbers are in
`03_knowledge_graph/reference_benchmarks_ssot/collected_references_log.md`.

| Signal | Floor | Set by |
|---|---|---|
| Long edge | **1079 px** | `raw_cialis_front.png` |
| Sharpness (variance of Laplacian) | **996** | `raw_viagra_front.png` |
| Subject area, share of frame | **56.5%** | `raw_Kamagra_front_01.png` |

A candidate worse than the **worst benchmark** on any signal is rejected.
**Lowering a floor to fill a folder is forbidden.** If nothing passes, the
template is marked `insufficient_references` and stays empty.

Two cautions about the sharpness figure. It moves with resolution and with how
much fine detail the packaging carries. And it does not track "good front
reference" — the sharpest image in the benchmark set is a *back* panel at 4248,
while the least sharp at 996 is a perfectly usable front packshot. The floor is
anchored to that front packshot deliberately.

---

## 5. Acquisition

### 5.1 The criterion

**Front-face design legibility, and nothing else.** Camera angle does not matter.
Rear panels, blister views, opened packs and dosage variants are welcome but are
not requirements and never justify accepting a weaker front view.

A candidate qualifies when its front face is legible enough to state: the colour
system and rough area shares, the layout archetype, the approximate zone of each
content element, and the graphic signature.

### 5.2 Limits

- **Maximum 7 images per template.** Never exceeded. When the cap is reached the
  search stops and the log records that it was truncated.
- **When two candidates are genuinely indistinguishable in quality, take both** —
  within the cap. The owner selects afterwards.

### 5.3 Sources, in order of priority

**1. Official manufacturer** → **2. European pharmacy or distributor** →
**3. Another reliable European source** → **4. Grey or unofficial source, as a
visual reference only.**

Work down the list. Exhausting the white segment without a usable image is **not
grounds to stop searching** — it is grounds to move to the next step.

What each step is worth in practice, measured on 2026-08-07 rather than assumed:

| Source | What it actually yields |
|---|---|
| Regulatory databases (EMA, MHRA, medicines.org.uk) | **No imagery at all.** SmPC and PIL text only |
| Licensed German pharmacies (Shop Apotheke, DocMorris, medpex) | **Placeholders for prescription products** — German advertising law forbids showing the pack. `placeholder-prescription-ad.png`, "Abbildung ähnlich" |
| FDA / DailyMed | Real flat unfoldings, but **US packaging**: NDC codes, US warnings |
| Manufacturer sites | Varies by company; the best white-segment bet |

The consequence is that for much of this catalogue the white segment is empty by
construction, not by bad luck.

### 5.4 Using a grey source

When no usable image of the original packaging is found in the white segment
after a genuine search, a grey or unofficial site **may be used solely as a
visual reference for the packaging** — to establish the actual design: colour
scheme, logos, typography, element placement, form.

Under that use:

- the legality of the seller or platform is **not assessed** — it is irrelevant
  to reading a design off a picture;
- the legal availability of the drug is **not assessed**;
- **nothing else on the page is used** — not the product description, not the
  price, not stock, not purchasing information;
- packaging found on a grey site is **not automatically European packaging**. If
  the European version is specifically required, the pack's origin and market
  must be verified separately;
- among several candidates, prefer the sharpest image in which the front and
  side faces can be reliably examined.

**The governing limit: we reproduce the appearance of a package, not the
activity of the site it was found on.** The file is saved, its URL and date are
logged, and its source tier is recorded in `metadata.json` so a later reader can
tell tier 1 from tier 4 without re-deriving it.

### 5.4 Rejection

Reject: resolution, sharpness or subject area below the floors; watermarks over
more than 20% of the package surface (measured, not judged); browser chrome or UI
overlays; visible compression artefacts or motion blur; a front face occluded by
a hand, price tag or blowout highlight. Deduplicate by **pixel hash**, not by URL
— the same photograph is served from many sites, and two formats of one picture
are one reference, not two.

Every rejection goes in the log with its URL and reason. Silent discards are how
a reference set stops being reproducible.

---

## 6. The design passport

One `reverse_engineering_passport.md` per template folder, plus `metadata.json`.
Sections, in order:

| Section | Contains |
|---|---|
| **A. Design Archetype** | One paragraph: what distinguishes this carton from any other. Where the colour lives, how the face is divided |
| **B. Content Zones** | Approximate placement in thirds of the front face, with relative size. Never pixel coordinates |
| **C. Colour System** | `[Measured]` palette with area shares over the carton mask |
| **D. Graphic Signature** | The distinctive non-text element — the shape that identifies the design language during search |
| **E. Layer Order** | Occlusion order, `[Estimated]` |
| **F. Typography Character** | Weight, case, hierarchy, number of distinct sizes. **Not** metrics, and families stay `[Unknown]` unless genuinely identified |
| **G. Material Impression** | Matte / foil / gloss as observed. **No** roughness, metallic or clearcoat numbers — a shader parameter cannot be measured from a photograph |
| **H. Reconstruction Constraints** | Everything not visible, everything eye-read rather than measured, and any discrepancy found against existing project data |

Camera reconstruction, vanishing points, Bézier decomposition, typography metrics
and shader values are **removed**, not relocated. They were the fabricated
sections.

`metadata.json` carries `schema_version: "3.0"`, the label content, the measured
palette and colour zones, the reference image list, and a `quality_gate` block
that states real limitations — `single_source`, contaminated measurements — rather
than reporting `complete` unconditionally.

---

## 7. Human gates

Two, both of which stop execution:

1. **After acquisition.** The owner selects which images to keep. No passport is
   written until they say so.
2. **After passports.** Confirmation before anything downstream consumes them.

---

## 8. Traps worth knowing before you debug them

- **The benchmark PNGs carry alpha and no background.** Converting straight to RGB
  turns transparent into black, which destroys the contrast OCR needs and makes
  the backdrop read as luma 0. Composite onto white first.
- **Tesseract's default page segmentation reads only the small print.** The brand
  title and the dosage need `--psm 3`. At the default the Viagra packshot returns
  `film-coated`, `tablets` and `sildenafil` and misses `VIAGRA` and `50mg`
  entirely.
- **Tesseract is not on PATH on this machine.** `scripts/render_qa.py` owns the
  probe that finds the binary; import it rather than writing a second search.
- **A strongly angled carton defeats OCR.** The Cialis benchmark returns `SSS` and
  `<—_—` — the recogniser reading curved graphic fields as letterforms. Content
  from such an image is `[Observed]`, not `[Measured]`, and the passport must say
  so.
- **A luma-based mask catches whatever else is in frame.** The Kamagra colour
  shares include a loose tablet lying beside the carton. Prefer alpha where it
  exists; where it does not, say what the mask actually captured.

---

## 9. Guards

`tests/test_reference_templates.py` enforces what documents cannot:

- every file listed in `metadata.json` exists;
- every image present is listed;
- no folder exceeds seven images;
- no two files in a folder are the same picture.

The photographs are gitignored while the metadata is tracked, so a clean clone has
the contracts but not the pictures. The guards distinguish that state from a
manifest that lies: a folder with no images at all is skipped, a folder with some
images and a listed one missing fails.
