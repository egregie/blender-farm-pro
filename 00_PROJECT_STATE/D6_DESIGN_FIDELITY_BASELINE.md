# D-6 — the distance from a rendered carton to the packaging it copies

*2026-08-14. `scripts/design_qa.py`, figures in `00_PROJECT_STATE/design_qa.json`,
strips (reference / spec / render) in `02_processing/reference_measurement/*.qa.png`.*

The loop is closed: render, rectify with the corners the driver publishes, and
measure against the design. "Looks like it" is now a number — several, kept
apart on purpose.

## Three distances, because one hides the others

| | what it measures | fails when |
|---|---|---|
| spec ~ ref | how much of the real carton the spec captured (D-2) | the fit missed a field |
| render ~ spec | how faithfully the renderer built that spec (D-4) | the driver placed it wrong |
| render ~ ref | the composite | either, and you cannot tell which |

A high second with a low first is a renderer building a bad spec perfectly. On
Cialis the three read 88.7% / 89.6% / 79.5%, and 0.887 × 0.896 = 0.795 — the
decomposition is consistent, which is the first thing worth checking about a new
instrument.

## The baseline

*Re-measured 2026-08-15, after the type rows reached the driver and after the
comparison stopped dividing by its own subject (below).*

| SKU | folder | spec~ref | render~spec | render~ref | worst ΔC |
|---|---|---:|---:|---:|---:|
| `404-min` | Ritalin | 95.7% | **99.8%** | **97.5%** | 0.066 |
| `308-min` | Lexotanil | **99.1%** | 99.6% | 97.1% | 0.093 |
| `74-min` | Viagra | 95.0% | 99.7% | 93.2% | 0.191 |
| `344-min` | Modafinil | 93.9% | 99.4% | 93.9% | **0.065** |
| `272-min` | Valium | 91.1% | 98.8% | 93.8% | 0.110 |
| `156-min` | Xanax | 93.3% | 98.6% | 92.4% | 0.116 |
| `340-min` | Xanax SR | 95.0% | 97.5% | 94.0% | 0.151 |
| `135-min` | Ativan | 89.6% | 97.2% | 90.2% | 0.126 |
| `64-min` | Kamagra | 90.5% | 97.0% | 93.1% | 0.247 |
| `155-min` | Imovane | 93.7% | 88.6% | 83.5% | 0.087 |
| `59-min` | Cialis | 88.2% | 78.5% | 74.0% | 0.150 |

## `64-min`'s colour error: the comparison was dividing by its own subject

Kamagra's 0.413 was the largest in the group by more than double, on a carton
whose render agreed with its spec at 98%. It was not the render.

The cause is `_flatten_illumination`, which divides a face by a blurred estimate
of its own luminance and multiplies back by that estimate's mean. At a blur
radius of a sixth of the face, the estimate **follows the design**: Kamagra's
teal covers half its carton, so the blur dipped where the teal is and the mean
sat low, and the cream board was divided down twice over. Measured, its board
rendered at `#A39D94` against a `#E3DACD` fill — 0.41 away, on paint that was
correct.

The signature is unmistakable across the sample. The ratio of rendered substrate
to nominal tracks **how dark the whole face is**, not orientation and not
anything about the renderer:

| | Kamagra | Cialis | Viagra | Ritalin | Modafinil |
|---|---:|---:|---:|---:|---:|
| dark share of face | 54% | 30% | 10% | 2% | 0% |
| substrate rendered / nominal | 0.673 | 0.850 | 0.858 | 0.930 | 0.948 |

Widening the estimate to half the face — a lighting gradient is nearly a plane —
takes Kamagra to 0.829 while the light-faced cartons move by a thousandth.

**The radius is now the caller's choice, and the two callers differ.** Widening it
inside `segment()` was tried and reverted: clustering never compares against a
nominal colour, so it never had the defect, and changing it changed every spec —
Viagra picked up its holographic patch as a design field and Imovane a grey one,
costing them 20 and 8 points against their photographs. `design_qa` passes the
wide radius for its own comparison and the segmentation keeps the narrow one.

Kamagra: **0.413 → 0.247**, with its agreement unchanged at 93.1%.

### The trade this makes, stated

A wide estimate leaves the residual gradient in place, and that gradient is what
was helping separate two near-identical colours. `59-min` and `155-min` — the two
cartons already documented as classification-limited, at 0.106 and 0.086 between
substrate and highlight — lose agreement for it: Cialis 89.6% → 78.5%, Imovane
91.7% → 88.6%. Colour error improves on eight of eleven and the group's worst
figure falls by 40%.

That is a trade between two metrics, not a repair of one. It is taken because ΔC
is the figure that is not self-referential: it asks whether the renderer painted
the colour it was told to, against a spec region known exactly.

## `64-min` explained: a third of a carton with no name

Kamagra was the row whose three figures could not all be true — 88.5% spec,
92.7% render, **52.0%** composite. The cause was upstream of all three.

Its face clustered into four: teal `#03453A` at 34.0%, dark teal `#0C2D24` at
20.3%, cream `#D9D6CB` at **31.1%**, and cream `#D3CCC1` at 14.6%. Roles are
handed out one per cluster — substrate, brand, highlight, type — so the two
creams consumed two roles between them and **the larger one got no role at all**.
It never reached the spec. The carton then rendered two thirds teal against a
photograph that is under half, and the spec agreed with the photograph on 53.9%
of pixels while its own D-2 figure read 88.5%, because that comparison is by
region against the same segmentation and cannot see a surface the segmentation
never named.

Three defects, each uncovered by fixing the one before it:

1. **Clusters of one surface were never merged.** Two creams 0.03 apart are one
   printed board split by a lighting gradient. Merging them first — at the same
   threshold a field must clear to be visible at all — makes Kamagra's substrate
   the cream at 45.6%, against the photograph's 44.7%.
2. **A leftover cluster was dropped silently.** After merging, anything still
   unnamed is a real surface, so it is now named `secondary_N`. Nothing measured
   goes unnamed.
3. **A role could alias the substrate.** `brand` fell back to the substrate when
   no cluster was left, which was harmless while every face produced three
   clusters and became a hole the moment merging could leave two: Modafinil's
   whole board was handed to the fitter as a colour field, which traced the face,
   dropped 92% of it as glyphs and scored 24.2%.

And naming every cluster must not become drawing every cluster: Cialis's leftover
is the **Lilly hologram**, which the owner excluded outright, and it entered
through the "large enough" escape at 7.5% of the face. Leftovers are now held to
the same strict test as ink — run off the face, or be a printed block.

## `59-min` and `155-min`: the driver is not what is costing them

The two lowest composites. Investigated by measuring **deep inside** each spec
region — eroded by 9px, away from boundaries and from our own printed type —
which is where a build defect would show and a classification limit would not.

| | spec separation | render, sampled at the boundary | render, sampled in the core |
|---|---:|---:|---:|
| `59-min` Cialis, substrate vs highlight | 0.1057 | 0.0899 | **0.1055** |
| `155-min` Imovane, substrate vs highlight | 0.0865 | 0.0215 | 0.0614 |

**Cialis is built correctly.** Its two creams — `#DDD1B9` board against a
`#DCDBD2` swoosh — come out of the renderer separated by 0.1055 against the
spec's 0.1057, and its olive fields score IoU 0.962. What costs it is that those
two colours are 0.106 apart: a nearest-colour classifier confuses them wherever
lighting has not been perfectly divided out, and our render additionally prints
label text the spec does not carry. Neither is a reason to change the driver.

**Imovane compresses its pair to 71%** — 0.0614 against 0.0865 — and that one is
real, if small. Its palette is the tightest in the sample, 0.086 against a
separability floor of 0.08, so part of the loss is the same classifier limit and
part is not. Open, with a number attached.

### An exposure correction was tried and rejected

A design spec carries PRINT colours; a render is a picture of that print at some
exposure, and every render in the group sits about 1.13× below its spec. Fitting
one per-channel gain on the largest region — what a photographer does with a grey
card — is the principled correction, and it was implemented, measured in both
sRGB and linear space, and **reverted**:

| | before | after |
|---|---:|---:|
| `59-min` render~spec | 89.6% | 86.8% |
| `64-min` render~spec | 98.3% | **91.0%** |
| `155-min` render~ref | 85.4% | 83.1% |

It moves Cialis's field IoU from 0.365 to 0.681 and takes Kamagra down fourteen
points. Helping one carton by hurting two is tuning, not fixing, and the reverted
attempt is recorded here so the next person does not spend the afternoon on it.

## What the first baseline was actually measuring

The first run put `156-min`, `272-min` and `404-min` at the bottom on colour
error and blamed the fitter. Half of that was right.

**The fitter was emitting fields that are not design.** Two defects, both found
by looking at the specs rather than the pictures:

- *A field indistinguishable from the board it sits on.* Xanax's "highlight"
  `#E9DCB6` is two levels from its substrate `#E8DBB2`; Valium's and Ritalin's
  the same. All three covered around a third of the face. They are the
  clustering splitting one printed surface in two under a lighting gradient, and
  they are why six of the eleven palettes came back inseparable.
- *The type cluster emitted as a colour field.* Printed ink is drawn from the
  manifest's strings. A part of that cluster now earns a place only by running
  off the face — like Valium's navy edge bar, which is genuinely design — or by
  being a filled block. It does not get the "large enough" escape the other
  roles have, because accumulating area without being design is exactly what ink
  does.

Fixing those took **inseparable palettes from six of eleven to none**, and the
vertex counts with them: Viagra 167 → 5, Ritalin 187 → 7, Xanax 254 → 29. Spec
agreement rose on eight rows and fell on one, by 0.7 points.

**But the colour error barely moved** — 0.618 → 0.600, 0.551 → 0.548, 0.406 →
0.410 — which is how the other half was found. Those three specs' surviving
fields are DARK, and the metric's dark cut, there to keep printed type out of
the score, was cutting dark FIELDS with it. Inside Xanax's near-black brand it
sampled only the lit fringe. Whether a pixel is scored now depends on what the
SPEC expects there rather than on how bright the pixel happens to be, and the
three read 0.122, 0.132 and 0.058.

Worth stating plainly: **the fitter fix is what moved the agreement figures, and
the metric fix is what moved the colour errors.** Had only the second been done,
the specs would still be carrying invisible fields and inked-in type while every
number looked healthy.

## The metric had to be told where it cannot see

`344-min` scores 19.4% against a render that looks nearly identical to its spec.
Its substrate `#A09C9D` and highlight `#A9A5A7` are **four levels apart**. A
nearest-colour classifier flips between them on noise, so the figure stops
measuring fidelity and starts counting coin flips. **Six of the eleven palettes
are like this**, and the run now says so per row rather than printing a number
that reads as failure.

So a second axis was added that survives it: **colour error by region**. The
spec's regions are known exactly, so nothing is inferred from our pixels — they
are only sampled. Two fills four levels apart make *which region is this pixel
in* unanswerable while leaving *is this region the colour it should be*
perfectly well posed. On `344-min` that reads 0.118, confirming the render is
right and the agreement figure was the thing at fault.

The D-2 numbers are unaffected: that comparison is by REGION, drawn from the
spec's own polygons, and never asks a classifier anything.

## What the instrument points at

- **`64-min` Kamagra: 92.7% against its spec, 52.0% against the photograph.**
  Those two cannot both be right alongside a spec that scores 88.5%. Unexplained,
  survived both fixes unchanged, and now the only row of its kind.
- **`308-min` Lexotanil at 99.6% / 97.0%** is what the pipeline does when the
  design is flat fields and straight edges. It is the ceiling the curved cartons
  are being measured against.

## Not measured here

Type. Every figure above excludes dark pixels, because our render prints the
label from the manifest and the spec carries no type rows. The brand size and
position, the ingredient row and the missing form line are D-2 measurements that
were never taken — visible in every `.qa.png` strip, absent from every number.
