# Design fidelity for the reference-template group

*Opened 2026-08-11, after the owner set a new target: the eleven SKU under
`Reference Templates/` are to be rendered **1:1 against their reference
photography** — composition, colour and typography — **excluding manufacturer
logos and holographic elements**.*

This replaces nothing in the audit roadmap. It sits beside it, and it is the
first workstream in this project aimed at what a packshot *looks like* rather
than at whether the code that makes it is sound.

## Why the roadmap does not cover this

`R-004`, `R-005`, `R-007`, `R-008`, `R-009` and `R-011` came out of an audit of
code health. Not one of them changes what is drawn on a carton. `R-011` is the
only item that touches art direction at all, and it moves existing logic into a
module rather than teaching it anything new.

## What actually stands between here and the target

**1. The design passports exist and reach nothing.** Eleven folders carry a
`reverse_engineering_passport.md` with exactly the right analysis — archetype,
content zones, colour system, layer order, typographic character. The renderer
consumes `render_manifest`, whose contract (1.3) has no field for any of it.
There is no channel.

**2. Not one catalogue palette matches its carton.** Measured on the eleven:

| folder | SKU | catalogue | measured |
|---|---|---|---|
| `02_T1_SMALL_Cialis` | `59-min` | `#006A4E` / `#C9A227` | `#385808` / `#D8D8D8` |
| `08_T1_Ativan` | `135-min` | `#003366` / `#0D5FB8` | `#083888` / `#0A7A4A` |
| `15_T1_Xanax` | `156-min` | `#003366` / `#0D5FB8` | `#182848` / `#5B2D8E` |
| `23_T1_Lexotanil` | `308-min` | `#003366` / `#0D5FB8` | `#98B838` / `#58A898` |

**Six of the eleven share the pair `#003366` / `#0D5FB8`** — a category default,
not a packaging colour. The Cialis passport puts the consequence plainly: the
brand green is an olive, yellow-shifted, and rendering it as a generic green
loses the brand immediately. The catalogue holds a blue-green.

**3. The art direction is calibrated against the wrong references.** Every hard
constraint in `CLAUDE.md` — white carton body always, brand colour in exactly two
places and never elsewhere, matte board, no contact shadow, no depth of field —
was derived from the nine curated renders in `01_input_raster/reference/`, which
are AI images. The Lilly photograph breaks four of them at once. These
constraints are enforced by tests, so this is a change of standard, not an
addition of features. **It applies to the eleven only**; the other 380 SKU keep
the present rules, which is what the owner chose.

**4. The driver has no vocabulary for the graphic signature.** It draws a bottom
stripe, a corner badge and four text rows in one family at two weights. The
target needs curved colour fields, type reversed out of a colour block, and four
levels of typographic hierarchy.

## What the measurement showed

The passport describes the Cialis face as "broad S-curves entering from the left
and right edges". Rectified and segmented, it is not that. It is a family of
**concentric arcs**: down the left edge the bands run cream, olive, cream, olive,
white, olive. The cream corridor holding the type is the widest band of that
family, not a gap between two curves.

Measured on the rectified front face (`110 x 50mm`, corners now recorded in the
folder's `metadata.json` as `front_face_px`):

| field | share | colour |
|---|---:|---|
| cream substrate | 51.3% | `#D9CDB4` |
| olive | 26.1% | `#465813` |
| white swoosh | 17.6% | neutral, brighter than the substrate |
| type | 5.0% | near-black |

Those shares are of the **face**. The `color_zones` block already in the
passport counts the whole photograph — 57.8% of it is wall and desk — and the
two must not be confused.

The method is settled and cheap: set the four face corners by hand against a
coordinate overlay, rectify with `src/deskew.flatten_face` (the same function the
OCR barrier already uses), then classify in HSV. The first corner set was 40px
too high at the top and pulled the lid into the frame; rectifying and looking is
what caught it, and that loop is the measurement procedure, not a mishap.

## Sequence

**D-1 · Measure all eleven faces.** Corners into each `metadata.json`, then the
rectified face and its four-class segmentation. Output: field shares and true
colours per SKU. *Nothing renders yet; this is data acquisition.*

**D-2 · A design-spec format, proven on Cialis.** The bands are conic arcs, so
fit conics to the band boundaries rather than tracing free polygons. A spec is:
substrate colour, an ordered list of bands (bounding conics + fill), colour
blocks, and type rows carrying position, size, weight, colour and alignment.
Verified by re-rasterising the spec and differencing it against the segmentation
— the spec is right when the difference is small, which is a number, not an
opinion.

**D-3 · A channel to the renderer.** Contract `1.4`: an optional `design` block
on the manifest. Optional because 380 SKU have no design passport; loud because a
SKU **in the sample** without one must fail rather than fall back to the generic
art direction. One contract, as the project already requires — not a second file
the driver reads behind Stage 1's back.

**D-4 · The driver builds it.** Filled curve objects for the bands, a colour
block with type reversed out, four type levels. Text stays real geometry — the
guarantee that a string cannot be invented is not traded for fidelity.

**D-5 · Constraints become conditional.** The white-body / two-places / matte /
shadowless rules apply where there is no design spec. Where there is one, the
spec governs and the tests that enforce those rules must scope themselves to the
generic path, not be deleted.

**D-6 · Compare and iterate.** Render, rectify our own output with the corners
the driver already emits, and difference it against the rectified reference in
the same four classes. That closes the loop the nine AI references never could:
a measurable distance from a real carton.

**D-7 · The type axis.** D-6 measures colour and fields and excludes dark pixels
outright, so the whole of point 4 above — typographic hierarchy — sits outside
every figure it reports. `scripts/type_qa.py` reads our own rows back off the
render with the same instrument D-2b used on the photographs, and compares only
what survives the two cartons carrying **different words**: where a row starts
down the face, where it sits across it at its alignment anchor, and how big it
is. Width and box overlap are not comparable and are not reported.
See [`D7_TYPE_FIDELITY.md`](D7_TYPE_FIDELITY.md).

## Out of scope by the owner's decision

Manufacturer logos and holographic elements. For Cialis that means the Lilly
script and the silver oval are not built; the ellipse they sit in leaves the
substrate showing. Brand names on the front face are unaffected — they are
already in `label_content` and already rendered.

## Known limits

- Eleven of 391. The rest of the catalogue keeps the present art direction, and
  the difference in fidelity between the two groups will be visible.
- All eleven are `T1` or `T1_SMALL`. Nothing here exercises a narrow face.
- Rectification depends on hand-set corners. They are recorded, and re-derivable
  by the same look-and-correct loop, but they are not automatic.
