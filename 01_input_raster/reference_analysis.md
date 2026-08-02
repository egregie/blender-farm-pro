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
