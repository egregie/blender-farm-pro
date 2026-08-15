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
| `dv_cap_top` | where the row's CAPITALS start down the face |
| `du_anchor` | where it sits across the face, read at the alignment pin: left edge for LEFT, right for RIGHT, centre for CENTER |
| `cap_ratio` | how big the type is, cap height over cap height |

Both vertical figures are read at the **cap line**, not at the ink. An OCR box is
the extent of the glyphs, so its top and its height both move with whatever
ascenders and descenders the string carries — and the two cartons carry different
words. Differencing the ink boxes reports a descender as a size error and an
ascender as a placement one.

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
| rows scored | 18/21 | **20/20** |
| worst vertical error | 0.0274 | **0.0014** |
| mean vertical error | 0.0180 | **0.0004** |
| worst `du_anchor` | 0.0091 | 0.0073 |
| `cap_ratio` above 1 | to **1.384** | to 1.03 |

*The denominator moved too: `MATCH_MIN` dropped three reference boxes that
covered under 60% of their own string, and word-level claiming added two. See the
`assign_roles` section below.*

Horizontal placement was already right and is untouched. Everything below is the
vertical axis and the two collisions.

| SKU | folder | scored | worst dv | worst du |
|---|---|---:|---:|---:|
| `64-min` | Kamagra | 2/2 | 0.0000 | 0.0073 |
| `74-min` | Viagra | 3/3 | 0.0002 | 0.0072 |
| `135-min` | Ativan | 1/1 | 0.0001 | 0.0000 |
| `155-min` | Imovane | 2/2 | 0.0009 | 0.0014 |
| `156-min` | Xanax | 1/1 | 0.0006 | 0.0010 |
| `272-min` | Valium | 2/2 | 0.0006 | 0.0040 |
| `308-min` | Lexotanil | 3/3 | 0.0002 | 0.0069 |
| `340-min` | Xanax Pfizer | 4/4 | 0.0008 | 0.0032 |
| `344-min` | Modafinil | 1/1 | 0.0014 | 0.0009 |
| `404-min` | Ritalin | 1/1 | 0.0000 | 0.0037 |
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

Eight rows on three cartons, every one below, none above. The first fix measured
the built row's ink top and translated it onto `v0`, which landed all eight on
0.0000. That was right about the direction and wrong about the anchor: an ink top
is a different quantity on every string, so it made our row's ink line up with a
row of different words. **The anchor is the cap line** — see the contract-1.5
section — and `_cap_drop()` gives it without a bounds read at all, because a
capital's top sits a fixed distance below the `align_y="TOP"` origin for a given
font whatever the string.

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

## Coverage, and how much to read into it

Every measured row is now located and scored — 20 of 20. That was not true at
baseline, and it was not true at any point in between: `74-min`'s ingredient is
0.055 of the face tall, dark grey on light grey, and moved in and out of coverage
across four runs of this loop on renders differing by a few pixels. It was always
**built correctly**; the scene dump is how that was known rather than assumed
(v 0.3292 against a measured 0.3292, u 0.5396–0.7296 against 0.5436–0.7336).

So read a one-row change in coverage as noise on marginal rows until the scene
dump says otherwise. A change of three, as below, is not noise.

Two rows are reported as **unreadable** rather than absent when the reader
returns something that is not the string we printed — a distinction the metric
needs and the one place it admits it cannot see:

- **`156-min` at baseline** read "XAXa" for "Xanax", scoring 0.50, with a box
  0.268 of the face wide of where our brand actually stands. Our brand was
  exactly right. The fitter had left the reference's **own traced wordmark** in
  the spec as a colour field, the driver duly built it, and the reader merged
  that shape with our type into one row. Once the anchor fix moved our brand
  clear of it the row reads "Xanax" and scores 3/3. **The wordmark itself was a
  D-2 fitter defect and is now fixed** — see below.

  The `.type.png` overlays show the same signature elsewhere, unmeasured and
  noted only as an observation: `135-min`'s colour block has a notch traced out
  of its left edge that eats into the "1" of "1mg", and the silver strip along
  its top edge is a sawtooth rather than a band.
- **`155-min`** read "Bmg 30 Pills" as one row. That one is not a defect at all:
  the dosage sits at the left of the bottom band and the unit count at the right,
  one baseline, no overlap — the layout `_lift_row`'s own doctrine asks for — and
  the reader groups by vertical centre. Rows are the right unit for *identifying*
  a label and the wrong one for *measuring* one, so `_narrow_to()` trims a row
  back to the words that spell the string being asked about. Imovane scores 2/2.

## The traced wordmark, and why a size threshold could not have fixed it

*Added 2026-08-15, after this document first recorded the defect.*

Xanax's face is one heavy black "XANAX". The clustering put it in the same
colour group as the purple bar down the carton's right edge, and it broke into
five components: the bar, then "XA", "N", "A", "X". Three were dropped as
glyphs. **"XA" survived, at 3.4% of the face.**

It survived through the fitter's "large enough" escape — past 3% of the face,
shape stopped mattering. And that escape could not be repaired by choosing a
better size, because the only other component in the whole group that depended
on it is **smaller**: Xanax Pfizer's magenta panel, at 3.2%. Any threshold
admitting the panel admits the letters.

**What the panel actually is.** A clean 138 × 160 pixel rectangle with a
**one-pixel thread** running a fifth of the face down the carton's right edge —
an artefact of rectifying a photograph. The thread carries about 1% of the
component's pixels and stretches its bounding box by half, so the panel filled
0.51 of its box and failed every rectangle test in the module. Remove the thread
with a one-pixel opening and it fills **0.96**. "XA" fills **0.49**.

So the escape is gone and a component earns its place three ways: it runs off the
face, it reads as a block, or its pixels fill its own box once hairlines are
removed. The middle one is not redundant — the four references that reverse the
dosage out of a filled block leave letter-shaped holes in it, and Cialis's block
fills 0.70 of its box by pixels against 0.95 by outline.

**Blast radius: one component in eleven specs.** Every other part is unchanged,
byte for byte, and Xanax's own spec agreement moves 93.3% → 93.2%.

`part_kind` was deliberately left alone. Making the panel a *block* would have
been the tidier-looking fix and would have been wrong: the driver reverses the
dosage out of `blocks[0]`, so Xanax Pfizer would have started printing "0.5mg"
inside a magenta square its reference prints nothing in.

### A second defect, found by diffing rather than by anything failing

`fit_design_spec` owns the fields and `measure_type_rows` owns `type_rows`, and
both write `design_spec.json`. The fitter rewrote the file **wholesale**, so
re-running it deleted every measured row: all eleven manifests came back with
`"type_rows": {}` and every design carton silently returned to the generic grid.
Nothing raised, nothing failed, and the D-7 figures would have looked *better*
for it — with no rows measured there is nothing to score against.

The fitter now carries the block forward, and a test compares each manifest's
`type_rows` against its spec's so the two cannot part company again.

## The 0.5 bar in `assign_roles`, and the two things it was hiding

*Added 2026-08-15.*

With the wordmark gone, what the measurement had actually captured was plain: our
"Xanax" sat at u 0.41–0.82, the right-hand **half** of a reference wordmark
running from u 0.113. D-2b read that row as `"NAX"`, which scores exactly 0.50
against "XANAX®" — the bar it had to clear.

That is not a coincidence. `_similar` divides by the longer string, so **0.5 is
very nearly the score of a box covering half what it claims to measure**, and the
bar sat exactly there.

### First, a confound had to go: the box was the whole ROW

Reading the distribution was pointless while three rows were failing the opposite
way — boxes **wider** than the string they were matched to, because the reader
groups words by vertical centre and a carton sets several labels on one line:

| read | matched to | score |
|---|---|---:|
| `0,5 mg ALPRAZOLAMUM` | Alprazolam | 0.60 |
| `Sildenafil Citrate Tablets` | Sildenafil Citrate | 0.71 |
| `50 mg film-coated tablets` | 4 film-coated tablets | 0.80 |

`narrow_to_string` — the trim D-7 already applied to our own rows — moved to
`measure_type_rows`, so both sides now narrow through one function rather than
two. Kamagra's ingredient goes 0.71 → 1.00, Xanax Pfizer's 0.60 → 0.82.

Narrowing then broke the bookkeeping under it: a role claimed the whole ROW, so
Viagra's dosage matched "50 mg" out of "50 mg film-coated tablets" at 1.00 and
took the unit count's words with it. **Words are claimed now, not rows** — which
is the layout the driver's own `_lift_row` doctrine describes, dosage at one end
of a band and unit count at the other.

Together those added two rows and narrowed three: 21 → 23.

### Then the bar, read off a distribution with a gap in it

Sorted, the 23 scores run 0.50, 0.50, 0.50, **0.74**, 0.82, 0.82, 0.88, 0.88,
0.94, then 1.00 fourteen times. The three at 0.50 are the whole of the problem,
and measuring the ink in their own band says how far off they were — the true
extent taken from the photograph's pixels, not from OCR:

| | box | ink in that band | covers |
|---|---|---|---:|
| Xanax brand | u 0.410–0.823 | u 0.113–0.822 | **58%** |
| Xanax dosage | u 0.112–0.316 | u 0.113–0.542 | **47%** |
| Ritalin unit count | u 0.203–0.357 | u 0.115–0.733 | **25%** |

`MATCH_MIN = 0.6` drops exactly those three. It is **not fitted to the eleven**:
the next score above 0.50 is 0.74, so any value in that gap gives the same
answer. What the evidence fixes is the floor — above "half the string" — not the
number.

This is the module's own stated rule finally being enforced: a label at a wrong
measured box is worse than one on the grid, because the grid is at least
consistent.

### What it cost, stated

| | before | after |
|---|---:|---:|
| reference rows measured | 21 | 20 |
| of those, located in our renders | 20 | **20/20** |
| `340-min` Xanax Pfizer | 3/4 | **4/4** |
| `74-min` Viagra | 2/4 | **3/4** |
| `156-min` Xanax | 3/4 | 1/4 |
| `404-min` Ritalin | 2/4 | 1/4 |

One row fewer overall, and for the first time every row that IS measured can be
found and scored in our own render — the reader no longer disagrees with itself
about where a row is.

**The one loss worth naming** is Xanax's dosage. Its box was short at the right
but its LEFT edge and top were exact, and the row is LEFT-aligned, so the anchor
it would have set was right and only the width was small. A prefix fragment on a
left-aligned row costs less than a suffix fragment on a centred one — Xanax's
brand, at CENTER, would have set its anchor 0.15 of the face out. The bar does
not know the difference. Making it know would mean measuring the true ink extent
per row, and the instrument for that currently catches design fields as well as
type: on Xanax it returns the purple edge bar along with the wordmark.

## `cap_frac` was an ink height wearing a cap height's name

*Added 2026-08-15. Contract **1.5**.*

`_place_measured_row` set our cap height to the reference's `cap_frac`, which was
the height of the OCR **ink box** — the extent of the glyphs, ascenders above the
cap line and descenders below the baseline. How much of that box is cap height
depends entirely on which letters the reference's own string happens to carry.
Measured in the vendored face over the twenty rows this sample has:

| | ink/cap |
|---|---:|
| `ALPRAZOLAM`, `XANAX’ SR`, `KAMAGRA-100` — caps only | 1.034 |
| `30 tabletek`, `Sildenafil Citrate` — ascenders, no descender | 1.062 |
| `50 mg`, `0,5 mg` | 1.308 |
| `Lorazepam Orion`, `Diazepam`, `30 comprima` — descenders | 1.329 |
| `Bromazépam`, `1 comprimé uadrisécable` — accent and descender | 1.384 |

**1.034 to 1.384, mean 1.180.** Every measured row was that much oversized, and
the size of the error was a property of another manufacturer's wording rather
than of anything about our carton — Kamagra's brand was 3% out and Lexotanil's
ingredient 38%, for no reason connected to either pack.

### Fixed at the measuring end, and the field renamed to what it holds

`measure_type_rows` now converts before it writes: `cap_frac` is a **cap height**
and a new `cap_top_v` records where the reference's capitals start. `v0` stays
the ink top, because that is what was measured and what the collision guards
treat as the row's occupied area.

Doing it there rather than in the driver keeps the field honest to its name and
keeps the font proxy in one place. It is a **proxy** and is labelled as one: the
reference's typeface cannot be recovered from a photograph, so the glyph profile
is taken in the face this project prints in. What it really measures is which
*categories* of glyph the string contains — has-cap, has-ascender, has-descender
— and those move together across sans-serif faces even where exact ratios do not.

The driver anchors the **cap line** to match: `_cap_drop()` measures how far below
the `align_y="TOP"` origin a capital's top sits, per unit `size`. Unlike an ink
measurement that is string-independent and survives `_fit_width` rescaling the
object, so the alignment is one arithmetic step rather than a second bounds read.

**This is a repurposing, not an addition, and the contract treats it as one.** A
1.4 row is not a 1.5 row with a field missing — it is the same number meaning
something else, and reading it as a cap height silently oversizes the row. `1.5`
therefore requires `cap_top_v` and `read_as`, and a 1.4 manifest is rejected.

### What the numbers say

`cap_ratio` is now cap height over cap height. Applying that metric to the old
build gives back the ink/cap figures above — 1.034 to 1.384. Applying it now:

| | |
|---|---|
| rows at exactly 1.00–1.01 | **10 of 20** |
| highest | **1.03** |
| the rest | 0.56–0.95, all below 1 |

Everything above 1 is gone; what remains is entirely below, and it is a different
constraint. **Our typeface is not the reference's**, so a row set at the
reference's cap height can be wider than the box it was measured in and
`_fit_width` shrinks it. That trade is deliberate — a row that overflows its
measured box lands on a design field — and a test now forbids the other
direction, a row built *larger* than its measurement.

The colour axis moved with it. `135-min` Ativan, whose reference brand string
descends and was therefore 33% oversized, reads **94.3% → 96.5%** against its
spec and 87.8% → 90.0% against its photograph, with its swing falling 2.6 → 0.4.
Four other rows gain a tenth of a point and none regresses.

### The instrument now crosses two independent implementations

The vertical figure is measured at the cap line on both sides, and the two sides
compute that line in different code: PIL/FreeType metrics in `ink_profile`, a
probe object in Blender for `_cap_drop`. They agree to **0.0014 of face height**
across twenty rows. A disagreement between them would show up here as a
placement error, which is a stronger check than either alone.

## Open, with a number attached

**Our typeface is wider than the references', and `_fit_width` pays for it.**
Ten of twenty rows keep the reference's cap height exactly; the other ten are
shrunk 0.56–0.95 to fit the box they were measured in. Nothing is oversized any
more, so this is now the whole of the size story — and it is a property of
DejaVu against an unknown print face, not of the measurement. A condensed
vendored face would close most of it; that changes every one of the 391 cartons
and is not a design-group decision.

**Cialis has no measured rows**, and the reference-side reader is what would have
to improve to give it any.
