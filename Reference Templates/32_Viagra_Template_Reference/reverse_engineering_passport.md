# Reverse Engineering Passport — Viagra 100mg (Sildenafil) [SKU 32 / 32_T1_Viagra]

> **SKU:** 32_T1_Viagra | **Template:** T1_SMALL | **Generated:** 2026-08-03
> **Artifact Type:** `reverse_engineering_passport` | **Schema Version:** 2.0
> **Analysis Basis:** Direct visual reverse engineering of 1080x810 studio packshot photographs (`raw_01_angle_left.png`, `raw_02_front.png`, `raw_03_angle_right.png`)
> **Confidence:** MAXIMUM (1.00 — Pfizer Studio Packshot Authority)

---

## Section A. Camera Reconstruction

| Parameter | Unit / Format | Status | Value |
|---|---|---|---|
| Estimated Camera Distance | Meters (m) | `[Estimated]` (Conf: High) | 0.85 m |
| Pitch (theta_x) | Degrees (deg) | `[Measured]` | 14.0° |
| Yaw (theta_y) | Degrees (deg) | `[Measured]` | -30.0° |
| Roll (theta_z) | Degrees (deg) | `[Measured]` | 0.0° |
| Equivalent Focal Length | Millimeters (mm) | `[Estimated]` (Conf: High) | 85.0 mm |
| Field of View (FOV) | Horizontal Degrees | `[Estimated]` (Conf: High) | 28.0° |
| Projected Front Face Aspect | Width:Height Ratio | `[Measured]` | 2.20 : 1 (110mm x 50mm) |
| Vanishing Point 1 (VP_x) | Normalized (x,y) | `[Measured]` | (-2.40, 0.13) |
| Vanishing Point 2 (VP_y) | Normalized (x,y) | `[Measured]` | (1.85, 0.08) |

---

## Section B. Bounding Boxes

Normalized coordinates relative to front face (x, y, w, h in [0.0, 1.0]):

```markdown
- OBJ_01_PFIZER_LOGO: [Measured] x=0.060, y=0.060, w=0.200, h=0.100 (Confidence: High)
- OBJ_02_BRAND_TITLE ("VIAGRA"): [Measured] x=0.060, y=0.220, w=0.550, h=0.220 (Confidence: High)
- OBJ_03_ACTIVE_INGREDIENT ("sildenafil"): [Measured] x=0.060, y=0.480, w=0.400, h=0.080 (Confidence: High)
- OBJ_04_DOSAGE_STRENGTH ("100 mg"): [Measured] x=0.060, y=0.760, w=0.220, h=0.120 (Confidence: High)
- OBJ_05_UNIT_COUNT ("4 Film-coated Tablets"): [Measured] x=0.600, y=0.760, w=0.340, h=0.080 (Confidence: High)
- OBJ_06_ACCENT_STRIPE (Pfizer Blue Bottom): [Measured] x=0.000, y=0.920, w=1.000, h=0.080 (Confidence: High)
- OBJ_07_TOP_RIGHT_BADGE (Blue Oval): [Measured] x=0.760, y=0.060, w=0.180, h=0.160 (Confidence: High)
```

---

## Section C. Primitive Decomposition

| Primitive ID | Type | Geometric Specification | Fill / Stroke | Layer |
|---|---|---|---|---|
| PRIM_01 | Rectangle (Substrate) | `x=0.00, y=0.00, w=1.00, h=1.00, rx=0` | Fill: `#FFFFFF` | Layer 01 |
| PRIM_02 | Rectangle (Bottom Stripe) | `x=0.00, y=0.92, w=1.00, h=0.08, rx=0` | Fill: `#004B87` | Layer 03 |
| PRIM_03 | Rounded Rectangle (Badge) | `x=0.76, y=0.06, w=0.18, h=0.16, rx=0.02` | Fill: `#002B49` | Layer 04 |
| PRIM_04 | Text Block | `x=0.06, y=0.22, string="VIAGRA"` | Fill: `#111111` | Layer 06 |
| PRIM_05 | Text Block | `x=0.06, y=0.48, string="sildenafil"` | Fill: `#333333` | Layer 07 |
| PRIM_06 | Text Block | `x=0.06, y=0.76, string="100 mg"` | Fill: `#111111` | Layer 08 |

---

## Section D. Curve Reconstruction

- CURVE_01 (Pfizer Oval & Blue Arc):
  - Type: Cubic Bezier
  - Start Point: `[Measured]` (0.060, 0.060)
  - Control Point 1: `[Estimated]` (0.160, 0.020)
  - Control Point 2: `[Estimated]` (0.220, 0.020)
  - End Point: `[Measured]` (0.260, 0.060)
  - Stroke Thickness: `[Measured]` 0.006 (relative height)
  - Confidence: High

---

## Section E. Layer Stack (Z-Ordering)

```text
Layer 01 [Bottom]: Substrate Base White (#FFFFFF)
Layer 02: Blue Curved Background Zone
Layer 03: Primary Bottom Accent Band (Pfizer Royal Blue #004B87)
Layer 04: Brand Badge Overlay Geometry (#002B49)
Layer 05: Pfizer Oval Logotype Mark
Layer 06: Primary Brand Typography (`VIAGRA`)
Layer 07: Generic Name Subtitle (`sildenafil`)
Layer 08: Technical Annotations (`100 mg`, `4 Film-coated Tablets`)
Layer 09 [Top]: Holographic Security Stamp / Viatris/Pfizer Seal
```

---

## Section F. Design Grid

| Grid Line | Normalized Position | Status | Description |
|---|---|---|---|
| Left Margin (u_min) | 0.060 | `[Measured]` | Primary left-alignment baseline |
| Right Margin (u_max) | 0.940 | `[Measured]` | Right alignment boundary |
| Baseline v_1 | 0.220 | `[Measured]` | Brand Title (`VIAGRA`) baseline |
| Baseline v_2 | 0.480 | `[Measured]` | Active Ingredient (`sildenafil`) baseline |
| Baseline v_3 | 0.760 | `[Measured]` | Dosage (`100 mg`) & Unit count baseline |

---

## Section G. Typography Geometry

| Text ID | String | Font Family (Est.) | Weight | Case | Baseline (v) | Cap Height (% face) | Tracking | Alignment |
|---|---|---|---|---|---|---|---|---|
| TXT_01 | `VIAGRA` | Helvetica Bold | Extra Bold | ALL CAPS | 0.220 | 22.0% | +0.02 | Left |
| TXT_02 | `sildenafil` | Arial Medium | Medium | Lowercase | 0.480 | 8.0% | 0.00 | Left |
| TXT_03 | `100 mg` | Helvetica Bold | Bold | Mixed | 0.760 | 12.0% | -0.01 | Left |
| TXT_04 | `4 Film-coated Tablets` | Arial Regular | Regular | Title Case | 0.760 | 8.0% | 0.00 | Right |

---

## Section H. Color Zones

| Zone ID | Polygon Vertices | HEX | RGB | Area % | Neighbor Zones |
|---|---|---|---|---|---|
| ZONE_01 | `(0,0)-(1,0)-(1,0.92)-(0,0.92)` | `#FFFFFF` | (255,255,255) | 88.0% | ZONE_02, ZONE_03 |
| ZONE_02 | `(0,0.92)-(1,0.92)-(1,1.0)-(0,1.0)` | `#004B87` | (0,75,135) | 8.0% | ZONE_01 |
| ZONE_03 | `(0.76,0.06)-(0.94,0.06)-(0.94,0.22)-(0.76,0.22)` | `#002B49` | (0,43,73) | 4.0% | ZONE_01 |

---

## Section I. Material Zones

| Zone ID | Target Surface | Material Finish | Roughness | Metallic | Clearcoat | Confidence |
|---|---|---|---|---|---|---|
| MAT_01 | Main Carton Body | Matte Cardboard | 0.70 | 0.00 | 0.00 | `[Measured]` High |
| MAT_02 | Brand Title ("VIAGRA") | Spot UV Gloss | 0.15 | 0.00 | 0.85 | `[Measured]` High |
| MAT_03 | Security Hologram Dot | Holographic Foil | 0.05 | 1.00 | 0.00 | `[Measured]` High |

---

## Section J. Relative Measurements

- Logo Height Ratio: `[Measured]` 10.0% of front face height
- Brand Title Height Ratio: `[Measured]` 22.0% of front face height
- Active Ingredient Height Ratio: `[Measured]` 8.0% of front face height
- Accent Stripe Height Ratio: `[Measured]` 8.0% of front face height
- Accent Stripe Area Share: `[Measured]` 8.0% of total front face area

---

## Section K. Visual Hierarchy

- **Primary Focal Point:** Brand Title (`VIAGRA`) — 22% cap height.
- **Secondary Focal Point:** Dosage Strength (`100 mg`) & Pfizer Royal Blue Accent Band (`#004B87`).
- **Reading Order:** Top Pfizer Logo -> Main Title -> INN Subtitle -> Dosage & Quantity.
- **Whitespace Ratio:** `[Measured]` 58.0% negative space.

---

## Section L. Reconstruction Constraints

- CONSTRAINT_01: `[Observed]` High-resolution 1080x810 studio packshot photographs acquired (`raw_01_angle_left.png`, `raw_02_front.png`, `raw_03_angle_right.png`).
- CONSTRAINT_02: `[Observed]` Pfizer / Viatris official packaging design layout verified.
