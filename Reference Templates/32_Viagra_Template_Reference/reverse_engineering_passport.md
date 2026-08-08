# Design Passport — Viagra 50mg (sildenafil) [32_T1_Viagra]

> **SKU:** 32_T1_Viagra | **Template:** T1_SMALL | **Rebuilt:** 2026-08-07
> **Source:** `raw_viagra_front.png`, 1080×810 RGBA
> **Measurements:** `scripts/reference_measure.py` → `03_knowledge_graph/reference_benchmarks_ssot/benchmark_measurements.json`

**What this document is for.** Reconstructing the *design* — the colour system,
the layout archetype and where each piece of content belongs. The camera is not
reconstructed: the render chooses its own angle, so measuring this photograph's
is effort spent on a number nothing consumes. Content zones are approximate by
intent; a renderer needs to know the dosage sits beside the brand, not that its
box begins at 0.3817.

**It replaces a passport that described a different carton.** The previous
version placed the brand at 0.060,0.220, the ingredient at the left margin and a
full-width `#004B87` stripe across the bottom — all tagged `[Measured]`, none of
it present. Its boxes were also identical to three decimals to the Cialis
passport's, which measurement cannot produce. The layout it described is the one
this project's own Blender driver renders, so it documented the renderer instead
of the photograph.

---

## A. Design Archetype

`[Observed]` **A pale board carton with one dark vertical side panel, printed in
a two-column layout.**

The distinguishing feature is that the brand colour lives on the **side panel**,
not on the front face. The front face is almost entirely substrate; the only
colour on it is a small violet block in the upper right. Nothing wraps around the
corner, and there is no band along the bottom.

This is worth stating plainly because it is the opposite of the archetype this
project currently renders — white body, accent stripe along the bottom of the
front face, badge in the top-right corner.

---

## B. Content Zones

Approximate placement, in thirds of the front face. Precision beyond this is not
useful: the render sets its own geometry.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Brand name `VIAGRA` | Upper left–centre | Largest element on the face, roughly 45% of carton width | ALL CAPS |
| Dosage `50 mg` | Directly below the brand, left column | About half the brand's height | |
| Form `film-coated tablets` | Right column, level with the dosage | Small | Lowercase |
| Active ingredient `sildenafil` | Right column, below the form line | Small | Lowercase, **not** at the left margin |
| Unit count `4 film-coated tablets` | Lower centre | Small | |
| Manufacturer mark `Pfizer` | Side panel, upper area | Medium | `[Observed]` — on the panel, not the face |
| Security hologram | Lower right of the face | Small patch | `[Observed]` |
| Braille | Across the centre of the face | — | `[Observed]` embossing, not ink |

**The layout is two-column.** A left column carries brand and dosage; a right
column carries the form line and the ingredient at a smaller size. The previous
passport described a single left-aligned column, which the photograph contradicts.

---

## C. Colour System

`[Measured]` over the alpha-masked carton. Shares are of the carton, not the frame.

| Role | HEX | Share | Where |
|---|---|---|---|
| Substrate | `#D8D8D8` | 64.2% | Front face body |
| Brand dark | `#082858` | 21.5% | Side panel |
| Neutral | `#787888` | 9.5% | Hologram and shaded edges |
| Accent | `#282898` | 3.4% | Upper-right block on the face |

The substrate reads `#D8D8D8` rather than pure white because that is the printed
board under studio light. A renderer targeting pure white will look colder than
the reference.

**Colour distribution is the design's signature here:** one large dark field on a
*separate face*, and a single small accent on the front. Two colours, one of them
almost entirely off the front face.

---

## D. Graphic Signature

`[Observed]` Rectilinear. No curves, no swooshes, no gradient fields. The design
is set entirely in rectangular blocks and type. The only non-rectangular elements
are the Pfizer oval on the side panel and the hologram patch.

This matters for search: a candidate carrying wave forms or curved colour
divisions is a different design language, however similar the product.

---

## E. Layer Order

`[Estimated]` (Medium) — inferred from occlusion.

```
substrate board
  → side panel field (a different FACE, not a layer on the front)
  → upper-right accent block
  → braille embossing (relief, not ink)
  → brand type → dosage → form line → ingredient → unit count
  → hologram patch [top]
```

The side panel is called out because treating it as a layer of the front face is
exactly the error that turned it into a bottom stripe last time.

---

## F. Typography Character

`[Observed]` — character, not metrics. Families are not identified; recognising a
typeface from a skewed photograph is a real inference and was not performed.

- Brand: heavy weight, ALL CAPS, wide tracking, by far the largest element.
- Everything else: light-to-regular weight, **lowercase**, small.
- The contrast between the brand and everything else is the layout's whole
  hierarchy — there is no intermediate size.

Worth noting against this project's current render, which sets the active
ingredient in title case. Here it is lowercase, as is every non-brand string.

---

## G. Material Impression

- `[Estimated]` (High) Matte board — no specular highlight across the face.
- `[Observed]` Reflective foil on the hologram patch.
- `[Unknown]` Whether the brand title carries spot gloss cannot be told from this
  view.

No roughness, metallic or clearcoat numbers are given. A shader parameter cannot
be measured from a photograph, and inventing one puts an unsupported value
straight into a renderer.

---

## H. Reconstruction Constraints

- `[Unknown]` The rear panel, top and bottom flaps are not visible here.
  `raw_viagra_back.png` exists and was not analysed for this passport.
- `[Unknown]` Font families.
- `[Unknown]` The braille content.
- `[Observed]` The `Pfizer` mark was legible to the eye but not returned by OCR.
- `[Measured]` **The photograph shows 50 mg. `metadata.json` recorded
  `"dosage_display": "100 mg"`.** Corrected; the photograph governs.
- `[Observed]` Reading these files needs two things that are not obvious: the
  PNGs carry alpha and no background, so a straight RGB conversion turns
  transparent into black and destroys OCR contrast; and Tesseract's default
  segmentation returns only the small print — the brand and dosage need `--psm 3`.
