# Marks — the owner's decision

**Status: NOT DECIDED. This file is a template awaiting a human.**

No code depends on it yet and none may be written until the decision column
below is filled in by the person entitled to make the call. An implementer may
not fill it, may not enter defaults, may not infer an answer from
`MARKS_EVIDENCE.md`, and may not read silence as permission.

---

## What is being decided

Whether this project's renders may draw the regions classified `mark` in
`print_truth.json`, and — paired with that and inseparable from it — whether the
holes classified `mark` may be cut.

The two halves are one decision. Cutting a `mark` hole while drawing nothing
into it shows board through our field in the shape of another company's logo,
which is the act contract 1.8 already refuses for another company's lettering.
Cutting it *as part of* drawing the mark is coherent. Neither half may ship
alone.

## What the facts are

Established in [`MARKS_EVIDENCE.md`](MARKS_EVIDENCE.md), summarised here because
a decision should not require chasing a second document:

- The measured gain is **+9.937 points** of group `truth_agreement`, and **92% of
  it is two Pfizer ovals** (`74-min` +5.290, `135-min` +3.865).
- **All eight holes are solid regions.** What cutting one produces is a filled
  ellipse or roundel. The wordmark inside is not separated by the segmentation,
  is not carried by the hole, and would not appear in the render. What would
  appear is the mark's silhouette in its printed position.
- The 27 **components** are a different case and carry none of the +9.937.
  Sixteen are solid, and a solid `mark` component is the mark's own printed
  shape — drawing `133_Ambien`'s eight Hemofarm wordmarks as flat fills would
  reproduce those wordmarks' silhouettes.
- Rights holders across the set: Pfizer, Lilly, Roche, Novartis, Shire,
  sanofi-aventis, Sun Pharma, Hemofarm, Neptune Laboratories, LCI, plus the
  Kamagra and Cialis product devices.
- The project already refuses to print LOT, EXP, an invented product code, or a
  fake 2D symbol, on the grounds that they would make a render pass for genuine
  packaging.

## Two entries that are not branding and are decided separately

| key | what it is | why separate |
|---|---|---|
| `357-min highlight#0/hole#0` | the **C-II schedule symbol**, +0.076 | a regulatory marking required by US law on a controlled substance, not a trademark |
| `59_Cialis secondary_1#0` | the **Lilly holographic oval**, 4.423% of face | an anti-counterfeiting security feature; carries none of the +9.937 and is out of scope — recorded so it is not picked up later by class name alone |

---

## To be completed by the owner

**Decided by:** _______________________

**Date:** _______________________

**Purpose the catalogue serves:** _______________________

**Basis — authorisation, licence, or the reasoning relied on:**

_______________________

**Scope in one sentence:** _______________________

### Per-entry decision

`draw?` — write `yes` or `no`. Leave nothing blank; a blank is not an answer and
the implementer must stop on one.

#### Holes — these carry the +9.937 and are cut only if the paired mark is drawn

| sku | key | points | what it is | draw? |
|---|---|---|---|---|
| 74-min | brand#0/hole#0 | +5.290 | Pfizer oval, solid | |
| 135-min | brand#0/hole#0 | +3.865 | Pfizer oval, solid | |
| 221-min | brand#0/hole#0 | +0.631 | LCI roundel, solid | |
| 357-min | highlight#0/hole#0 | +0.076 | **C-II schedule symbol** (regulatory, not branding) | |
| 221-min | brand#0/hole#13 | +0.056 | LCI roundel, solid | |
| 221-min | brand#0/hole#25 | +0.022 | LCI roundel, solid | |
| 357-min | highlight#0/hole#4 | −0.001 | Shire logotype swash | |
| 357-min | highlight#0/hole#5 | −0.002 | Shire logotype swash | |

#### Components — the marks themselves as printed regions; none was priced

| folder | key | area % | rights holder | draw? |
|---|---|---|---|---|
| 60_Cialis_Professional | highlight#2 | 1.125 | Cialis (Lilly) device | |
| 60_Cialis_Professional | brand#2 | 0.688 | Cialis (Lilly) device | |
| 272_Valium_Brand | brand#1 | 0.411 | Roche | |
| 64_Kamagra | highlight#7 | 0.395 | Kamagra device | |
| 150_Waklert | brand#4 | 0.321 | Sun Pharma | |
| 59_Cialis | brand#9 | 0.321 | Lilly | |
| 230_Slimex | brand#8 | 0.303 | Neptune Laboratories | |
| 133_Ambien | brand#2 | 0.297 | Hemofarm | |
| 133_Ambien | brand#3 | 0.275 | Hemofarm | |
| 157_Valium | type#8 | 0.231 | Roche | |
| 133_Ambien | brand#4 | 0.208 | Hemofarm | |
| 133_Ambien | brand#5 | 0.203 | Hemofarm | |
| 64_Kamagra | highlight#17 | 0.184 | Kamagra device | |
| 230_Slimex | brand#9 | 0.154 | Neptune Laboratories | |
| 155_Imovane | highlight#2 | 0.152 | sanofi-aventis | |
| 60_Cialis_Professional | highlight#15 | 0.138 | Lilly | |
| 133_Ambien | brand#6 | 0.123 | Hemofarm | |
| 64_Kamagra | highlight#18 | 0.119 | Kamagra device | |
| 152_Artvigil | brand#26 | 0.119 | Signature script | |
| 272_Valium_Brand | brand#13 | 0.116 | Roche | |
| 404_Ritalin | type#19 | 0.115 | Novartis | |
| 133_Ambien | brand#7 | 0.109 | Hemofarm | |
| 404_Ritalin | type#20 | 0.106 | Novartis | |
| 64_Kamagra | highlight#21 | 0.103 | Kamagra device | |
| 133_Ambien | brand#8 | 0.102 | Hemofarm | |
| 133_Ambien | brand#9 | 0.101 | Hemofarm | |
| 59_Cialis | secondary_1#0 | 4.423 | **holographic — out of scope, see above** | n/a |

---

## What happens after this file is filled

Phase 3 of the brief, and only within the scope written above:

1. contract 1.9 gains `design.marks[]`; a manifest at 1.8 is rejected;
2. `fit()` emits marks only for keys marked `yes` here — a key absent from this
   file is not emitted;
3. a `mark` hole is cut **iff** its paired mark was emitted in the same build,
   derived from the emission rather than from any reclassification;
4. `validate_manifest` rejects, by name, a manifest carrying a cut `mark` hole
   without its mark, on write and on read;
5. every figure is re-measured. **The +9.937 is not carried forward** — it was
   measured by cutting a hole with nothing behind it, and drawing a mark into
   the hole is a different measurement.

If the decision is `no` throughout, that is a complete outcome: it is recorded in
`CLAUDE.md` and `HOLE_CEILING.md` so the +9.937 is never again read as available
headroom, and no code changes.

`print_truth.json` is not edited either way. It records what a thing **is**; this
file records what may be done with it.
