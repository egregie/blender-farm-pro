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
  calibration in `docs/DESIGN_RATIONALE.md`/the Gemini prompt templates), not a
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
1. **A solid accent stripe along the bottom edge of the front face**, roughly
   8–12% of the box's front-face height, spanning the full width. Color =
   `palette.accent` (verified against source JSON: T1's `1-min` stripe is the
   dark magenta `#6B2D5C` from its passport; consistently darker/more saturated
   than `palette.primary`, never the lighter primary tone).
2. **A colored square badge in the top-right corner of the front face**,
   containing an abstract white geometric line-art motif (varies per SKU: an
   X-hatch lattice, a wireframe diamond/polyhedron, a filled ring/circle, a
   filled overlapping-circles mark, an angular network pattern). The badge is
   **either filled-solid or outline-only** depending on the SKU — no obvious
   rule was identified from 7 samples for which style is used when; flagged as
   an open question in §7.

This directly confirms the `[SURFACE COLOUR MANDATE]` rule already documented
in `src/passport_generator.py`'s prompt templates and `docs/DESIGN_RATIONALE.md`
— genuinely useful to have visually verified, not just read in code.

## 6. Typography & label layout

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

## 8. Concrete tuning recommendations for `assets/blender/render_driver.py`

Based on §2–4 above, before further Blender template work:
- ⬜ Reduce ground-contact shadow further (lower key-light size/raise light
  height, or add a subtle contact-shadow-only technique) — references show
  almost no visible shadow, current driver still shows one.
- ✅ Raise the body material roughness from `0.5` toward **~0.7–0.8** (matte
  cardboard, not semi-gloss). *Done: `CARTON_ROUGHNESS = 0.7` in
  `render_driver.py`, applied to the printed accent too (§4: no print sheen
  either). Asserted by `tests/test_blender_carton.py`.*
- ✅ Do **not** implement a literal DOF blur at f/8 — these references read as
  fully sharp; a strong DOF would look *less* like the reference set, not more.
  *Still the case: an f/8 aperture value is set but DOF stays disabled.*
- ✅ The white-body / two-accent-color rule (stripe + corner badge) is confirmed
  and should be treated as a hard constraint on any future template, not just
  a nice-to-have. *Now built and enforced: the body no longer takes
  `palette.primary`, the stripe sits at the bottom edge, and the corner badge
  is built. Written up in `docs/DESIGN_RATIONALE.md` §7.*

Note for whoever picks up the shadow item: `--dump-scene <path>` on the driver
builds the scene and writes measured geometry as JSON without rendering, which
is how the rules above are tested without inspecting pixels.

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
- Accent-stripe height ratio was eyeballed (~8–12%), not pixel-measured —
  worth a precise measurement pass if Blender geometry needs to match exactly.
- Whether the top-face sliver is ever rendered with the accent color (it
  wasn't in any of the 7 samples) — Row-6/front-face-only rule appears absolute
  but only 7 data points confirm it.
