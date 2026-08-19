# D-1 — the eleven reference faces, measured
> **Superseded for eight of the eleven, 2026-08-18.** An acquisition run replaced
> the reference photograph in every folder except `02_Cialis`,
> `31_Kamagra_Template_Reference` and `32_Viagra_Template_Reference`, and the new
> frames are *different packaging* rather than re-encodes — a different
> manufacturer, market, dosage or pack size in each case. The originals were never
> tracked in git, so nothing on disk reproduces the measurements below.
>
> Six folders were rebuilt against the new frames: `08_Ativan`, `14_Imovane`,
> `15_Xanax`, `23_Lexotanil`, `25_Modafinil_Generic`, `30_Ritalin`.
> `21_Valium_Brand` and `24_Xanax_Pfizer` left the design group — their new frames
> cannot be measured (a blister lying across the printed face; two cartons in one
> shot) — and now take the generic art direction.
>
> **Every figure below for those eight describes the previous reference.** Cialis,
> Kamagra and Viagra are unchanged and their rows remain live. Kept as a record of
> what was measured and why each instrument is built the way it is.


*2026-08-11. `scripts/measure_reference_face.py`, corners in each folder's
`metadata.json`, previews in `02_processing/reference_measurement/`.*

Every reference face is rectified out of its photograph and segmented, so the
design behind it is data rather than prose. Two things came out that change how
D-2 has to be posed.

## The catalogue's carton is not the reference's carton

| SKU | folder | reference aspect | catalogue aspect | corners |
|---|---|---:|---:|---|
| `59-min` | Cialis | 0.629 | 0.455 | good |
| `64-min` | Kamagra | 1.404 | 0.455 | good |
| `74-min` | Viagra | 1.102 | 0.455 | good |
| `135-min` | Ativan | 0.428 | 0.478 | fair |
| `155-min` | Imovane | 0.346 | 0.478 | good |
| `156-min` | Xanax | 0.625 | 0.478 | fair |
| `272-min` | Valium | 0.431 | 0.478 | fair |
| `308-min` | Lexotanil | **2.026** | 0.478 | good |
| `340-min` | Xanax SR | 0.581 | 0.478 | good |
| `344-min` | Modafinil | **0.310** | 0.478 | approximate |
| `404-min` | Ritalin | 0.508 | 0.455 | fair |

The catalogue gives all eleven a face between 0.455 and 0.478. The photographs
span **0.310 to 2.026** — a 6.5× range. Lexotanil is a tall narrow box, Kamagra
and Viagra are portrait, and five are flatter than the catalogue thinks.

So "1:1 with the reference" cannot mean copying the layout into face
coordinates and rendering it: on `308-min` that would map a portrait design onto
a landscape face and produce something the reference does not contain. **D-2 has
to decide the mapping explicitly** — stretch the design to our face, preserve its
proportions inside our face, or change the carton's dimensions to the reference's
where the passport allows it. The measurement records both aspects and imposes
neither.

## Not one catalogue palette is the carton's colour

| SKU | measured brand field | share | catalogue primary | substrate | share |
|---|---|---:|---|---|---:|
| `59-min` | `#3F5A0A` olive | 29.7% | `#006A4E` | `#DDD1B9` | 38.6% |
| `64-min` | `#002F26` teal | 20.3% | `#6B2D5C` | `#00463B` **teal** | 34.0% |
| `74-min` | `#34376D` navy | 9.7% | `#003366` | `#DDDEDB` | 76.3% |
| `135-min` | `#09377E` blue | 11.6% | `#003366` | `#C2C2B6` | 77.0% |
| `155-min` | `#683E6C` purple | 22.6% | `#003366` | `#AFAEA7` | 58.3% |
| `156-min` | `#2C1F2A` | 16.2% | `#003366` | `#E8DBB2` | 40.2% |
| `272-min` | `#C16AA0` pink | 17.1% | `#003366` | `#C9C5C0` | 46.1% |
| `308-min` | `#55A096` cyan | 8.2% | `#003366` | `#8AB663` **lime** | 78.5% |
| `340-min` | `#E53BBA` magenta | 4.5% | `#003366` | `#FAF7F5` | 52.7% |
| `344-min` | `#9C9796` | 16.5% | `#DDA7A5` | `#A09C9D` | 39.7% |
| `404-min` | `#5D5C5A` | 2.2% | `#DDA7A5` | `#817F78` | 79.1% |

Six SKU carry the same catalogue pair. The cartons carry olive, teal, navy,
purple, pink, cyan and magenta.

**Two of the eleven have a coloured board**: Kamagra's teal `#00463B` and
Lexotanil's lime `#8AB663`. "White carton body always" is not a rule these
cartons follow, and it fails inside the sample rather than at its edge.

`404-min` (Ritalin/Motiron) has no colour field at all — its 2.2% "brand" is the
red warning triangle. Cream board, navy type, orange dosage. A design language
worth naming, because the current renderer would give it a stripe and a badge it
does not have.

## What the designs are made of

Repeated devices across the sample, which is what a spec format has to cover:

- **Curved colour fields** — Cialis (olive S-curves), Imovane (purple sweep),
  Ativan (blue swoosh), Kamagra (five parallel curved rules). Four of eleven.
  Conic arcs, not free-form paths: the boundaries are large ellipse sections.
- **Dosage reversed out of a colour block** — Cialis, Ativan, Imovane, Lexotanil.
  The dosage is not just coloured type; it sits on a filled rectangle.
- **A colour block at the face edge** — Xanax and Xanax SR both put a solid block
  hard against the right edge, half off the face.
- **Dosage-coded colour, observed in the wild.** Valium Roche 5 mg has a pink
  band and 10 mg an orange one, same design otherwise, in one photograph. Xanax
  0,25 mg is magenta and 0,50 mg purple, in another. This is the owner's own
  dosage-colour rule appearing in the reference material rather than being
  imposed on it.

## Honest limits of this pass

- **Corners are hand-set.** One is `approximate` (`344-min`, a steep camera angle
  that four passes did not fully straighten) and four are `fair` — usually a
  clipped bottom edge. Each carries its own note in `metadata.json`. Anything
  tracing precise layout should re-corner the `fair` and `approximate` ones
  first.
- **`156-min`'s face is ~450x280 px in its source photograph.** Enough for
  colour, thin for geometry.
- **`type` is blank where no dark cluster separated.** Not a claim that the
  carton has no type — the clustering did not isolate it. Nothing downstream
  needs it: type comes from the manifest's strings.
- **`64-min` (Kamagra) is not European packaging** — "Sildenafil Citrate Tablets
  IP" is the Indian Pharmacopoeia. It sits in a sample otherwise chosen under an
  EU-only constraint.
- The reference for `135-min` is Lorazepam Orion, for `155-min` Zopiclone
  Actavis, for `344-min` Aspendos and for `404-min` Motiron — ingredient-class
  references rather than the brand named in the catalogue, as the acquisition log
  already records.
