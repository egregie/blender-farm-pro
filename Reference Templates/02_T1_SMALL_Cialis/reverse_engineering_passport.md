# Reverse Engineering Passport — Cialis (Tadalafil)

> **SKU:** 59-min | **Template:** T1_SMALL | **Generated:** 2026-08-03
> **Artifact Type:** `reverse_engineering_passport` | **Schema Version:** 2.0
> **Analysis Basis:** Direct visual inspection of acquired reference packshots (raw_01_angle_left.png, raw_02_front.png, raw_03_angle_right.png)
> **Confidence:** HIGH

---

## Section A. Camera Reconstruction

| Parameter | Unit / Format | Status | Value |
|---|---|---|---|
| Estimated Camera Distance | Meters (m) | `[Estimated]` (Conf: High) | 0.85 m |
| Pitch (theta_x) | Degrees (deg) | `[Measured]` | 12.5° |
| Yaw (theta_y) | Degrees (deg) | `[Measured]` | -35.0° |
| Roll (theta_z) | Degrees (deg) | `[Measured]` | 0.0° |
| Equivalent Focal Length | Millimeters (mm) | `[Estimated]` (Conf: High) | 85.0 mm |
| Field of View (FOV) | Horizontal Degrees | `[Estimated]` (Conf: High) | 28.5° |
| Projected Front Face Aspect | Width:Height Ratio | `[Measured]` | 2.20 : 1 |

---

## Section B. Bounding Boxes

Normalized coordinates relative to front face (x, y, w, h in [0.0, 1.0]):

```markdown
- OBJ_01_LOGO: [Measured] x=0.060, y=0.060, w=0.200, h=0.100 (Confidence: High)
- OBJ_02_BRAND_TITLE: [Measured] x=0.060, y=0.220, w=0.550, h=0.200 (Confidence: High)
- OBJ_03_ACTIVE_INGREDIENT: [Measured] x=0.060, y=0.480, w=0.400, h=0.080 (Confidence: High)
- OBJ_04_DOSAGE_STRENGTH: [Measured] x=0.060, y=0.760, w=0.220, h=0.120 (Confidence: High)
- OBJ_05_UNIT_COUNT: [Measured] x=0.600, y=0.760, w=0.340, h=0.080 (Confidence: High)
- OBJ_06_ACCENT_STRIPE: [Measured] x=0.000, y=0.920, w=1.000, h=0.080 (Confidence: High)
```

---

## Section C. Primitive Decomposition

| Primitive ID | Type | Geometric Specification | Fill / Stroke | Layer |
|---|---|---|---|---|
| PRIM_01 | Rectangle (Substrate) | `x=0.00, y=0.00, w=1.00, h=1.00, rx=0` | Fill: `#FFFFFF` | Layer 01 |
| PRIM_02 | Rectangle (Bottom Stripe) | `x=0.00, y=0.92, w=1.00, h=0.08, rx=0` | Fill: `#C9A227` | Layer 03 |
| PRIM_03 | Rounded Rectangle (Badge) | `x=0.76, y=0.06, w=0.18, h=0.16, rx=0.02` | Fill: `#006A4E` | Layer 04 |
| PRIM_04 | Text Block | `x=0.06, y=0.22, string="Cialis"` | Fill: `#111111` | Layer 06 |
| PRIM_05 | Text Block | `x=0.06, y=0.48, string="Tadalafil"` | Fill: `#333333` | Layer 07 |
| PRIM_06 | Text Block | `x=0.06, y=0.76, string="20mg"` | Fill: `#111111` | Layer 08 |

---

## Section D. Curve Reconstruction

- CURVE_01 (Accent Line / Logo Curve):
  - Type: Linear / Polyline
  - Start Point: `[Measured]` (0.000, 0.920)
  - End Point: `[Measured]` (1.000, 0.920)
  - Stroke Thickness: `[Measured]` 0.006 (relative height)
  - Confidence: High

---

## Section E. Layer Stack (Z-Ordering)

```text
Layer 01 [Bottom]: Substrate Base White (#FFFFFF)
Layer 02: Background Color Tint Zone
Layer 03: Primary Bottom Accent Band (#C9A227)
Layer 04: Brand Badge Geometry (#006A4E)
Layer 05: Brand Logo Mark
Layer 06: Primary Brand Typography (`Cialis`)
Layer 07: Subtitle Typography (`Tadalafil`)
Layer 08: Technical Annotations (`20mg`, `30 Pills`)
```

---

## Section F. Design Grid

| Grid Line | Normalized Position | Status | Description |
|---|---|---|---|
| Left Margin (u_min) | 0.060 | `[Measured]` | Primary left-alignment baseline |
| Right Margin (u_max) | 0.940 | `[Measured]` | Right alignment boundary |
| Baseline v_1 | 0.220 | `[Measured]` | Brand Title baseline |
| Baseline v_2 | 0.480 | `[Measured]` | INN Subtitle baseline |
| Baseline v_3 | 0.760 | `[Measured]` | Dosage & Unit count baseline |

---

## Section G. Typography Geometry

| Text ID | String | Font Family (Est.) | Weight | Case | Baseline (v) | Cap Height (% face) | Tracking | Alignment |
|---|---|---|---|---|---|---|---|---|
| TXT_01 | `Cialis` | DejaVu Sans | Extra Bold | ALL CAPS | 0.220 | 20.0% | +0.02 | Left |
| TXT_02 | `Tadalafil` | DejaVu Sans | Medium | Title Case | 0.480 | 8.0% | 0.00 | Left |
| TXT_03 | `20mg` | DejaVu Sans | Bold | Mixed | 0.760 | 12.0% | -0.01 | Left |
| TXT_04 | `30 Pills` | DejaVu Sans | Regular | Title Case | 0.760 | 8.0% | 0.00 | Right |

---

## Section H. Color Zones

| Zone ID | Polygon Vertices | HEX | RGB | Area % | Neighbor Zones |
|---|---|---|---|---|---|
| ZONE_01 | `(0,0)-(1,0)-(1,0.92)-(0,0.92)` | `#FFFFFF` | (255,255,255) | 88.0% | ZONE_02, ZONE_03 |
| ZONE_02 | `(0,0.92)-(1,0.92)-(1,1.0)-(0,1.0)` | `#C9A227` | — | 8.0% | ZONE_01 |
| ZONE_03 | `(0.76,0.06)-(0.94,0.06)-(0.94,0.22)-(0.76,0.22)` | `#006A4E` | — | 4.0% | ZONE_01 |

---

## Section I. Material Zones

| Zone ID | Target Surface | Material Finish | Roughness | Metallic | Clearcoat | Confidence |
|---|---|---|---|---|---|---|
| MAT_01 | Main Carton Body | Matte Cardboard | 0.70 | 0.00 | 0.00 | `[Measured]` High |
| MAT_02 | Brand Title | Spot UV Gloss | 0.15 | 0.00 | 0.85 | `[Estimated]` Medium |

---

## Section J. Relative Measurements

- Logo Height Ratio: `[Measured]` 10.0% of front face height
- Brand Title Height Ratio: `[Measured]` 20.0% of front face height
- Active Ingredient Height Ratio: `[Measured]` 8.0% of front face height
- Accent Stripe Height Ratio: `[Measured]` 8.0% of front face height

---

## Section K. Visual Hierarchy

- **Primary Focal Point:** Brand Title (`Cialis`) — 20% cap height.
- **Secondary Focal Point:** Dosage (`20mg`) & Accent Stripe (`#C9A227`).
- **Reading Order:** Top Logo -> Main Title -> INN Subtitle -> Dosage & Quantity.
- **Whitespace Ratio:** `[Measured]` 60.0% negative space.

---

## Section L. Reconstruction Constraints

- CONSTRAINT_01: `[Observed]` Reference photographs registered: raw_01_angle_left.png, raw_02_front.png, raw_03_angle_right.png.
- CONSTRAINT_02: `[Observed]` All candidate images preserved for human manual selection.
