# Contract 1.10: the marks that ship, and what they actually draw

Measured 26 August 2026. `design.marks[]` is required and usually empty. **22
marks across 12 of the 28 folders** — the 8 holes and 14 components the owner
approved by name in [`MARKS_DECISION.md`](MARKS_DECISION.md), and nothing else.

This is the third document about marks and the shortest. The first
([`MARKS_EVIDENCE.md`](MARKS_EVIDENCE.md)) measured what the regions are; the
second recorded a person's decision about them; this records what shipped, what
it cost, and the two things the first document got wrong.

---

## What was wrong, and it mattered because a decision rested on it

`MARKS_EVIDENCE.md` measured every approved hole as solid — `islands = 0`,
`solid_frac = 1.000` — and that was read out, twice and in writing, as **"the
wordmark is not carried and would not appear in the render"**. Both halves are
false.

- **A glyph touching the boundary is not an island.** It is a NOTCH, and the
  Moore-neighbour trace walks around it, so it survives into the outline.
  `74_Viagra`'s Pfizer oval emits as an oval with the "fi" ligature cut out of
  it.
- **A silhouette of a wordmark IS the wordmark.** A filled outline of Lilly's
  script reads "Lilly". Nothing about being one flat colour makes it less the
  mark — and `MARKS_EVIDENCE.md` had itself said so about components, in the
  same paragraph that was quoted to support the opposite.

`scripts/measure_mark_shapes.py` now measures it instead of remembering it. It
takes the EMITTED polygon and reports **solidity**, the ring's area over its
convex hull's: a blob is near 1.0, a script far below.

**11 of the 22 emitted marks carry letterform geometry.** The threshold `0.85`
sits in a real gap — eleven marks at 0.907–1.000, eleven at 0.190–0.825, nothing
between — and a test pins that, because a threshold chosen inside a crowd would
make the count meaningless.

| mark | solidity | what it draws |
|---|---|---|
| `152_Artvigil brand#26` | **0.190** | a script swash |
| `64_Kamagra highlight#7` | 0.323 | a crescent |
| `155_Imovane highlight#2` | 0.593 | the letters "ven" |
| `221_Inderal brand#0/hole#0` | 0.623 | the LCI roundel |
| `74_Viagra brand#0/hole#0` | 0.918 | an oval with "fi" notched out |

Shown the drawn polygons, the owner withdrew one entry and confirmed the rest.
The withdrawal is the one that mattered: `59_Cialis brand#9` reads "Lilly" and
turned out to be **the lettering OF the holographic sticker**, whose own region
was out of scope from the start — its bounding box, u 0.677–0.804 and v
0.743–0.854, lies entirely inside the sticker's u 0.617–0.875 and v 0.650–0.948.
A containment check finds no other approved mark inside a refused one. **A
security feature is refused whole, lettering included.**

---

## The pairing rule holds in three places, on purpose

`MARKS_DECISION.md`: cutting a mark hole while drawing nothing into it shows
board through our field in the shape of another company's logo.

1. **`fit()` cuts the hole and emits the mark from ONE loop**, so the unpaired
   case is unreachable in the producer.
2. **`parts[].mark_holes`** records which cut rings are marks. Without it the
   rule is unverifiable on a manifest at all: a mark hole and a window are both
   just rings.
3. **`_reject_unpaired_marks` refuses BOTH directions**, on write and on read. A
   manifest is a file — it can be hand-edited — and a rule only the producer
   keeps is a rule the artefact does not carry.

---

## The index-based figures cannot judge a mark, and now say so

`verify()`, `design_coverage` and `design_qa` all compare region IDENTITY
against a vocabulary of FIELDS. A mark is deliberately neither a field nor the
board, and scoring one against a field-indexed ground truth is a category error.
It was measured being one: **`230_Slimex`, whose only spec content is two
approved marks, read 0.00%**, and `272_Valium_Brand` 54.31%, because every pixel
they draw met a truth that says substrate. Widening that truth to admit approved
marks was tried and recovered 0.20 points of the group — the indices still
cannot match for a mark whose role is not a field at all.

So a mark's area leaves the scored set in all three, on BOTH sides. Cutting and
drawing is neutral there rather than banking what cutting alone earns, which is
what `MARKS_DECISION.md` meant by *"the +9.937 is not carried forward"*.

**In `design_qa` there is a sharper reason: a mark's colour is not in the
palette.** The palette is the set of colours the spec paints as fields, so every
mark pixel would classify to whichever entry happened to be nearest — on both
sides — and land in some field's IoU having nothing to do with that field.
Adding the mark colours instead would make `field_iou_worst` a statement about
fields and marks at once, which is the silent redefinition `to_field` exists to
stop.

**`region_colour_gap` does judge them**, and is the right instrument: its regions
come from `spec_index`, which gives a mark its own index, so it asks the only
question that matters without needing a word for it — does our render put the
measured colour where the photograph has it? `74_Viagra`'s Pfizer oval reads
**0.102**.

### And the substrate core had to be cleaned

A mark can be the colour of the board. `74_Viagra`'s oval is `#D8D9D5` against a
substrate of `#DDDEDB` — **0.0364 apart**, so it classifies as substrate, joins
`_substrate_core`, and the illumination plane is fitted through a region the
spec paints separately. The core now excludes marks.

---

## The label grid does not know marks exist — OPEN, and the fix was worse

`_prepared_parts` in the driver reads `design["fields"]` and nothing else, so
neither `_surface_fill` (which chooses a measured row's ink) nor
`_clear_of_design` (which moves a grid row off a surface that would hide it) can
see a mark. The renders show what that costs:

- **`157_Valium` prints "30 Pills" straight across the Roche hexagon.**
- **`152_Artvigil` prints "150mg" across its signature swash.**

That is precisely the defect `_clear_of_design` exists to prevent for fields,
reappearing because a new kind of printed surface was added and the grid was not
told about it.

**The obvious fix was built, measured, and reverted.** Adding marks to
`_prepared_parts` cleared both cartons — and the OCR gate then read **eight rows
lost against three gained**. `221_Inderal` is the case to look at rather than to
count: its "40mg" was **white on the purple band and fully legible**, and with
marks visible the clearing search moved it off the LCI roundel and onto the
board, where it lands half on the band in dark ink and is half hidden.

Trading a row printed across a mark for a row nobody can read is not a fix, so
it is reverted and the evidence is recorded in the driver at the point where it
was removed rather than only in a commit message.

**The shape of a real fix is known and is not this contract's work.** The change
has two halves and they were not separated: `_surface_fill` choosing INK from a
mark is the useful half — "30 Pills" would then reverse to white on the hexagon
— and `_clear_of_design` MOVING a row because of one is the harmful half. Each
needs its own measurement.

---

## What it cost

`design_qa`, over fresh renders of all 28, against the contract-1.9 report.

| figure | 1.9 | with marks | movement |
|---|---|---|---|
| `render~ref` | 0.9382 | **0.9398** | 8 up, **0 down** |
| `field_iou_worst` | 0.9691 | **0.9706** | none down beyond 0.02 |
| `render~spec` | 0.9943 | **0.9946** | **0 down** |
| `region_colour_gap` worst | 0.1489 | 0.1616 | 5 rose, all explained below |

`design_coverage`, which takes no render:

| | 1.9 | with marks |
|---|---|---|
| `pixel_agreement` | 99.18% | **99.27%** |
| `print_agreement` | 52.79% | **53.14%** |
| `truth_agreement` | 95.36% | **95.76%** |
| drawn off print | 0.76% | **0.72%** |

**All 16 cartons that carry no mark moved by exactly zero on every figure.** The
change is confined to the twelve that do, which is the neutrality this contract
is entitled to claim and nothing more.

### The marks' own colour, now that they are their own regions

`region_colour_gap` keyed 254, worst first: `150-min` 0.306, `357-min` 0.196,
`404-min` 0.195, `230-min` 0.172, `155-min` 0.148, `74-min` 0.102, `157-min`
0.093, `64-min` 0.074, `221-min` 0.058, `135-min` 0.055. Before the outline fix
below, the same figures ran to **0.857** and **0.610**.

### Two cartons' colour gap rose, and the rise is the figure getting honest

`74-min` +0.041 and `135-min` +0.026 on `region_colour_gap`, both Pfizer-oval
cartons. Not a regression, and it is arithmetic rather than an argument.

A controlled A/B renders the band **bit-identically** with the mark and without
it, and the illumination model did not change. What changed is the REGION:
before, the brand field included the oval, where our render painted navy and the
photograph has a light mark. Those two contributions pulled the regional means
toward each other.

Reconstructed from the measured means and pixel counts — band 198 153 px at
`[0.143, 0.203, 0.355]` ours against `[0.019, 0.160, 0.360]` reference, oval
12 017 px at `[0.722, 0.734, 0.746]` reference:

| | gap |
|---|---|
| band + oval, our render painting the oval navy | **0.0887** |
| the pre-marks report | **0.0857** |
| band alone, oval cut out | **0.1313** |

The reconstruction lands on the recorded value. Cutting the oval removes a
cancellation that was masking a **+0.124 error in the red channel** across the
whole band. The band was always that wrong; the figure was not saying so.

---

## Five marks were painted solid where the carton prints an OUTLINE

The largest defect of this contract, and the one the numbers were pointing at
while I read them as being about something else.

`_mark_entry` emitted `holes: []` on the strength of `MARKS_EVIDENCE.md`
measuring every approved region solid. That is true of the eight HOLES — they
fill 0.9-1.0 times the ink they describe — and false of the components:

| mark | inks | filled | ratio |
|---|---|---|---|
| `230_Slimex brand#9` | 918 px | 8 696 | **9.5x** |
| `272_Valium_Brand brand#1` | 1 980 px | 17 765 | **9.0x** |
| `157_Valium type#8` | 1 977 px | 16 619 | **8.4x** |
| `230_Slimex brand#8` | 1 806 px | 6 215 | 3.4x |
| `404_Ritalin type#20` | 533 px | 1 267 | 2.4x |

`157_Valium`'s Roche mark is a hexagonal **outline**. Filled, it covers eight
times the ink and most of what it covers is board — measurably: the mark
declared `#022E99` while the photograph inside that same region read
`#B8BEC3`.

**Painting those solid is a worse reproduction than the carton's own, not a
lesser one.** It invents a filled logo where the pack prints a line.

A mark now carries its own holes, traced **without** consulting
`print_truth.json`. That is not a relaxation of contract 1.8's rule: 1.8 protects
a printed FIELD from showing board in the shape of the reference's own lettering.
Here the ring is the mark's own interior, cutting it is what makes the mark the
shape the carton prints, and leaving it filled is the invention.

After: **every one of the 22 marks fills 0.9-1.4 times its ink, and none is
solid over an outline.** The declared colour now agrees with the photograph
inside its own region — `157-min` `#022E99` against `#103A9C`, `64-min`
`#8E562A` against `#8D562A` — and the mark colour gaps fell with it: `157-min`
0.585 → **0.093**, `404-min` 0.332 → 0.195, `230-min` 0.331 → 0.172.

---

## The OCR cost, which is the decision's and not a defect

Drawing the marks costs **nine rows** of the OCR barrier and gains three. Every
one was looked at on the rectified face at native scale and every glyph is
legible to a person — what changed is that these faces now carry small
letterform-like shapes, and Tesseract treats them as characters:

- `157_Valium`'s Roche hexagon is an **outline** and "30 Pills" crosses it;
- `230_Slimex`'s Neptune mark is an orange outline sitting **over** "15mg";
- `404_Ritalin`'s two Novartis fragments sit on the board **beside**
  "Ritalin 10mg" at the same height.

Filed as the READER on the project's two checks and not on the OCR return. Nine
rows enter `KNOWN_OCR_MISSES` with that evidence; the three that started reading
— `230-min` active ingredient, `150-min` unit count, `357-min` brand — are
removed rather than left recorded as broken.

This is a real price and it belongs to the decision rather than to a bug: a
carton that prints a manufacturer's mark is harder for a reader that was built
to find four label rows on a clean board.

### And it broke the fixture format, which was worth finding

Nine and three is a PNG-to-PNG figure, and it took a detour to become one.

The committed fixtures are WEBP, written at quality 98 because contract 1.9
measured that quality reading identically to the PNG on all 112 of the sample's
rows. **Contract 1.10 falsified that**: three rows now sit on Tesseract's
decision boundary and q98 disagrees on all three — and not in one direction.
`230-min`'s ingredient and `357-min`'s brand are read by the render and lost by
the encode; `357-min`'s ingredient is missed by the render and RECOVERED by it.
Raising quality is not the answer and never was: **q100 disagrees on three too,
a different three**. Lossless disagrees on none.

The symptom was that the ratchet lists could not be made consistent. One barrier
reads the fixture and demanded `357-min`'s ingredient come off the list; the
other reads a fresh render and demanded it stay on. Two rows were entered on the
fixture's answer before that was understood, which was wrong — the disagreement
was the instrument, not the carton.

Before blaming the codec, all 28 fixtures were checked to reproduce
byte-for-byte from the renders on disk, so staleness was excluded rather than
assumed. The set is lossless now, 2.82 → 31.97 MB, and the two agree again.
