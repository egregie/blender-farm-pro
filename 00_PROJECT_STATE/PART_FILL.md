# A part is painted its cluster's colour, and on 41% of them that is the wrong colour

Phases 0 and 1 of the per-part-fill brief, from commit `9a6c886`. **The brief's
own edge case fired and the work stopped there.** Read-only: no code changed, no
spec, manifest or figure changed, `print_truth.json` untouched in all 28 folders.

The brief set out to recover three components misfiled `unrepresentable` because
`fill` lives on the field and a part has none. Phase 1 was to take the emission
threshold from the distribution of part-versus-cluster colour distance. The
distribution has no gap, the three candidates are not separable from anything,
and the reason is that they are not three cases. They are three of at least
thirty-one.

---

## Phase 0 — who reads "what colour is this region"

Seven sites on the project side, four in the driver. More than the brief listed;
`measure_type_rows.py` and `type_qa.py` were not named in it and both pair a
field's fill with a part's outline.

| file | site | what it does |
|---|---|---|
| `scripts/fit_design_spec.py` | `:731` | **producer** — emits `fill` from the cluster's colour |
| `scripts/fit_design_spec.py` | `:864` | `rasterise()` — `img.paste(f["fill"], …, region)`, per part, field's colour |
| `scripts/design_qa.py` | `:461` | builds the classification palette from `[f["fill"] for f in fields]` |
| `scripts/measure_type_rows.py` | `:527` | pairs field fill with part outline for `ink_within()` |
| `scripts/type_qa.py` | `:214` | the same pairing |
| `scripts/label_print.py` | `:210,266` | cluster colour for the labelling aid — display, not painting |
| `scripts/calibrate_render.py` | `:109` | synthesises a chart spec — producer |
| `render_driver.py` | `:454` | `_part_cache` carries `field.get("fill")` into **`_surface_fill()`** |
| `render_driver.py` | `:1027` | `_reverse_ink(dosage_block["fill"])` — a measured row's ink |
| `render_driver.py` | `:1768` | **one material per FIELD**, shared by every part in it |
| `render_driver.py` | `:1847` | emits `fill` into `--dump-scene` |

`design_coverage.py` does not read colour at all — it compares field indices —
which is why none of what follows shows up in `truth_agreement` or
`print_agreement`.

---

## Phase 1 — the distance, measured the project's own way

For every enumerated component of all 28 folders: the median of its RAW pixels,
exactly how `segment()` measures a cluster's `colour`, against the colour its
cluster reported. Euclidean in 0..1 sRGB — the same units as
`SAME_SURFACE_MAX = 0.08`, the threshold at which this project already declares
two clusters to be one surface.

Over the 75 components classified `print` — the ones that become the spec's
parts — the distances are:

```
0.000 0.000 0.000 0.000 0.000 0.004 0.004 0.005 0.007 0.007 0.007 0.009 0.009
0.009 0.014 0.014 0.016 0.018 0.020 0.020 0.021 0.023 0.024 0.024 0.024 0.025
0.026 0.028 0.029 0.037 0.042 0.043 0.046 0.055 0.057 0.058 0.059 0.060 0.064
0.068 0.072 0.073 0.075 0.077 0.083 0.094 0.095 0.099 0.101 0.111 0.129 0.134
0.149 0.151 0.152 0.182 0.189 0.196 0.219 0.219 0.259 0.286 0.290 0.297 0.325
0.359 0.374 0.434 0.455 0.455 0.542 0.542 0.560 0.673 0.739
```

A smooth ramp with no gap anywhere, running to **0.7389**.

### The three candidates are not special

| candidate | distance | its own colour | painted |
|---|---|---|---|
| `150_Waklert` `brand#1` | 0.6834 | `#0C6875` teal | `#AE6335` orange |
| `158_Klonopin` `highlight#1` | 0.4149 | `#887579` | `#52C147` green |
| `64_Kamagra` `highlight#19` | 0.0957 | `#041D16` | `#002F26` |

The largest is **not** the largest in the group: `152_Artvigil brand#1`, class
`print` and shipping today, sits at **0.7389**. The smallest, Kamagra's, is
below 47 of the 75 print parts. A threshold set at the lowest candidate
(0.0957) captures **28 further print parts**.

There is no threshold. The brief's edge case — *"порог отделяет больше трёх
компонентов — стоп и спросить, объём задачи другой"* — is the correct outcome.

### Verified by looking, not by the number

Four crops, top of the distribution, with the component's own colour beside the
colour the spec paints it:

| carton | part | class | own | painted | what the crop shows |
|---|---|---|---|---|---|
| `152_Artvigil` | `brand#1` | **print** | `#2D3336` | `#E05506` | a dark charcoal S-curve, painted orange |
| `157_Valium` | `type#0` | **print** | `#083BC7` | `#1F0A24` | a bright blue bar, painted near-black purple |
| `150_Waklert` | `brand#1` | unrepresentable | `#0C6875` | `#AE6335` | the teal Waklert badge, painted orange |
| `272_Valium_Brand` | `brand#0` | **print** | `#0179E1` | `#09517A` | a bright blue Roche hexagon, painted dark navy |

Three of those four are classified `print` and ship. The one labelled
`unrepresentable` is the same defect with a written reason beside it.

---

## What the measurement actually found

| | |
|---|---|
| print parts further from their paint than `SAME_SURFACE_MAX` | **31 of 75 — 41%** |
| their summed area | **109.6%** of face-equivalents, against 446.5% for all printed parts |
| cartons affected | **18 of 25** |

Roughly **a quarter of all printed design area in the group is painted a colour
that is not its own**, and it has been shipping.

Worst by area:

| folder | parts | area % |
|---|---|---|
| `149_Modalert` | 3 | 19.43 |
| `344_Modafinil_Generic` | 3 | 19.43 |
| `152_Artvigil` | 2 | 15.54 |
| `362_Hydrocodone` | 2 | 11.28 |
| `150_Waklert` | 2 | 10.25 |
| `59_Cialis` | 2 | 5.26 |
| `64_Kamagra` | 1 | 4.95 |
| `135_Ativan` | 1 | 4.01 |

### Why nothing caught it

`design_coverage.py` compares **field indices**, not colours: a part painted
orange where the reference is charcoal still agrees, because both sides say
"this pixel belongs to field 0". So `truth_agreement` and `print_agreement` are
blind to it by construction — the same blindness recorded in
`UNREPRESENTABLE_TRIAGE.md`, arriving from a second direction.

`design_qa` does compare colour, but it classifies the render against **the
spec's own palette**. Told to paint orange and painting orange, a render scores
a colour error of zero. The reference is what disagrees, and only `render~ref`
sees that — one figure among many, for a defect spread thinly over 18 cartons.

---

## What the task actually is

Not an optional per-part fill above a threshold. The honest shape is **every
part carries its own measured fill**, with the field's colour kept as provenance
— which is the variant the brief considered and set aside for having too large a
blast radius. The blast radius is the finding: it is large because the defect is.

Consequences, stated so the size is not a surprise:

- Every design carton's colours change. All of `design_qa`'s colour figures —
  `colour_error_by_region`, ΔC, `render~ref` — are a re-measurement event across
  25 cartons, not 3.
- `render_calibration.json` is measured against rendered patches and is not
  affected by which colour a field is told to paint; the driver fingerprint
  would still invalidate on the driver edit.
- Three of the eleven consumer sites decide a measured row's **ink** from the
  field's fill (`_surface_fill`, `ink_within` in two scripts). A part with its
  own paint changes what ink a row over it needs — the class of defect
  `_surface_fill` was built for in the first place.
- The three `unrepresentable` components stop being unrepresentable and want
  reclassifying, but they are now a footnote to the change rather than its
  purpose.
- `truth_agreement` will barely move, because it cannot see any of this. The
  acceptance figure has to be `render~ref` and looking at renders.

**Not started.** The brief authorised a narrow, three-component change and the
measurement says the narrow change does not exist. Deciding whether to take the
wide one is a scoping call, not a measurement.

---

## What is on disk

Nothing but this document. The probe that produced the distribution is
reproducible from the description above: enumerate components as `fit()` does,
take `np.median(raw[mask], axis=0)` per component against `group["colour"]`, and
compare in 0..1 sRGB.

`print_truth.json` unchanged in all 28 folders. Suite green at 392 tests.
