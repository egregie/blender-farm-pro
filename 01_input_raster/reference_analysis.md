# Reference Image Analysis

> Basis for Blender scene/template design. Grounded in **direct visual inspection**
> of 7 of the 9 copied references (not inferred from code alone) — see §7 for
> exactly which. Source: `01_input_raster/reference/` (curated from
> `01_input_raster/gemini_renders_final/`, 389 finished Gemini renders forked
> from PharmaGen PRO).

## 1. Composition & framing

Every image, across every template, uses the **same compositional recipe**:
- **3/4 isometric view.** Exactly two faces of the carton are visible: the front
  (facing camera, slightly right-of-center) and the left side panel (foreshortened,
  showing depth). The top face is barely visible as a thin sliver — the camera
  is close to eye-level with the box, not looking down on it.
- **Single object, dead-center, generous negative space.** The box occupies
  roughly the middle 45–55% of the frame vertically; there is no cropping, no
  secondary props, no hands/context — pure packshot isolation.
- **No visible horizon line.** The background is a single, seamless white plane
  with no floor/wall transition visible in frame.

**Blender implication:** this matches the driver script's current `TRACK_TO`-camera
approach (§9 of the Blender Roadmap) reasonably well, but the *degree* of
isometric tilt should be tuned against these references rather than assumed —
see §8.

## 2. Camera & lens character

- Very **shallow apparent perspective distortion** — edges of the box stay close
  to parallel, consistent with a longer lens (matches the documented `85mm`
  calibration in `06_docs/DESIGN_RATIONALE.md`/the Gemini prompt templates), not a
  wide-angle look.
- **Depth of field is essentially infinite** — both the near (front-bottom) and
  far (top-back) edges of the box are equally sharp. No visible bokeh, no
  falloff. This is a meaningful, checkable difference from real product
  photography (which usually shows *some* falloff at f/8 on a macro subject) —
  either the "f/8" spec in the prompt isn't being obeyed literally by the image
  model, or the effective focal distance is far enough that DOF is negligible
  at this scale. **For Blender: do not over-apply DOF blur** trying to match a
  literal f/8 — these references read as everything-in-focus.

## 3. Lighting

- **Soft, broad, high-key studio lighting.** No hard specular highlights, no
  visible catchlight shapes, no hard-edged shadows anywhere on the carton itself.
  Shading is a very gentle gradient across each face (front face slightly
  brighter toward camera-left, side face noticeably darker/cooler — a soft
  falloff, not a hard light/shadow boundary).
- **Contact shadow is minimal to nearly absent.** None of the 7 references show
  a strong, sharp ground shadow — at most a very faint, soft darkening directly
  under the box. This is a **deliberate, consistent stylistic choice** (a "product
  floating on white" look), not an oversight.
- **No colored light spill** — even on strongly colored accent stripes (deep
  magenta, medical blue, mustard yellow), the white body immediately adjacent
  to the stripe shows no visible bounce-color tint.

**Blender implication:** this is the single most important, concrete, and
actionable finding — my Phase-1 lighting rig (documented in the Blender Roadmap
§9) originally overexposed the whole frame at 800W/300W and, even after the
fix to 25W/8W, still produces a **visible ground shadow** the references don't
show. §8 below has the specific tuning recommendation.

## 4. Material & surface

- **Matte, uncoated cardboard/cardstock** — no gloss, no reflections, no
  visible print sheen. Roughness reads high (~0.6–0.8 in a Principled-BSDF
  sense), not the ~0.35 currently hardcoded in `render_driver.py`.
- **Crisp, sharp box edges and visible fold/crease lines** at every panel
  corner — a subtle but present bevel/crease, not perfectly knife-sharp CG edges.
- **No visible paper grain/texture at this resolution** — surface reads smooth,
  not fibrous.

## 5. Color system (confirms the documented "SURFACE COLOUR MANDATE")

Every single reference, regardless of `branding.palette.primary`, has a **pure
white carton body**. Brand color appears in exactly two places, never more:
1. **A solid accent stripe along the bottom edge of the front face**, spanning
   the full width and **2.9–6.1% of the front-face height (median 4.0%)** —
   pixel-measured across all 9 references, resolving the question §9 raised about
   the earlier eyeballed "8–12%". That estimate was roughly double the truth; the
   driver enforced it and produced a band ~50% too thick on T1 and ~135% too
   thick on `T_VERT_VIAL`. In millimetres the band runs 2.2–5.8mm, which brackets
   the ~4mm of Row 6. The stripe does **not** wrap onto the side panel: it starts
   at the near vertical corner and runs to the front face's right edge. Color =
   `palette.accent` (verified against source JSON: T1's `1-min` stripe is the
   dark magenta `#6B2D5C` from its passport; consistently darker/more saturated
   than `palette.primary`, never the lighter primary tone).
2. **A colored square badge in the top-right corner of the front face**, filled
   with **`palette.primary`** — the *lighter* of the two, the complement of the
   stripe's `accent`. Confirmed by sampling the badge in all 9 references against
   each SKU's passport palette: T1's badge means (207,157,155) against
   `#DDA7A5`, T3's (214,89,65) against `#E2583E`, `T_MULTIPACK`'s (28,100,149)
   against `#005A9C`. 9/9 match primary, none match accent — worth stating
   explicitly, because "brand colour" alone leaves the two interchangeable and
   swapping them is the obvious way to get this wrong. Measured geometry: side
   **~25% of the shorter front-face edge** (21–37% across the set — tighter than
   sizing from face height alone, 12–29%, or from face width, 7–37%), inset **~5%
   of face width** from the right edge and **~3% of face height** from the top.
   Each badge carries an abstract geometric line-art motif (varies per SKU: an
   X-hatch lattice, a wireframe diamond/polyhedron, a filled ring/circle, a
   filled overlapping-circles mark, an angular network pattern) — drawn as a
   *dark* line over the badge fill in the samples measured, not white. The badge
   is **either filled-solid or outline-only** depending on the SKU — no obvious
   rule was identified from 7 samples for which style is used when; flagged as
   an open question in §7.

This directly confirms the `[SURFACE COLOUR MANDATE]` rule already documented
in `src/passport_generator.py`'s prompt templates and `06_docs/DESIGN_RATIONALE.md`
— genuinely useful to have visually verified, not just read in code.

## 6. Typography & label layout

> **Measured, and now built.** The four text rows below are rendered by
> `render_driver.py` as real Blender text objects. Measured positions in the
> front face's own coordinates (u across, v down), reference → render:
> brand v 0.110 → 0.128, ingredient v 0.460 → 0.478, dosage/count row
> v 0.810 → 0.813, unit-count right edge u 0.946 → 0.949.
>
> Type size follows **two laws**, not one: the brand name scales with the carton
> (6.3-30.6mm across templates, but a steady 0.131-0.209 of face height), while
> the small print holds an absolute size (bottom row 4.4-5.5mm on eight of nine,
> though it varies 3.5x as a fraction of the face). The side panel is built too —
> see the note under it. Row 3, the braille, is **not**.

A consistent grid appears on every front face, top to bottom:
1. Product/brand name — **bold, large**, up to 2 lines (e.g. "Atomoxetine
   Generic", "Test Pack L-VC").
2. Active ingredient / subtitle — **regular weight, smaller**, 1 line (e.g.
   "Atomoxetine", "Naltrexone", or a combo string like "Sildenafil / Tadalafil
   / Vardenafil (Specimen Mix)").
3. A **Braille dot pattern** — decorative/regulatory row, consistently
   positioned directly under the ingredient line, consistent dot density
   across all samples.
4. A bottom row split **dosage (bottom-left, bold) / unit count (bottom-right,
   regular)** — e.g. "40mg" / "10 Pills", "0.01ml" / "1 Bottle", "100mg" /
   "Assorted Pack" (confirms the P21 "Assorted Pack" quantity-label finding
   already recorded in `docs/DECISIONS/`).

Side panel (the visible left face) consistently carries: a vertical barcode
(1D linear and/or a 2D DataMatrix square), "LOT / EXP" field labels (rotated
90°), and a block of small, dense "regulatory microprint" text — sometimes a
real-looking multi-line paragraph (the `HUCOG-2000` vial sample), sometimes
just repeating placeholder glyphs.

> **Almost none of that content is real — magnify it.** On `T1_1` the 2D code is
> a blob of organic noise with no quiet zone, no L-finder and no clock track; it
> would not scan. Beneath "LOT / EXP" sit `БАШЛ ТЕЯ`, `SLAQF FDЯT`, `TLAЯF 2023`
> — invented glyphs imitating a batch number and a date. The microprint block is
> not text either. This is the same failure §7 records as "Datels", and it is the
> whole panel rather than one word of it.
>
> **The reference is evidence of LAYOUT, not of CONTENT**, and the driver treats
> it that way. Built: a real, decodable **Code 128** of the SKU id with its
> human-readable line; **LOT and EXP as empty field labels with a rule** — which
> is what a real carton carries, because the batch and expiry are inkjetted at
> packing time, and which the `T_VERT_VIAL_144` reference actually shows (a boxed
> LOT and a bare EXP, no values); and a small block printing only strings the
> manifest holds — board material, carton dimensions, packaging geometry and the
> declared `features`. Nothing on this panel is invented.
>
> **Not built: any 2D symbol.** A DataMatrix needs Reed–Solomon and a layout
> engine, and a decorative one would re-create precisely the defect above. The
> measurement argues for building it properly later: an 11-character Code 128 is
> a long symbol, so its module lands at **0.08–0.40mm** across the catalogue,
> under the ~0.19mm a scanner needs on every panel shorter than about 90mm. That
> is exactly why real small-format pharma packs carry a DataMatrix — the same
> payload in a fraction of the area — and why the passports declare a
> `DataMatrix_Zone`. The driver warns on stderr when the module falls below the
> threshold rather than shipping a symbol that only looks like one.

## 7. AI-generation artifacts (a genuine Blender advantage, not just a limitation to work around)

On the `Lumigan` sample (`T_VERT_DROPPER`), the side-panel field labels read
**"LOT / EXP / Field / Datels"** — "Datels" is not a real word; it's a garbled/
hallucinated label, a known failure mode of AI image generation rendering fine
print. This is a concrete, visually-confirmed example of exactly the risk
[TECHNICAL_DEBT.md](../00_governance/release/TECHNICAL_DEBT.md) and the Blender
Roadmap flag under "text rendering quality." **The flip side is a real Blender
advantage worth stating plainly: a Blender text object renders the exact string
it's given — it cannot hallucinate a word.** Correctness of small regulatory
text is something Blender can *guarantee* where Gemini cannot.

## 8. Concrete tuning recommendations for `05_assets/blender/render_driver.py`

Based on §2–4 above, before further Blender template work:
- ~~Reduce ground-contact shadow further~~ — **done**, and the measurement is
  more brutal than "minimal to nearly absent" implied: directly beneath the
  carton the references sit at **254.9 (min 248)**, i.e. no contact shadow worth
  the name. The driver's backdrop is now an **emissive** plane rather than a
  diffuse floor lit by the key, so it takes no cast shadow and needs no light
  aimed at it. Measured under the carton after the change: 254.9, min 254.
  Fixing the shadow and the background turned out to be the same fix.
- ~~Raise the body material roughness from `0.5` toward **~0.7–0.8**~~ —
  **done**: `MATTE_ROUGHNESS = 0.7`, applied to the body, the stripe and the
  badge, since §3 records no hard specular highlight anywhere on the carton and
  printed ink sits on the same matte board.
- Do **not** implement a literal DOF blur at f/8 — these references read as
  fully sharp; a strong DOF would look *less* like the reference set, not more.
  *Still the case: an f/8 aperture value is set but DOF stays disabled.*
- ✅ The white-body / two-accent-color rule (stripe + corner badge) is confirmed
  and should be treated as a hard constraint on any future template, not just
  a nice-to-have.
- **The scene was ~2.8 stops over-exposed, and Blender's default AgX view
  transform hid it.** AgX's highlight rolloff kept the white body at a plausible
  237 while the ~15%-albedo accent stripe landed at (195,135,179) — a pale
  orchid — against the (99,42,72) measured here. Fixed by pinning the *film
  response* (`view_transform="Standard"`), not by touching the 25 W / 8 W light
  energies. Always measure the stop count off an **unclipped** render and scale
  back; estimating it from an AgX render gives ~2.0, which still clips T1.
- **The backdrop is emissive, not a lit floor.** Two small lights cannot light 50
  metres of plane evenly: the render showed a hot spot behind the carton falling
  to grey (corner brightness 75–178 across templates) against the flat 255 every
  reference holds. An emissive plane renders at a fixed value everywhere, takes
  no cast shadow, and frees the key and fill to light nothing but the product.
  It is switched out of all indirect ray paths so it cannot bounce back into the
  carton and wash the accent out — irrelevant under EEVEE, which gathers no such
  light, but load-bearing under Cycles.

## 9. Coverage & open questions

**Directly viewed (7 of 9 copied references):** `T1` (1), `T1_LARGE` (352),
`T3` (111), `T_BOTTLE_BOX` (10), `T_MULTIPACK` (347), `T_VERT_VIAL` (144),
`T_VERT_DROPPER` (229). **Copied but not yet visually reviewed:** `T1_SMALL`
(103), `T_VERT_INHALER` (268) — present in `01_input_raster/reference/` for a
follow-up pass; findings above are not assumed to extend to them without
checking.

**Open questions, not resolved by this pass:**
- What determines filled-vs-outline badge style per SKU? Not visible in the 7
  samples reviewed; may correlate with `branding.design_elements` fields not
  cross-checked here.
- ~~Accent-stripe height ratio was eyeballed (~8–12%)~~ — **resolved.** A
  pixel-measurement pass over all 9 references puts it at 2.9–6.1% of front-face
  height (median 4.0%); §5 now carries the measured figure and
  `render_driver.py` enforces 3–6%. The same pass measured the badge (fill =
  `palette.primary`, side ~25% of the shorter face edge, insets ~5% / ~3%).
- Whether the top-face sliver is ever rendered with the accent color (it
  wasn't in any of the 7 samples) — Row-6/front-face-only rule appears absolute
  but only 7 data points confirm it.

- ~~White-body brightness varies with carton size in the Blender render~~ —
  **resolved.** The key and fill were positioned proportionally to `target_size`
  while their energies stayed fixed, so a 170mm carton was lit from ~1.5× the
  distance of a 55mm one at the same wattage. `light_energy()` now scales power
  with the **square** of the size ratio, which cancels the inverse-square falloff
  exactly and holds irradiance constant. The 25 W / 8 W pair is unchanged in
  substance — it is now the power *at* the reference size, 0.115 m, which is also
  the catalogue's modal carton (259 of 391 SKU), so two thirds of the catalogue
  is lit at literally the old numbers.

  Measured, front face across the nine templates: **182–255 (spread 73, five
  templates clipping) → 236–239 (spread 3.6, none clipping)**, against a
  reference band of 235.0–241.5. The render set is now tighter than the
  references themselves.

**Newly open after this pass:**
- **Front-vs-side face contrast is too flat: +9 here against +26 in `T1_1`.** The
  references show a far more definite falloff between the lit front face and the
  shaded side panel (§3) than the current rig produces, and this is the largest
  remaining visual gap to them. Closing it means changing the *size or position*
  of the key and fill — the one part of `setup_lighting()` deliberately frozen,
  because its 25 W / 8 W replaced room-scale wattages that blew out the frame.
  So it needs a decision before anyone touches it, not a quiet tweak.
- Measuring a contact shadow: compare the darkest pixel under the object against
  the backdrop **at the same image rows**, so the backdrop's own gradient cannot
  be mistaken for a shadow. On that method the references sit at 0.7–4.0% below
  backdrop (`T1_LARGE_352` 0.7%, `T1_1` 2.4%, `T3_111` 4.0%) and ours at 0.8% —
  inside the reference range and shallower than two of the three. Note the
  detached shadow that prompted this was caused by the carton *floating*; seating
  it on the backdrop is what fixed it, not any change to the lights.
- **A residual ~0.13-stop shape effect, corrected in the meter rather than the
  rig.** After the energy law the per-template requirement still separated
  cleanly by carton *shape*: landscape (w ≥ h) wanted −2.71…−2.76 EV, portrait
  wanted −2.87…−2.88, with no overlap. The key is an area light roughly two
  face-widths out, so across a **wide** front face its far end is materially
  further than its near end and the mean over the face drops; a narrow portrait
  face barely sees it. No single scalar rig size equalises the horizontal and
  vertical falloff for both shapes at once — it is geometry, not a defect.
  Rather than distort the rig, the driver meters the two shapes separately
  (`FILM_EXPOSURE_LANDSCAPE` / `FILM_EXPOSURE_PORTRAIT`); the lighting itself is
  bit-for-bit identical for every carton. Revisit only if that gap grows, which
  would mean the rig has drifted.
- **A dark badge picks up more specular white than the references show.** On
  `#003366` navy the rendered badge reads R≈38 where the reference reads R≈4;
  the base colour has zero red, so the excess is the Principled BSDF's specular
  lobe. Under CYCLES, which computes a real specular response rather than
  EEVEE's approximation, two of seven sampled templates now sit outside ±30 on
  that channel (`T_VERT_DROPPER_229` at 37, `T_VERT_VIAL_144` at 32) where under
  EEVEE it was one of nine. Cheap candidate fix: lower specular/IOR on the
  printed elements. Not attempted here — it is a material change, unrelated to
  lighting calibration.

## 10. Silhouette proportion: what the references actually ask for

Measured 2026-08-09 with `src.silhouette.measured_silhouette_aspect` (threshold
250, one-pixel erosion). Aspect is silhouette width over height — framing-
invariant, so unlike frame fill it survives the bounding-sphere camera and can be
compared at all.

**Compare a reference against `visible_faces_aspect`, not `silhouette_aspect`.**
A reference draws its top face; our render cannot show one, because a white board
under near-shadowless high-key light reads 254.7–254.9 against a backdrop of
254.96 and has no upper edge in pixels at any threshold. So the reference's
measurement is its whole silhouette and ours is only the vertical faces. Matching
apparent shape to apparent shape means matching those two. The first version of
this section used the full-box model instead and it is a 13–14% error on the
landscape templates — large enough to report `T1` as already correct when it is
not, which is exactly what it did.

| Template | SKU | Carton (mm) | Reference | Ours, visible | Gap |
|---|---|---|---:|---:|---:|
| `T_MULTIPACK` | 347 | 110×50×18 | 1.4066 | 1.4068 | **−0.0%** |
| `T_BOTTLE_BOX` | 10 | 55×100×55 | 0.6203 | 0.7127 | −13.0% |
| `T1_SMALL` | 103 | 115×55×48 | 1.3109 | 1.5227 | −13.9% |
| `T1` | 1 | 115×55×48 | 1.3036 | 1.5227 | −14.4% |
| `T3` | 111 | 140×35×25 | 1.5322 | 1.9369 | −20.9% |
| `T1_LARGE` | 352 | 115×55×48 | 1.1480 | 1.5227 | −24.6% |
| `T_VERT_INHALER` | 268 | 55×115×48 | 0.8057 | 0.5908 | **+36.4%** |
| `T_VERT_DROPPER` | 229 | 50×110×18 | 0.7723 | 0.4897 | **+57.7%** |
| `T_VERT_VIAL` | 144 | 80×170×35 | 0.9224 | 0.5199 | **+77.4%** |

The instrument's own uncertainty is 0.6–3.6% across thresholds 248–253, except
`T_VERT_DROPPER` at 7.6% (`MEASURE_UNCERTAINTY_PCT = 4.0`).

**Only `T_MULTIPACK` already matches.** Every other template is 13% or more out,
and the vertical family is 36–77% out — ten to twenty times the instrument's
uncertainty and consistent in direction across all three.

**The reference set contradicts itself where the data says it should not.**
`T1`, `T1_SMALL` and `T1_LARGE` are SKU whose passports give the identical
carton, 115×55×48. The references draw them at 1.3036, 1.3109 and 1.1480 — 13%
of spread over three pictures of the same box. That is what "the Gemini prompt
carries no dimensions" looks like when measured: the proportion is invented per
image. `T1_LARGE`'s extra 10 points over `T1` are therefore not evidence of a
wanted shape. The owner's decision, taken with these numbers in hand, is to
target all nine regardless.

**The vertical family is a different phenomenon, and the pictures agree.**
`T_VERT_VIAL_144.webp` is a squat ten-vial box, not the tall pen-shaped carton
80×170×35 describes. Reshaping solves it to 172×170×35: wider than tall as a
box, yet a portrait *picture* at 0.9224, because the camera looks down a portrait
carton. This is why the reshape's flip guard tests the silhouette rather than the
box edges — testing the edges refuses this case, which is correct rather than a
flip.

**A superseded number, recorded so it is not re-derived.** The art-direction ТЗ
predicted `80x170 -> 159x170` for the vial. That came from pairing a reference's
full silhouette against a model of our printed faces — the two quantities this
section exists to keep apart — and does not survive the correction.

## 11. The silhouette target is not reachable, and the measurement is why

Measured 2026-08-09 by rendering `1-min` at five heights, holding width 115mm and
depth 48mm, and measuring each render the same way the references were measured.

| Height (mm) | Rendered | Full model | Visible model |
|---:|---:|---:|---:|
| 56.39 | 1.5347 | 1.3036 | 1.5004 |
| 60.00 | 1.4736 | 1.2631 | 1.4455 |
| 64.00 | **1.2021** | 1.2212 | 1.3893 |
| 67.00 | 1.1710 | 1.1916 | 1.3500 |
| 70.79 | 1.1351 | 1.1563 | 1.3036 |

Up to 60mm the render measures as its **visible faces**. From 64mm it measures as
its **full silhouette**. Between them the measured value jumps from 1.4736 to
1.2021 without passing through anything in between — the carton's far top edge
crosses the brightness threshold and the bounding box gains 145 pixels of height
at once.

**`T1`'s target of 1.3036 sits inside that jump.** No carton height renders to it.
Solving against the visible model gives 70.79mm, which renders at 1.1351, 12.9%
low. Solving against the full model gives 56.39mm, which renders at 1.5347, 17.7%
high. Both were rendered and measured, not predicted.

**The discontinuity is in the instrument, not in the picture.** A carton at 60mm
and one at 64mm look almost identical; what changes is whether a threshold finds
the top edge. So a threshold-derived bounding box is not a quantity that can be
art-directed onto: it is not a continuous function of the geometry that produces
it.

**This also puts the reference targets in question.** All nine references sit in
the "top edge found" regime — their topmost band reads 225–243. But the regime
gap measured here is about 18%, and the spread between `T1` at 1.3036 and
`T1_LARGE` at 1.1480 for the identical 115×55×48 carton is 13%. Those are the
same order of magnitude, so part of what section 10 calls reference scatter may
be this switch happening between one reference image and another rather than
Gemini drawing the box differently. Not yet separated.

**What this does not invalidate.** The analytic model is exact and unaffected —
it never used pixels. The reshape solver is correct for whatever target it is
given. The disagreement the whole exercise set out to settle is real and large:
the vertical family is 36–77% away from its references by any of these measures,
far outside the regime gap. What is now in doubt is the precision of the targets,
not their direction.

**Open.** A target has to be a continuous function of the geometry. The front
face's projected quad is one — the driver already emits it per render as
`{stem}.view.json`, and `src/silhouette.front_face_px` computes it exactly — but
the references carry no such sidecar, so recovering their front-face quad means
locating the accent stripe and badge in each image. Not attempted here.

### 11a. The front face cannot be measured either, and what that leaves

Tried 2026-08-09, following the decision to retarget onto the front face.
`src.silhouette.front_face_aspect` computes it exactly and is smooth in the
geometry — 1.9591, 1.7959, 1.6838, 1.5224 for T1 at heights 55, 60, 64 and 70.79.
The model half works. The measurement half does not.

**Our renders have no front/top boundary.** Reading a column down through the
carton at x=608: 255, 255, 255, 254.7, 251.3, 249.7, 246.0, 243.0, 240.0, 236.0,
232.0, then the accent stripe at 78. The front face is not a flat 238 — it runs a
smooth vertical gradient from about 254 at its top edge to about 232 at its
bottom, and it meets the top face continuously. The "235–241" in section 3 is a
mean over the band just above the stripe, not a value for the whole face. So the
face's top edge has no pixel signature, and a threshold walk from the stripe
upward stops wherever the gradient happens to cross it, which is what it did:
+39.9% mean error over 40 renders, +144% worst.

**Neither do the references.** `T1_1.webp` at x=1100 reads 255, 246, 246, 246,
245, 243, 243, 242, 241, 240 — one step of about 9 levels where the backdrop
meets the carton, then a smooth ramp down the face. The step is the silhouette's
top edge, not the front face's. Gemini shades the two faces alike.

**What is left.** Only the carton's outer silhouette is measurable on a reference,
and on our own renders even that is ambiguous by up to the regime gap. So no
measurement of our own output can serve as the target; the target has to be an
exact model quantity, solved analytically, and the apparent result accepted to
differ from it by up to the top face's worth of ambiguity.

Which model quantity is the right one — full silhouette, visible faces, or front
face — is then a judgement about what "matching the reference" means, and this
document has established that it cannot be settled by measuring what we render.
The three differ by 13–18%. That is the open question, and it is smaller than the
36–77% the vertical family is out by, which stays true under all three.

## 12. The carton had no volume, and the rig was lighting the lid

Spotted by eye — the top face read as nothing at all — then measured 2026-08-09.

| | top face | backdrop | contrast |
|---|---:|---:|---:|
| ours, `T1` / `T3` / `T1_LARGE` / `T_MULTIPACK` | **255.0** | 254.96 | **−0.04** |
| ours, vertical family | 252.5–253.3 | 254.96 | 1.6–2.4 |
| the nine references | 221.8–244.8 | 254.6 | 9.8–32.8 |

The top face was clipped to pure white and was *brighter than the backdrop*. There
is no tone in it to see, which is why the box read as a flat label rather than an
object.

**The cause is the key's position, computed from the rig.** At `KEY_OFFSET =
(2, -2, 3)` the printed front face stands almost edge-on to the key:

| light | cos(front face) | cos(top face) | top/front |
|---|---:|---:|---:|
| key `(2, -2, 3)` | 0.119 | 0.728 | 6.11× |
| fill `(-2, -1.5, 2)` | 0.742 | 0.625 | 0.84× |

Weighted by 25 W and 8 W, the rig delivered 8.91 to the front face and 23.19 to
the top: **2.60×**. And of the front face's 8.91, the fill supplied 5.94 against
the key's 2.98 — a light a third the wattage doing twice the work. The key was
functionally a top light, and the roughly three stops of negative exposure
compensation were the frame being pulled back down afterwards.

**Exposure could never have fixed it.** Metering the front face to 238 is exactly
what pushes a face receiving 2.6× as much light past clipping.

**The fix is `KEY_OFFSET = (2, -4.5, 3)`** — same side, same elevation band, moved
forward. Top/front falls to 1.06, inside the references' 0.89–1.04; the key takes
back 1.85× the fill's share of the front face. Re-metered against the reference
band of 235.0–241.5: `1-min` renders its front face at 238.23 and `229-min` at
238.93, with the top face at 0.93–1.05 of the front. Exposures move from
−2.76/−2.84 to −1.77/−1.87.

`tests/test_blender_carton.py` computes the ratio from the rig — no render needed
— and fails above 1.35. Restoring the old offset makes it fail at 2.60.

**What this unblocks.** Sections 10, 11 and 11a all foundered on the same thing:
a top face at the backdrop's own brightness has no edge, so the silhouette could
not be measured continuously and no art-direction target could be solved onto it.
With the lid carrying tone that obstacle is gone, and the targets in section 10
are worth re-measuring against renders that have a top face.

### 12a. Landscape lids: fixed by lowering the key, and what it cost

`(3, -3, 3)` cleared the side panel but left the landscape lids clipped in their
brightest 40–60%: the mean sat inside the reference band while the gradient's
bright end saturated. Lowering the key to **`(3, -3, 2)`** is what stops that.

| | 1-min lid | 111-min lid |
|---|---:|---:|
| before | 39.7% clipped | 59.7% clipped |
| after | **0.0%** | **9.2%** |

Exposures re-metered to −2.18 / −2.21. Side/front stays inside the reference
spread on all four gate shapes (0.958–1.004 against 0.855–1.081), and `111-min`'s
front face improves from 233.17 to 234.04 against a floor of 235.0.

**The elevation has an optimum rather than a direction.** Measured at z = 3.0,
2.4, 2.0, 1.7 and 1.4: clipping falls to a minimum near 1.7–2.0 and rises again
below it, while the side panel climbs out of the reference spread.

**Moving the whole rig farther makes it worse.** Tested at 1.8×, 3× and 5× the
offsets with matched angular size and compensated exposure: top/front rises from
1.17 to 1.31. At distance the rig approaches a directional light, where the lid's
geometric cosine (0.577) dwarfs the printed face's (0.142). The proximity of the
lights was helping, not hurting.

**The cost, stated rather than hidden: portrait lids go dark.** top/front lands at
0.793–0.817 against a reference band of 0.969–1.042. One rig cannot satisfy both
shapes, because the references are AI images that draw every face at nearly one
tone whatever the carton's proportions, while a real rig gives a landscape carton
a large lid facing the key and an upright one almost none. A dim lid still carries
gradient; a clipped one carries nothing, so the trade goes this way.
