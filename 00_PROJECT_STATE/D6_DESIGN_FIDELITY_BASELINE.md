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

| SKU | folder | spec~ref | render~spec | render~ref | worst ΔC |
|---|---|---:|---:|---:|---:|
| `308-min` | Lexotanil | 86.3% | **99.6%** | **97.0%** | **0.094** |
| `135-min` | Ativan | 91.9% | 97.4% | 88.6% | 0.128 |
| `64-min` | Kamagra | 88.5% | 92.7% | 52.0% | 0.497 |
| `155-min` | Imovane | 89.8% | 91.7% | 85.4% | 0.130 |
| `59-min` | Cialis | 88.7% | 89.6% | 79.5% | 0.199 |
| `404-min` | Ritalin | 79.4% | 87.5% | 69.6% | 0.406 |
| `74-min` | Viagra | 91.2% | 84.8% | 70.0% | 0.200 |
| `340-min` | Xanax SR | 92.9% | 77.7% | 69.6% | 0.181 |
| `272-min` | Valium | 87.2% | 75.2% | 63.7% | 0.551 |
| `156-min` | Xanax | 88.7% | 74.9% | 58.0% | 0.618 |
| `344-min` | Modafinil | 85.1% | 19.4% | 24.3% | 0.118 |

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

- **`156-min` 0.618, `272-min` 0.551, `404-min` 0.406** — the largest colour
  errors, and all three are cartons whose "brand field" D-2 already reported as
  mostly TYPE rather than a colour field (brand IoU 0.459, 0.786, none). The
  spec asks for a field where the real carton has words; the renderer leaves
  substrate there. The fix is in the fitter, not the driver.
- **`64-min` Kamagra: 92.7% against its spec, 52.0% against the photograph.**
  Those two cannot both be right alongside a spec that scores 88.5%. Unexplained,
  and the most interesting row in the table.
- **`308-min` Lexotanil at 99.6% / 97.0%** is what the pipeline does when the
  design is flat fields and straight edges. It is the ceiling the curved cartons
  are being measured against.

## Not measured here

Type. Every figure above excludes dark pixels, because our render prints the
label from the manifest and the spec carries no type rows. The brand size and
position, the ingredient row and the missing form line are D-2 measurements that
were never taken — visible in every `.qa.png` strip, absent from every number.
