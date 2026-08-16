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

*Re-measured 2026-08-16, after the scored-mask fix, the measured transfer curve,
the ink rim, the seam and the outline repair — all five below. Type work keeps
moving these figures too, because moving a label changes which pixels are
excluded.*

| SKU | folder | spec~ref | render~spec | **worst field** | render~ref | worst ΔC | residual | swing | on-line |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `344-min` | Modafinil | 93.9% | **100.0%** | **100.0%** | 95.5% | 0.062 | — | ±0.0 | |
| `74-min` | Viagra | 95.0% | **100.0%** | 99.9% | 94.4% | 0.188 | — | ±0.0 | |
| `308-min` | Lexotanil | **99.1%** | **100.0%** | 99.9% | **98.5%** | 0.091 | — | ±0.0 | |
| `404-min` | Ritalin | 95.7% | **100.0%** | 98.6% | 98.4% | **0.058** | — | ±0.0 | |
| `272-min` | Valium | 91.1% | **100.0%** | 98.4% | 96.6% | 0.119 | 0.025 | ±0.0 | |
| `340-min` | Xanax SR | 95.0% | 99.9% | 96.8% | **98.6%** | 0.129 | **0.010** | ±0.0 | |
| `64-min` | Kamagra | 90.5% | 99.1% | 96.4% | 86.9% | 0.180 | 0.012 | ±0.0 | |
| `155-min` | Imovane | 93.7% | 99.4% | 96.1% | 90.5% | 0.082 | 0.009 | ±0.1 | **0.015** |
| `59-min` | Cialis | 88.2% | 99.0% | 96.0% | 82.0% | 0.165 | 0.054 | ±1.2 | |
| `135-min` | Ativan | 89.6% | 99.4% | 94.2% | 93.3% | 0.144 | 0.047 | ±0.0 | **0.017** |
| `156-min` | Xanax | 93.2% | 99.9% | **91.6%** | 95.0% | 0.106 | 0.056 | ±0.0 | **0.013** |

`residual` is ΔC once the picture's own exposure and black level are taken out —
see below. A dash is a carton with too few regions to fit them.

**The table is sorted by worst field, and that is not the order agreement gives.**
Ritalin holds the group's best agreement on its third-worst field; Cialis, the
worst agreement, has the second-best fields. Agreement is area-weighted and a
substrate is 55–99.9% of these faces, so it is largely a statement about the
board. Read the field column for whether a design was built.

**`swing` is the agreement figure's own uncertainty**, measured rather than
assumed: the same classification run under a second illumination model, on
identical pixels. It is not an error bar on the carton — it is how much of the
number is the measurement rather than the render.

## An outline that crosses itself is not a region — and this one reached the packshot

**The first defect in this sequence that is in the RENDER rather than in the
instrument.** Everything above changed what a figure measured; this changed the
picture.

Xanax SR's `brand` read **75.2% at 100.0% recall and 75.2% precision** — our
magenta strictly *contained* the spec's and was a third larger. It was not near
the panel either: the false pixels sat a median of 48 pixels away, and they were
genuinely magenta in the render, not a classification artefact.

Its brand outline has eight points, and one of them does not belong to the
others:

```
[0.976, 0.227], [0.980, 0.707], [0.979, 0.490], [0.856, 0.484],
[0.853, 0.321], [0.853, 0.233], [0.975, 0.238], [0.976, 0.229]
```

Seven describe a panel spanning v 0.23–0.49. The second, at **v 0.707**, sits
far below all of them — the same one-pixel thread artefact `fills_its_box`
already guards against, traced off the carton's right edge.

That makes the ring self-intersecting, and **a self-intersecting ring is not a
region**: it is a drawing instruction whose meaning depends on the fill rule.
This project's two sides use different ones. `rasterise()` fills with PIL's
even-odd scanline, which is what every spec's `verification.pixel_agreement` was
measured against, and drops the sliver. The driver hands the same points to a
Blender curve with `fill_mode = BOTH`, which tessellates them and **filled the
triangle back to the panel — 1.33% of the face** against a measured excess of
1.07%. Our packshot carried a magenta wedge the real carton does not have.

Nothing said so. The renderer was obeying the contract; the contract was
ambiguous.

**Eight parts across six of the eleven cartons are tangled this way** — Cialis's
highlight, both of Kamagra's, two of Ativan's, Imovane's highlight, and both of
Xanax SR's.

`simple_ring()` repairs them by dropping the fewest vertices that untangle the
ring, preferring the removal that changes the enclosed area least, and only
vertices belonging to a crossing edge are candidates. One to four vertices per
part. Against the original's even-odd raster the repaired rings score **0.972 to
0.9999 IoU**, so this preserves the region that was verified rather than
redrawing it.

It runs in `load_design()` — the single loader every consumer goes through, so
the manifest builder and the QA raster see the same rings. **The spec file on
disk stays as traced**: it is a measurement of a photograph, and the repair
belongs at the contract boundary, not in the record. Where a ring was repaired
the part carries `simplified_from`, so it is visible rather than quiet.

`validate_manifest()` now rejects a tangled outline by name, on write and on
load, because JSON Schema cannot express "does not cross itself" and a manifest
written before this would otherwise render the wedge again in silence.

| | before | after |
|---|---:|---:|
| `340-min` worst field | 75.2% | **96.8%** |
| `340-min` render~spec | 98.5% | 99.9% |
| `340-min` render~ref | 97.2% | **98.6%** — best in the group |
| `340-min` worst ΔC | 0.141 | 0.129 |

The other five cartons moved by a tenth of a point: their tangles are small
local crossings in outlines of 40–120 vertices, where even-odd and tessellation
disagree about very little.

## The seam between two regions was counted as the third

Ativan's `highlight` read **63.8%** at 92.2% recall and 67.4% precision — the
same shape of failure as Xanax, from the same cause one layer up.

`#8E9DA0` is a **42% blend of its substrate `#C2C2B6` and its `secondary_1`
`#50697C`**. Ativan has four regions, a brand in three parts and 175 vertices,
so **6.9% of its face is within two pixels of a boundary** — the most in the
group — and **94.0% of its false highlight pixels lay in that band**.

The asymmetry causing it is structural rather than anyone's mistake:
`rasterise()` fills polygons hard-edged, and our render arrives through a
Lanczos rectification. The target has a step where we have a ramp, the ramp
passes through every colour between the two fills, and where a palette entry
lives there it collects the whole boundary.

`_seam()` drops it, one pixel either side. Again the width is measured: r=1
takes the group's mean field from 90.1% to 95.2%, and r=2, 3, 4 give 95.3%,
95.2%, 95.1% — it saturates and then decays. Costs 0.1–4.1% of scored pixels.

| SKU | worst field before | after |
|---|---:|---:|
| `135-min` Ativan | 63.8% | **94.3%** |
| `156-min` Xanax | 82.7% | 91.6% |
| `64-min` Kamagra | 90.7% | 96.4% |
| `344-min` Modafinil | 98.4% | **100.0%** |
| `340-min` Xanax SR | 73.8% | 75.2% |

**Five cartons now agree with their spec at 100.0%**, and again nothing
regressed on any column. ΔC improved on six, because the seam was in the region
means too — Kamagra's residual halves, 0.024 → 0.012.

### Two things checked before throwing pixels away

**It does not blind the figure to a misplaced field.** Shifting our own
classification two pixels and re-scoring with the seam excluded: Ativan 94.4% →
59.5%, Modafinil 100.0% → 65.2%, Valium 98.4% → 64.6%, Ritalin 98.6% → 70.2%. A
one-pixel exclusion cannot hide a two-pixel error, and a synthetic test pins the
arithmetic — widen the exclusion to three pixels and the test's offset bar reads
1.0 instead of 0.9.

**It does not hollow a field out.** Every field keeps at least 68.9% of itself
and all but Ativan's highlight keep 83% or more. `field_kept_min` travels in the
report so a field measured on a sliver would say so rather than report a
confident number about very little of itself.

### A softer target was tried instead, and is worse

The spec rasterised at 4× and box-averaged down, so both sides carry a ramp and
no pixels are discarded. It helps — but much less: Ativan 70.4% against the
exclusion's 94.4%, Kamagra 93.8% against 96.4%. A box-filtered 4× raster is not
the ramp a Lanczos rectification leaves, so the two softnesses still disagree.
Recorded because it is the obvious alternative and the reason it loses is not
obvious.

## The ink's rim was being counted as a field

Xanax's `highlight` read **49.8%** at 93.0% recall and 51.8% precision — nearly
all of the field found, and about twice as much area claimed as the spec draws.

The false pixels were not scattered. **99.8% of them lay within two pixels of
dropped ink**, and they came to 0.80% of the face against a field that is 0.93%
of it. The reason is in the palette: `#968974` is a **44% blend of the substrate
`#E8DCB4` and the brand `#2C1F2A`, to within 0.013**. Every antialiased glyph
edge on the carton averages to exactly that colour, so every glyph edge was
counted as the field.

The dark cut was already dropping the ink. It was not dropping the ink's rim,
and a pixel straddling a glyph edge is a mixture of ink and board — evidence
about neither, and on this palette evidence *for* the highlight.

**The width is measured, not chosen.** A one-pixel rim takes the group's mean
field from 80.1% to 90.1%; two pixels reach 90.3% and three go no further. The
benefit saturates at the resampling width, which is all this is — the face is
rectified to 1100px from a 2048 render. It costs 0.5–1.7% of the scored pixels,
reported as `edge_dropped` rather than left silent.

| SKU | worst field before | after |
|---|---:|---:|
| `156-min` Xanax | 49.8% | **82.7%** |
| `344-min` Modafinil | 75.8% | **98.4%** |
| `272-min` Valium | 81.8% | **97.3%** |
| `404-min` Ritalin | 86.8% | **97.0%** |
| `74-min` Viagra | 88.1% | **98.8%** |
| `340-min` Xanax SR | 65.8% | 73.8% |
| `135-min` Ativan | 58.2% | 63.8% |

**Nothing regressed on any column** — agreement, worst field, render~ref and ΔC
all improved or held on all eleven, and three cartons now read 100.0% against
their spec. ΔC moved too, on seven of them, because the rim was contaminating
the region means as well.

This also corrects the reading in the commit before it. Ritalin, Valium,
Modafinil and Viagra were recorded there as *losing* field IoU to the transfer
curve, and the losses were real numbers attributed to the wrong cause: they were
glyph rim, which the curve had made slightly more visible. All four now sit far
above where they were under either classifier.

### The pairwise separability figure cannot see this

`palette_closest_pair` asks whether two entries can be told apart. Xanax has the
group's **second-widest** closest pair, 0.522, and is the carton this broke.

The condition that matters is an entry lying **on the segment between two
others**, because that is what every boundary pixel between those two averages
to. `palette_on_line` reports it, and the evidence has a gap in it: three
cartons sit at 0.013–0.017 and the next is 0.064.

| SKU | closest pair | on the line | which |
|---|---:|---:|---|
| `156-min` Xanax | 0.522 | **0.013** | highlight on substrate–brand |
| `155-min` Imovane | 0.086 | **0.015** | substrate on brand–highlight |
| `135-min` Ativan | 0.265 | **0.017** | highlight on substrate–secondary_1 |
| `59-min` Cialis | 0.106 | 0.064 | substrate on brand–highlight |
| `64-min` Kamagra | 0.122 | 0.084 | brand on substrate–highlight |

It is **not a gate**, because nothing can be done about it from the renderer's
side — the colours are the carton's. It is reported so that Ativan's 63.8% and
Xanax's 82.7% are read as the palette rather than as the build.

## The classifier now compares against a chart, not against the paint

Kamagra's `highlight` read **0.084** — the group's worst field by a factor of
five, on a carton whose renderer builds the field correctly.

Its two greens are `#00463B` and `#002F26`, 0.122 apart. Measured inside each
region, our render separates them by 0.089 — it built both. But both arrive with
a **red channel near 0.135 against a spec that says 0.000**: a lit surface does
not return black. That displacement is shared, so it does not distinguish them,
and at 0.145 it is larger than the 0.089 gap it has to preserve. The darker
green lands nearer the lighter one's *paint*, and 89% of the field is classified
as `brand`.

`_anchor` cannot reach it. It reads one known surface, so it can fit one
parameter per channel, and a gain has no black level. The transfer needs two.

**So the transfer is measured.** `scripts/calibrate_render.py` renders each
carton a second time with its design replaced by a chart of 19 known patches —
same geometry, same rig, same exposure, no design present — and reads the curve
off it. The chart says three things worth stating:

- the transfer is **per channel and independent of the others**: `#400000`
  renders `(0.251, 0.133, 0.133)`, its red where the ramp puts 0.251 and its two
  empty channels where the ramp puts 0. One curve is therefore enough;
- it is **not affine**. Kamagra's ramp runs 0.000→0.133, 0.126→0.172,
  0.251→0.243, 0.439→0.377, 0.659→0.573, 0.878→0.756, 1.000→0.859. A straight
  line through that leaves a residual of 0.046; the interpolated curve leaves
  0.013 over the twelve colour patches, which is the channel-to-channel bleed a
  1-D model cannot carry;
- the **black lift is a rig constant**: 0.133–0.141 across all eleven cartons,
  sd 0.0024. The white end is not — 0.859 to 0.936 — because exposure is metered
  per carton shape.

The palette is then mapped **forward** into the render's space and the classifier
compares there. Forward, not inverted, so it cannot be mistaken for correcting
the render — which is how ColourError's answer would be erased.

**A curve fitted on the group's own regions would also have worked, and was not
shipped.** Holding each carton out in turn, it classifies all thirty region
medians correctly against one for nearest-paint. It is still a transform fitted
to the regions being judged: it can absorb a real build error as calibration and
then the instrument agrees with whatever the renderer did. The chart costs one
render per carton and removes the objection.

### Both halves are load-bearing

The curve alone **broke Imovane**: worst field 91.9% → 76.2%, swing ±0.1 → ±2.9.
Its substrate and highlight are 0.086 apart, and the chart is read on the face as
it comes while the frame being classified has had its illumination divided out —
`flatten_on_substrate` renormalises to the estimate's mean rather than preserving
the level. The residual is 0.02–0.03, which is a third of the gap Imovane's
classifier has to resolve.

So `_refer_to_substrate()` puts the predicted appearance on the frame's own
level, using the same grey card `_anchor` reads. **The curve supplies the shape,
the substrate the level**, and each carton that needs one is broken by the other:

| | paint + anchor | curve alone | curve × substrate |
|---|---:|---:|---:|
| `64-min` Kamagra worst field | 8.4% | 90.7% | **90.7%** |
| `155-min` Imovane worst field | 91.9% | 76.2% | **91.9%** |
| `155-min` Imovane swing | ±0.1 | ±2.9 | **±0.1** |
| worst field in the group | 8.4% | 50.0% | **49.8%** |
| mean field | 73.6% | 78.9% | **80.1%** |

### What it cost, and why the cost is smaller than it reads

Five cartons lose field IoU: Ritalin 92.6% → 86.8%, Valium 85.5% → 81.8%,
Modafinil 78.6% → 75.8%, Xanax SR 67.2% → 65.8%, Viagra 88.7% → 88.1%. All five
are **thin type-shaped fields of 1.5–3% of the face**, where almost every pixel
is an edge.

Read as *area* rather than as IoU, the direction reverses:

| SKU | field | spec draws | anchor found | curve finds |
|---|---|---:|---:|---:|
| `64-min` | brand | 36.15% | 50.90% | **37.00%** |
| `64-min` | highlight | 16.69% | 1.50% | **15.58%** |
| `404-min` | type | 1.63% | 1.65% | 1.78% |
| `272-min` | type | 1.54% | 1.69% | 1.79% |
| `344-min` | type | 2.00% | 2.50% | 2.60% |

The losses are a thin field claimed a pixel wider — a tenth of a point of face
area. The gain is a fifth of a carton being found at all. And each field's own
median now sits **0.004 to 0.028** from its predicted appearance, against 0.34 to
1.00 from the substrate's: the targets are essentially exact where the field is
unambiguous.

**The calibration is refused if it is stale.** `render_calibration.json` carries
a fingerprint of the driver plus the engine, sample and resolution settings, and
`load_curve()` exits rather than applying a curve measured against different
output. Same reasoning as `render_fresh`'s refusal to compare against a stale
PNG, and a missing calibration is fatal rather than a silent fall back to the
uncalibrated comparison.

## A dark field was scored only where we got it wrong

The instrument's ranking was inverted, and one line of masking did it.

The dark cut exists so printed **type** stays out of the figures: our render
prints it, the spec deliberately does not carry it, and scoring it would measure
the type grid instead of the design. It drops any pixel whose brightest channel
is under 0.30. But eight of the eleven cartons carry a **field** that dark, and
the cut took those too — dropping each one *exactly where our render painted it
correctly*, because that is where our render is dark. What survived was the
misses, and the field was scored over them alone.

`404-min` Ritalin is the demonstration. It held the group's **best** agreement,
99.87%, on an IoU of **0.043** over its only field. Both figures were honest
arithmetic over the wrong set of pixels.

Contract 1.5 had already fixed this for ΔC — "whether a pixel is scored depends
on what the spec expects there, not on how bright it happens to be" — and the
fix was applied to `_colour_error` and `_response` and **not** to `_agreement`,
which is the one the report is read by. `scored_mask()` is now the single place
that decides, and all four axes take it.

| SKU | field | fill | IoU before | after |
|---|---|---|---:|---:|
| `404-min` | type | `#2E1D3C` | 0.043 | **0.926** |
| `156-min` | brand | `#2C1F2A` | 0.024 | **0.955** |
| `272-min` | type | `#1D2C30` | 0.106 | 0.855 |
| `64-min` | brand | `#00463B` | 0.185 | 0.696 |
| `340-min` | type | `#48323D` | 0.241 | 0.692 |
| `344-min` | type | `#43384B` | 0.781 | 0.786 |
| `64-min` | highlight | `#002F26` | 0.000 | 0.084 |

**Every field the cut could not reach is unchanged to three decimals** — Cialis
0.947/0.944, Viagra 0.887, Lexotanil 0.974 — which is what says the change is
the defect and not a recalibration. Mean field IoU across the group: 0.601 →
0.791.

**Kamagra pays for it and the bill is real.** Its two greens are 53% of its
face and the instrument was seeing 3% of them; scored, its agreement falls
**96.9% → 84.0%** and render~ref 94.8% → 86.3%. The earlier claim that every
carton agreed with its spec at 96.9% or better was resting on this bug. What is
left is the near-degenerate pair — `#00463B` against `#002F26`, 0.122 apart —
which the anchor was not enough to separate and which `SEPARABLE_MIN = 0.08`
still calls separable. That threshold was fixed from Modafinil's four-level
pair; Kamagra is evidence 0.122 is not far enough either. Open.

**What the cut still cannot answer.** A dark pixel where the spec draws the
light substrate is either a dark field overrunning its outline or the printed
type the spec does not carry, and nothing in the colour separates them. It is
dropped either way, so a dark field's overspill costs nothing and its IoU
degenerates to **recall** — the figure catches a field placed short, not one
placed wide. Light fields are still scored both ways. Stated in a test rather
than left to be rediscovered.

`scripts/design_qa.py` had no tests at all before this; `tests/test_design_qa.py`
is synthetic, because the properties are about masks and index maps and stating
them in pixels is clearer than rendering a carton to demonstrate one.

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

*Since the transfer curve above, the anchor no longer stands in for the level of
the whole comparison — one known surface can only ever fit a gain, and Kamagra
needed a lift. What survives is exactly the half a grey card can answer: the
curve supplies the shape and `_refer_to_substrate()` puts it on the frame's own
level. Imovane still needs that half, and demonstrably: the curve without it read
76.2% at ±2.9.*

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

Nine of eleven do not move at all under the perturbation. The two tightest
palettes are still the two that move — 0.106 and 0.086 between substrate and
highlight — but by a point rather than by ten.

*This section once read "every carton now agrees with its spec at 96.9% or
better". It did not: Kamagra's 96.9% was 53% of its face being dropped before it
could disagree. See the scored-mask section above.*

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
