# Design Passport — Ritalin 10 mg (Novartis) among eight methylphenidate cartons

> **Folder:** `30_T1_Ritalin` | **Template:** T1 | **Built:** 2026-08-10
> **Source:** `raw_ritalin_01.jpg` 4000×2667 · `raw_ritalin_02.jpg` 2348×1086
> **Measurements:** `scripts/reference_measure.py`

**What this document is for.** Reconstructing the *design*. The camera is not
reconstructed: the render chooses its own angle. Content zones are approximate by
intent — the owner's criterion is the design, not pixel coordinates.

**The most useful acquisition in the set, and not because of any one carton.**
`raw_ritalin_01` holds eight cartons of the same molecule at the same strength from
SEVEN different houses — Novartis, Hexal, TAD, 1A Pharma, UCB, Medice, and Medice
again in a retard version. Put side by side they separate what is convention from
what is brand, which is the question a design passport has to answer and a single
box cannot.

`raw_ritalin_02` is a single Nordic carton at full size, for measuring one face.

---

## A. Design Archetype

`[Observed]` **There is no single archetype here, and that is the finding.** Eight
cartons for one molecule, and the constants across all of them are narrow:

- white or near-white board on every one;
- the molecule name printed in full on every one, in the same weight as or heavier
  than the brand;
- a coloured element carrying the strength on most, but placed differently on each;
- the pack size stated as a German `N1` / `N2` code on all of them.

What varies: whether colour appears as a corner wedge (Ritalin), a full band
(Equasym), a horizontal rule (Medikinet), a left field (TAD), or barely at all
(1A Pharma). **The convention is white board plus one colour; the brand is where
that colour goes.**

`[Observed]` `raw_ritalin_02` — the Nordic Motiron — is a fourth arrangement again:
cream board, blue type, and a large red-and-amber house graphic bleeding off the
right edge.

---

## B. Content Zones

**Ritalin (Novartis)** — `[Observed]` from `raw_ritalin_01`

| Content | Zone | Relative size | Notes |
|---|---|---|---|
| Brand `Ritalin®` | Upper left | Largest | Sentence case |
| Dosage `10 mg` | Right of the brand, same baseline | Medium | |
| Form `Tabletten` | Below the brand | Medium | |
| Maker `Novartis Pharma GmbH` | Below the form | Small | With a web address |
| Orange field | Right third | — | Full height, holds the small print |
| Unit count `20 Tabletten/N1` | Below the form line | Small | |
| Braille | Across the upper face | — | |

**Motiron (Sandoz)** — `[Observed]` from `raw_ritalin_02`

| Content | Zone | Notes |
|---|---|---|
| Brand `Motiron®` + `10 mg` | Top line | Dose in amber, brand in blue |
| INN `methylphenidathydrochlorid` | Below the brand | One long word, German-style compound |
| Unit count `30 tabletter` | Below the INN | Bold numeral |
| Article number `Vnr 01 39 78` | Upper right | Nordic retail code |
| Warning triangle | Centre | Red equilateral, filled outline |
| Tablet pictogram | Right of the triangle | Blue outline, scored |
| House mark `SANDOZ` | Lower left | With a triangle glyph |

---

## C. Colour System

`[Measured]` by `scripts/reference_measure.py`. **The tool masks by luma
difference from the frame corner, not by an alpha channel — these photographs have
none — so the background and every carton in frame are counted together.** Entries
marked *(not packaging)* are backdrop.

| Role | HEX | Share | Where |
|---|---|---|---|
| Board + backdrop | `#C8C8C8` | 58.9% | Eight cartons and the pale ground, not separated |
| *(mixed)* | `#988888` | 13.9% | Shading between boxes |
| Brightest board | `#F8F8F8` | 8.6% | The faces catching most light |
| Blues | `#081868` | 4.5% | Hexal, TAD and 1A Pharma type |
| Medikinet mauve | `#785868` | 4.5% | |
| Medikinet retard green | `#083818` | 4.0% | |
| **Ritalin orange** | `#984808` | 2.3% | The only warm value in the frame |

**Seven houses, and the palette measures as one board colour plus five brand
colours.** The Ritalin orange is the smallest of them and the only warm one, which
is why it reads as the brand of the group even at 2.3%.

`[Observed]` For `raw_ritalin_02` the mask inverts — the carton fills the frame, so
the corner it anchors on is board rather than backdrop and the shares describe what
DIFFERS from the board: `#480808` 33.7% and `#885818` 33.8% are the Sandoz corner
graphic, `#081848` 12.9% the blue type. Read as "how much of the face is not plain
board", not as a palette.

---

## D. Graphic Signature

`[Observed]` **No shared signature — that is what eight cartons for one molecule
demonstrate.** Ritalin uses a full-height orange field on the right third; Equasym
a full-width band; Medikinet a horizontal rule with the brand straddling it; TAD a
left field with a curved boundary; 1A Pharma almost nothing but a red logo block.

`[Observed]` The one recurring device across houses is **a coloured area sized to
hold the small print**, rather than a decorative mark. None of these cartons has a
pictorial logo on the front face.

`[Observed]` Motiron: **a large house graphic bleeding off the right edge**, amber
on dark red, with the house name repeated as a tiled watermark inside it.

---

## E. Layer Order

`[Estimated]` (Medium), for the Ritalin carton:

```
white board
  -> orange right field
  -> braille embossing
  -> type: brand -> dosage -> form -> maker -> unit count
  -> small print inside the orange field [top]
```

---

## F. Typography Character

`[Observed]`

- Every one of the eight sets the molecule name in full, and on five of them it is
  as large as or larger than the brand. That is a regulatory convention, not a
  design choice, and it is the strongest constant in the group.
- Ritalin brand: bold, sentence case, largest on its face.
- Dosage: bold on all eight, and on six of them it is the second-largest string.
- Small print: light, and always inside or beside the coloured area.
- Motiron: brand bold blue, dose bold amber — two colours in one line, which none
  of the German cartons does.

---

## G. Material Impression

- `[Estimated]` (High) Matte board on all nine cartons across both files.
- `[Observed]` Braille on several of the German cartons and on the Motiron.
- `[Unknown]` No foil or varnish visible on any.

---

## H. Reconstruction Constraints

- `[Unknown]` Rear panels, flaps, most side panels.
- `[Unknown]` Font families.
- `[Measured]` **Board and backdrop were not separated in `raw_ritalin_01`**, and
  in `raw_ritalin_02` the mask inverts entirely. Neither file yields carton area
  shares directly.
- `[Observed]` The eight cartons in `raw_ritalin_01` are stacked at angles and
  several are partly occluded. Only three faces are unobstructed edge to edge —
  Medikinet retard, Equasym and Ritalin.
- `[Observed]` `raw_ritalin_02` is a methylphenidate generic under a Nordic brand,
  not Ritalin. It is here for the single measurable face, not for the brand.
- `[Observed]` Two of the eight are `retard` / extended-release formulations and
  carry extra type because of it. Do not average their layout with the plain ones.
