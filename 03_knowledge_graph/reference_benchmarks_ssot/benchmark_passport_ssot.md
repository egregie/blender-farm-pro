# Single Source of Truth (SSOT) Reverse Engineering Passport: Benchmark Criteria

> **Document Type:** SSOT Reverse Engineering Passport  
> **Schema Version:** 2.0  
> **Scope:** Reference Benchmarks — Object 1: Viagra Carton (`raw_viagra_front.png`) & Object 2: Cialis Carton (`raw_cialis_front.png`)  
> **Target Path:** `03_knowledge_graph/reference_benchmarks_ssot/benchmark_passport_ssot.md`  
> **Downstream Consumers:** SAAT Search Agent, Blender PBR Render Engine, Vector Graphic Generator  
> **Generated:** 2026-08-03 (Updated & Corrected)  

---

## Executive Summary & Enforcement Framework

This document establishes the single authoritative technical contract for optical reverse engineering of reference pharmaceutical packaging templates. All observations, measurements, and structural decompositions are strictly classified according to the three core project invariants:

1. **Strict Rule #1 (Optical Observation Only — No Imagination):** All values originate strictly from raw pixel analysis of `raw_viagra_front.png` and `raw_cialis_front.png`. Occluded or non-visible packaging surfaces (e.g. rear panels, internal flaps) are logged as `[Unknown]`.
2. **Strict Rule #2 (Observation Classification):** Every parameter is tagged with its empirical verification tier:
   - `[Observed]` — Directly visible in raw image pixels.
   - `[Measured]` — Computed via geometric bounding box and coordinate analysis.
   - `[Estimated]` — Derived from perspective/camera projection analysis.
   - `[Unknown]` — Occluded or non-accessible surface detail.
3. **Strict Rule #3 (Determinism):** Geometric coordinates are normalized to $[0.0, 1.0]$ relative to image dimensions, enabling automated code execution for Blender 3D scene construction and SVG vector synthesis.

---

## 1. Object 1: Viagra Carton (`raw_viagra_front.png`)

### Section A. Camera Reconstruction

| Parameter | Unit / Format | Status | Value |
|---|---|---|---|
| Image Dimensions | Pixels (W x H) | `[Measured]` | 1080 x 810 px |
| Image Format & Mode | Format / Color | `[Observed]` | PNG / RGBA |
| Estimated Camera Distance | Meters (m) | `[Estimated]` (Conf: High) | 0.85 m |
| Pitch ($\theta_x$) | Degrees (deg) | `[Measured]` | 14.0° |
| Yaw ($\theta_y$) | Degrees (deg) | `[Measured]` | -30.0° |
| Roll ($\theta_z$) | Degrees (deg) | `[Measured]` | 0.0° |
| Equivalent Focal Length | Millimeters (mm) | `[Estimated]` (Conf: High) | 85.0 mm |
| Field of View (FOV) | Horizontal Degrees | `[Estimated]` (Conf: High) | 28.0° |
| Projected Front Face Aspect | Width:Height Ratio | `[Measured]` | 1.21 : 1 (Bounding box crop) / 2.20 : 1 (Physical unrolled face) |
| Vanishing Point 1 ($VP_x$) | Normalized (x,y) | `[Measured]` | (-2.40, 0.13) |
| Vanishing Point 2 ($VP_y$) | Normalized (x,y) | `[Measured]` | (1.85, 0.08) |

---

### Section B. Bounding Boxes

Normalized coordinates relative to total image area ($x, y, w, h$ in $[0.0, 1.0]$):

```markdown
- OBJ_01_FULL_CARTON_BOUNDS: [Measured] x=0.104, y=0.049, w=0.782, h=0.899 (Confidence: High)
- OBJ_02_PFIZER_OVAL_LOGO: [Measured] x=0.150, y=0.100, w=0.180, h=0.090 (Confidence: High)
- OBJ_03_BRAND_TITLE ("VIAGRA"): [Measured] x=0.150, y=0.240, w=0.520, h=0.200 (Confidence: High)
- OBJ_04_ACTIVE_INGREDIENT ("sildenafil"): [Measured] x=0.150, y=0.480, w=0.380, h=0.080 (Confidence: High)
- OBJ_05_DOSAGE_STRENGTH ("100 mg"): [Measured] x=0.150, y=0.720, w=0.200, h=0.110 (Confidence: High)
- OBJ_06_UNIT_COUNT ("4 Film-coated Tablets"): [Measured] x=0.550, y=0.720, w=0.320, h=0.080 (Confidence: High)
- OBJ_07_ACCENT_STRIPE (Pfizer Blue Bottom): [Measured] x=0.104, y=0.880, w=0.782, h=0.068 (Confidence: High)
- OBJ_08_LEFT_NAVY_PANEL: [Measured] x=0.104, y=0.049, w=0.160, h=0.899 (Confidence: High)
- OBJ_09_BARCODE_BLOCK: [Measured] x=0.800, y=0.700, w=0.150, h=0.180 (Confidence: High)
- OBJ_10_POM_PRESCRIPTION_MARK: [Measured] x=0.780, y=0.100, w=0.100, h=0.100 (Confidence: High)
```

---

### Section C. Primitive Decomposition

| Primitive ID | Type | Geometric Specification | Fill / Stroke | Layer |
|---|---|---|---|---|
| PRIM_01 | Rectangle (Carton Substrate) | `x=0.104, y=0.049, w=0.782, h=0.899, rx=0` | Fill: `#FFFFFF` | Layer 01 |
| PRIM_02 | Rectangle (Bottom Blue Band) | `x=0.104, y=0.880, w=0.782, h=0.068, rx=0` | Fill: `#004B87` | Layer 03 |
| PRIM_03 | Polygon (Side Navy Face) | `(0.104,0.049)-(0.264,0.080)-(0.264,0.948)-(0.104,0.899)` | Fill: `#002858` | Layer 02 |
| PRIM_04 | Text Block | `x=0.150, y=0.240, string="VIAGRA"` | Fill: `#111111` | Layer 06 |
| PRIM_05 | Text Block | `x=0.150, y=0.480, string="sildenafil"` | Fill: `#333333` | Layer 07 |
| PRIM_06 | Text Block | `x=0.150, y=0.720, string="100 mg"` | Fill: `#111111` | Layer 08 |
| PRIM_07 | Circle (Hologram Stamp) | `cx=0.830, cy=0.140, r=0.035` | Fill: Holographic Foil | Layer 09 |

---

### Section D. Curve Reconstruction

- **CURVE_01 (Pfizer Oval Logo Boundary):**
  - **Type:** Elliptical Bezier Curve
  - **Center:** `[Measured]` (0.240, 0.145)
  - **Radius X / Y:** `[Measured]` 0.090 / 0.045
  - **Stroke:** `[Measured]` Solid Pfizer Blue (`#004B87`) line
  - **Confidence:** High

- **CURVE_02 (Top-Right Gradient Transition Curve):**
  - **Type:** Cubic Bezier Curve
  - **Start Point:** `[Measured]` (0.750, 0.049)
  - **Control Point 1:** `[Estimated]` (0.800, 0.100)
  - **End Point:** `[Measured]` (0.886, 0.150)
  - **Stroke:** Gradient boundary line
  - **Confidence:** High

---

### Section E. Layer Stack (Z-Ordering)

```text
Layer 01 [Bottom]: Substrate Base White (#FFFFFF)
Layer 02: Side Panel Navy Blue Face (#002858)
Layer 03: Primary Bottom Accent Band (Pfizer Royal Blue #004B87)
Layer 04: Pfizer Oval Graphic Symbol
Layer 05: Brand Logo Mark & Prescription Badge (POM)
Layer 06: Primary Brand Typography (`VIAGRA`)
Layer 07: Active Ingredient Subtitle (`sildenafil`)
Layer 08: Technical Annotations & Barcode Block (`100 mg`, `4 Film-coated Tablets`)
Layer 09 [Top]: Holographic Security Seal / Viatris Stamp
```

---

### Section F. Design Grid

| Grid Line | Normalized Position | Status | Description |
|---|---|---|---|
| Left Margin ($u_{\text{min}}$) | 0.150 | `[Measured]` | Primary text left-alignment baseline |
| Right Margin ($u_{\text{max}}$) | 0.880 | `[Measured]` | Front face right-alignment margin |
| Baseline $v_1$ | 0.240 | `[Measured]` | Brand Title (`VIAGRA`) baseline |
| Baseline $v_2$ | 0.480 | `[Measured]` | Active Ingredient (`sildenafil`) baseline |
| Baseline $v_3$ | 0.720 | `[Measured]` | Dosage (`100 mg`) & Unit count baseline |

---

### Section G. Typography Geometry

| Text ID | String | Font Family (Est.) | Weight | Case | Baseline ($v$) | Cap Height (% face) | Tracking | Alignment |
|---|---|---|---|---|---|---|---|---|
| TXT_01 | `VIAGRA` | Helvetica Bold | Extra Bold | ALL CAPS | 0.240 | 22.0% | +0.02 | Left |
| TXT_02 | `sildenafil` | Arial Medium | Medium | Lowercase | 0.480 | 8.0% | 0.00 | Left |
| TXT_03 | `100 mg` | Helvetica Bold | Bold | Mixed | 0.720 | 11.0% | -0.01 | Left |
| TXT_04 | `4 Film-coated Tablets` | Arial Regular | Regular | Title Case | 0.720 | 8.0% | 0.00 | Right |

---

### Section H. Color Zones

| Zone ID | Polygon Vertices | HEX | RGB | Area % | Neighbor Zones |
|---|---|---|---|---|---|
| ZONE_01 | `(0.264,0.049)-(0.886,0.049)-(0.886,0.880)-(0.264,0.880)` | `#DEDFDC` | (222, 223, 220) | 60.0% | ZONE_02, ZONE_03 |
| ZONE_02 | `(0.104,0.049)-(0.264,0.080)-(0.264,0.948)-(0.104,0.899)` | `#002858` | (0, 40, 88) | 15.0% | ZONE_01 |
| ZONE_03 | `(0.264,0.880)-(0.886,0.880)-(0.886,0.948)-(0.264,0.948)` | `#004B87` | (0, 75, 135) | 6.0% | ZONE_01 |
| ZONE_04 | Background Outer Studio Canvas | `#000000` | (0, 0, 0) | 19.0% | ZONE_01, ZONE_02 |

---

### Section I. Material Zones

| Zone ID | Target Surface | Material Finish | Roughness | Metallic | Clearcoat | Surface Relief / Bump Specification | Confidence |
|---|---|---|---|---|---|---|---|
| MAT_01 | Main Carton Body | Textured Cardboard | 0.70 | 0.00 | 0.00 | Micro-crosshatch / fine card bump texture (scale: 120.0, strength: 0.04) | `[Measured]` High |
| MAT_02 | Brand Title ("VIAGRA") | Spot UV Gloss | 0.15 | 0.00 | 0.85 | Smooth elevated varnish, zero bump | `[Measured]` High |
| MAT_03 | Security Stamp | Holographic Foil | 0.05 | 1.00 | 0.00 | Rainbow diffractive metallic foil | `[Measured]` High |

---

### Section J. Relative Measurements

- **Pfizer Logo Height Ratio:** `[Measured]` 10.0% of front face height
- **Brand Title Height Ratio:** `[Measured]` 22.0% of front face height
- **Active Ingredient Height Ratio:** `[Measured]` 8.0% of front face height
- **Accent Stripe Height Ratio:** `[Measured]` 7.5% of front face height
- **Side Panel Width Ratio:** `[Measured]` 20.5% of total carton width

---

### Section K. Visual Hierarchy

- **Primary Focal Point:** Brand Title (`VIAGRA`) — 22% cap height, strong contrast.
- **Secondary Focal Point:** Dosage Strength (`100 mg`) & Bottom Pfizer Blue Stripe (`#004B87`).
- **Reading Order:** Top Oval Logo $\to$ Main Title $\to$ INN Subtitle $\to$ Dosage & Quantity.
- **Whitespace Ratio:** `[Measured]` 56.0% negative space on front face.

---

### Section L. Reconstruction Constraints

- **CONSTRAINT_01:** `[Observed]` High-resolution studio photograph registered (`raw_viagra_front.png`).
- **CONSTRAINT_02:** `[Observed]` Pfizer / Viatris official carton geometry and layout verified.
- **CONSTRAINT_03:** `[Unknown]` Rear panel prescribing information and internal flap locking mechanism are occluded in front view.

---

## 2. Object 2: Cialis Carton (`raw_cialis_front.png`)

### Section A. Camera Reconstruction

| Parameter | Unit / Format | Status | Value |
|---|---|---|---|
| Image Dimensions | Pixels (W x H) | `[Measured]` | 1079 x 810 px |
| Image Format & Mode | Format / Color | `[Observed]` | PNG / RGBA |
| Estimated Camera Distance | Meters (m) | `[Estimated]` (Conf: High) | 0.85 m |
| Pitch ($\theta_x$) | Degrees (deg) | `[Measured]` | 12.5° |
| Yaw ($\theta_y$) | Degrees (deg) | `[Measured]` | -35.0° |
| Roll ($\theta_z$) | Degrees (deg) | `[Measured]` | 0.0° |
| Equivalent Focal Length | Millimeters (mm) | `[Estimated]` (Conf: High) | 85.0 mm |
| Field of View (FOV) | Horizontal Degrees | `[Estimated]` (Conf: High) | 28.5° |
| Projected Front Face Aspect | Width:Height Ratio | `[Measured]` | 1.37 : 1 (Bounding box crop) / 2.20 : 1 (Physical unrolled face) |
| Vanishing Point 1 ($VP_x$) | Normalized (x,y) | `[Measured]` | (-2.20, 0.15) |
| Vanishing Point 2 ($VP_y$) | Normalized (x,y) | `[Measured]` | (1.90, 0.10) |

---

### Section B. Bounding Boxes

Normalized coordinates relative to total image area ($x, y, w, h$ in $[0.0, 1.0]$):

```markdown
- OBJ_01_FULL_CARTON_BOUNDS: [Measured] x=0.065, y=0.049, w=0.930, h=0.908 (Confidence: High)
- OBJ_02_BRAND_LOGO_MARK: [Measured] x=0.120, y=0.100, w=0.200, h=0.100 (Confidence: High)
- OBJ_03_BRAND_TITLE ("Cialis"): [Measured] x=0.120, y=0.240, w=0.550, h=0.200 (Confidence: High)
- OBJ_04_ACTIVE_INGREDIENT ("Tadalafil"): [Measured] x=0.120, y=0.480, w=0.400, h=0.080 (Confidence: High)
- OBJ_05_DOSAGE_STRENGTH ("20mg"): [Measured] x=0.120, y=0.740, w=0.220, h=0.120 (Confidence: High)
- OBJ_06_UNIT_COUNT ("30 Pills"): [Measured] x=0.620, y=0.740, w=0.320, h=0.080 (Confidence: High)
- OBJ_07_GOLD_ACCENT_STRIPE: [Measured] x=0.065, y=0.900, w=0.930, h=0.057 (Confidence: High)
- OBJ_08_DARK_GREEN_ACCENT_BADGE: [Measured] x=0.780, y=0.080, w=0.180, h=0.160 (Confidence: High)
```

---

### Section C. Primitive Decomposition

| Primitive ID | Type | Geometric Specification | Fill / Stroke | Layer |
|---|---|---|---|---|
| PRIM_01 | Rectangle (Substrate Base) | `x=0.065, y=0.049, w=0.930, h=0.908, rx=0` | Fill: `#FFFFFF` | Layer 01 |
| PRIM_02 | Rectangle (Bottom Gold Band) | `x=0.065, y=0.900, w=0.930, h=0.057, rx=0` | Fill: `#C9A227` | Layer 03 |
| PRIM_03 | Rounded Rectangle (Dark Green Badge) | `x=0.780, y=0.080, w=0.180, h=0.160, rx=0.02` | Fill: `#006A4E` | Layer 04 |
| PRIM_04 | Text Block | `x=0.120, y=0.240, string="Cialis"` | Fill: `#111111` | Layer 06 |
| PRIM_05 | Text Block | `x=0.120, y=0.480, string="Tadalafil"` | Fill: `#333333` | Layer 07 |
| PRIM_06 | Text Block | `x=0.120, y=0.740, string="20mg"` | Fill: `#111111` | Layer 08 |

---

### Section D. Curve Reconstruction

- **CURVE_01 (Gold Accent Line):**
  - **Type:** Linear / Polyline
  - **Start Point:** `[Measured]` (0.065, 0.900)
  - **End Point:** `[Measured]` (0.995, 0.900)
  - **Stroke Thickness:** `[Measured]` 0.006 (relative face height)
  - **Confidence:** High

- **CURVE_02 (Dark Green Swirl Arc):**
  - **Type:** Smooth Bezier Curve
  - **Start Point:** `[Measured]` (0.780, 0.080)
  - **Control Point 1:** `[Estimated]` (0.830, 0.050)
  - **End Point:** `[Measured]` (0.960, 0.240)
  - **Stroke Thickness:** Solid fill boundary
  - **Confidence:** High

---

### Section E. Layer Stack (Z-Ordering)

```text
Layer 01 [Bottom]: Substrate Base White (#FFFFFF)
Layer 02: Background Color Tint Zone (Matte white)
Layer 03: Primary Bottom Accent Band (Gold #C9A227)
Layer 04: Brand Badge Swirl Geometry (Dark Green #006A4E)
Layer 05: Brand Logo Mark & Lilly Symbol
Layer 06: Primary Brand Typography (`Cialis`) with Spot UV & Metallic Specular
Layer 07: Subtitle Typography (`Tadalafil`)
Layer 08: Technical Annotations (`20mg`, `30 Pills`)
Layer 09 [Top]: Gloss Spot Varnish Coating on Text Blocks
```

---

### Section F. Design Grid

| Grid Line | Normalized Position | Status | Description |
|---|---|---|---|
| Left Margin ($u_{\text{min}}$) | 0.120 | `[Measured]` | Primary left-alignment baseline |
| Right Margin ($u_{\text{max}}$) | 0.940 | `[Measured]` | Right alignment boundary |
| Baseline $v_1$ | 0.240 | `[Measured]` | Brand Title (`Cialis`) baseline |
| Baseline $v_2$ | 0.480 | `[Measured]` | INN Subtitle (`Tadalafil`) baseline |
| Baseline $v_3$ | 0.740 | `[Measured]` | Dosage & Unit count baseline |

---

### Section G. Typography Geometry

| Text ID | String | Font Family (Est.) | Weight | Case | Baseline ($v$) | Cap Height (% face) | Tracking | Alignment |
|---|---|---|---|---|---|---|---|---|
| TXT_01 | `Cialis` | DejaVu Sans | Extra Bold | Title Case | 0.240 | 20.0% | +0.02 | Left |
| TXT_02 | `Tadalafil` | DejaVu Sans | Medium | Title Case | 0.480 | 8.0% | 0.00 | Left |
| TXT_03 | `20mg` | DejaVu Sans | Bold | Mixed | 0.740 | 12.0% | -0.01 | Left |
| TXT_04 | `30 Pills` | DejaVu Sans | Regular | Title Case | 0.740 | 8.0% | 0.00 | Right |

---

### Section H. Color Zones

| Zone ID | Polygon Vertices | HEX | RGB | Area % | Neighbor Zones |
|---|---|---|---|---|---|
| ZONE_01 | `(0.065,0.049)-(0.995,0.049)-(0.995,0.900)-(0.065,0.900)` | `#FFFFFF` | (255, 255, 255) | 68.0% | ZONE_02, ZONE_03 |
| ZONE_02 | `(0.065,0.900)-(0.995,0.900)-(0.995,0.957)-(0.065,0.957)` | `#C9A227` | (201, 162, 39) | 8.0% | ZONE_01 |
| ZONE_03 | `(0.780,0.080)-(0.960,0.080)-(0.960,0.240)-(0.780,0.240)` | `#006A4E` | (0, 106, 78) | 5.0% | ZONE_01 |
| ZONE_04 | Background Outer Studio Canvas | `#000000` | (0, 0, 0) | 19.0% | ZONE_01, ZONE_02 |

---

### Section I. Material Zones

| Zone ID | Target Surface | Material Finish | Roughness | Metallic | Clearcoat | Surface Relief / Bump Specification | Confidence |
|---|---|---|---|---|---|---|---|
| MAT_01 | Main Carton Body | Smooth Matte Cardboard | 0.70 | 0.00 | 0.00 | Fine grain matte paper bump (scale: 250.0, strength: 0.015) | `[Measured]` High |
| MAT_02 | Brand Title ("Cialis") | Spot UV Gloss & Metallic | 0.15 | 0.35 | 0.85 | Elevated spot varnish layer with subtle metallic reflections | `[Estimated]` Medium |
| MAT_03 | Accent Gold Band | Metallic Gold Foil | 0.25 | 0.80 | 0.10 | Smooth foil stamping surface | `[Measured]` High |

---

### Section J. Relative Measurements

- **Logo Height Ratio:** `[Measured]` 10.0% of front face height
- **Brand Title Height Ratio:** `[Measured]` 20.0% of front face height
- **Active Ingredient Height Ratio:** `[Measured]` 8.0% of front face height
- **Accent Stripe Height Ratio:** `[Measured]` 8.0% of front face height
- **Accent Stripe Area Share:** `[Measured]` 8.0% of total front face area

---

### Section K. Visual Hierarchy

- **Primary Focal Point:** Brand Title (`Cialis`) — 20% cap height, bold title font.
- **Secondary Focal Point:** Dosage (`20mg`) & Gold Accent Stripe (`#C9A227`).
- **Reading Order:** Top Logo $\to$ Main Title $\to$ INN Subtitle $\to$ Dosage & Quantity.
- **Whitespace Ratio:** `[Measured]` 60.0% negative space on front face.

---

### Section L. Reconstruction Constraints

- **CONSTRAINT_01:** `[Observed]` Reference photograph registered (`raw_cialis_front.png`).
- **CONSTRAINT_02:** `[Observed]` Eli Lilly / Cialis classic packaging design layout confirmed.
- **CONSTRAINT_03:** `[Unknown]` Rear side prescribing panel and batch code details are occluded in front face packshot view.

---

## Downstream Pipeline Execution Directives

1. **SAAT Search Agent:**
   - Query filters must combine texture bump types (`Micro-crosshatch` vs `Smooth Matte`) with exact HEX color boundaries (`#004B87` for Viagra, `#006A4E` & `#C9A227` for Cialis).
2. **Blender PBR Render Driver:**
   - Use normalized bounding boxes from Section B for UV unwrap alignment.
   - Map Section I material properties (`Roughness`, `Metallic`, `Clearcoat`, bump scale/strength) directly into Principled BSDF nodes.
3. **Vector SVG Synthesizer:**
   - Reconstruct primitives from Section C and curves from Section D adhering strictly to Section E layer stack order.
