# D-7 — where our carton sets its type, against where the real one does

*2026-08-15. `scripts/type_qa.py`, figures in `00_PROJECT_STATE/type_qa.json`,
overlays (reference boxes green, ours magenta) in
`02_processing/reference_measurement/*.type.png`.*

D-6 measures colour and fields and says plainly that it does not measure type:
every figure there excludes dark pixels, because the spec carries fields and the
label is drawn from the manifest. This is that axis. It is the last part of the
owner's target — *composition, colour and typography* — with no number against
it, and the first run found two build defects that every D-6 figure was blind to,
one of them a carton printing two rows through one another.

## What can be compared, and what cannot

The two cartons carry **different words**, deliberately: the Ritalin folder
photographs a pack reading "Motiron", ours prints Ritalin, and copying the
reference's wording onto our carton is the exact failure the text-as-geometry
rule exists to prevent. Four of the eleven differ this way.

So a row's **width is not evidence** — a longer word makes a longer box — and
neither is box IoU, which is mostly width. Neither is reported. What survives the
difference in strings:

| | |
|---|---|
| `dv_top` | where the row starts down the face |
| `du_anchor` | where it sits across the face, read at the alignment pin: left edge for LEFT, right for RIGHT, centre for CENTER |
| `cap_ratio` | how big the type is, ours over the reference's |

Both sides are read with the **same instrument** — Tesseract word boxes on a
rectified face, the reader D-2b used on the photographs — so the reader's own
bias sits on both sides of the subtraction rather than on ours alone. Taking our
figure from `--dump-scene` instead would be exact for our render and would then
be differenced against an OCR box, putting the whole of the reader's error into
our column.

The scene dump is used the other way round: to **check the instrument**. On the
rows both saw, OCR and exact geometry agreed to within 0.001 of face height.

## The baseline, and what moved it

| | at baseline | now |
|---|---:|---:|
| rows scored | 18/21 | **20/21** |
| worst `dv_top` | 0.0274 | **0.0014** |
| mean \|`dv_top`\| | 0.0180 | **0.0005** |
| worst `du_anchor` | 0.0091 | 0.0091 |

Horizontal placement was already right and is untouched. Everything below is the
vertical axis and the two collisions.

| SKU | folder | scored | worst dv | worst du |
|---|---|---:|---:|---:|
| `64-min` | Kamagra | 2/2 | 0.0000 | 0.0013 |
| `74-min` | Viagra | 1/2 | 0.0000 | 0.0091 |
| `135-min` | Ativan | 1/1 | 0.0000 | 0.0000 |
| `155-min` | Imovane | 2/2 | 0.0013 | 0.0014 |
| `156-min` | Xanax | 3/3 | 0.0007 | 0.0027 |
| `272-min` | Valium | 2/2 | 0.0011 | 0.0040 |
| `308-min` | Lexotanil | 3/3 | 0.0000 | 0.0069 |
| `340-min` | Xanax Pfizer | 3/3 | 0.0008 | 0.0030 |
| `344-min` | Modafinil | 1/1 | 0.0014 | 0.0013 |
| `404-min` | Ritalin | 2/2 | 0.0000 | 0.0050 |
| `59-min` | Cialis | 0/0 | — | — |

**`59-min` is not a pass.** Its reference measured no rows at all, so there is
nothing to compare and the row is blank rather than perfect. Cialis prints its
whole label on the generic grid — the carton that started this workstream is the
one the type work has not reached.

## Defect 1: every measured row sat below its own measurement

`align_y="TOP"` pins the top of the font's **line box**, which stands above the
tallest glyph by the font's ascent-above-cap. The measurement is an **ink box** —
Tesseract returns the glyphs' own extent. Anchoring one to the other is a
systematic drop, and it was one:

| SKU | row | measured `v0` | built `v0` | drop, in cap heights |
|---|---|---:|---:|---:|
| `156-min` | brand | 0.0764 | 0.1146 | 0.145 |
| `156-min` | dosage | 0.2700 | 0.2879 | 0.109 |
| `156-min` | ingredient | 0.4636 | 0.4869 | 0.150 |
| `308-min` | brand | 0.0938 | 0.1070 | 0.181 |
| `308-min` | ingredient | 0.2350 | 0.2425 | 0.138 |
| `308-min` | unit count | 0.5417 | 0.5581 | 0.231 |
| `404-min` | ingredient | 0.3318 | 0.3489 | 0.231 |
| `404-min` | unit count | 0.4776 | 0.4925 | 0.199 |

Eight rows on three cartons, every one below, none above. `_align_ink_top()`
measures the built row and translates it, which lands all eight on 0.0000 — the
correction is exact in one pass because it is a translation, not a scale.

Corrected by measuring rather than by a constant, for the reason the type sizes
are already set as cap height: the gap depends on which glyphs the string
happens to carry, and the eight rows above spread over 0.109–0.231.

## Defect 2: a grid row printed through a measured one, twice

A measured row lands where the reference puts it, which is anywhere. A role the
reference could not be read for stays on the generic grid, which is fixed. The
two knew nothing about each other in one direction only — the existing guard
covers a grid **brand** shrinking to clear the measurements above it, and nothing
else.

**`135-min` Ativan.** Reference brand at v 0.432–0.562; grid ingredient at 0.46.
"Ativan" printed straight through "Lorazepam", and the reader returned **nothing
at all** from that face, upright or inverted — it is the only carton in the group
that read as blank. `_clear_below()` lowers the grid row; Ativan now scores
1/1 at 0.0000.

**`340-min` Xanax Pfizer.** Reference unit count at v 0.869–0.912 in the bottom
LEFT corner, which is exactly where the grid hangs the dosage: "0.5mg" and
"30 Pills" were printed through one another. Here the grid row **rises** — at the
foot of the face there is nowhere below to go — so the fix is an extra floor on
`_lift_row()`, not another `_clear_below()`. 2/3 → 3/3.

Both guards test **both axes**, and the second axis is not caution: the same
Ativan carton sets its dosage in a colour block at the right of the very band the
brand occupies at the left, sharing its whole height and touching nothing.
Dropping a row for an obstacle it never meets is a wrong layout too, just a
quieter one.

### The version of that guard that was wrong, and what caught it

The first `_lift_row` floor cleared every measured row sharing a column,
without asking whether the bottom row ran into it vertically. That threw
Kamagra's entire bottom row from v 0.81 to **v 0.07** — over the top of the
carton, above an ingredient row it sat 0.6 of a face below and never touched.
Coverage said so immediately, 19/21 → 18/21, which is the whole reason the
instrument was built before the fixes rather than after them.

## What is still not scored: one row of twenty-one

`74-min`'s ingredient. Tesseract does not return "Sildenafil" from that render —
0.055 of the face tall, dark grey on light grey, a marginal read at baseline too
(it came back as a 0.030-tall box). **It is built correctly**, and the scene dump
is how that is known rather than assumed: v 0.3292 against a measured 0.3292,
u 0.5396–0.7296 against 0.5436–0.7336.

Coverage is not stable for a row that marginal. It moved in and out across three
runs of this loop on renders that differ by a few pixels, which is worth knowing
before reading a one-row change as a regression.

Two rows are reported as **unreadable** rather than absent when the reader
returns something that is not the string we printed — a distinction the metric
needs and the one place it admits it cannot see:

- **`156-min` at baseline** read "XAXa" for "Xanax", scoring 0.50, with a box
  0.268 of the face wide of where our brand actually stands. Our brand was
  exactly right. The fitter had left the reference's **own traced wordmark** in
  the spec as a colour field, the driver duly built it, and the reader merged
  that shape with our type into one row. Once the anchor fix moved our brand
  clear of it the row reads "Xanax" and scores 3/3 — **but the traced wordmark is
  still on the carton**, printing a nonsense glyph pair beside the brand. That is
  a D-2 fitter defect, recorded here with its number and not fixed in this pass:
  re-fitting moves every D-6 figure and the last two rounds show how touchy that
  is.

  The `.type.png` overlays show the same signature elsewhere, unmeasured and
  noted only as an observation: `135-min`'s colour block has a notch traced out
  of its left edge that eats into the "1" of "1mg", and the silver strip along
  its top edge is a sawtooth rather than a band. Whatever is done about the
  Xanax wordmark should be judged against these too.
- **`155-min`** read "Bmg 30 Pills" as one row. That one is not a defect at all:
  the dosage sits at the left of the bottom band and the unit count at the right,
  one baseline, no overlap — the layout `_lift_row`'s own doctrine asks for — and
  the reader groups by vertical centre. Rows are the right unit for *identifying*
  a label and the wrong one for *measuring* one, so `_narrow_to()` trims a row
  back to the words that spell the string being asked about. Imovane scores 2/2.

## Open, with a number attached

**`cap_frac` is the reference's ink-box height being used as our cap height.**
Where the two strings carry different ascenders and descenders those are not the
same quantity, and the sizes come out 0.54–1.34 of the reference's box, with only
10 of 20 rows inside ±10%. The extremes are exactly the strings that differ most:
`156-min`'s dosage reads "0.5mg" against a reference "0,50" — digits only, no
descender — and comes out 0.56.

Fixing it means converting each reference box into a cap height using the
reference's own string, which D-2b already records as `read_as`. The risk is that
`read_as` is an OCR reading and sometimes a garbled one ("NAX", "dala fil"), so
the glyph profile it implies can be wrong. Not attempted here.

**Cialis has no measured rows**, and the reference-side reader is what would have
to improve to give it any.
