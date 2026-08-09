# Design Passport — Zopiclone Actavis 5 mg

> **Folder:** `14_T1_Imovane` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_imovane_01.jpg`, 1280x960
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**A brand substitution, and a strength substitution too.** The folder is named for
Imovane; the carton is Actavis's generic zopiclone at 5 mg where the catalogue
lists 7.5 mg.

---

## A. Design Archetype

`[Observed]` **A white carton with a saturated colour field down its LEFT EDGE,
from which a grey rule and a white swoosh sweep right across the face.**

The colour is neither a bottom stripe nor a corner badge: it is a vertical field
occupying roughly the left fifth, and the movement runs horizontally out of it.
The house mark sits inside that field reversed out in white; everything else sits
on the board to its right.

A different organising principle again from the three benchmarks — closest to
Kamagra in that a solid field is part of the composition, but rotated ninety
degrees.

---

## B. Content Zones

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| House mark `actavis` | Upper left, INSIDE the colour field | Medium | White on purple, lower case |
| Article number `Vnr 45 48 68` | Upper right | Small | Nordic retail code |
| Brand `Zopiclone Actavis` | Centre, aligned to the swoosh | Largest | Molecule then house |
| Dosage `5` + `mg` | Fused to the end of the brand line | Medium | Numeral reversed out of a blue block; `mg` blue on white |
| INN `zopiclon.` | Directly below the brand | Small | Lower case, terminal full stop |
| Warning triangle | Below the INN, left | Small | Red equilateral outline |
| Unit count `10 tabletter` | Lower right | Small-medium | |
| Braille | Full width, across the middle | — | Overlaps BOTH the purple field and the board |

**The dosage numeral and its unit are split across two treatments** — `5` reversed
out of blue, `mg` set in blue on white. All three benchmarks keep the dosage as one
object.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **Read the shares with the
caveat that the tool masks by luma difference from the frame corner, not by an
alpha channel — these photographs have none — so the background and anything
lying beside the carton are counted.** Entries marked *(not packaging)* are that,
and the remaining shares are diluted by their area.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#A8A8A8` | 76.8% | The grey studio backdrop |
| Brand purple | `#683868` | 14.4% | The left-edge field |
| Neutral | `#787878` | 4.8% | The grey rule and shading |
| Ink | `#181818` | 2.4% | Type |

`[Observed]` Two colours the quantiser did not reach at 1%: the dosage block's
blue, roughly `#1E6FC8`, and the warning triangle's red, roughly `#D32F2F`. Both
are small in area and load-bearing.

**The backdrop at 77% is the honest reading of this frame**, not a defect in the
carton: the box is small and centred with generous margins. Any area target from
this table must be renormalised over the carton alone.

---

## D. Graphic Signature

`[Observed]` **A purple field down the left edge with a curved right boundary**,
out of which a mid-grey rule and a white swoosh sweep right and taper. The three
edges are concentric, reading as one gesture rather than three elements.

`[Observed]` **A red equilateral warning triangle**, outline only, no fill — the
Nordic driving-impairment mark. Regulatory rather than decorative, and its position
is stable across Nordic packs.

`[Observed]` Braille runs the full width and crosses the purple/white boundary, so
the embossing is applied after printing and ignores the artwork.

---

## E. Layer Order

`[Estimated]` (Medium) — inferred from occlusion.

```
white board
  -> purple left field
  -> grey rule, then white swoosh (both over the field's right edge)
  -> blue dosage block
  -> braille embossing (relief, crosses everything)
  -> type: house mark -> Vnr -> brand -> dosage -> INN -> unit count
  -> red warning triangle [top]
```

---

## F. Typography Character

`[Observed]`

- Brand: bold, sentence case, largest string, set on one line with the dosage.
- Dosage numeral: bold, reversed out; `mg` the same size in blue.
- INN: light, lower case, about half the brand's size, terminal full stop.
- Unit count: medium, lower case.
- House mark: bold lower case, white on purple, its own lockup.
- Four sizes; the hierarchy leans on colour and reversal more than on size.

---

## G. Material Impression

- `[Estimated]` (High) Matte board throughout; no specular anywhere on the face.
- `[Observed]` Physical braille relief across the full width.
- `[Unknown]` No foil, hologram or spot varnish visible. Absence in one frame is
  not evidence of absence on the carton.

---

## H. Reconstruction Constraints

- `[Unknown]` **Everything except this one front view.**
- `[Unknown]` Font families.
- `[Measured]` **77% of the measured area is backdrop.** The shares are unusable
  as area targets without re-masking to the carton.
- `[Observed]` **Brand AND strength substitution.** Actavis generic at 5 mg
  against a catalogue Imovane at 7.5 mg.
- `[Measured]` OCR at `--psm 3` recovers `Vnr 45 48 68`, `Zopiclone Actavis`,
  `zopiclon.` and `10 tabletter`, independently confirming the brand line, the
  article number and the unit count. It does not recover the dosage block or the
  house mark — both reversed out, which the recogniser handles poorly.
