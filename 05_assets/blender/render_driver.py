"""PharmaGen PRO — Blender scene driver (EXPERIMENTAL, runs INSIDE Blender).

Invoked headless by src/blender_renderer.py:
    blender --background --factory-startup --python render_driver.py -- \
        --job <job.json> --out <out.png> --engine-type CYCLES --samples 64 \
        --res-x 2048 --res-y 2048

The job file is a RENDER MANIFEST conforming to
schemas/render_manifest.schema.json, validated on the project side before it
gets here. This script therefore trusts its shape and does not re-derive
anything from it — notably, carton dimensions arrive resolved, so there is no
aspect-ratio guessing in this file.

Builds a PROCEDURAL packshot scene from the job's structured data (no
hand-authored .blend asset required — see the roadmap §1 "design choice").
An OPTIONAL hand-authored "{template_id}.blend" in blender.scenes_dir can be
added later (Phase 2) and loaded instead of the procedural build; this script
already looks for one and prefers it when present.

Camera pitch/rotation reuse the SAME optical language documented for the
Gemini prompt templates (25 deg pitch / 35 deg rotation for most families,
20/25-30 deg for the vertical family) so both engines target comparable
framing — see 06_docs/DESIGN_RATIONALE.md.
"""
import bpy
import mathutils
import sys
import json
import math
from pathlib import Path

# ── argv (everything after the bare "--") ────────────────────────────────────
_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(flag: str, default=None):
    if flag in _argv:
        return _argv[_argv.index(flag) + 1]
    return default


JOB_PATH   = _arg("--job")
OUT_PATH   = _arg("--out")
ENGINE     = _arg("--engine-type", "CYCLES")
SAMPLES    = int(_arg("--samples", "64"))
RES_X      = int(_arg("--res-x", "2048"))
RES_Y      = int(_arg("--res-y", "2048"))
# Diagnostic seam: build the scene, write its measured geometry to this path as
# JSON, and skip rendering. Exists because carton/stripe placement can only be
# verified inside Blender, and a packshot is far too slow and too indirect to
# assert on in a unit test — see tests/test_blender_carton.py.
DUMP_SCENE = _arg("--dump-scene")

if not JOB_PATH or not (OUT_PATH or DUMP_SCENE):
    raise SystemExit(
        "[render_driver] --job is required, plus --out to render "
        "(or --dump-scene to only measure the built scene)")

with open(JOB_PATH, "r", encoding="utf-8") as f:
    JOB = json.load(f)

# Camera calibration per template family — same numbers used in the Gemini
# prompt templates (src/passport_generator.py TEMPLATE_* constants).
VERTICAL_FAMILY = {"T_VERT_VIAL", "T_VERT_DROPPER", "T_VERT_INHALER"}
if JOB.get("template_id") in VERTICAL_FAMILY:
    PITCH_DEG, ROTATION_DEG = 20.0, 27.5   # 20 deg pitch, ~25-30 deg rotation
else:
    PITCH_DEG, ROTATION_DEG = 25.0, 35.0


def hex_to_rgba(hex_str: str, default=(0.9, 0.9, 0.9, 1.0)):
    """sRGB hex -> approximate linear RGBA for Principled BSDF base_color."""
    if not hex_str or not str(hex_str).startswith("#"):
        return default
    h = hex_str.lstrip("#")
    if len(h) != 6:
        return default
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return default
    srgb_to_linear = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def make_material(name: str, hex_color: str, roughness=0.35) -> "bpy.types.Material":
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = hex_to_rgba(hex_color)
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = roughness
    return mat


# Row 6 of the front-panel grid (src/passport_generator.py) specifies a ~4mm
# band. reference_analysis.md §5 put it at "roughly 8-12%" of the front-face
# height, but §9 flagged that as eyeballed rather than pixel-measured — and it
# was too generous: measuring the accent band in all nine curated references
# gives 2.9-6.1% (median 4.0%). At 8% the band came out ~50% too thick on T1 and
# ~135% too thick on T_VERT_VIAL. The millimetre figure stays the target and the
# measured percentages bound it.
STRIPE_TARGET_M = 0.004
STRIPE_MIN_FRAC = 0.03
STRIPE_MAX_FRAC = 0.06

# Matte, uncoated cardstock (reference_analysis.md §4: "roughness reads high
# ~0.6-0.8 in a Principled-BSDF sense", §8: raise the body from 0.5). The stripe
# and badge are printed ink on that same board, and §3 records no hard specular
# highlight anywhere on the carton, so every carton surface takes this value —
# leaving the stripe semi-gloss would put a sheen on it the references lack.
# The background plane is deliberately rougher still and keeps its own 0.9.
MATTE_ROUGHNESS = 0.7

# The top-right brand badge (reference_analysis.md §5, second of the two places
# brand colour is allowed to appear). Measured across the nine references: the
# square runs 21-37% of the SHORTER front-face edge — a tighter fit than either
# face-height (12-29%) or face-width (7-37%) alone — inset ~5% of face width from
# the right edge and ~3% of face height from the top.
BADGE_SIDE_FRAC         = 0.25
BADGE_MARGIN_RIGHT_FRAC = 0.05
BADGE_MARGIN_TOP_FRAC   = 0.03

# ── the front-panel label grid ───────────────────────────────────────────────
# Fonts are VENDORED, not taken from the system. The project's determinism
# invariant (see the world-background and film-response comments) says the same
# input must give the same pixel on any machine, and a system font silently
# changes the render on a machine that lacks it. DejaVu is redistributable —
# 05_assets/blender/fonts/LICENSE_DEJAVU. It reads wider and rounder than the
# neo-grotesque in the references; that is a known, accepted difference.
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONT_REGULAR = "DejaVuSans.ttf"
FONT_BOLD    = "DejaVuSans-Bold.ttf"

# Near-black rather than pure black: the references measure ~#1A1A1A on the
# darkest glyph interiors, and pure black on matte board reads artificially hard.
LABEL_INK = "#1A1A1A"

# The grid, measured off the references in the FRONT FACE's own coordinates —
# u across (0 = near vertical corner, 1 = far edge), v down (0 = top, 1 = bottom).
# See reference_analysis.md §6 for the row order and the measurement pass that
# produced these numbers.
LABEL_LEFT_FRAC  = 0.07     # every row starts here
LABEL_RIGHT_FRAC = 0.95     # the right-aligned unit count ends here

# TYPE SIZE IS NOT ONE RULE. Measuring the references shows two different laws,
# and using either one for everything is what made the first attempt wrong:
#
#   brand name  scales with the carton — 6.3mm on a T3 to 30.6mm on a
#               T_VERT_VIAL (4.9x), but a steady 0.131-0.209 of the FACE HEIGHT
#               (1.6x). It is the hero element, sized to the package.
#   small print holds its size in MILLIMETRES — the bottom row measures 4.4-5.5mm
#               on eight of nine templates (1.9x) while varying 3.5x as a
#               fraction of the face. It is set to be read, not to fill space.
#
# Driving the small print off face height, as this originally did, gives 2.9mm on
# a T1 (unreadably small against a 5.5mm reference) and 8.8mm on a T_VERT_VIAL,
# where "2000iu" and "10 Vials" then close on each other in the bottom row.
BRAND_TOP_FRAC   = 0.10     # measured 0.07-0.12 across templates
BRAND_LINE_FRAC  = 0.15     # cap height, fraction of face height (0.131-0.209)
# Baseline-to-baseline distance when the name wraps, as a multiple of cap height.
# The reference's two brand lines sit at v 0.110 and 0.260 over a 0.12 cap, so
# 1.25 — tighter than Blender's default single spacing, which at this cap height
# would push the second line into the ingredient row.
BRAND_LINE_PITCH = 1.25
BRAND_MAX_LINES  = 2
# Clear space the brand block must leave above the ingredient row.
BRAND_INGREDIENT_GAP_FRAC = 0.01
# The brand block shares its rows with the badge in the top-right corner, so it
# has to stop short of it. This gap is measured from where the badge ACTUALLY
# lands rather than assumed: the badge is sized off the shorter face edge, so on
# a portrait carton it eats a much larger share of the width (u from 0.70 on
# T_VERT_VIAL) than on a landscape one (0.84 on T_MULTIPACK). A single fixed
# limit that clears one shape runs straight into the other.
BRAND_BADGE_GAP_FRAC = 0.03

INGREDIENT_TOP_FRAC = 0.46  # measured 0.44-0.48
INGREDIENT_CAP_M    = 0.0055   # reference 3.8-7.7mm, median 5.5

# ...but an absolute size still has to yield on a shallow face. A T3 carton is
# only 35mm tall, and 5.5mm of ingredient plus 5mm of bottom row inside the
# 11.9mm the grid leaves between those two rows leaves them touching. The
# references do the same thing: T3 carries the smallest type in the set, 3.8mm.
# Capping the small print at this fraction of face height reproduces that
# (0.12 x 35 = 4.2mm) and changes nothing on a normal carton, where the absolute
# size is already the smaller of the two.
SMALL_PRINT_MAX_FRAC = 0.12

BOTTOM_ROW_TOP_FRAC = 0.80  # measured 0.76-0.83; dosage left, unit count right
BOTTOM_ROW_CAP_M    = 0.0050   # reference 4.4-8.5mm, eight of nine at 4.4-5.5
# The bottom row holds two strings that grow toward each other from opposite
# margins, so each is capped at half the space with this gutter between them.
# Sizing them independently lets them meet in the middle on a narrow face: a
# 50mm-wide T_VERT_DROPPER put "2000iu" and "10 Vials" through each other.
# Absolute, not a fraction of the face: on a 55mm-wide T_VERT_INHALER a 4%
# gutter is 2.2mm, which between two 5mm capitals reads as no gap at all.
BOTTOM_ROW_GUTTER_M = 0.006
# Clear space between the bottom row's descenders and the accent stripe.
BOTTOM_ROW_CLEARANCE_FRAC = 0.02


# ── the side panel ───────────────────────────────────────────────────────────
# The visible side panel is the carton's local -X face. The camera looks along
# +Y, the carton is rotated by +ROTATION_DEG about Z, and that turns the -X
# normal to (-cos, -sin, 0): the negative Y component means it faces the camera
# and the negative X puts it on the left of frame. The +X face turns away and is
# never seen. True for both rotation angles the project uses, 35 and 27.5.
#
# WHAT THE REFERENCE PANEL ACTUALLY CONTAINS, and why most of it is not copied:
# magnifying the side panel of the curated renders shows a 2D code that is a blob
# of organic noise with no quiet zone, no finder pattern and no clock track; a
# LOT/EXP block whose values read "BAWNL TE9?" and "SLAQF FD9T"; and a microprint
# paragraph that is not text at all. That is the same failure reference_analysis
# §7 records as "Datels". The reference is evidence of LAYOUT, not of CONTENT.
#
# So: the barcode is a real, decodable Code 128 of the SKU id; LOT and EXP are
# printed as empty field labels, which is what a real carton carries because the
# batch and expiry are inkjetted at packing time (and the T_VERT_VIAL reference
# shows exactly that — a boxed LOT and a bare EXP with no values); and the small
# block prints strings the manifest already holds. Nothing here is invented.
PANEL_MARGIN_FRAC   = 0.10   # of panel width, kept clear at both edges
BARCODE_TOP_FRAC    = 0.06   # of panel height, where the symbol starts
BARCODE_LEN_FRAC    = 0.40   # of panel height the symbol spans
BARCODE_BAR_FRAC    = 0.55   # of panel width the bars run across
BARCODE_HRI_CAP_M   = 0.0025 # human-readable line under the symbol
FIELD_TOP_FRAC      = 0.56   # LOT / EXP block
FIELD_CAP_M         = 0.0035
FIELD_RULE_FRAC     = 0.45   # rule length, of panel width
DATA_BLOCK_TOP_FRAC = 0.74
DATA_BLOCK_GAP_FRAC = 0.03   # clear space under the LOT/EXP block
PANEL_BOTTOM_MARGIN_FRAC = 0.02  # clear space above the carton's bottom edge
DATA_BLOCK_CAP_M    = 0.0022
# Code 128 cannot be printed below roughly this module width and still scan.
BARCODE_MIN_MODULE_M = 0.00019


# Code 128 bar/space widths, symbol values 0..106. Each entry is six digits: the
# widths of bar, space, bar, space, bar, space in modules, totalling 11.
_CODE128_PATTERNS = (
    "212222", "222122", "222221", "121223", "121322", "131222", "122213",
    "122312", "132212", "221213", "221312", "231212", "112232", "122132",
    "122231", "113222", "123122", "123221", "223211", "221132", "221231",
    "213212", "223112", "312131", "311222", "321122", "321221", "312212",
    "322112", "322211", "212123", "212321", "232121", "111323", "131123",
    "131321", "112313", "132113", "132311", "211313", "231113", "231311",
    "112133", "112331", "132131", "113123", "113321", "133121", "313121",
    "211331", "231131", "213113", "213311", "213131", "311123", "311321",
    "331121", "312113", "312311", "332111", "314111", "221411", "431111",
    "111224", "111422", "121124", "121421", "141122", "141221", "112214",
    "112412", "122114", "122411", "142112", "142211", "241211", "221114",
    "413111", "241112", "134111", "111242", "121142", "121241", "114212",
    "124112", "124211", "411212", "421112", "421211", "212141", "214121",
    "412121", "111143", "111341", "131141", "114113", "114311", "411113",
    "411311", "113141", "114131", "311141", "411131", "211412", "211214",
    "211232", "233111",
)
_CODE128_STOP = "2331112"          # seven elements: the stop bar is 2 wide
_CODE128_START_B = 104


def encode_code128b(text: str):
    """Encode *text* as Code 128 subset B and return its module widths.

    Returns a list of integers: alternating bar, space, bar, space ... starting
    with a bar, each the width of that run in modules. Quiet zones are NOT
    included; the caller adds them, because they are part of laying the symbol
    out rather than of encoding it.

    A real, decodable symbol rather than a decorative one. That is not vanity:
    the reference renders put a 2D code on this panel that cannot be scanned, and
    reproducing an unscannable barcode would be re-creating by hand exactly the
    hallucination this engine exists to eliminate. tests/test_blender_carton.py
    decodes what comes out of here with an independent reader.
    """
    for ch in text:
        if not 32 <= ord(ch) <= 126:
            raise ValueError(
                f"[render_driver] {ch!r} (U+{ord(ch):04X}) is outside Code 128 "
                f"subset B, which covers ASCII 32-126; cannot encode {text!r}")
    values = [_CODE128_START_B] + [ord(c) - 32 for c in text]
    checksum = values[0]
    for i, v in enumerate(values[1:], start=1):
        checksum += i * v
    values.append(checksum % 103)
    widths = []
    for v in values:
        widths.extend(int(d) for d in _CODE128_PATTERNS[v])
    widths.extend(int(d) for d in _CODE128_STOP)
    return widths


def _load_font(filename: str):
    """Vendored font, loaded once per Blender session."""
    existing = bpy.data.fonts.get(filename)
    if existing is not None:
        return existing
    font = bpy.data.fonts.load(str(FONT_DIR / filename))
    font.name = filename
    return font


def _text_dimensions(obj):
    """World-space size of a text object, after evaluation.

    Text has no mesh until the depsgraph builds one, so `obj.dimensions` is zero
    until it is evaluated. Because the object is rotated upright, the returned
    axes read (width, thickness, height).
    """
    dg = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(dg).dimensions


_CAP_RATIO_CACHE = {}


def _cap_ratio(font) -> float:
    """Cap height per unit of Blender's text `size`, measured for this font.

    `size` is not the cap height and the two are not related by any documented
    constant — for the vendored DejaVu the ratio comes out near 0.49. Measuring
    it rather than hardcoding it means the grid constants below can be stated as
    what they actually are, fractions of the face that a capital letter fills,
    directly comparable to the numbers measured off the references. It also means
    swapping the font does not silently resize every label in the catalogue.
    """
    key = font.name
    if key not in _CAP_RATIO_CACHE:
        bpy.ops.object.text_add(location=(0.0, 0.0, 0.0))
        probe = bpy.context.active_object
        probe.data.body = "H"
        probe.data.font = font
        probe.data.size = 1.0
        _CAP_RATIO_CACHE[key] = _text_dimensions(probe).y or 1.0
        bpy.data.objects.remove(probe, do_unlink=True)
    return _CAP_RATIO_CACHE[key]


def _balanced_two_lines(text: str) -> str:
    """Split on the word break that leaves the two lines closest in length."""
    words = text.split()
    if len(words) < 2:
        return text
    best, best_diff = None, None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        diff = abs(len(a) - len(b))
        if best_diff is None or diff < best_diff:
            best, best_diff = (a, b), diff
    return "\n".join(best)


def _add_text(name, body, font, cap_h, ink_mat, x, z, y, align="LEFT"):
    """One row of the label, standing on the front face.

    A text object is created lying in the XY plane facing +Z. The carton's front
    face points -Y, so rotating +90 deg about X turns the glyph plane to face it
    while leaving the reading direction on +X and the ascenders on +Z.

    `cap_h` is the height a capital letter should occupy, not Blender's `size` —
    see _cap_ratio(). Sizing rows by cap height keeps the type consistent between
    rows whose strings happen to contain different ascenders and descenders.
    """
    bpy.ops.object.text_add(location=(x, y, z))
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.font = font
    t.data.size = cap_h / _cap_ratio(font)
    t.data.align_x = align
    t.data.align_y = "TOP"
    t.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    t.data.materials.append(ink_mat)
    return t


def _fit_above(t, floor_z):
    """Shrink a row until its lowest point clears `floor_z`, top left in place.

    Needed for the brand name once it wraps. Two lines at the single-line cap
    height do not fit the band the grid leaves above the ingredient row: measured
    over the catalogue, 18 of 391 names wrap, and every one of them ran past
    v 0.46 and into the row below. The references do the same thing — T1's
    two-line name is set at a 0.12 cap where a one-liner gets more.

    The correction is exact in one pass. Text scales about its origin, which
    align_y="TOP" puts at the top of the block, so shrinking by
    (allowed / actual) lands the bottom precisely on the floor.
    """
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    lowest = min((t.matrix_world @ Vector(c)).z
                 for c in t.evaluated_get(dg).bound_box)
    if lowest >= floor_z:
        return t
    actual, allowed = t.location.z - lowest, t.location.z - floor_z
    if actual > 0 and allowed > 0:
        t.data.size *= allowed / actual
    return t


def _required_lift(t, floor_z):
    """How far this row would have to rise to clear `floor_z`. Never negative."""
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    lowest = min((t.matrix_world @ Vector(c)).z
                 for c in t.evaluated_get(dg).bound_box)
    return max(floor_z - lowest, 0.0)


def _lift_row(texts, floor_z):
    """Raise a whole row by one amount so it clears `floor_z`.

    The bottom row is positioned from the top of the face while its size is an
    absolute millimetre value, so on a short face the two assumptions collide:
    5mm of type hung from v=0.80 of a 55mm carton drives the descender of "40mg"
    through the accent stripe. Anchoring against the obstacle beats guessing a v
    that happens to clear it for every carton in the catalogue.

    Crucially the lift is shared. Measuring each string separately moves "40mg",
    which has a descender, further than "10 Pills", which has none — and the two
    stop sharing a baseline, which is exactly what a reader notices.
    """
    if floor_z is None or not texts:
        return texts
    lift = max(_required_lift(t, floor_z) for t in texts)
    for t in texts:
        t.location.z += lift
    return texts


def _fit_width(t, max_width):
    """Shrink a row until it fits the space allowed for it.

    Font size scales the glyphs linearly, so one corrective pass is exact rather
    than iterative. Real data needs this: brand names reach 30 characters and the
    ingredient row reaches 61 ("Sildenafil / Tadalafil / Vardenafil / Avanafil
    (Specimen Mix)"), against faces as narrow as 35mm.
    """
    width = _text_dimensions(t).x
    if width > max_width > 0 and width > 0:
        t.data.size *= max_width / width
    return t


def build_label(box, label_content: dict, face_w, face_h, left_x, front_y, top_z,
                half_thick, unit_scale, badge_left_x=None, stripe_top_z=None):
    """The printed front panel: brand, ingredient, dosage and unit count.

    Every string is rendered as real text geometry carrying the manifest's bytes
    verbatim. That is the whole point of the Blender engine over a prompt-driven
    one: reference_analysis.md §7 caught the Gemini renders printing "Datels", a
    word that does not exist, on the Lumigan sample. A text object cannot
    hallucinate — it draws the string it is given or nothing at all.

    Rows are placed in the FRONT FACE's own coordinates and the objects are
    parented to the carton before it rotates, exactly like the stripe and badge.
    """
    # A job with no label_content did not come through the contract: the field
    # is `required` in the schema. Rendering an unlabelled carton is a silent
    # content failure, so stop instead — the same reasoning that makes a missing
    # carton block fatal a few lines up.
    if label_content is None:
        raise SystemExit(
            "[render_driver] job has no 'label_content' block, which the render "
            "manifest schema marks required. Rendering an unlabelled packshot "
            "would fail silently. Regenerate the manifest via Stage 1.")
    if not label_content:
        return []

    ink = make_material("label_ink", LABEL_INK, roughness=MATTE_ROUGHNESS)
    regular, bold = _load_font(FONT_REGULAR), _load_font(FONT_BOLD)
    # Sat just proud of the face so the glyphs cannot z-fight with it. The stripe
    # and badge straddle the plane instead; text is flat, so it goes in front.
    y = front_y - half_thick
    left = left_x + LABEL_LEFT_FRAC * face_w
    right = left_x + LABEL_RIGHT_FRAC * face_w
    rows = []

    def v_to_z(v):
        return top_z - v * face_h

    def small_print_cap(cap_m):
        """Absolute size, but never enough to crowd a shallow face."""
        return min(cap_m * unit_scale, SMALL_PRINT_MAX_FRAC * face_h)

    brand = (label_content.get("brand_name_display") or "").strip()
    if brand:
        t = _add_text("label_brand", brand, bold, BRAND_LINE_FRAC * face_h, ink,
                      left, v_to_z(BRAND_TOP_FRAC), y)
        # Run to the badge if there is one, otherwise to the normal right margin.
        brand_right = (badge_left_x - BRAND_BADGE_GAP_FRAC * face_w
                       if badge_left_x is not None else right)
        allowed = max(brand_right - left, 0.1 * face_w)
        if _text_dimensions(t).x > allowed and BRAND_MAX_LINES > 1:
            # Wrapping buys height in exchange for width, so try it before
            # shrinking: a two-line name at full size reads better than a
            # one-line name squeezed to half the cap height.
            t.data.body = _balanced_two_lines(brand)
            t.data.space_line = (BRAND_LINE_PITCH * BRAND_LINE_FRAC * face_h) / t.data.size
        _fit_width(t, allowed)
        # Only ever shrinks, so a one-line name that already fits is untouched.
        _fit_above(t, v_to_z(INGREDIENT_TOP_FRAC - BRAND_INGREDIENT_GAP_FRAC))
        rows.append(t)

    ingredient = (label_content.get("active_ingredient_display") or "").strip()
    if ingredient:
        t = _add_text("label_ingredient", ingredient, regular,
                      small_print_cap(INGREDIENT_CAP_M), ink,
                      left, v_to_z(INGREDIENT_TOP_FRAC), y)
        rows.append(_fit_width(t, right - left))

    half_row = max((right - left - BOTTOM_ROW_GUTTER_M * unit_scale) / 2.0,
                   0.1 * face_w)
    # Keep the bottom row clear of the accent stripe by this much of the face.
    floor_z = (stripe_top_z + BOTTOM_ROW_CLEARANCE_FRAC * face_h
               if stripe_top_z is not None else None)

    bottom_row = []
    dosage = (label_content.get("dosage_display") or "").strip()
    if dosage:
        t = _add_text("label_dosage", dosage, bold, small_print_cap(BOTTOM_ROW_CAP_M),
                      ink, left, v_to_z(BOTTOM_ROW_TOP_FRAC), y)
        bottom_row.append(_fit_width(t, half_row))

    count = (label_content.get("unit_count_display") or "").strip()
    if count:
        t = _add_text("label_unit_count", count, regular,
                      small_print_cap(BOTTOM_ROW_CAP_M), ink,
                      right, v_to_z(BOTTOM_ROW_TOP_FRAC), y, align="RIGHT")
        bottom_row.append(_fit_width(t, half_row))

    rows.extend(_lift_row(bottom_row, floor_z))

    for t in rows:
        t.parent = box
        t.matrix_parent_inverse = box.matrix_world.inverted()
    # Counts LINES, not strings: a wrapped brand name is two. Cheap enough to
    # print on every render and it is the one number that says at a glance
    # whether the face came out labelled.
    lines = sum(t.data.body.count(chr(10)) + 1 for t in rows)
    print(f"[render_driver] label: {lines} text object(s)")
    return rows


def _add_panel_text(name, body, font, cap_h, ink_mat, u, v, x, align="LEFT"):
    """A text row on the -X side panel.

    A text object is created in the XY plane facing +Z. Rotating +90 deg about X
    stands it upright facing -Y (the front face); a further -90 about Z swings it
    round to face -X, which is the side panel. The sign matters: +90 about Z
    would leave the normal at +X, pointing INTO the carton, and the row would
    render mirrored and backfacing. Reading then runs along -Y, so rows are
    anchored at the panel's back edge and read toward the front.
    """
    bpy.ops.object.text_add(location=(x, u, v))
    t = bpy.context.active_object
    t.name = name
    t.data.body = body
    t.data.font = font
    t.data.size = cap_h / _cap_ratio(font)
    t.data.align_x = align
    t.data.align_y = "TOP"
    t.rotation_euler = (math.radians(90.0), 0.0, math.radians(-90.0))
    t.data.materials.append(ink_mat)
    return t


def build_side_panel(box, manifest: dict, panel_w, panel_h, left_x, back_y,
                     top_z, half_thick, unit_scale):
    """The visible side panel: barcode, empty LOT/EXP fields, and a data block.

    panel_w is the carton DEPTH and panel_h its height. Everything is placed in
    the panel's own coordinates and every string comes from the manifest.
    """
    carton = manifest.get("carton") or {}
    sku_id = str(manifest.get("sku_id") or "")
    built = []
    if not sku_id:
        return built

    ink = make_material("panel_ink", LABEL_INK, roughness=MATTE_ROUGHNESS)
    regular, bold = _load_font(FONT_REGULAR), _load_font(FONT_BOLD)
    x = left_x - half_thick                      # just proud of the -X face
    margin = PANEL_MARGIN_FRAC * panel_w
    usable_w = panel_w - 2 * margin
    # Rows read along -Y, so they start at the BACK edge and run to the front.
    u_start = back_y + panel_w - margin
    u_front = back_y + margin

    def v_at(frac):
        return top_z - frac * panel_h

    # ── barcode ──────────────────────────────────────────────────────────────
    widths = encode_code128b(sku_id)
    total_modules = sum(widths) + 20              # 10 modules of quiet zone each end
    span = BARCODE_LEN_FRAC * panel_h
    module = span / total_modules
    bar_len = BARCODE_BAR_FRAC * usable_w

    # An 11-character Code 128 is a long symbol, and these are small cartons.
    # Measured across the catalogue the module lands between 0.08mm and 0.40mm,
    # so on the shorter panels it falls under the ~0.19mm a scanner needs and
    # under the ~2 pixels per module a 2048px render can resolve — the bars merge
    # into a grey block. Say so rather than shipping a code that only looks like
    # one. This is also the argument FOR the DataMatrix the carton data already
    # asks for in `features`: a 2D symbol carries the same payload in a fraction
    # of the area, which is exactly why real small-format pharma packs use one.
    module_mm = (module / unit_scale) * 1000.0 if unit_scale else 0.0
    if module_mm < BARCODE_MIN_MODULE_M * 1000.0:
        print(f"[render_driver] WARNING: barcode module is {module_mm:.3f}mm on a "
              f"{panel_h / unit_scale * 1000:.0f}mm panel, below the ~"
              f"{BARCODE_MIN_MODULE_M * 1000:.2f}mm a scanner needs; the symbol is "
              f"correct but will not resolve at this size", file=sys.stderr)

    v = v_at(BARCODE_TOP_FRAC) - 10 * module      # leading quiet zone
    for i, w in enumerate(widths):
        run = w * module
        if i % 2 == 0:                            # even index = bar
            bpy.ops.mesh.primitive_cube_add(
                size=1.0, location=(x, u_front + bar_len / 2, v - run / 2))
            bar = bpy.context.active_object
            bar.name = f"panel_barcode_{i:03d}"
            bar.scale = (half_thick * 2, bar_len, run)
            bpy.ops.object.transform_apply(scale=True)
            bar.data.materials.append(ink)
            built.append(bar)
        v -= run

    built.append(_add_panel_text(
        "panel_barcode_hri", sku_id, regular,
        min(BARCODE_HRI_CAP_M * unit_scale, 0.30 * usable_w), ink,
        u_start, v - 0.4 * module * 20, x))
    _fit_width(built[-1], usable_w)

    # ── LOT / EXP, labels only ───────────────────────────────────────────────
    # No values, deliberately. There is no lot or expiry data anywhere in this
    # project, and a real carton does not carry one either: it is inkjetted at
    # packing time onto exactly this blank rule.
    cap = min(FIELD_CAP_M * unit_scale, 0.22 * usable_w)
    for n, (field, frac) in enumerate((("LOT", 0.0), ("EXP", 0.12))):
        t = _add_panel_text(f"panel_field_{field.lower()}", field, bold, cap, ink,
                            u_start, v_at(FIELD_TOP_FRAC + frac), x)
        _fit_width(t, 0.30 * usable_w)
        built.append(t)
        rule_len = FIELD_RULE_FRAC * usable_w
        rule_v = v_at(FIELD_TOP_FRAC + frac) - cap * 1.15
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(x, u_front + rule_len / 2, rule_v))
        rule = bpy.context.active_object
        rule.name = f"panel_rule_{field.lower()}"
        rule.scale = (half_thick * 2, rule_len, module * 0.8)
        bpy.ops.object.transform_apply(scale=True)
        rule.data.materials.append(ink)
        built.append(rule)

    # ── data block: manifest strings only ────────────────────────────────────
    # Anchored under whatever the LOT/EXP block actually came out as, not at a
    # fixed v. The fields are sized in absolute millimetres, so on a short panel
    # they occupy a larger share of it and a constant would collide.
    from mathutils import Vector
    dg = bpy.context.evaluated_depsgraph_get()
    lowest = min((o.matrix_world @ Vector(cnr)).z
                 for o in built for cnr in o.evaluated_get(dg).bound_box)
    block_top = min(v_at(DATA_BLOCK_TOP_FRAC),
                    lowest - DATA_BLOCK_GAP_FRAC * panel_h)
    lines = [str(carton.get("material") or ""),
             f"{carton['width_mm']:.0f}x{carton['height_mm']:.0f}"
             f"x{carton['depth_mm']:.0f}mm",
             str(manifest.get("packaging_geometry") or "")]
    features = carton.get("features") or []
    if features:
        lines.append(" / ".join(features))
    lines = [ln for ln in lines if ln]
    if lines:
        cap = min(DATA_BLOCK_CAP_M * unit_scale, 0.14 * usable_w)
        t = _add_panel_text("panel_data_block", "\n".join(lines), regular, cap,
                            ink, u_start, block_top, x)
        _fit_width(t, usable_w)
        # And shrink to the panel's bottom edge if it still runs off. The block
        # is anchored under the LOT/EXP fields and sized in absolute millimetres,
        # so on the catalogue's smallest panel — a 25x35mm T3 — three lines reach
        # past the bottom of the carton. Found by the 391-SKU sweep, not by the
        # curated templates: exactly one SKU in 391.
        _fit_above(t, (top_z - panel_h) + PANEL_BOTTOM_MARGIN_FRAC * panel_h)
        built.append(t)

    for obj in built:
        obj.parent = box
        obj.matrix_parent_inverse = box.matrix_world.inverted()
    return built


def build_box(dims_m, palette: dict, label_content: dict = None,
              manifest: dict = None):
    """The printed carton — i.e. the SECONDARY packaging, which is what a
    packshot shows — sized in metres, with an accent stripe band welded to the
    bottom of the front face (Row-6 rule, see 06_docs/DESIGN_RATIONALE.md §2) and a
    square brand badge in its top-right corner.

    Not to be confused with the primary package (the blister, bottle or syringe
    inside): that is a smaller object on different axes, and passing its
    dimensions here produces an undersized, sometimes misoriented box.

    SURFACE COLOUR MANDATE (reference_analysis.md §5): the body is WHITE for
    every SKU, and brand colour appears in exactly two places, never more — the
    bottom stripe in palette.ACCENT and the top-right badge in palette.PRIMARY.
    A body tinted with primary is a mismatch, not a brand cue.
    """
    w, h, d = dims_m
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h / 2))
    box = bpy.context.active_object
    box.name = "carton"
    # size=1.0 is a UNIT cube spanning -0.5..0.5, so its edge length is 1 and the
    # scale factor IS the finished edge length in metres. Scaling by the HALF
    # extents (w/2, d/2, h/2) — which is what Blender's default size=2.0 cube
    # would want — is the trap that built every carton at half its nominal
    # millimetres. Scene units are real metres.
    box.scale = (w, d, h)
    bpy.ops.object.transform_apply(scale=True)

    body_mat = make_material("carton_body", "#FFFFFF", roughness=MATTE_ROUGHNESS)
    box.data.materials.append(body_mat)

    # Measure the mesh that was actually built instead of assuming it spans
    # (w, h, d). It does not: primitive_cube_add(size=1.0) is a UNIT cube, so
    # scaling it by (w/2, d/2, h/2) leaves edge lengths of w/2, d/2, h/2 — the
    # carton mesh is half its nominal millimetres. Camera framing is calibrated
    # against that (see SPHERE_FILL), so the size is left alone here, but
    # anything placed ON the carton has to come off these measured extents.
    # Deriving the stripe from (w, h, d) instead is what detached it: it was
    # pinned to y = -d/2 while the real front face is at -d/4, leaving it
    # floating a quarter-depth clear of the box and swinging visibly wide of the
    # silhouette once the carton was rotated for the packshot.
    xs = [c[0] for c in box.bound_box]
    ys = [c[1] for c in box.bound_box]
    zs = [c[2] for c in box.bound_box]
    face_w, face_h = max(xs) - min(xs), max(zs) - min(zs)
    front_y, bottom_z = min(ys), min(zs)
    right_x, top_z = max(xs), max(zs)
    depth = max(ys) - min(ys)
    unit_scale = face_h / h if h else 1.0   # scene units per real metre
    # Thin slab straddling the face plane, so printed elements read as ink rather
    # than as an applied tile and cannot z-fight with the surface they sit on.
    # Shared by the stripe and the badge, hence hoisted out of either branch.
    half_thick = depth * 0.002

    stripe_top_z = None
    accent_hex = palette.get("accent")
    if accent_hex:
        # Target 4mm, held inside the measured 3-6% band.
        stripe_m = min(max(STRIPE_TARGET_M, h * STRIPE_MIN_FRAC), h * STRIPE_MAX_FRAC)
        stripe_h = stripe_m * unit_scale

        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0, front_y, bottom_z + stripe_h / 2),
        )
        stripe = bpy.context.active_object
        stripe.name = "accent_stripe"
        stripe_top_z = bottom_z + stripe_h
        stripe.scale = (face_w * 0.999, half_thick * 2, stripe_h)
        bpy.ops.object.transform_apply(scale=True)
        stripe_mat = make_material("accent_stripe_mat", accent_hex,
                                   roughness=MATTE_ROUGHNESS)
        stripe.data.materials.append(stripe_mat)

        # Parent BEFORE rotating, and pin matrix_parent_inverse explicitly. Both
        # meshes currently bake to identity object transforms (transform_apply
        # defaults to location=True), so the carton's rotation is about the world
        # Z axis through its own centre and the stripe rides along correctly even
        # without this. That is a coincidence of the current build order, not a
        # guarantee: give a child a non-identity parent matrix and an identity
        # matrix_parent_inverse and the parent's transform is applied twice.
        stripe.parent = box
        stripe.matrix_parent_inverse = box.matrix_world.inverted()

    # The badge: brand colour's second and only other permitted appearance.
    # Filled with palette.PRIMARY — the lighter tone — while the stripe above
    # takes the darker palette.accent. That is not a guess: sampling the badge in
    # all nine curated references matches primary every time (T1's #DDA7A5 reads
    # (207,157,155), T3's #E2583E reads (214,89,65)), and reference_analysis.md
    # §5 does not say which of the two it is.
    badge_left_x = None
    primary_hex = palette.get("primary")
    if primary_hex:
        # Sized off the SHORTER front-face edge. Measured against the references
        # that holds to 21-37%, where sizing from face height alone spreads
        # 12-29% and from face width 7-37% — a wide flat T3 and a tall narrow
        # T_VERT_VIAL only agree on the short edge.
        side = BADGE_SIDE_FRAC * min(face_w, face_h)
        badge_x = right_x - BADGE_MARGIN_RIGHT_FRAC * face_w - side / 2
        badge_z = top_z - BADGE_MARGIN_TOP_FRAC * face_h - side / 2
        badge_left_x = badge_x - side / 2
        # Always fits, so no clamp: side + margin is 0.30 of the shorter edge,
        # comfortably inside both face dimensions, and the badge's lower edge
        # stays far above the stripe (which never exceeds 6% of face height).

        # Local +X is the far/right end of the front face in frame: the camera
        # looks along +Y, so world +X is image-right, and rotating the carton by
        # +ROTATION_DEG about Z turns the front normal to (sin, -cos, 0) — still
        # facing the camera, angled right. Top-right on film is therefore max X,
        # max Z here.
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(badge_x, front_y, badge_z),
        )
        badge = bpy.context.active_object
        badge.name = "brand_badge"
        badge.scale = (side, half_thick * 2, side)
        bpy.ops.object.transform_apply(scale=True)
        badge_mat = make_material("brand_badge_mat", primary_hex,
                                  roughness=MATTE_ROUGHNESS)
        badge.data.materials.append(badge_mat)

        # Parented before the rotation below, same reasoning as the stripe.
        badge.parent = box
        badge.matrix_parent_inverse = box.matrix_world.inverted()

    build_label(box, label_content, face_w, face_h, right_x - face_w,
                front_y, top_z, half_thick, unit_scale, badge_left_x, stripe_top_z)

    if manifest:
        build_side_panel(box, manifest, depth, face_h, min(xs), front_y,
                         top_z, half_thick, unit_scale)

    box.rotation_euler[2] = math.radians(ROTATION_DEG)
    return box, max(w, h, d)


def build_background(hex_color: str, exposure: float):
    """A seamless, evenly-lit backdrop — not a floor that catches the key light.

    It used to be a diffuse plane lit by the key and fill. Two small lights
    cannot light 50 metres of plane evenly, so the render showed a hot spot
    behind the carton falling away to grey (measured: corner brightness 75-178
    across templates, against the flat 255 every reference holds) plus a hard
    cast shadow reaching well clear of the box. reference_analysis.md §1 asks for
    "a single, seamless white plane with no floor/wall transition visible" and §3
    for a contact shadow "minimal to nearly absent" — measured, the references
    sit at 254.9 directly beneath the carton, i.e. no shadow to speak of.

    Making the backdrop EMISSIVE decouples it from the rig: it renders at a fixed
    value everywhere, takes no cast shadow, and needs no light aimed at it, so the
    key and fill are free to do nothing but light the product. That is the
    "product floating on white" look the references are shot in.
    """
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "background"

    mat = bpy.data.materials.new(name="background_mat")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = hex_to_rgba(hex_color or "#FFFFFF")
    # Exactly full scale after the film transform, so the backdrop always renders
    # pure white whatever exposure this carton is metered at. Deriving it beats a
    # magic number: the two can never drift apart.
    emission.inputs["Strength"].default_value = 2.0 ** (-exposure)
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    plane.data.materials.append(mat)

    # A large bright surface would otherwise bounce into the carton, lifting the
    # shadows and washing the accent out of tolerance. EEVEE does not gather that
    # indirect light anyway, but Cycles does, and the same driver has to serve
    # both — so switch the backdrop out of every indirect path explicitly.
    for attr in ("visible_diffuse", "visible_glossy", "visible_transmission",
                 "visible_volume_scatter", "visible_shadow"):
        if hasattr(plane, attr):
            setattr(plane, attr, False)


LENS_MM = 85.0        # matches the documented Gemini optical calibration
SENSOR_MM = 36.0      # Blender's default sensor width
# How much of the frame the carton's BOUNDING SPHERE is asked to fill. Values
# Calibrated against the measured reference renders, whose dominant axis fills
# 76-88% of frame with the object centred at 50-52% height. This value belongs
# to the TRUE-SCALE carton: while the mesh was built at half its nominal
# millimetres the same framing needed 1.70, and the two must move together.
# (Note the "45-55%" quoted in reference_analysis.md §1 does not match a direct
# measurement of those same images.)
SPHERE_FILL = 0.8365


def setup_camera(dims_m):
    """Frame the carton from its real size rather than a fixed distance.

    Distance is solved from the bounding sphere and the lens field of view, so
    a 35mm-deep dropper carton and a 170mm-tall vial tray both fill the frame
    consistently. The previous fixed `max(size*3, 0.3)` worked only while every
    box was the same nominal 100mm; with real dimensions it cropped tall cartons
    and left flat ones tiny.
    """
    w, h, d = dims_m
    centre_z = h / 2.0

    radius = 0.5 * math.sqrt(w * w + h * h + d * d)
    half_fov = math.atan((SENSOR_MM / 2.0) / LENS_MM)
    distance = radius / math.sin(SPHERE_FILL * half_fov)

    pitch = math.radians(PITCH_DEG)
    cam_y = -distance * math.cos(pitch)
    cam_z = centre_z + distance * math.sin(pitch)

    # Aim by explicit rotation rather than a TRACK_TO constraint. A constraint
    # only resolves once the depsgraph is evaluated, which made framing depend
    # on evaluation order and left the carton riding high in the frame; a
    # camera rotated (90deg - pitch) about X looks along +Y tilted down by
    # exactly `pitch`, putting the aim point dead centre every time.
    bpy.ops.object.camera_add(
        location=(0.0, cam_y, cam_z),
        rotation=(math.radians(90.0) - pitch, 0.0, 0.0),
    )
    cam = bpy.context.active_object
    cam.name = "camera"
    cam.data.lens = LENS_MM
    cam.data.dof.aperture_fstop = 8.0  # f/8, same documented value (DOF stays off)

    bpy.context.scene.camera = cam


# ── the light rig ────────────────────────────────────────────────────────────
# One studio for the whole catalogue. Every quantity below is a multiple of the
# carton's own size, so the rig is scale-invariant: from the carton's point of
# view the key always arrives from the same direction and subtends the same
# angle, whatever the carton measures. Directions are as built, NOT as sometimes
# described in prose — the key is on the camera's RIGHT (+X) and the fill on its
# LEFT (-X); do not "correct" them the other way round.
KEY_OFFSET  = (2.0, -2.0, 3.0)    # x, y, z in multiples of target_size
FILL_OFFSET = (-2.0, -1.5, 2.0)
LIGHT_SIZE_FRAC = 2.0             # area-light edge, also in multiples

# Scene is macro-scale (objects ~0.05-0.3m, camera ~0.3-1m away). Blender's
# AREA-light Watts are calibrated for room-scale scenes; at this proximity the
# values once here (800W/300W) clipped the whole frame to white (found + fixed
# via the smoke-test render — see roadmap §9). These stay studio-strobe scale;
# they are NOT to be raised back toward room wattages.
KEY_ENERGY_W  = 25
FILL_ENERGY_W = 8

# The size these wattages were tuned at: the T1 family's largest dimension, and
# also the catalogue's modal carton — 259 of 391 SKU measure exactly this, so
# two thirds of the catalogue is lit at literally 25 W / 8 W as before.
LIGHT_REF_SIZE_M = 0.115


def light_energy(base_w: float, target_size: float) -> float:
    """Base wattage corrected so irradiance at the carton is size-independent.

    The rig's positions are multiples of target_size, so light DISTANCE scales
    linearly with the carton while a fixed wattage does not — and irradiance from
    a fixed-power source falls as 1/distance². Big cartons were therefore lit
    dimmer than small ones by exactly the factor the rig grew: measured across
    the nine curated templates the front face ran 182-255 where the references
    hold a tight 232-243, and no single exposure can close a spread like that
    because exposure moves every template together.

    Scaling power with the SQUARE of the size ratio cancels the falloff exactly.
    Over the real catalogue (target_size 0.080-0.170m) that is 0.48x-2.19x, i.e.
    key 12-55 W. Note this is a change of INTERPRETATION, not of the protected
    numbers: 25 W / 8 W is now the power *at the reference size*, and at that
    size the rig is bit-for-bit what it was.
    """
    return base_w * (target_size / LIGHT_REF_SIZE_M) ** 2


# Captured for --dump-scene, which needs to report the size the rig resolved
# against. Not read by anything that builds the scene.
_LAST_TARGET_SIZE = None


def setup_lighting(target_size: float):
    global _LAST_TARGET_SIZE
    _LAST_TARGET_SIZE = target_size
    # Size is strictly proportional, with no lower clamp. A clamp makes the light
    # relatively LARGER on a small carton, i.e. softer shadows there than on a big
    # one — a per-template style difference, which is the thing this rig exists to
    # avoid. (The clamp that used to sit here never bound in practice: the
    # smallest carton in the catalogue puts the light at 0.160, above the old
    # 0.15 floor. Removing it costs nothing today and closes the hole.)
    key = bpy.data.lights.new(name="key_light", type="AREA")
    key.energy = light_energy(KEY_ENERGY_W, target_size)
    key.size = target_size * LIGHT_SIZE_FRAC
    key_obj = bpy.data.objects.new("key_light", key)
    key_obj.location = tuple(c * target_size for c in KEY_OFFSET)
    bpy.context.collection.objects.link(key_obj)

    fill = bpy.data.lights.new(name="fill_light", type="AREA")
    fill.energy = light_energy(FILL_ENERGY_W, target_size)
    fill.size = target_size * LIGHT_SIZE_FRAC
    fill_obj = bpy.data.objects.new("fill_light", fill)
    fill_obj.location = tuple(c * target_size for c in FILL_OFFSET)
    bpy.context.collection.objects.link(fill_obj)

    # Pin the world background explicitly (rather than relying on
    # --factory-startup's default) so exposure is deterministic across
    # Blender versions/installs — a project invariant (see PROJECT_HISTORY.md
    # Determinism discussion for the Gemini engine's contrasting lack of this).
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs["Color"].default_value = (0.05, 0.05, 0.05, 1.0)
        bg.inputs["Strength"].default_value = 0.3


# Film response, pinned for the same reason the world background is: so exposure
# is deterministic across Blender versions and installs rather than inherited
# from whatever --factory-startup currently defaults to.
#
# This is a CAMERA/FILM setting, not a lighting one. setup_lighting()'s 25 W key
# and 8 W fill are a deliberate studio-strobe-scale fix (see its comment) and are
# not what needed correcting. Blender's default AgX transform rolls the
# highlights off far enough to hide that the scene is over-exposed: the white
# body still landed at a plausible 237, while the ~15%-albedo accent stripe came
# out (195,135,179) — a pale orchid — against the (99,42,72) the references
# measure. A pastel stripe satisfies "brand colour appears here" only on paper.
#
# Measured, not estimated: render the front face at an exposure low enough that
# nothing clips, read it, and scale back. That puts the face at ~6.0-6.7x full
# scale, i.e. ~2.9 stops hot, against the 0.858 linear the references hold.
# Estimating this off an AgX render instead gives ~2.0 — AgX is not linear, and
# at -2.0 the T1 face still clips at 255, dragging the badge and stripe printed
# on it out of tolerance too.
#
# light_energy() equalises irradiance across carton SIZES, which took the
# per-template requirement from ~1.2 stops down to 0.17. What survives is not a
# size effect but a SHAPE one, and it separates cleanly with no overlap:
#
#     landscape cartons (w >= h)  want -2.74 .. -2.77      -> -2.76
#     portrait  cartons (h >  w)  want -2.82 .. -2.87      -> -2.84
#
# Re-measured under CYCLES on the TRUE-SCALE carton, which is what production
# renders. The earlier figures (-2.75 / -2.88) came from EEVEE on the half-scale
# mesh, because a broken engine check reported CYCLES unavailable on every
# install and every render silently fell through. They survived the correction
# almost intact - the rig scales with the carton and the film response is a pure
# multiplier - but "almost" is not "measured", so these are the measured ones.
#
# The key is an area light roughly two face-widths from the carton. Across a WIDE
# front face its far end is materially further away than its near end, so the
# mean over the face drops; a narrow portrait face barely sees that. No single
# scalar rig size can equalise the horizontal and the vertical falloff at once
# for both shapes — it is geometry, not a defect, and correcting it in the rig
# would mean changing the rig's proportions, i.e. the look.
#
# So the LIGHTING stays bit-for-bit identical for every carton and only the
# metered exposure differs — which is what a photographer does anyway: the strobe
# pack is not touched between shots, the meter is read for each one. Two values
# keyed on carton shape, not a nine-entry table keyed on template.
FILM_VIEW_TRANSFORM = "Standard"
FILM_EXPOSURE_LANDSCAPE = -2.76
FILM_EXPOSURE_PORTRAIT = -2.84


def film_exposure(dims_m) -> float:
    """Exposure for this carton's shape. See FILM_EXPOSURE_* above."""
    w, h, _ = dims_m
    return FILM_EXPOSURE_LANDSCAPE if w >= h else FILM_EXPOSURE_PORTRAIT


def setup_film(exposure: float):
    view = bpy.context.scene.view_settings
    view.view_transform = FILM_VIEW_TRANSFORM
    view.exposure = exposure


def setup_render(out_path: str, engine: str, samples: int, res_x: int, res_y: int):
    scene = bpy.context.scene
    # Ask Blender to make the assignment rather than introspecting the enum.
    # RenderSettings.engine is a DYNAMIC enum: Blender builds its real item list
    # through an RNA callback at assignment time, and that list is NOT what
    # bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items returns.
    # That introspection yields only the static placeholder — ('BLENDER_EEVEE',)
    # on 5.1.2 — so it reported CYCLES "unavailable" on every install, including
    # ones where Cycles is enabled and renders fine, and every render quietly
    # fell through to EEVEE with `samples` never applied.
    #
    # An unavailable engine is FATAL, not substituted. Engine choice changes
    # sampling, denoising and light falloff, so a quietly swapped renderer emits
    # off-spec packshots with nothing in the logs to say so — the same reasoning
    # that makes main.py fail Stage 2 when it exits 0 having produced no PNG.
    # SystemExit specifically: Blender prints an ordinary traceback and still
    # exits 0, which blender_renderer.py would read as a successful render.
    try:
        scene.render.engine = engine
    except (TypeError, ValueError) as exc:
        raise SystemExit(
            f"[render_driver] render engine '{engine}' is not available in this "
            f"Blender ({bpy.app.version_string}); refusing to substitute a "
            f"different one. Blender reports: {exc}. Set blender.engine_type in "
            f"config.yaml to an identifier from that list.")

    print(f"[render_driver] engine {scene.render.engine} "
          f"({samples} samples, {res_x}x{res_y})")
    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = out_path


def _base_color(obj):
    """Linear RGBA of an object's first Principled BSDF, or None."""
    if not obj.data.materials:
        return None
    mat = obj.data.materials[0]
    if not mat.use_nodes:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        return None
    return list(bsdf.inputs["Base Color"].default_value)


def _roughness(obj):
    """Roughness of an object's first Principled BSDF, or None."""
    if not obj.data.materials:
        return None
    mat = obj.data.materials[0]
    if not mat.use_nodes:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None or "Roughness" not in bsdf.inputs:
        return None
    return bsdf.inputs["Roughness"].default_value


def _bounds_in_frame(obj, reference):
    """Axis-aligned bounds of obj's mesh expressed in `reference`'s local frame.

    Measured in the carton's own frame rather than in world space on purpose: a
    thin plate lying flat on a rotated box has a world-space AABB that pokes
    outside the box's world-space AABB even when it is perfectly glued on, so a
    world-space containment check reports false alarms. In the carton's frame
    "on the front face, at the bottom" is a plain interval comparison.
    """
    to_ref = reference.matrix_world.inverted() @ obj.matrix_world
    if obj.type == "FONT":
        # A text object has no vertices until the depsgraph builds glyphs for
        # it, so measure its evaluated bounding box instead. Same frame, same
        # meaning; only the source of the points differs.
        from mathutils import Vector
        dg = bpy.context.evaluated_depsgraph_get()
        pts = [to_ref @ Vector(c) for c in obj.evaluated_get(dg).bound_box]
    else:
        pts = [to_ref @ v.co for v in obj.data.vertices]
    return {
        "min": [min(p[i] for p in pts) for i in range(3)],
        "max": [max(p[i] for p in pts) for i in range(3)],
    }


# ── Where the printed faces landed in the rendered frame ─────────────────────
# OCR of a packshot needs the front face flattened first, and flattening needs
# its four corners in pixels. The renderer holds the camera and the built mesh,
# so it publishes the answer; a consumer that reconstructs it from the image is
# guessing, and two attempts to do that failed.
#
# Corners come off the built mesh's bound_box, never off (w, h, d) -- see the
# note in build_box about the nominal dimensions and the mesh extents not being
# the same thing.
def _order_quad(pts):
    """[top-left, top-right, bottom-right, bottom-left], in image pixels."""
    by_y = sorted(pts, key=lambda p: p[1])
    top = sorted(by_y[:2], key=lambda p: p[0])
    bottom = sorted(by_y[2:], key=lambda p: p[0])
    return [top[0], top[1], bottom[1], bottom[0]]


def _face_corners_px(box, axis: int, take_min: bool):
    """One axis-aligned local face of *box*, projected to image pixels.

    axis 0/1/2 = local X/Y/Z. The front face is local -Y and the visible side
    panel is local -X; +ROTATION_DEG about Z turns both toward the camera.
    """
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    cam = scene.camera
    if box is None or cam is None:
        return None
    local = [mathutils.Vector(c) for c in box.bound_box]
    values = [v[axis] for v in local]
    target = min(values) if take_min else max(values)
    face = [v for v in local if abs(v[axis] - target) < 1e-6]
    if len(face) != 4:
        return None
    out = []
    for v in face:
        ndc = world_to_camera_view(scene, cam, box.matrix_world @ v)
        # world_to_camera_view puts (0, 0) at the frame's BOTTOM-left with y up;
        # image pixels count from the TOP-left with y down.
        out.append([ndc.x * RES_X, (1.0 - ndc.y) * RES_Y])
    return _order_quad(out)


def printed_faces_px():
    """Both printed faces in image pixels, plus the resolution they refer to."""
    box = bpy.data.objects.get("carton")
    scene = bpy.context.scene
    # world_to_camera_view() derives the camera's view frame from the scene's
    # CURRENT render resolution (via Camera.view_frame()), not from RES_X/RES_Y
    # directly. On the --dump-scene path this function runs before
    # setup_render() ever executes, so the scene still holds Blender's own
    # default (1920x1080) rather than the requested resolution; projecting
    # against that mismatched aspect skews the vertical axis -- measured, a
    # corner landed at y=2162 against a reported frame height of 2048. On the
    # render path setup_render() has already set these to the same values, so
    # this is a no-op there and changes nothing about the render itself (it
    # runs after setup_render, and resolution_percentage/file settings are
    # untouched here).
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    bpy.context.view_layer.update()
    return {
        "resolution": [RES_X, RES_Y],
        "front_face_px": _face_corners_px(box, axis=1, take_min=True),
        # Nothing consumes the side panel yet. It comes from the same call, and
        # emitting it now avoids touching the driver twice.
        "side_panel_px": _face_corners_px(box, axis=0, take_min=True),
    }


def dump_scene(path: str):
    """Write the measured geometry of the built scene as JSON."""
    box = bpy.data.objects.get("carton")
    stripe = bpy.data.objects.get("accent_stripe")
    badge = bpy.data.objects.get("brand_badge")
    bpy.context.view_layer.update()

    view = bpy.context.scene.view_settings
    lighting = {"target_size": _LAST_TARGET_SIZE}
    for name in ("key_light", "fill_light"):
        obj = bpy.data.objects.get(name)
        lighting[name] = None if obj is None else {
            "energy": obj.data.energy,
            "size": obj.data.size,
            "location": list(obj.location),
        }
    out = {
        "carton": None,
        "stripe": None,
        "badge": None,
        # Present even when nothing was built, so a consumer never has to guess
        # whether an empty panel means "no panel" or "key missing". The
        # hand-authored .blend branch builds none of this.
        "side_panel": [],
        "label": [],
        "lighting": lighting,
        # Read back off the scene rather than echoing the FILM_* constants, so
        # the dump reports what Blender actually holds.
        "film": {"view_transform": view.view_transform,
                 "exposure": view.exposure},
        **printed_faces_px(),
    }
    if box is not None:
        out["carton"] = {
            "dimensions": list(box.dimensions),
            "self_bounds": _bounds_in_frame(box, box),
            "rotation_z_deg": math.degrees(box.matrix_world.to_euler().z),
            "base_color": _base_color(box),
            "roughness": _roughness(box),
        }
        for key, obj in (("stripe", stripe), ("badge", badge)):
            if obj is not None:
                out[key] = {
                    "bounds_in_carton_frame": _bounds_in_frame(obj, box),
                    "base_color": _base_color(obj),
                    "roughness": _roughness(obj),
                }
        # Every label row, with the exact string it will draw. `body` is what
        # makes the engine's headline claim checkable: a test can compare it byte
        # for byte against the manifest and prove nothing was dropped, truncated
        # or invented on the way to the glyphs.
        out["side_panel"] = [
            {
                "name": o.name,
                "kind": ("barcode" if o.name.startswith("panel_barcode_") and
                         o.type != "FONT" else
                         "rule" if o.name.startswith("panel_rule_") else "text"),
                "body": o.data.body if o.type == "FONT" else None,
                "bounds_in_carton_frame": _bounds_in_frame(o, box),
            }
            for o in sorted((x for x in bpy.data.objects
                             if x.name.startswith("panel_")),
                            key=lambda x: (-x.location.z, x.name))
        ]
        out["label"] = [
            {
                "name": t.name,
                "body": t.data.body,
                "size": t.data.size,
                "align_x": t.data.align_x,
                "font": t.data.font.name if t.data.font else None,
                "bounds_in_carton_frame": _bounds_in_frame(t, box),
            }
            # Front-panel rows only. The side panel's text is reported
            # separately, under "side_panel".
            for t in sorted((o for o in bpy.data.objects
                             if o.type == "FONT" and o.name.startswith("label_")),
                            key=lambda o: -o.location.z)
        ]
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"[render_driver] dumped scene geometry to {path}")


def main():
    clear_scene()

    palette = JOB.get("palette", {}) or {}
    template_id = JOB.get("template_id", "T1")

    # Carton dimensions are guaranteed by the manifest contract, which resolves
    # them (and records their provenance) before anything reaches Blender. There
    # is deliberately no aspect-ratio guess here any more: the fallback table
    # lives once, in src/render_manifest.py. A missing carton means the job was
    # not built through the contract, and rendering a silently wrong size is
    # worse than stopping.
    carton = JOB.get("carton")
    if not carton:
        raise SystemExit(
            "[render_driver] job has no 'carton' block — it was not produced by "
            "src/render_manifest.py. Regenerate it via Stage 1 or "
            "src.blender_renderer, which validate against "
            "schemas/render_manifest.schema.json."
        )

    # Resolved before the branch: the .blend override brings its own scene but is
    # still metered for this carton's shape, and the backdrop needs the same
    # figure to render at full scale.
    dims_m = (float(carton["width_mm"]) / 1000.0,
              float(carton["height_mm"]) / 1000.0,
              float(carton["depth_mm"]) / 1000.0)
    exposure = film_exposure(dims_m)

    # Optional Phase-2 hand-authored .blend override (loaded instead of the
    # procedural build below, if the loader finds a matching file).
    scenes_dir = Path(_arg("--scenes-dir", "")) if _arg("--scenes-dir") else None
    blend_override = (scenes_dir / f"{template_id}.blend") if scenes_dir else None
    if blend_override and blend_override.exists():
        bpy.ops.wm.open_mainfile(filepath=str(blend_override))
        # A hand-authored scene is expected to already own camera/lights/materials;
        # only the render settings are still applied below.
    else:
        print(f"[render_driver] carton {carton['width_mm']}x{carton['height_mm']}"
              f"x{carton['depth_mm']}mm (source: {carton.get('source', 'unknown')}) "
              f"exposure {exposure:+.2f}")

        box, target_size = build_box(dims_m, palette, JOB.get("label_content"), JOB)
        build_background(palette.get("background", "#FFFFFF"), exposure)
        setup_camera(dims_m)
        setup_lighting(target_size)

    # Applied to the hand-authored .blend branch as well: a scene loaded from
    # disk brings its own camera, lights and materials, but exposure is a
    # project-wide invariant, and applied BEFORE the --dump-scene return so the
    # measurement path sees exactly what the render path will.
    setup_film(exposure)

    if DUMP_SCENE:
        dump_scene(DUMP_SCENE)
        return

    setup_render(OUT_PATH, ENGINE, SAMPLES, RES_X, RES_Y)

    # Sidecar for post-render QA. Written before the render so it exists even if
    # rendering later fails, and the pixels are unaffected either way.
    view_path = Path(OUT_PATH).with_suffix(".view.json")
    view_path.write_text(json.dumps(printed_faces_px(), indent=2), encoding="utf-8")
    print(f"[render_driver] wrote {view_path}")

    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
