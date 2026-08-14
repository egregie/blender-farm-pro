# D-2 — the design-spec format, and what it scores

*2026-08-11. `scripts/fit_design_spec.py`, one `design_spec.json` per template
folder, previews in `02_processing/reference_measurement/*.spec.png`.*

## The mapping decision, taken

The reference cartons are not the catalogue's cartons — D-1 measured aspects from
0.310 to 2.026 against a catalogue that gives all eleven 0.455–0.478. **The
carton is built in the reference's proportions.** Anything else stops being 1:1:
mapping Lexotanil's portrait design onto a landscape face produces a layout the
reference does not contain.

This needs no new mechanism. `reshape_to_art_direction()` already builds a box
whose scene geometry differs from `passport_dimensions`, and already keeps the
real measurements separate for printing. For the design group the target aspect
comes from `design_spec.face_aspect` instead of the per-template constant.

## The format

```
substrate      one colour, the board
fields[]       role, fill, coverage_pct
  parts[]      area_pct, smoothness, outline (u,v in 0..1 of the FACE)
```

**Outlines, not conics.** The plan called for conics, because the Cialis fields
are arcs of large ellipses. Then the sample answered: four of the eleven designs
are built on curves, Lexotanil's bands are straight, Kamagra's transition is five
parallel rules, and Ritalin has no colour field at all. One primitive has to
carry all of them. A polygon approximates a conic to whatever accuracy is asked;
a conic cannot carry a rectangle without a special case. `smoothness` — the share
of vertices turning less than 25° — is recorded per part so D-4 fits curves where
the source curves and builds straight edges where it does not. It reads 0.68 on
the Cialis olive band and 0.00 on its dosage block, which is exactly the
distinction it exists to make.

## Verification is a number

The spec is rasterised back and compared with the segmentation **as regions**,
so a fill that happens to resemble its neighbour cannot score a match it did not
earn.

| folder | fields | vertices | agreement | brand IoU |
|---|---:|---:|---:|---:|
| `24_T1_Xanax_Pfizer` | 3 | 243 | 92.9% | 0.691 |
| `08_T1_Ativan` | 2 | 133 | 91.9% | 0.704 |
| `32_Viagra` | 2 | 167 | 91.2% | 0.336 |
| `14_T1_Imovane` | 2 | 95 | 89.8% | 0.872 |
| `02_T1_SMALL_Cialis` | 2 | 220 | 88.7% | 0.815 |
| `15_T1_Xanax` | 2 | 254 | 88.7% | 0.459 |
| `31_Kamagra` | 2 | 534 | 88.5% | 0.575 |
| `21_T1_Valium_Brand` | 3 | 259 | 87.2% | 0.786 |
| `23_T1_Lexotanil` | 1 | 27 | 86.3% | 0.896 |
| `25_T1_Modafinil_Generic` | 3 | 323 | 85.1% | 0.744 |
| `30_T1_Ritalin` | 2 | 187 | 79.4% | — |

Where brand IoU is low the carton has little colour-field design and the cluster
is mostly type: Viagra, Xanax and Ritalin are type-on-white. `30_T1_Ritalin`'s
79.4% is the substrate-only baseline — it genuinely has no field to fit, which
the number reports rather than hides.

## The failure worth recording

**Letterforms are not design.** On Cialis the type never separated into its own
cluster, so its strokes landed in the olive field and the tracer drew them as
regions: the first clean-looking spec printed "Cialis" and a fragment of the
Lilly script as olive polygons. A spec carrying letter outlines would print the
REFERENCE's words on every carton built from it — the same failure the
text-as-geometry rule exists to prevent, arriving through the back door.

Three tests were needed, each because the previous one was wrong:

- **Area alone** — Cialis's "C" and "a" are larger than its dosage block.
- **Convexity** — the tracer follows an outer boundary and ignores holes, so a
  round letter comes back looking convex; "a" scored 0.85 and survived. It also
  dropped the white swoosh, a deeply concave crescent, and took agreement from
  88.6% to 73.5%.
- **What survives**: a field either runs off the face, *or* covers more than 3%
  of it, *or* fills 85% of its own bounding box. A glyph does none of the three.

And the score excludes the pixels dropped as glyphs — 1.69% of the Cialis face.
Counting them would penalise the spec for being right, and would reward one that
traced the reference's words back into the fields.

## Not yet in the spec

- **Type rows.** Position, size, weight and colour per row are still unmeasured;
  the spec carries fields only. The renderer draws the strings from the manifest,
  so what is missing is where to put them, not what they say.
- **The side panel.** Measured on no reference; the front face is all D-1 rectified.
- **Print finish.** The references are glossy; nothing here records that.
