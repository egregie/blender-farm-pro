# Design Passport — Lorazepam Orion 1 mg

> **Folder:** `08_T1_Ativan` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_ativan_01.jpg`, 1280x960
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**This is a brand substitution and the passport says so throughout.** The folder
is named for Ativan; the carton is Orion Pharma's generic lorazepam. Same molecule,
a different design language, and nothing here should be read as Ativan's artwork.

---

## A. Design Archetype

`[Observed]` **A white carton crossed by a single blue swoosh, with a foil band
along the top edge and the dosage reversed out of a coloured badge on the brand
line.**

The board stays white and colour arrives in exactly three places: a metallic strip
along the very top edge, a broad blue curve across the lower third, and a green
rectangle carrying the strength. Everything printed sits in the white corridor
between the strip and the swoosh.

Structurally this is the closest of all the acquired references to what this
project's own renderer already builds — white body, accent low on the face, a
coloured dosage block — and unlike the curved-field archetypes of the Cialis and
Kamagra benchmarks.

---

## B. Content Zones

Approximate placement in thirds of the front face. `[Observed]` throughout.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Unit count `30 tabletek` | Upper left | Small | Sits ABOVE the brand |
| Brand `Lorazepam Orion` | Upper centre-left | Largest element | Molecule first, house second |
| Dosage `1 mg` | Right of the brand, same baseline | Medium | White on a solid green rectangle |
| INN `Lorazepamum` | Below the brand | Small, italic | Latin genitive, the Polish convention |
| Form `tabletki` | Below the INN | Small | |
| Braille | Across the middle right | — | Embossing over the white board |
| Manufacturer `ORION PHARMA` | Lower right | Medium | Below the swoosh |

**The unit count is the top line of the face**, above the brand. Of the three
benchmarks only Kamagra puts anything above its brand, and there it is the INN.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **Read the shares with the
caveat that the tool masks by luma difference from the frame corner, not by an
alpha channel — these photographs have none — so the background and anything
lying beside the carton are counted.** Entries marked *(not packaging)* are that,
and the remaining shares are diluted by their area.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#B8A898` | 47.8% | Table and background |
| Substrate | `#D8D8C8` | 20.3% | Carton board, off-white |
| *(mixed)* | `#888878` | 16.4% | Blister foil below the carton, plus shading |
| Brand blue | `#083888` | 5.6% | Top foil stripe and lower swoosh |
| Neutral | `#585858` | 6.0% | Edges and side panel |

`[Observed]` The dosage badge is a saturated mid-green the quantiser did not reach
at 1% — small in area, load-bearing in the design. Eye-read as roughly `#0A7A4A`.

**The blue does two jobs in two finishes**: the top strip is metallic foil and
carries a specular highlight; the lower swoosh is flat ink. Rendering both as one
material loses the top edge.

---

## D. Graphic Signature

`[Observed]` **One broad blue curve rising left to right across the lower third**,
upper edge concave. It does not touch the top strip and does not wrap onto the
visible side panel.

`[Observed]` **A foil band along the top edge**, full width, distinctly metallic —
the only reflective element on the carton.

`[Observed]` The green dosage badge is a plain square-cornered rectangle set tight
to the brand's baseline rather than floating in a corner.

---

## E. Layer Order

`[Estimated]` (Medium) — inferred from occlusion.

```
white board
  -> blue swoosh (lower third)
  -> top foil strip (separate finish)
  -> green dosage badge
  -> braille embossing (relief, not ink)
  -> type: unit count -> brand -> dosage -> INN -> form
  -> ORION PHARMA mark [top]
```

---

## F. Typography Character

`[Observed]` — character, not metrics. Families not identified.

- Brand: bold, sentence case, by far the largest string; molecule and house name
  at the same weight and size, reading as one phrase.
- Dosage: bold, reversed out of green.
- INN: italic, light, noticeably smaller.
- Unit count and form line: regular, small, matched to each other.
- Four sizes; hierarchy carried by size alone except the dosage, which uses reversal.

---

## G. Material Impression

- `[Estimated]` (High) Matte board across the printed white.
- `[Observed]` Metallic foil on the top strip — a visible specular band.
- `[Observed]` Physical braille relief.
- `[Unknown]` Whether the blue swoosh carries varnish.

---

## H. Reconstruction Constraints

- `[Unknown]` **Everything except this one front view.** No rear panel, no flaps,
  no opened pack. The visible side panel carries a barcode and small print too
  small to read at this resolution.
- `[Unknown]` Font families.
- `[Measured]` **The colour shares include the table and a blister strip.** The
  carton's own palette is white board, one blue, one green; the numbers above are
  not usable as area targets without re-masking.
- `[Observed]` **Brand substitution.** Orion Pharma's generic, not Ativan. The
  `1 mg / 30` happens to match the catalogue, which is coincidence rather than
  correspondence.
- `[Observed]` OCR returns nothing at `--psm 3` on this file — dark-on-white at
  low contrast, carton slightly tilted. Every string above is eye-read.
