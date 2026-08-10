# R-006 — Where the time in a render actually goes

*Measured 2026-08-10. Blender 5.1, CYCLES, 2048², `blender.samples: 16`, this machine.*
*Decision: **batch mode is not built.** Reason below — it is a result, not a refusal.*

The question was how much of a ~30 s per-SKU render is Blender's own startup, because that
is the only part a persistent batch process could remove. The answer is **2.6 s, 9.3%**,
and the measured ceiling of an actual batch is lower still — **6.7%**.

## The five SKU

Three runs per SKU, decomposed by running the driver two ways rather than by
instrumenting it: `--dump-scene` returns before `setup_render()`, so it prices boot plus
scene build; the ordinary invocation prices everything.

    startup = a no-op Blender launch      scene = dump-scene - startup      render = full - dump-scene

| SKU | template | total | startup | scene | render | startup share |
|---|---|---:|---:|---:|---:|---:|
| `1-min` | T1 | 28.2 s | 2.6 s | 0.3 s | 25.3 s | 9.2% |
| `111-min` | T3 | 26.8 s | 2.6 s | 0.2 s | 24.0 s | 9.7% |
| `10-min` | T_BOTTLE_BOX | 28.0 s | 2.6 s | 0.2 s | 25.2 s | 9.3% |
| `144-min` | T_VERT_VIAL | 27.6 s | 2.6 s | 0.3 s | 24.7 s | 9.4% |
| `352-min` | T1_LARGE | 28.7 s | 2.6 s | 0.2 s | 25.9 s | 9.1% |

Boot floor measured three times at 2.60 / 2.61 / 2.64 s; the minimum is used. Scene build
is 0.2–0.3 s across every shape in the catalogue — building the carton, its text objects,
the barcode geometry, the lights and the camera costs **one percent** of a render.

## The batch ceiling, measured rather than modelled

Subtracting a boot floor assumes boot is the *only* per-process cost. Cycles could plausibly
compile kernels or initialise a device once and skip it afterwards, which subtraction would
miss. So three SKU were run through one Blender process against the same three as three
invocations:

| | `1-min` | `111-min` | `10-min` | total |
|---|---:|---:|---:|---:|
| three invocations (what Stage 2 does today) | 28.2 s | 26.2 s | 28.4 s | 82.9 s |
| one process, three SKU | 25.4 s | 23.9 s | 25.4 s | 77.3 s wall |

**Saved: 5.5 s of 82.9 s = 6.7%, i.e. 1.84 s per SKU.** The per-SKU times inside the batch
are flat — 25.4 / 23.9 / 25.4, no first-render penalty — so there is no warm-process effect
beyond boot. Model and measurement agree.

Across the whole catalogue that is **~12 minutes off a ~3 h pass**, in exchange for holding
391 renders inside one long-lived process, where a single bad manifest takes the run down
with it instead of one SKU. Not worth it.

## Where the time is instead

The sample count was swept on `1-min` at 2048² to separate fixed cost from sampling:

| samples | 1 | 4 | 16 | 32 | 64 |
|---|---:|---:|---:|---:|---:|
| total | 19.6 s | 21.2 s | 28.2 s | 37.6 s | 57.6 s |

A line through 4–64 fits every point within 0.6 s: **0.607 s per sample, 18.8 s fixed.**
Re-rendering with the denoiser disabled (via a `render_pre` handler, nothing in the driver
changed) costs **13.3 s** instead of 28.2 s, which places the denoiser at ~14.9 s and leaves
~1 s for Cycles' device init, BVH build and PNG save together.

| component | cost | share |
|---|---:|---:|
| Blender process startup | 2.6 s | 9% |
| scene build | 0.3 s | 1% |
| Cycles init + BVH + save | ~1.0 s | 3% |
| sampling, 16 samples | ~9.7 s | 34% |
| **OpenImageDenoise** | **~14.9 s** | **53%** |

**More than half of every render is the denoiser** — 5.7× the process startup that this
task was sent to price, and 15× the BVH build that `CLAUDE.md` used to name alongside it.

This is not an argument for switching it off. The 60.6 dB at 16 samples is a *denoised*
figure, and `CLAUDE.md` already records that the denoiser rather than the sample count is
what carries the image. It is an argument that if the catalogue pass ever needs to be
faster, GPU denoising is the lever — worth ~1.6 h of a 3 h pass, eight times what batch mode
offers — and cutting samples is not: at zero samples a render still costs 19 s.

## Corrections to what was written down

- **~67 s per SKU → 27.9 s** (mean of the five above). A full 391-SKU pass is **~3 h 02 m**,
  not ~7 h. The 16-vs-64 comparison the figure came from still holds in shape (28.2 s vs
  57.6 s, ~2×); only the absolute numbers moved.
- **"Roughly 45 s of each render is fixed cost (startup, BVH build, denoiser)"** — fixed cost
  is 18.8 s, and BVH build is ~1 s of it, not a share worth naming.
- **"Roughly 20 s of every render is fixed startup cost, about 2 h of overhead across the
  catalogue"** (`CURRENT_STATE.md`) — startup is 2.6 s and the catalogue-wide overhead is
  ~17 minutes.

## Reproducing

Harness in the session scratchpad (`measure_startup.py`, `measure_batch_ceiling.py`);
nothing in the project was modified and no render was written into
`02_processing/blender_test_renders/`. Re-measure after any change that adds glass, metal or
real global illumination — and after any change to the denoiser, which is now known to be
the dominant term.
