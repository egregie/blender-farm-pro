# Design Passport — Aspendos 100 mg (modafinil)

> **Folder:** `25_T1_Modafinil_Generic` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_modafinil_generic_01.jpg`, 1159×809
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**The folder is named for the molecule, not a brand**, which is why a Romanian
modafinil generic belongs here and would not belong in `26_T1_Modvigil`. It is the
smallest accepted file — 1159 px on the long edge against a 1079 floor — and the
only European modafinil carton found anywhere.

---

## A. Design Archetype

`[Observed]` **An almost entirely white carton whose only graphic is a row of
three rounded squares, repeated at two sizes, with the dosage set in a warm red
that appears nowhere else.**

There is no colour field, no stripe, no badge and no curve. The design is carried
by one repeated shape and by the contrast between a cool violet and a single warm
accent. Of everything acquired, this is the most reduced.

---

## B. Content Zones

`[Observed]` — the carton is at three-quarters, so these are approximate.

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Squares (3) | Left of the brand, baseline-aligned | Medium | Violet, rounded corners |
| Brand `ASPENDOS` | Centre-left | Largest | ALL CAPS, letterspaced |
| Dosage `100mg` | Right of the brand, same baseline | Medium | Warm red, no space before `mg` |
| Form `comprimate` | Below the brand | Small | Lower case |
| INN `Modafinil` | Below the form line | Medium-small | Larger than the form line |
| Squares (6, graded) | Upper right | Small | Violet, fading left to right |
| Unit count `30 comprimate` | Below the graded squares | Small | |
| House mark | Lower right | Small | Two-colour |

**The graded row of six squares is a quantity pictogram**, not decoration: it
sits directly above the unit count and its tones step from pale to solid.

**The INN is set larger than the form line**, the same inversion the Cialis
benchmark shows.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and anything beside the carton are counted.** Entries
marked *(not packaging)* are that.

| Role | HEX | Share | Where |
|---|---|---|---|
| Substrate + backdrop | `#D8D8E8` | 47.7% | **Not separated** — both are near-white |
| *(mixed)* | `#A8A8A8` | 45.2% | The carton's shadow side and the surface |
| Brand violet | `#483868` | 3.4% | The squares |
| Ink | `#080808` | 1.6% | Type |

`[Observed]` The dosage red falls below the 1% floor. Eye-read as roughly
`#E8452C` — a warm orange-red, clearly not the violet's complement, and the only
warm value on the carton.

**The mask could not separate board from backdrop here** because both are white.
Any substrate share taken from this file is meaningless; the archetype above is
what the file is good for.

---

## D. Graphic Signature

`[Observed]` **Three rounded violet squares in a row, repeated at a second size
and in graded tone.** That is the entire graphic vocabulary — one shape, two
scales, two roles. Nothing else on the carton is a mark.

`[Observed]` No stripe, no field, no curve, no badge. A candidate for this
template that carries a coloured field is a different design language.

---

## E. Layer Order

`[Estimated]` (Medium)

```
white board
  -> violet squares (both rows)
  -> type: brand -> dosage -> form -> INN -> unit count
  -> house mark [top]
```

Flat by construction — nothing overlaps anything.

---

## F. Typography Character

`[Observed]`

- Brand: regular weight, ALL CAPS, generously letterspaced — not bold, which is
  unusual among the acquired set.
- Dosage: bold, warm red, set tight (`100mg`, no space).
- INN: regular, sentence case, second largest.
- Form line and unit count: light, lower case, smallest.
- Four sizes, and the only bold on the face is the dosage.

---

## G. Material Impression

- `[Estimated]` (Medium) Matte board. The three-quarter view shows a soft edge
  highlight that could be sheen or could be the lighting.
- `[Unknown]` **No braille visible.** For a European pack that is notable — either
  the pack predates the requirement, or the embossing does not read at this
  resolution. Do not conclude either.
- `[Unknown]` No foil or varnish visible.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panel, flaps, the far side panel.
- `[Unknown]` Font families.
- `[Measured]` **Board and backdrop were not separated by the mask.** Colour
  shares from this file describe the frame, not the carton.
- `[Observed]` **Smallest accepted file**, 1159×809. It clears the 1079 floor on
  the long edge and nothing more; small print on the side panel is not legible.
- `[Observed]` Brand substitution by design: the folder is the molecule, and
  Aspendos is one European generic of it, not a catalogue product.
