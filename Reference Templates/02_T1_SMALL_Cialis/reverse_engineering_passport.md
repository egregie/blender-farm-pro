# Design Passport — Cialis 10mg (tadalafil) [02_T1_SMALL_Cialis]

> **SKU:** 02_T1_SMALL_Cialis | **Template:** T1_SMALL | **Rebuilt:** 2026-08-07
> **Source:** `raw_cialis_front.png`, 1079×810 RGBA
> **Measurements:** `scripts/reference_measure.py` → `03_knowledge_graph/reference_benchmarks_ssot/benchmark_measurements.json`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent.

**It replaces a passport that described a different carton.** The previous
version gave bounding boxes identical to three decimals to the Viagra passport's
— logo 0.060,0.060, brand 0.060,0.220, a full-width accent stripe at 0.000,0.920
— all tagged `[Measured]`. Two packages from different manufacturers cannot
measure the same, and neither photograph contains that layout. It described this
project's own renderer.

**OCR is largely unavailable here, and that shapes the document.** The carton is
photographed at a strong angle and the recogniser returned almost nothing usable
— `SSS`, `SS`, `<—_—` are it reading the curved graphic elements as letters. Only
`tablets` came back with confidence. Content below is therefore `[Observed]` by
eye rather than `[Measured]`, and is tagged accordingly.

---

## A. Design Archetype

`[Observed]` **A cream carton crossed by large curved green fields entering from
both sides, with the type set in the light channel between them.**

The green does not sit in a block or a band. It sweeps in as broad S-curves from
the left and right edges, and the printed content occupies the pale corridor they
leave open through the middle. The design is built around negative space carved
by curves.

Colour also carries a functional role: the dosage is set in white on a solid
green rectangle, so the badge is part of the colour system rather than an overlay
on the substrate.

---

## B. Content Zones

Approximate placement, in thirds of the front face. `[Observed]` throughout —
OCR could not confirm these positions at this angle.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Brand `Cialis®` | Centre left, mid-height | Largest element on the face | Title case, not all caps |
| Dosage `10 mg` | Immediately right of the brand, same baseline | Medium | White type on a solid green block |
| Form `film-coated tablets` | Below the brand, centred | Small | Lowercase |
| Active ingredient `tadalafil` | Below the form line | Medium-small | Lowercase, larger than the form line |
| Unit count `4 film-coated tablets` | Upper right of the face | Small | `[Measured]` — the one string OCR returned confidently |
| Manufacturer mark `Lilly` | Lower right | Medium | Red script on a silver holographic oval |
| Braille | Across the centre-left of the face | — | `[Observed]` embossing |
| Side panel | Far left, vertical | Narrow, dark | Carries a 2D data-matrix code |

**The dosage shares a baseline with the brand**, set to its right. That differs
from both other benchmarks: Viagra puts the dosage below the brand, Kamagra fuses
it into the brand and repeats it in a badge.

**The ingredient is set larger than the form line**, reversing the usual
relationship — `tadalafil` reads as a second-order headline rather than fine print.

---

## C. Colour System

`[Measured]` over the alpha-masked carton.

| Role | HEX | Share | Where |
|---|---|---|---|
| Substrate | `#D8D8D8` | 57.8% | Cream-white board |
| Brand green | `#385808` | 23.9% | Curved fields and the dosage block |
| Neutral | `#686868` | 10.1% | Side panel, shading, hologram |
| Dark | `#181808` | 3.9% | Type and the side panel's darkest areas |
| Light neutral | `#989888` | 3.1% | Edges and gradients |

The green is an **olive**, `#385808` — yellow-shifted, not a blue-green. Rendering
it as a generic green loses the brand immediately.

Substrate to brand colour runs about 58:24 — the carton reads as predominantly
pale with substantial colour, sitting between Viagra (64:21, colour mostly off the
front face) and Kamagra (47:38, near-equal fields).

---

## D. Graphic Signature

`[Observed]` **Broad S-curves in olive green entering from the left and right
edges**, meeting nowhere and leaving a light corridor through the middle where all
type sits. They are the single most recognisable feature and the reason OCR
misreads this carton — the recogniser tries to read them as letterforms.

`[Observed]` A silver holographic oval carrying the manufacturer's script mark,
lower right. It is the only reflective element.

A candidate for this template without curved colour fields is a different design
language, however close the product.

---

## E. Layer Order

`[Estimated]` (Medium) — inferred from occlusion.

```
cream substrate
  → left curved green field
  → right curved green field
  → dosage block (solid green, behind the dosage type)
  → braille embossing (relief, not ink)
  → type: brand → dosage → form line → ingredient → unit count
  → holographic oval + manufacturer script [top]
  → side panel field with data-matrix [separate face]
```

---

## F. Typography Character

`[Observed]` — character, not metrics. Families not identified.

- Brand: regular-to-medium weight, **Title Case**, by far the largest element.
  Notably *not* bold and *not* all caps — unlike both other benchmarks.
- Dosage: medium weight, reversed out in white on green.
- Ingredient: light weight, lowercase, second-largest string.
- Form line and unit count: light, lowercase, smallest.
- Four distinct sizes, a wider hierarchy than Viagra's two or Kamagra's three.

---

## G. Material Impression

- `[Estimated]` (High) Matte board across the printed faces.
- `[Observed]` Holographic foil on the manufacturer oval — visibly iridescent.
- `[Observed]` Physical braille relief across the face.
- `[Unknown]` Whether the brand carries spot gloss.

No roughness, metallic or clearcoat numbers are given; they cannot be measured
from a photograph.

---

## H. Reconstruction Constraints

- `[Unknown]` **Text positions are eye-read, not measured.** The angle defeats
  OCR: it returned `SSS`, `SS` and `<—_—`, which are the curved fields being read
  as letterforms, plus `tablets` at confidence 96. Nothing in Section B except the
  unit count should be treated as measured.
- `[Unknown]` The rear panel and flaps. `raw_cialis_back.png` exists and was not
  analysed for this passport.
- `[Unknown]` Font families.
- `[Unknown]` The braille content and the side panel's data-matrix payload.
- `[Measured]` **The photograph shows 10 mg. `metadata.json` recorded
  `"dosage_display": "20mg"`.** The photograph governs.
- `[Observed]` The curved fields make this the hardest of the three benchmarks to
  reconstruct from measurement alone. If precise geometry is ever needed here, a
  flatter view of the same carton is worth acquiring rather than deriving it from
  this one.
