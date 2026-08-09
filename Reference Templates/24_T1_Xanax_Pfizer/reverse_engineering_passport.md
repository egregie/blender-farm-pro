# Design Passport — Xanax SR 0,5 mg (Pfizer)

> **Folder:** `24_T1_Xanax_Pfizer` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_xanax_pfizer_01.jpg`, 3264×2448
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**The sharpest single front face in the whole acquired set**, photographed flat-on
from above. Where `15_T1_Xanax` holds the comparative frame, this is the one to
measure a face on. It is also the Pfizer brand rather than a generic.

---

## A. Design Archetype

`[Observed]` **A white carton with a deep blue field down the left third and a
saturated magenta block flush to the right edge — the same architecture as the
plain Xanax in `15_T1_Xanax`, at a different strength and in a different market.**

Two markets, one design system: the navy field carrying the house oval, a pale
horizontal band, and a strength block bleeding off the right trim. That the Polish
SR pack and the French immediate-release packs share it is worth more than either
alone — it separates house style from local artwork.

---

## B. Content Zones

`[Observed]` throughout; the face is flat-on so these are unusually reliable.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| House oval `Pfizer` | Left field, vertically centred | Medium | White on blue |
| Brand `XANAX® SR` | Upper right of centre | Largest | ALL CAPS, the `SR` set close |
| Dosage `0,5 mg` | Below the brand, left-aligned to it | Medium | Magenta type |
| INN `ALPRAZOLAMUM` | Right of the dosage, same baseline | Small | Latin, ALL CAPS |
| Form `Tabletki o przedłużonym uwalnianiu` | Lower centre | Small | Two words wide |
| Unit count `30 tabletek` | Directly below the form line | Small | |
| Magenta block | Flush right, upper half | — | Full bleed on that edge |
| Braille | Across the middle, over the white | — | Six cells visible |

**The dosage and the INN share a baseline**, dosage left in colour, INN right in
black. Of the three benchmarks only Cialis does that, and there both are black.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and anything beside the carton are counted.** Entries
marked *(not packaging)* are that.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#282828` | 53.5% | The dark wooden table |
| Substrate | `#F8F8F8` | 25.9% | Carton board, white |
| *(not packaging)* | `#686868` | 13.4% | Blister foil and a coin |
| Neutral | `#C8C8C8` | 3.8% | Shading on the board |

`[Observed]` **Both brand colours fall below the 1% floor** — the blue field is
narrow and the magenta block small. Eye-read: field roughly `#1D3C78`, block
roughly `#D6006E`.

**More than half the measured area is a table.** This frame is excellent for
geometry and poor for colour shares; the two do not have to come from the same
image.

---

## D. Graphic Signature

`[Observed]` **A blue field down the left third, straight-edged**, holding the
house oval. No curve on this carton at all.

`[Observed]` **A pale blue horizontal band** separating the field from the white,
narrow, running the full width.

`[Observed]` **A magenta block flush to the right trim**, occupying roughly the
upper half of that edge — full bleed, not inset.

---

## E. Layer Order

`[Estimated]` (High — the flat-on view makes occlusion unambiguous)

```
white board
  -> blue left field
  -> pale blue horizontal band
  -> magenta right-edge block
  -> braille embossing
  -> type: Pfizer oval -> brand -> dosage -> INN -> form -> unit count [top]
```

---

## F. Typography Character

`[Observed]`

- Brand: bold, ALL CAPS, largest; the `SR` suffix at the same size, not superscript.
- Dosage: bold, magenta, the only coloured type on the face.
- INN: regular, ALL CAPS, roughly half the brand's height.
- Form line: regular, sentence case, the longest string and the smallest type.
- Unit count: regular, same size as the form line.
- Four sizes; the only colour in the type is the dosage, which ties it to the block.

---

## G. Material Impression

- `[Estimated]` (High) Matte board; the flat-on light shows no specular anywhere.
- `[Observed]` Braille relief, six cells, over plain white.
- `[Unknown]` No foil or varnish visible.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panel, side panels, flaps — the view is directly overhead.
- `[Unknown]` Font families.
- `[Measured]` **53% of the frame is table and 13% is loose blisters and a coin.**
  Colour shares from this file are not carton shares.
- `[Observed]` Blisters and a 1-złoty coin lie beside the carton. The coin is a
  scale reference for whoever photographed it and is not packaging.
- `[Observed]` The `SR` (sustained release) formulation is a different product
  from the plain Xanax in `15_T1_Xanax`; the two share a design system, not a SKU.
