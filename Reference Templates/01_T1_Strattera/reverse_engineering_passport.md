# Design Passport — Strattera (atomoxetine) [01_T1_Strattera]

> **SKU:** 01_T1_Strattera | **Template:** T1 | **Created:** 2026-08-07
> **Catalogue SKU served:** `2-min` (Strattera 40mg, 30 Pills) and `1-min`
> (Atomoxetine Generic 40mg, 10 Pills) — both 40 mg
> **Source type:** flat label unfoldings, DailyMed (NIH), set
> `309de576-c318-404a-bc15-660c2b1876fb`
> **Measurements:** `scripts/reference_measure.py` and the dosage sweep recorded below

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed — the render chooses its own angle. Content zones are approximate.

**Source type differs from the three benchmarks.** Those are 3/4 studio packshots
of a physical carton. These are flat scans of the unfolded label: every panel in
one plane, no perspective, no carton geometry. That makes them better for reading
the design and useless for reading proportions or material.

**The front panel was identified by the owner, not by a tool.** It spans roughly
**0.35 to 0.66** of the unfolding's width; everything left of it is the
side/information panel and everything right is the barcode and warnings panel.
Automatic identification was attempted and failed — see Section H.

---

## A. Design Archetype

`[Observed]` **A white panel with a single solid colour field occupying its lower
half, the brand set in lowercase above it, and the dosage reversed out in white
on the colour field.**

The layout is horizontally banded, not curved and not cornered. There is one
colour and one substrate, with a hard straight boundary between them.

**The colour field is the design's only variable.** Substrate, typography and
layout are identical across all seven strengths; only the hue changes.

---

## B. Content Zones

Approximate placement, in thirds of the front panel.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Unit count `30 Capsules` | Top left, on a colour bar | Small | |
| NDC code | Top right, on the same bar | Small | |
| Brand `strattera` | Upper centre, on substrate | Largest element | **lowercase**, with a superscript ® |
| Active ingredient `atomoxetine capsules` | Directly under the brand | Medium-small | lowercase |
| `Rx only` | Left, on the colour field | Small | white on colour |
| Dosage `40 mg` | Right of `Rx only`, same band | Medium | **white on a rounded white-outlined block** |
| Capsule image | Centre, on the colour field | Small | photographic, not illustrative |
| Equivalence note | Right of the capsule | Small | |
| Warning line | Below the colour field | Small | red type on substrate |
| `www.strattera.com` | Lower left | Small | |
| Manufacturer script `Lilly` | Lower right | Medium | red script |

---

## C. Colour System

`[Measured]` over the owner-marked front panel only, not the whole unfolding.
Measuring the unfolding gives 40% to a black service block that is not part of
the design.

| Role | HEX | Share of front panel |
|---|---|---|
| Substrate | `#FCFCFC` | 44–46% across all strengths |
| Colour field | **varies by dosage — see below** | 23–32% |

### The dosage → colour rule

`[Measured]` across seven strengths from one manufacturer set. **This is the
rule for choosing the front colour: it follows the dosage in the SKU, not the
product.**

| Dosage | Front colour | Share |
|---:|---|---:|
| 10 mg | `#CCB40C` olive-yellow | 24.1% |
| 18 mg | `#E46C24` orange | 27.4% |
| 25 mg | `#FCB40C` yellow | 23.4% |
| 40 mg | `#5484B4` mid blue | 27.4% |
| 60 mg | `#545454` grey | 32.6% |
| 80 mg | `#6C2424` dark maroon | 28.4% |
| 100 mg | `#0C2454` navy | 28.5% |

**Both catalogue SKUs are 40 mg, so this template renders `#5484B4`.**

Two cautions. The 60 mg entry is achromatic grey — a first pass looking for
saturated colour missed it and reported no accent, which was a fault in the
detector, not a property of the packaging. And **this table is a property of this
brand**, measured here; it must not be carried to another product. Viagra shows
no such coding across its available views, and Kamagra exists in a single frame.

The catalogue's own palette for these SKUs is `primary #DDA7A5`, `accent
#6B2D5C` — neither colour appears anywhere on the real carton, and both SKUs
carry the identical palette despite being a brand and a generic. See Section H.

---

## D. Graphic Signature

`[Observed]` A **straight horizontal boundary** between substrate and colour
field, with the dosage set in a rounded outlined block floating on the colour.
No curves, no waves, no corner badge.

`[Observed]` A photographic image of the capsule itself sits on the colour field —
unusual in this benchmark set, where no other carton depicts its contents on the
front.

`[Observed]` The manufacturer mark is a red handwritten script, bottom right.

---

## E. Layer Order

`[Estimated]` (Medium).

```
white substrate
  → top colour bar (unit count, NDC)
  → main colour field (lower half)
  → dosage block (outlined, on the colour field)
  → capsule photograph (on the colour field)
  → type: brand → ingredient → Rx only → equivalence note → warning → URL
  → manufacturer script [top]
```

---

## F. Typography Character

`[Observed]` — character, not metrics. Families not identified.

- Brand: **lowercase**, light-to-regular weight, widely spaced, by far the
  largest element. Lowercase branding distinguishes this carton from Viagra
  (ALL CAPS) and Kamagra (ALL CAPS); it shares the trait with Cialis, which is
  Title Case.
- Ingredient: lowercase, roughly half the brand's size.
- Dosage: bold, reversed to white.
- Everything else: small, regular.

---

## G. Material Impression

- `[Unknown]` **Not assessable from this source.** A flat label scan carries no
  lighting, so matte versus gloss, foil and embossing cannot be judged. The
  benchmarks' matte-board finding does not transfer to this carton by assumption.

---

## H. Reconstruction Constraints

- `[Unknown]` **Carton proportions.** A flat unfolding shows panel layout, not
  box geometry. Width, height and depth are not derivable from these images.
- `[Unknown]` **Material and finish** — see Section G.
- `[Measured]` **All seven images are 766–776 px on the long edge, against the
  benchmark floor of 1079.** No DailyMed unfolding meets that floor; this is a
  property of the source, not bad luck. After cropping to the front panel the
  usable width is about 240 px — enough for the colour system and the archetype,
  not enough to read small print.
- `[Observed]` **Front-panel identification is a human step.** Automatic
  detection by text orientation was tried and failed: Tesseract reads rotated
  side-panel text as horizontal nonsense (`Jo`, `Is`, `40}`, `0€-6228-2000`), so
  the horizontal and rotated token spans overlap almost completely — 0.055–0.785
  against 0.160–0.957 — and the front panel cannot be separated from them.
- `[Measured]` **The catalogue's palette for these SKUs does not match the
  carton.** `1-min` and `2-min` both carry `primary #DDA7A5`, `accent #6B2D5C`;
  neither appears on the packaging, and an identical palette is assigned to a
  brand and a generic alike. Recorded, not fixed — the palette lives in
  `src/render_manifest.py` and changing it belongs to the pipeline work, not to
  reference collection.
- `[Unknown]` The rear panel and flaps as folded; the unfolding shows all panels
  but not which fold is which.
