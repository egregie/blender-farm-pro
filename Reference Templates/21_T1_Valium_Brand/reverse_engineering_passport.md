# Design Passport — Valium Roche 5 mg and 10 mg

> **Folder:** `21_T1_Valium_Brand` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_valium_brand_01.jpg`, 1226×1601
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**The dosage-colour rule, measured rather than eye-read.** Two Valium Roche cartons
at 5 and 10 mg sit one above the other, identical in every respect except one
band — and `reference_measure.py` separated both colours above its 1% floor. This
is the only acquired file where the rule appears as numbers.

A ratiopharm/Teva generic of the same molecule sits above them, which makes the
frame a brand-versus-generic comparison as well.

---

## A. Design Archetype

`[Observed]` **A white carton with a narrow blue bar down the left edge and a
full-width horizontal band across the middle whose COLOUR carries the strength.**

The band is the design. It runs trim to trim, sits at roughly mid-height, and holds
the dosage in bold at its left end. Everything else is black type on white board.
Change the strength and only that band changes.

`[Observed]` The ratiopharm generic above uses the same idea with a different
grammar: a turquoise band, but placed lower, carrying a pictogram and a route
statement rather than the dosage.

---

## B. Content Zones

**Valium Roche** — `[Observed]`

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Blue bar | Flush left, full height | — | Narrow, unbroken |
| Brand + strength `Valium® Roche 5 mg` | Top line | Largest | Brand, house and dose on ONE line |
| Form `Comprimé sécable` | Below the brand | Small-medium | |
| INN `Diazépam` | Below the form line | Medium | |
| Colour band | Full width, mid-height | — | Pink at 5 mg, orange at 10 mg |
| Dosage `5 mg` / `10 mg` | Inside the band, left | Medium | Bold, black on the colour |
| Route `Voie orale` | Below the band, left | Small | |
| Unit count `40 comprimés sécables` | Lower left | Small | With a tablet pictogram |
| House mark `Roche` | Lower right | Medium | Blue hexagon outline |
| Braille | Over the upper white and across the band | — | |

**The dosage appears twice** — once fused into the top line and once inside the
band. Kamagra does the same; the other benchmarks do not.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and every carton in frame are counted together.** Entries
marked *(not packaging)* are backdrop.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#A89878` | 36.9% | The wall behind the cartons |
| Substrate | `#D8D8D8` | 21.1% | Carton board, white |
| Generic turquoise | `#389898` | 11.8% | The ratiopharm band — a different product |
| Neutral | `#585848` | 9.2% | Shading and edges |
| Ink | `#181818` | 6.5% | Type |
| **10 mg orange** | `#D85818` | 5.5% | The strength band on the 10 mg carton |
| **5 mg pink** | `#C868A8` | 4.7% | The strength band on the 5 mg carton |

`[Measured]` **Both strength colours cleared the 1% floor and were separated by the
quantiser.** That makes this the one file in the set where the dosage-colour
mapping is a measurement rather than an eye-read:

| Strength | Band |
|---|---|
| 5 mg | `#C868A8` |
| 10 mg | `#D85818` |

`[Observed]` The Roche blue of the left bar and the hexagon falls below the floor;
eye-read as roughly `#1B4E9B`.

---

## D. Graphic Signature

`[Observed]` **A narrow blue bar flush to the left trim**, running the full height,
unbroken and unmodulated.

`[Observed]` **A full-width horizontal band at mid-height**, square-ended at both
trims. It is not a stripe at the foot of the face — the position is the middle, and
type sits both above and below it.

`[Observed]` **A blue hexagon outline** carrying the house name, lower right. It is
an outline, not a fill, and it is the only enclosed shape on the carton.

---

## E. Layer Order

`[Estimated]` (Medium)

```
white board
  -> blue left bar
  -> strength band (full width, mid-height)
  -> braille embossing (crosses the band)
  -> type: brand line -> form -> INN -> dosage (in band) -> route -> unit count
  -> Roche hexagon [top]
```

---

## F. Typography Character

`[Observed]`

- Brand line: bold, sentence case; brand, house and strength all one size, reading
  as a single phrase.
- Dosage in the band: bold, black on colour — not reversed out.
- Form and INN: regular, sentence case, stepping down in size.
- Route and unit count: light, smallest.
- Four sizes, and the only colour behind type is the band.

---

## G. Material Impression

- `[Estimated]` (High) Matte board on all three cartons.
- `[Observed]` Braille relief on all three.
- `[Unknown]` No foil or varnish visible.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panels, flaps, side panels.
- `[Unknown]` Font families.
- `[Measured]` **37% of the frame is wall.** The two strength colours are still
  trustworthy as VALUES; their shares are not carton shares.
- `[Observed]` Three cartons from two houses. The ratiopharm/Teva box shares the
  molecule and the band idea but not the layout — do not blend the two into one
  description.
- `[Observed]` The photograph is taken slightly from below and the cartons are
  stacked, so the lower two are partly occluded by the one above.
