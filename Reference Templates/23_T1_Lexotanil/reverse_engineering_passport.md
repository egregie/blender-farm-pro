# Design Passport — Lexomil Roche 6 mg (bromazepam)

> **Folder:** `23_T1_Lexotanil` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_lexotanil_01.jpg`, 1850×1051
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**Not a substitution — a local name.** Lexomil is what Roche calls Lexotanil in
France. The molecule, the house and the product are the same.

The frame also carries the `Bromazépam arrow` generic beside it, and the two
disagree interestingly: same colour, opposite grammar.

---

## A. Design Archetype

`[Observed]` **A carton whose BOARD is the brand colour — a strong yellow-green
over the whole face — with a narrow turquoise band carrying the strength and
everything else set as black type directly on the green.**

This is the inverse of the white-body archetype that dominates the rest of the set.
There is no white substrate to speak of: the colour is the ground, not an accent
applied to one.

`[Observed]` The `Bromazépam arrow` generic beside it uses the SAME green but
splits the face into a cream upper third and a green lower two thirds, with the
dosage huge in white reversed out of the green and a field of blue dots below it.
Same colour, opposite structure.

---

## B. Content Zones

**Lexomil Roche** — `[Observed]`

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Blue bar | Flush left, full height | — | Narrow, as on the Valium pack |
| Brand `Lexomil® Roche` | Top line | Largest | Brand and house on one line |
| Form `Comprimé-Baguette, comprimé quadrisécable` | Below the brand, two lines | Small | The longest string on the face |
| INN `Bromazépam` | Below the form | Medium | |
| Turquoise band | Full width, upper-middle | — | Narrow |
| Dosage `6 mg` | Inside the band, left | Medium | Bold, black on turquoise |
| Route `Voie orale` | Below the band | Small | Bold |
| Composition block | Centre, four lines | Small | Rare — the other cartons do not print this on the face |
| Unit count `30 comprimés quadrisécables` | Lower left | Small | |
| House mark `Roche` | Lower right | Medium | Blue hexagon |

**A composition block on the front face** — `Composition : Bromazépam : 6 mg /
Excipients q.s.p. / ... / Lactose` — is unique in the acquired set. Every other
carton keeps that on a side panel or a leaflet.

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and every carton in frame are counted together.** Entries
marked *(not packaging)* are backdrop.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#D8C8A8` | 41.4% | Table and papers behind |
| **Brand green** | `#98B838` | 27.9% | The board of BOTH cartons |
| *(mixed)* | `#988878` | 16.7% | Shading and edges |
| Ink | `#182818` | 3.2% | Type |
| Generic blue | `#286898` | 3.1% | The dots and type of the arrow pack |
| Accent turquoise | `#58A898` | 1.6% | The dosage band on the Lexomil carton |

**The brand green is the substrate here**, at 28% of a frame that is 41% table.
Renormalised over the cartons alone it is the majority value — the opposite
relationship to every white-bodied carton in this set.

---

## D. Graphic Signature

`[Observed]` **A green ground with a narrow turquoise band across it.** Two greens
doing different jobs: the board's yellow-green and the band's blue-green. They are
close enough that a renderer collapsing them to one loses the band.

`[Observed]` **A narrow blue bar flush left** and **a blue hexagon lower right** —
the same two Roche house marks as the Valium carton, on a completely different
ground. That is the house signature, independent of product colour.

`[Observed]` On the generic: **a field of blue ellipses** arranged in a loose grid,
occupying the lower third. Purely decorative and unlike anything else acquired.

---

## E. Layer Order

`[Estimated]` (Medium)

```
green board
  -> blue left bar
  -> turquoise dosage band
  -> type: brand -> form -> INN -> dosage -> route -> composition -> unit count
  -> Roche hexagon [top]
```

---

## F. Typography Character

`[Observed]`

- Brand: bold, sentence case, largest; brand and house one size.
- Form line: regular, sentence case, wraps to two lines — the longest string.
- INN: regular, slightly larger than the form line.
- Dosage: bold, black on turquoise.
- Composition block: light, four short lines, the smallest type on the face.
- Five sizes — the widest hierarchy of any acquired carton, and all of it black on
  colour with no reversal anywhere.

---

## G. Material Impression

- `[Estimated]` (High) Matte board; the green shows no sheen.
- `[Observed]` Braille on the adjacent generic. **On the Lexomil carton itself the
  braille is not resolvable** at this size and angle — do not conclude it is absent.
- `[Unknown]` No foil or varnish visible.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panels, flaps, side panels.
- `[Unknown]` Font families.
- `[Measured]` **41% of the frame is table.** The green's share needs renormalising
  before use as a target.
- `[Observed]` Two pill tubes stand either side of the cartons. They are primary
  packaging of the same products and are NOT the object this project renders.
- `[Observed]` The two cartons share a colour and contradict each other on
  structure. Blending them into one description would invent a carton that exists
  in neither.
