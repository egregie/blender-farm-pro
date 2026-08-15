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

*Re-measured 2026-08-15, after the D-7 type work, the Xanax fitter fix, the
`assign_roles` threshold and contract 1.5's cap heights. Type work keeps moving
these figures because moving the label changes which pixels are excluded — see
the two notes below.*

| SKU | folder | spec~ref | render~spec | render~ref | worst ΔC | residual | swing |
|---|---|---:|---:|---:|---:|---:|---:|
| `404-min` | Ritalin | 95.7% | **99.9%** | **97.6%** | **0.060** | — | ±0.0 |
| `308-min` | Lexotanil | **99.1%** | 99.8% | 97.2% | 0.093 | — | ±0.0 |
| `340-min` | Xanax SR | 95.0% | 97.6% | 95.0% | 0.149 | **0.014** | ±0.0 |
| `344-min` | Modafinil | 93.9% | 99.5% | 94.0% | 0.065 | — | ±0.0 |
| `272-min` | Valium | 91.1% | 98.8% | 94.2% | 0.128 | 0.025 | ±0.0 |
| `64-min` | Kamagra | 90.5% | 96.9% | 94.8% | 0.189 | 0.024 | ±0.0 |
| `74-min` | Viagra | 95.0% | 99.7% | 93.4% | 0.191 | — | ±0.0 |
| `156-min` | Xanax | 93.2% | 98.8% | 92.3% | 0.112 | 0.045 | ±0.0 |
| `135-min` | Ativan | 89.6% | 97.3% | 90.4% | 0.153 | 0.050 | ±0.0 |
| `155-min` | Imovane | 93.7% | 98.4% | 89.0% | 0.093 | 0.013 | ±0.1 |
| `59-min` | Cialis | 88.2% | 98.1% | 80.3% | 0.170 | 0.056 | ±1.1 |

`residual` is ΔC once the picture's own exposure and black level are taken out —
see below. A dash is a carton with too few regions to fit them.

*Re-measured after the classifier was anchored and its illumination model chosen
on evidence — the two sections below. Every row improved or held, every carton now
agrees with its spec at 96.9% or better, and the worst swing in the group is ±1.1.*

**`swing` is the agreement figure's own uncertainty**, measured rather than
assumed: the same classification run under a second illumination model, on
identical pixels. It is not an error bar on the carton — it is how much of the
number is the measurement rather than the render.

## The agreement figure was measuring our exposure, not our carton

`155-min` Imovane sat at 85.1% against its spec with a swing of ±7.5, the worst
in the group on both counts. Four explanations were tried and each ruled out by
measurement:

- **A build defect.** Its spec is right: measured deep inside each region on the
  photograph, the two greys sit 0.073 apart against a spec that says 0.086, and
  the render separates them by 0.061.
- **Speckle.** A neighbourhood vote at radius 4 and 8 moved the figure by 0.1
  and the swing by 0.1. The disagreement is systematic, not noise.
- **The wrong second model.** Swapping the alternative from a narrow blur to a
  wide one moved the outlier onto Cialis rather than removing it.
- **Signal against noise.** Gap over within-region spread correlates with the
  swing at only −0.44 across the eleven, and puts Kamagra worse than Imovane.

Then the disagreement was **looked at** rather than theorised about. Under the
primary model our render's highlight band was classified over **0.3% of the face
against a spec that draws it over 14.3%** — the whole band falling to the
substrate side of the boundary.

The cause is that a nearest-colour classifier compares a RENDER against PRINT
colours with nothing holding the two at the same level, and our renders sit
5–15% below their spec. A render is a photograph of paint at an exposure rather
than the paint. Where the palette is wide that costs nothing; where two entries
are 0.086 apart it decides everything.

`_anchor()` reads a per-channel gain off the **substrate**, eroded clear of its
own edges — the spec draws that region and states its paint, so it is a grey card
the picture actually contains rather than a fitted correction.

| | before | after |
|---|---:|---:|
| `155-min` render~spec | 85.1% | **98.4%** |
| `155-min` render~ref | 80.5% | **89.0%** |
| `155-min` swing | ±7.5 | ±4.3 |
| rows with zero swing | 6 | **9** |

Nothing regressed: every one of the eleven improved or held on both agreement
figures, and **every ΔC is unchanged to the thousandth**, which is the point —
the anchor is applied to the classifier only.

**It is deliberately not applied to `colour_error_by_region`.** That figure asks
whether the renderer painted the colour it was told to, and anchoring the frame
to the spec is precisely how you erase its answer. The earlier attempt put a
grey-card gain in front of both and was reverted for costing Kamagra fourteen
points; the lesson was *where it belongs*, not that it was wrong.

The second illumination model changed with it, from a blur at a sixth of the face
to one at a half. The narrow blur is not a legitimate second opinion — it follows
the design, which is the defect this document already records against Kamagra's
colour error — and under an anchored classifier it is corrected twice over.

## Which illumination model, decided on the substrate

Anchoring left `59-min` Cialis swinging ±9.5 — the worst in the group, and now
the only figure of its kind. Both models had previously agreed at ~85.7% because
both were dominated by the same level offset; with that gone they disagreed, and
the disagreement is specific: the **plane** classifies 28.9% of Cialis's face as
the white swoosh where the spec draws 21.1%, while the wide **blur** lands on
21.8%.

Neither model is right everywhere, so neither can be the model. What settles it
without looking at the answer is how flat each leaves the **substrate** — a
surface the spec draws and whose paint it states, so anything still varying
inside it is the model's own error and nothing about the fields enters:

| | plane residual | blur residual | plane agrees | blur agrees |
|---|---:|---:|---:|---:|
| `59-min` Cialis | 0.0847 | **0.0662** | 88.6% | **98.1%** |
| `155-min` Imovane | **0.0296** | 0.0358 | **98.4%** | 94.1% |
| the other nine | — | — | within 0.1 of each other | |

**On both cartons where the two models differ at all, the one that flattens the
substrate better is the one that agrees better.** That is the whole of the
evidence for choosing per carton, and it is not circular: the residual never sees
a field.

`illumination` and `illumination_residual` are reported per row so the choice can
be checked rather than trusted.

### And the swing became the figure's own uncertainty again

Differencing against the REJECTED model reports the cost of an estimate the
substrate already showed to be worse — not how uncertain the figure is. The swing
is now the same model under a different arbitrary knob: the erosion the plane is
fitted through, or the radius the blur is taken at.

| | before anchoring | anchored, rejected-model swing | now |
|---|---:|---:|---:|
| `59-min` Cialis | ±0.2 | ±9.5 | **±1.1** |
| `155-min` Imovane | ±7.5 | ±4.3 | **±0.1** |
| worst in the group | ±7.5 | ±9.5 | **±1.1** |

Every carton now agrees with its spec at **96.9% or better**, and nine of eleven
do not move at all under the perturbation. The two tightest palettes are still
the two that move — 0.106 and 0.086 between substrate and highlight — but by a
point rather than by ten.

**ColourError still reads the plane, always.** It asks whether a region is the
colour it should be, so its illumination estimate must not be able to absorb the
design — a blur can, which is the defect recorded against Kamagra below. Every ΔC
in the table above is unchanged to the thousandth across both of these changes,
which is the check that the two axes stayed apart.

## `59-min` and `155-min`: what was ruled out along the way

Both were investigated for a build defect and neither has one. Measured deep
inside their regions, Cialis separates its two creams by 0.1055 against a spec
of 0.1057 and scores IoU 0.962 on the olive fields it actually draws; Imovane's
two greys come out 0.061 apart against a spec of 0.086 and a photograph of 0.073.

Nothing in the driver was changed for either.

## ΔC was reporting the exposure, not the paint

`64-min` Kamagra carried the worst colour error in the group at 0.189, with
`74-min` Viagra beside it at 0.191. Both are the SUBSTRATE, and both substrates
render at **exactly 0.87 times their spec on all three channels**:

| | spec | rendered | ratio |
|---|---|---|---|
| Kamagra `#E3DACD` | 0.890 0.855 0.804 | 0.775 0.745 0.701 | 0.87 0.87 0.87 |
| Viagra `#DEDEDB` | 0.871 0.871 0.859 | 0.760 0.760 0.750 | 0.87 0.87 0.87 |

A neutral scale is an exposure, not a colour. And the dark regions go the other
way: Kamagra's `#00463B` has a red channel of **zero** on the spec and 0.128 in
our render, because a lit surface in a studio does not return black.

Neither is the renderer painting the wrong colour and neither is a defect —
they are what a picture of paint does. But ΔC claims to ask *whether this region
is the colour it should be*, and on the two worst rows in the group it was
answering a different question.

`_response()` fits the picture's own gain and black level per channel across the
regions, and reports what is left:

| | worst ΔC | worst residual |
|---|---:|---:|
| `64-min` Kamagra | 0.189 | **0.024** |
| `340-min` Xanax SR | 0.149 | 0.014 |
| `155-min` Imovane | 0.093 | 0.013 |
| `272-min` Valium | 0.128 | 0.025 |
| `156-min` Xanax | 0.112 | 0.045 |
| `135-min` Ativan | 0.153 | 0.050 |
| `59-min` Cialis | 0.170 | 0.056 |

The fitted gains run 1.13–1.39 with lifts of −0.04 to −0.19: our renders are
darker and lower in contrast than the paint, consistently, across every carton
that can be fitted.

**Both figures are reported and neither replaces the other.** ΔC keeps its
meaning — a systematic exposure error is still visible in it, and would be
invisible in the residual. The residual answers what ΔC was being read as. That
distinction is the same one an earlier attempt got wrong by applying a grey-card
gain *in front of* ΔC and erasing its answer; here nothing is erased, the
response is simply named.

**Four cartons cannot be fitted and say so.** Two regions determine a line
exactly, so Viagra, Lexotanil, Modafinil and Ritalin report a dash rather than a
residual of zero they did not earn. Viagra is the one that matters: it holds the
group's largest ΔC at 0.191 and its substrate shows the same 0.87 neutral scale,
so the figure is almost certainly the same exposure — but this instrument cannot
prove it on two regions, and does not claim to.

At three regions the fit has one degree of freedom, so those residuals are
optimistic. Ativan, with four, is the only one with two.

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

Type — and that is now a division of labour rather than a gap.

Every figure above excludes dark pixels. It has to: the spec carries fields, our
render prints the label from the manifest, and scoring the glyphs would move this
number every time a string changed length. So nothing in this document says
anything about where the type sits, and reading these figures as if it did is the
mistake they invite.

The type rows themselves were measured in D-2b and reach the renderer through
contract 1.4 — 21 rows across the eleven, from three on Xanax down to none on
Cialis. **What compares them against the photograph is `scripts/type_qa.py`, and
its figures live in [`D7_TYPE_FIDELITY.md`](D7_TYPE_FIDELITY.md).** It found two
build defects on its first run that every number above was blind to, including a
carton printing two rows through one another.
