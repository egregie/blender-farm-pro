# Design Rationale (Reverse-Engineering of Decisions)

> **ADR vs. this document.** The [ADRs](DECISIONS/) record *what* was decided.
> This document reconstructs *why it had to be that way* — the forces, the
> rejected alternatives, and what we would revisit. Some reasoning is recovered
> from the code and git history and is marked **[confirm with author]**.

---

## 1. Why this pipeline shape (SSOT → passport → renderer → output)?

**Forces.** 391 SKU, each needing a consistent, regulated packshot; image
generation is the slow, unreliable, expensive step; everything else is cheap and
deterministic.

**Why split into three file-based stages.** Isolating the volatile step
(rendering) from the deterministic steps (passport compilation, image
optimization) means a failure or change in one stage never corrupts the others,
and each stage can be re-run independently. File-based handoffs (JSON → MD → PNG →
WEBP), keyed by SKU stem, make state inspectable on disk and make **resume**
trivial: "done" is simply "the artifact exists". A monolith would have coupled the
fragile browser step to the safe steps and made partial recovery hard.

**Would revisit:** the file-based contract is implicit; a documented manifest
would help CRM integration (see CRM Readiness audit).

## 2. Why Markdown, not JSON, for the prompt?

**Forces.** The prompt encodes art direction — colour zoning, optical calibration,
text-sanitization output — that humans must **review and trust** before 391
images are generated.

**Why Markdown.** It is human-readable and diffable: a reviewer opens
`pipeline/passports.markdown/<stem>.md` and reads exactly what the renderer will
receive. JSON would be machine-clean but hostile to visual review of prose-like
art-direction rules, and it would invite treating the prompt as data to mutate
rather than a frozen, auditable artifact. JSON is still the *input* (the passport
record); Markdown is the *compiled prompt*. See [ADR-002](DECISIONS/ADR-002-why-markdown.md).

**Why not JSON for the prompt specifically:** reviewability and git-diff clarity
beat structural strictness for a prompt that is ultimately free text to the model.

## 3. Why Gemini?

**Forces.** Need high-quality, photorealistic pharma packshots at near-zero
marginal cost. The git history shows a graveyard of attempts (DALL·E, Flux,
Hugging Face, Pollinations, Imagen) now in `trash/_archive/`.

**Why Gemini won.** It produced acceptable quality **and** was reachable for free
through an interactive session, whereas the API alternative (Imagen/Vertex)
required paid Cloud billing and the other engines fell short on quality/cost.
See [ADR-001](DECISIONS/ADR-001-why-gemini.md). **[confirm with author]** for the
exact quality comparison that settled it.

## 4. Why a browser (RPA), not an API?

**Forces.** Gemini's free image generation lives in the chat UI; the paid API
path was a budget decision the project chose to avoid.

**Why RPA.** Driving the UI with Selenium turns the free interactive capability
into an automatable one, at the cost of fragility (DOM selectors), serialization
(one browser/session), and a non-headless requirement. This was a deliberate
**cost-vs-robustness trade**: zero render cost in exchange for operational
fragility. See [ADR-004](DECISIONS/ADR-004-why-rpa.md). It is the single biggest
architectural constraint and the main thing to revisit if volume/SLA grows
(an API renderer would unlock concurrency and determinism).

## 5. Why WEBP (1600×1600, ≤500 KB)?

**Forces.** Final assets are for web/catalogue use; they must be small yet keep
small pharmaceutical label text legible.

**Why WEBP with an auto-tuned quality ladder.** It hits a hard ≤500 KB weight cap
with broad browser support; LANCZOS upscaling preserves text legibility. PNG has
no practical weight cap; JPEG smears text/edges. The dynamic quality loop trades a
little fidelity to guarantee the weight budget. See [ADR-003](DECISIONS/ADR-003-why-webp.md).

## 6. Why SSOT / `SKU.csv` as the routing authority?

**Forces.** The same product attributes existed in JSON passports, `master.json`
and `SKU.csv`, producing conflicting template routing.

**Why one CSV authority.** Routing must be deterministic, so exactly one source
must win; `SKU.csv` `package_type` was made primary (P6.0), with
`unit_count_standard` overriding the JSON. This trades flexibility (multiple
sources) for predictability (one truth). See [ADR-005](DECISIONS/ADR-005-ssot-routing-authority.md).

## 7. Why a white carton with exactly two spots of brand colour?

**The rule.** The carton body is pure white `#FFFFFF` on every SKU, whatever
`branding.palette.primary` says. Brand colour appears in exactly two places on
the front face and nowhere else:

| Element | Position | Colour |
|---|---|---|
| Accent stripe ("Row 6") | full-width band at the **very bottom edge** of the front face, ~8–12% of face height | `palette.accent` |
| Brand badge | small square in the **top-right corner**, ~6–8% of panel width | `palette.primary` |

Never on side panels, never on the top face, never on the text.

**Where it actually lives.** The authority is the front-panel grid in
`src/passport_generator.py` (the layout comment above `grid_lines`, plus the
`[SURFACE COLOUR MANDATE]` and `[RENDER CONSTRAINTS]` blocks in every prompt
template). This section exists because that rule had no documented "why" —
flagged as **B2** in the [Bus Factor audit](../00_governance/audits/BUS_FACTOR_AUDIT.md)
— and because `assets/blender/render_driver.py` cited *this* document for it,
which previously said nothing on the subject.

**Forces.** The two engines have to be interchangeable at Stage 2, so an
art-direction rule expressed as prose for Gemini has to hold as geometry in
Blender. And 391 SKU share one visual system: if the body took the palette,
each SKU would read as a different product line rather than one catalogue.

**Why white specifically. [confirm with author]** The original motivation is not
recorded. What *is* verifiable: direct inspection of the curated reference
renders found a pure white body on every sample regardless of its
`palette.primary`, with brand colour confined to those two elements — see
[reference_analysis.md §5](../01_input_raster/reference_analysis.md). So the
rule is confirmed as *observed practice* across the finished catalogue even
though its original rationale is unrecovered; treat it as a hard constraint.

**Note on the colour split.** The stripe and the badge do **not** take the same
colour. `badge_bg_hex = primary_hex` in `passport_generator.py`, while the
stripe is `accent_hex`. Summaries that say "brand colour" for both are
imprecise; `palette.accent` is consistently the darker, more saturated tone.

---

## Cross-cutting principle

Every choice optimizes the same thing: **keep the deterministic, cheap parts
safe, auditable and re-runnable; quarantine the one expensive, non-deterministic,
fragile part (rendering) behind a clean boundary.** That principle explains the
stage split, the file handoffs, the resume model, and the decision to treat
`output/` as the system of record rather than something to regenerate.
