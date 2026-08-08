# Design Passport — Kamagra 100mg (Sildenafil Citrate) [31_T1_Kamagra]

> **SKU:** 31_T1_Kamagra | **Template:** T1 family | **Created:** 2026-08-07
> **Source:** `raw_Kamagra_front_01.png`, 1536×1024 RGB
> **Measurements:** `scripts/reference_measure.py` → `03_knowledge_graph/reference_benchmarks_ssot/benchmark_measurements.json`
> **Status:** `single_source` — one photograph only

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent.

**`single_source` is a real limitation, not a formality.** This benchmark has one
frame. The second image it shipped with was 608×380, below the quality floor
derived from the benchmark set, and the owner ruled it out rather than lower the
floor. Everything not visible in this single view is a constraint below, not an
inference.

---

## A. Design Archetype

`[Observed]` **A two-tone carton split horizontally by a wave: cream above, deep
green below, with the division carried by a band of parallel wavy rules.**

The split is the design. It is not a stripe at the bottom edge and not a badge in
a corner — roughly the lower half of the front face is a solid colour field, and
the boundary between the two fields is a curve, not a line.

Content is distributed across both fields: the type sits in the cream half, and
the dosage badge sits *inside* the green half. That is a different organising
principle from a white carton with accents applied to it.

---

## B. Content Zones

Approximate placement, in thirds of the front face.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| `Rx` symbol | Upper left | Small | `[Measured]` OCR at the top of the text column |
| Active ingredient `Sildenafil Citrate Tablets IP` | Upper left–centre, **above the brand** | Medium | `[Measured]` — the INN line sits ABOVE the brand name |
| Brand `KAMAGRA-100` | Upper centre, below the INN line | Largest type, ~48% of carton width | `[Measured]` ALL CAPS, dosage fused into the name |
| Manufacturer logo | Left, below the brand, on the wave | Medium | `[Observed]` two stylised figures forming a heart, warm orange-brown |
| Dosage badge `100mg` | Right of centre, **inside the green field** | Small block | `[Observed]` peach-coloured square, dark type |
| Unit count `04` | Lower left, on the green field | Small block | `[Observed]` blue rounded square, white numerals |
| Side panel edge | Far left, vertical | Narrow | `[Observed]` red stripe |

**The INN line above the brand is unusual and worth carrying forward.** Most
cartons in this catalogue put the brand first. Here `Sildenafil Citrate Tablets
IP` is the top line of the text column and the brand sits beneath it.

**The dosage appears twice**: fused into the brand as `KAMAGRA-100`, and again in
the peach badge as `100mg`.

---

## C. Colour System

`[Measured]` over the carton mask. **Caveat: the mask is a luma difference from
the frame corner, not an alpha channel — this file has none — and it captured the
loose tablet lying beside the carton as well.** The `#58B8B8` entry is that
tablet, not packaging, and the other shares are diluted by its area.

| Role | HEX | Share | Where |
|---|---|---|---|
| Substrate | `#E8D8C8` | 47.1% | Upper field — warm cream, not white |
| Brand dark | `#084838` | 38.1% | Lower field — deep green |
| Secondary green | `#088878` | 7.3% | Wavy rules in the divider band |
| Accent | `#D88878` | 1.9% | Dosage badge — peach |
| *(not packaging)* | `#58B8B8` | 1.7% | The loose tablet in frame |
| Neutral | `#787878` | 1.1% | Shading and edges |

**Two colours dominate at nearly equal weight** — 47% cream against 38% green.
That balance is the design, and it is unlike a white carton with a small accent.

The substrate is a warm cream, not white. A renderer targeting `#FFFFFF` will
read colder and lose the design's character entirely.

---

## D. Graphic Signature

`[Observed]` **A band of five parallel wavy rules** sweeping across the full
width, separating the cream field from the green one. They are the carton's most
distinctive element and carry the eye left to right.

`[Observed]` A pictorial manufacturer logo — two abstract human figures forming a
heart outline, in warm orange-brown. It is the only warm colour on the carton
besides the dosage badge, and the only illustrative element.

A candidate for this template that carries neither a curved field division nor a
pictorial mark is a different design language, whatever the product name.

---

## E. Layer Order

`[Estimated]` (Medium) — inferred from occlusion.

```
cream substrate
  → green field (lower half, curved upper boundary)
  → wavy rule band along that boundary
  → manufacturer logo (crosses the boundary, sits above both fields)
  → dosage badge (on the green field)
  → unit-count block (on the green field)
  → type: INN line → brand
  → side panel red stripe [separate face]
```

---

## F. Typography Character

`[Observed]` — character, not metrics. Families not identified.

- Brand: heavy weight, ALL CAPS, with the dosage hyphenated into it.
- INN line: light weight, **Title Case**, noticeably smaller than the brand but
  larger than anything else.
- Badge numerals: bold, small, set inside coloured blocks rather than on the
  substrate.
- There are only three type sizes on the whole face, and the hierarchy is carried
  as much by the coloured blocks as by size.

---

## G. Material Impression

- `[Estimated]` (High) Matte board throughout — no specular highlight on either
  field.
- `[Unknown]` No foil, hologram or gloss varnish is visible in this view. Absence
  in one frame is not evidence of absence on the carton.

No roughness, metallic or clearcoat numbers are given; they cannot be measured
from a photograph.

---

## H. Reconstruction Constraints

- `[Unknown]` **Everything except this one front view.** `single_source`: no rear
  panel, no side panel content beyond the red edge stripe, no flaps, no opened
  pack. This is the sharpest limitation of the three benchmarks.
- `[Unknown]` Font families.
- `[Unknown]` Whether the carton carries braille — none is visible here, but this
  is a rendered-looking studio image and embossing may simply not be shown.
- `[Observed]` The image appears to be a rendered or heavily retouched product
  visual rather than a photograph of a physical box: edges are uniformly clean and
  the backdrop is a flat cut-out. Treat surface-finish inferences accordingly.
- `[Measured]` The colour shares above include a loose tablet that is not part of
  the packaging. Re-measure against an alpha-masked or manually cropped source
  before using them as targets.
- `[Observed]` OCR recovered the INN line and the brand at `--psm 3`. It did not
  return the `100mg` badge or the `04` block — both are dark type on saturated
  colour, which the recogniser handles poorly. Their content is read by eye.
