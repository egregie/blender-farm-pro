# Design Passport — Xanax 0,25 / 0,50 mg (Pfizer) and four alprazolam generics

> **Folder:** `15_T1_Xanax` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_xanax_01.jpg` 1795×1722 · `raw_xanax_02.jpg` 4160×2340
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**Two files with different jobs.** `raw_xanax_01` is the comparative frame: six
French cartons stacked, the real Pfizer XANAX among them at two strengths.
`raw_xanax_02` is the measurable one: a single Italian Alprazolam EG carton
flat-on at 4160×2340, the largest alprazolam face acquired anywhere here.

**This folder is the project's clearest evidence for the dosage-colour rule.** The
same brand, the same layout, the same everything — and the colour block changes
with the strength.

---

## A. Design Archetype

`[Observed]` **Xanax: a white carton with a deep navy field down the left third,
crossed by one pale horizontal band, and a solid colour block flush to the right
edge that carries the strength by its COLOUR rather than by any number.**

The navy field holds the house oval reversed out in white. The right-edge block is
not a badge floating in a corner — it runs to the trim and is the only saturated
colour on the white portion.

`[Observed]` **Alprazolam EG: a teal field down the left with a large letterform
used as a watermark inside it, and a thin outlined dosage box top right.** A
different archetype entirely from the Pfizer pack, which is the point of holding
both files.

---

## B. Content Zones

**Xanax (from `raw_xanax_01`)** — `[Observed]`

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| House oval `Pfizer` | Left field, upper | Medium | White on navy |
| Brand `XANAX®` | Upper centre-right | Largest | ALL CAPS |
| Dosage `0,25 mg` / `0,50 mg` | Below the brand, left-aligned to it | Medium | Set in the strength colour |
| INN `ALPRAZOLAM` | Below the dosage | Small | ALL CAPS, lighter weight |
| Unit count `30 comprimés sécables` | Lower left | Small | |
| Colour block | Flush right, mid-height | — | Magenta at 0,25 mg, violet at 0,50 mg |
| Braille | Across the middle | — | Over the white |

**Alprazolam EG (from `raw_xanax_02`)** — `[Observed]`

| Content | Zone | Notes |
|---|---|---|
| Brand `Alprazolam EG®` | Upper left, crossing out of the teal field | Serif, unusually |
| Dosage `0,25 mg` | Upper right, inside a thin outlined box | |
| Form `compresse` / `Medicinale equivalente` / `USO ORALE` | Right column, stacked, rules between | |
| Tablet pictogram + `20 compresse` | Lower right | |
| Watermark `A` | Inside the teal field, very large | Tone-on-tone, not an outline |

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and anything beside the carton are counted.** Entries
marked *(not packaging)* are that.

| Role | HEX | Share | Where |
|---|---|---|---|
| *(not packaging)* | `#E8D8B8` | 61.1% | Wall and desk behind the stack |
| *(mixed)* | `#A89888` | 16.6% | Shading, edges, carton sides |
| Pfizer navy | `#182848` | 13.3% | The left field of the three Xanax cartons |
| Pale blue | `#4898A8` | 2.4% | The horizontal band on the Xanax face |

`[Observed]` **The two strength colours are the load-bearing values and both sit
below the 1% quantiser floor** because each block is small. Eye-read: magenta at
0,25 mg, roughly `#C2185B`; violet at 0,50 mg, roughly `#5B2D8E`.

**That pair is the most reusable thing in this folder.** Two cartons identical in
every other respect, photographed together, differing only in that block. It is
the dosage-colour rule demonstrated rather than asserted.

---

## D. Graphic Signature

`[Observed]` **A navy field down the left third with a straight vertical
boundary** — no curve anywhere on the Pfizer pack. Movement comes from one thin
horizontal band, not from a swoosh.

`[Observed]` **A colour block flush to the right trim**, full bleed on that edge.

`[Observed]` On the EG carton, **a letterform used as a large tone-on-tone
watermark** inside the colour field — the initial of the house, at perhaps six
times the type size, deliberately low-contrast.

---

## E. Layer Order

`[Estimated]` (Medium)

```
white board
  -> left colour field (navy on Xanax, teal on EG)
  -> watermark letterform (EG only, inside the field)
  -> horizontal band (Xanax only)
  -> right-edge strength block (Xanax) / outlined dosage box (EG)
  -> braille embossing
  -> type: house -> brand -> dosage -> INN -> unit count [top]
```

---

## F. Typography Character

`[Observed]`

- Xanax brand: bold, ALL CAPS, widest string on the face.
- Xanax dosage: bold, set IN the strength colour rather than reversed out — so the
  colour appears twice, as type and as block.
- INN: regular, ALL CAPS, distinctly lighter than the brand.
- EG brand: a **serif** face, which none of the other acquired cartons uses.
- Three sizes on the Xanax face, four on the EG.

---

## G. Material Impression

- `[Estimated]` (High) Matte board on all six cartons.
- `[Observed]` Braille relief on every one.
- `[Unknown]` No foil or varnish visible on any.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panels, flaps, side panels beyond a sliver.
- `[Unknown]` Font families, including the EG serif.
- `[Measured]` **61% of `raw_xanax_01` is wall and desk.** Shares need
  renormalising over the cartons before use.
- `[Observed]` `raw_xanax_01` is a stack: the cartons occlude one another and no
  single front face is unobstructed edge to edge. For measuring a face, use
  `raw_xanax_02`; for the colour rule, use `raw_xanax_01`.
- `[Observed]` The strengths differ between the two files (0,50 and 0,25 mg on the
  Xanax pair, 0,25 mg on the EG) and neither matches the catalogue's `0.5mg / 30`
  exactly in count. The design is what carries over.
