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

*Re-measured 2026-08-14 after the fitter fix below.*

| SKU | folder | spec~ref | render~spec | render~ref | worst ΔC |
|---|---|---:|---:|---:|---:|
| `404-min` | Ritalin | 95.1% | **99.8%** | **97.5%** | **0.058** |
| `308-min` | Lexotanil | **99.1%** | 99.6% | 97.0% | 0.094 |
| `74-min` | Viagra | 94.4% | 99.5% | 93.2% | 0.195 |
| `156-min` | Xanax | 94.8% | 99.4% | 95.1% | 0.122 |
| `344-min` | Modafinil | 87.5% | 99.1% | 93.5% | 0.126 |
| `272-min` | Valium | 87.4% | 98.4% | 93.7% | 0.132 |
| `340-min` | Xanax SR | 92.2% | 97.3% | 93.5% | 0.162 |
| `135-min` | Ativan | 91.9% | 97.4% | 88.6% | 0.126 |
| `64-min` | Kamagra | 88.5% | 92.7% | **52.0%** | 0.422 |
| `155-min` | Imovane | 93.7% | 91.7% | 85.4% | 0.130 |
| `59-min` | Cialis | 88.7% | 89.6% | 79.5% | 0.199 |

Ten of eleven now build their spec to better than 89%, and seven to better than
97%. `64-min` is the one row left where the three figures cannot all be true at
once.

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
