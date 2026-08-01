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
framing — see docs/DESIGN_RATIONALE.md.
"""
import bpy
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
# JSON, and skip rendering. Exists because carton scale, seating and stripe
# placement can only be verified inside Blender, and a packshot is far too slow
# and too indirect to assert on in a unit test — see tests/test_blender_carton.py.
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
# band; reference_analysis.md §5 measures it at 8-12% of the front-face height
# across the curated set. The two agree for a mid-size carton and diverge at the
# extremes, so the millimetre figure is the target and the percentages bound it.
STRIPE_TARGET_M = 0.004
STRIPE_MIN_FRAC = 0.08
STRIPE_MAX_FRAC = 0.12

# The second — and only other — place brand colour is allowed on a carton: a
# small square badge in the TOP-RIGHT corner of the front face, "approximately
# 6-8% of panel width" (front-panel grid, src/passport_generator.py), set in
# from the corner by a minimal margin and subordinate to the typography.
BADGE_WIDTH_FRAC = 0.07
BADGE_MARGIN_FRAC = 0.03

# Matte, uncoated cardstock: reference_analysis.md §4 reads roughness as ~0.6-0.8
# and §8 asks for 0.7-0.8 specifically. It applies to the printed accent too —
# the references show no print sheen on the stripe or badge either, so a glossier
# value for the ink would be just as much a mismatch as it is on the body.
CARTON_ROUGHNESS = 0.7


def build_box(dims_m, palette: dict):
    """The printed carton — i.e. the SECONDARY packaging, which is what a
    packshot shows — sized in metres, WHITE-bodied, carrying the two and only
    two pieces of brand colour the art direction allows on a front face: an
    accent stripe welded to the bottom edge, and a square badge in the top-right
    corner.

    Not to be confused with the primary package (the blister, bottle or syringe
    inside): that is a smaller object on different axes, and passing its
    dimensions here produces an undersized, sometimes misoriented box.

    SURFACE COLOUR MANDATE (reference_analysis.md §5): the body is WHITE for
    every SKU. palette.primary is deliberately NOT painted onto it — in the
    references the brand colour appears only in this stripe and in a top-right
    badge, so a body tinted with primary is a mismatch, not a brand cue.

    The "Row 6" rule both elements come from is defined in the front-panel grid
    in src/passport_generator.py ("very bottom edge of the FRONT FACE") and
    written up in docs/DESIGN_RATIONALE.md §7. Earlier revisions of this
    docstring cited §2 of that document, which is "Why Markdown, not JSON" and
    justifies nothing here.
    """
    w, h, d = dims_m
    # size=1.0 is a UNIT cube: it spans -0.5..0.5, so its edge length is 1 and
    # the scale factor IS the finished edge length in metres. Scaling it by
    # (w/2, d/2, h/2) — the half-extents, which is what you would want from
    # Blender's *default* size=2.0 cube — is the trap that built every carton at
    # half its nominal millimetres. Scene units are real metres here.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h / 2))
    box = bpy.context.active_object
    box.name = "carton"
    box.scale = (w, d, h)
    # Centre sits at z = h/2 with a half-height of h/2, so the carton rests ON
    # the backdrop. A carton that floats casts the detached contact shadow the
    # reference renders do not have.
    bpy.ops.object.transform_apply(scale=True)

    body_mat = make_material("carton_body", "#FFFFFF", roughness=CARTON_ROUGHNESS)
    box.data.materials.append(body_mat)

    # Measure the mesh that was actually built instead of assuming it spans
    # (w, h, d). It does now — the scale above is the fix for a carton that used
    # to be built at half its nominal millimetres — but anything placed ON the
    # carton still comes off these measured extents rather than off (w, h, d),
    # so a future change to how the mesh is sized cannot silently detach the
    # stripe again. That is exactly how it detached before: it was pinned to
    # y = -d/2 while the real front face of the half-size mesh was at -d/4,
    # leaving it floating a quarter-depth clear of the box and swinging visibly
    # wide of the silhouette once the carton was rotated for the packshot.
    # unit_scale is consequently 1.0 now, and is kept as the seam that proves it.
    xs = [c[0] for c in box.bound_box]
    ys = [c[1] for c in box.bound_box]
    zs = [c[2] for c in box.bound_box]
    face_w, face_h = max(xs) - min(xs), max(zs) - min(zs)
    front_y, bottom_z = min(ys), min(zs)
    depth = max(ys) - min(ys)
    unit_scale = face_h / h if h else 1.0   # scene units per real metre

    accent_hex = palette.get("accent")
    if accent_hex:
        # Target 4mm, held inside the 8-12% band the references measure.
        stripe_m = min(max(STRIPE_TARGET_M, h * STRIPE_MIN_FRAC), h * STRIPE_MAX_FRAC)
        stripe_h = stripe_m * unit_scale
        # Thin slab straddling the face plane, so it reads as printed ink rather
        # than an applied tile and cannot z-fight with the surface it sits on.
        half_thick = depth * 0.002

        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0, front_y, bottom_z + stripe_h / 2),
        )
        stripe = bpy.context.active_object
        stripe.name = "accent_stripe"
        # Same unit-cube convention as the carton: scale == edge length.
        stripe.scale = (face_w * 0.999, half_thick * 2, stripe_h)
        bpy.ops.object.transform_apply(scale=True)
        stripe_mat = make_material("accent_stripe_mat", accent_hex,
                                   roughness=CARTON_ROUGHNESS)
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

    # The badge takes the BRAND colour, which is NOT the stripe's accent:
    # `badge_bg_hex = primary_hex` in the front-panel grid, and palette.accent is
    # consistently the darker, more saturated of the two. This is the one place
    # palette.primary legitimately appears on a carton — painting the body with
    # it (as this function used to) is the mismatch, not the badge.
    badge_hex = palette.get("primary") or palette.get("accent")
    if badge_hex:
        badge = face_w * BADGE_WIDTH_FRAC
        margin = face_w * BADGE_MARGIN_FRAC
        half_thick = depth * 0.002
        # +X is screen-right for this camera (it looks along +Y with +Z up), so
        # max-x/max-z is the corner the references put the badge in.
        bpy.ops.mesh.primitive_cube_add(
            size=1.0,
            location=(max(xs) - margin - badge / 2, front_y,
                      max(zs) - margin - badge / 2),
        )
        badge_obj = bpy.context.active_object
        badge_obj.name = "brand_badge"
        # Square on the face; same unit-cube convention as the carton and stripe.
        badge_obj.scale = (badge, half_thick * 2, badge)
        bpy.ops.object.transform_apply(scale=True)
        badge_obj.data.materials.append(
            make_material("brand_badge_mat", badge_hex, roughness=CARTON_ROUGHNESS)
        )
        badge_obj.parent = box
        badge_obj.matrix_parent_inverse = box.matrix_world.inverted()

    box.rotation_euler[2] = math.radians(ROTATION_DEG)
    return box, max(w, h, d)


# ── Front-face label ─────────────────────────────────────────────────────────
# Every size and position below is a FRACTION of the carton face, never an
# absolute measurement: the catalogue runs from a 45x80mm dropper carton to a
# 115x55mm landscape box, so a fixed point size overflows the narrow ones and
# vanishes on the wide ones.
LABEL_MARGIN   = 0.08   # side margin, fraction of face width
BRAND_TOP      = 0.88   # top of the brand block, fraction of face height
BRAND_FLOOR    = 0.42   # the block may not grow below this
BADGE_CLEAR    = 0.02   # gap left between the brand and the badge, fraction of width
BRAND_SIZE     = 0.15   # brand cap height, fraction of face height
BRAND_LINE_GAP = 1.30   # line pitch multiplier when the brand wraps to two lines
BOTTOM_ROW     = 0.20   # baseline of the dosage/count row, fraction of face height
DOSAGE_SIZE    = 0.12   # dosage is the emphasised element (see schema description)
COUNT_SIZE     = 0.085
BOTTOM_GAP     = 0.12   # minimum gap between dosage and count, fraction of face width
INK_HEX        = "#111111"
# The type has to share the face with the two brand-colour elements build_box()
# puts there, so it is bounded away from both rather than trusting numbers that
# live in that function: BOTTOM_ROW clears the accent stripe welded to the bottom
# edge (8-12% of face height), and the brand block is held clear of the top-right
# badge horizontally. The badge is MEASURED off the built object below, because
# its side is a fraction of face WIDTH while the brand is sized off face HEIGHT —
# on a landscape carton the badge reaches down past 0.79 of the face and would
# otherwise sit on top of the brand line.


def _text_width(probe, s: str) -> float:
    """Width of `s` at size 1.0. Width scales linearly with `size`, so one
    measurement is enough to solve for the size that fits a given box."""
    probe.data.body = s
    bpy.context.view_layer.update()
    return probe.dimensions.x


def _wrap_two_lines(probe, text: str) -> list:
    """Split on the space that minimises the wider of the two resulting lines."""
    words = text.split()
    if len(words) < 2:
        return [text]
    best, best_at = None, 1
    for i in range(1, len(words)):
        widest = max(_text_width(probe, " ".join(words[:i])),
                     _text_width(probe, " ".join(words[i:])))
        if best is None or widest < best:
            best, best_at = widest, i
    return [" ".join(words[:best_at]), " ".join(words[best_at:])]


def build_label(box, label: dict, ink_mat):
    """Print the manifest's label_content on the carton's front face (-Y).

    The strings are reproduced verbatim: not hallucinating the text is the whole
    point of rendering geometrically instead of prompting an image model, so a
    string that does not fit is scaled down, never truncated.

    Face geometry is MEASURED from the box's own bounding box rather than taken
    from the manifest's nominal millimetres. Those two do not currently agree —
    build_box() scales a size=1.0 cube (whose verts sit at +-0.5) by w/2, so the
    rendered carton is half its nominal size and floats at h/4..3h/4 instead of
    resting on 0..h. Measuring means the label lands on the face that actually
    exists, and keeps landing there if that scaling is ever corrected.
    """
    corners = [tuple(c) for c in box.bound_box]      # local space, 8 corners
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    zs = [c[2] for c in corners]
    x_min, x_max = min(xs), max(xs)
    z_min, z_max = min(zs), max(zs)
    w = x_max - x_min                                # face width
    h = z_max - z_min                                # face height

    face_y = min(ys) - max(w, h) * 0.002             # just proud of face and stripe
    avail = w * (1.0 - 2.0 * LABEL_MARGIN)
    left = x_min + w * LABEL_MARGIN
    right = x_max - w * LABEL_MARGIN

    # The brand shares the top of the face with the badge, so measure the badge
    # that was actually built and stop short of it.
    brand_avail = avail
    badge = bpy.data.objects.get("brand_badge")
    if badge is not None:
        inv = box.matrix_world.inverted()
        badge_x0 = min((inv @ c).x for c in _world_corners(badge))
        brand_avail = min(brand_avail, (badge_x0 - w * BADGE_CLEAR) - left)
        brand_avail = max(brand_avail, avail * 0.25)   # never starve the brand

    # One throwaway object does all the measuring and is deleted at the end.
    bpy.ops.object.text_add(location=(0, 0, 0))
    probe = bpy.context.active_object
    probe.data.size = 1.0

    made = []

    def place(name, body, size, x, z, align_x):
        bpy.ops.object.text_add(location=(0, 0, 0))
        obj = bpy.context.active_object
        obj.name = name
        obj.data.body = body
        obj.data.size = size
        obj.data.align_x = align_x
        obj.data.align_y = "BOTTOM"
        obj.location = (x, face_y, z)
        obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        obj.data.materials.append(ink_mat)
        made.append(obj)
        return obj

    # ── brand: one line if it fits at the target size, otherwise two, otherwise
    #    the same block shrunk until it fits.
    brand = (label.get("brand_name_display") or "").strip()
    if brand:
        target = h * BRAND_SIZE
        v_room = h * (BRAND_TOP - BRAND_FLOOR)
        lines = [brand]
        size = min(target, v_room, brand_avail / max(_text_width(probe, brand), 1e-9))
        # Wrapping is worth it only when two lines can be set LARGER than one,
        # and a two-line block has to fit the same vertical room.
        candidate = _wrap_two_lines(probe, brand)
        if len(candidate) == 2:
            widest = max(_text_width(probe, ln) for ln in candidate)
            two_size = min(target,
                           v_room / (1.0 + BRAND_LINE_GAP),
                           brand_avail / max(widest, 1e-9))
            if two_size > size:
                lines, size = candidate, two_size
        z = z_min + h * BRAND_TOP - size
        for ln in lines:
            place("label_brand", ln, size, left, z, "LEFT")
            z -= size * BRAND_LINE_GAP

    # ── bottom row: dosage left (emphasised), unit count right.
    #    Both are set at their natural size, then shrunk TOGETHER if the pair plus
    #    a mandatory gap would not fit. Shrinking together keeps their relative
    #    emphasis; capping each to a fixed share of the width instead let them end
    #    up a fraction of a millimetre apart on the narrow cartons, where "250mg"
    #    and "1 Pills" read as one word.
    row_z = z_min + h * BOTTOM_ROW
    dosage = (label.get("dosage_display") or "").strip()
    count = (label.get("unit_count_display") or "").strip()

    d_size = min(h * DOSAGE_SIZE, avail / max(_text_width(probe, dosage), 1e-9)) if dosage else 0.0
    c_size = min(h * COUNT_SIZE, avail / max(_text_width(probe, count), 1e-9)) if count else 0.0
    if dosage and count:
        needed = (_text_width(probe, dosage) * d_size
                  + _text_width(probe, count) * c_size
                  + avail * BOTTOM_GAP)
        if needed > avail:
            shrink = avail / needed
            d_size *= shrink
            c_size *= shrink

    if dosage:
        place("label_dosage", dosage, d_size, left, row_z, "LEFT")
    if count:
        place("label_count", count, c_size, right, row_z, "RIGHT")

    bpy.data.objects.remove(probe, do_unlink=True)

    # Parent AFTER build_box() has applied the carton's Z rotation, so the text
    # is authored in unrotated face coordinates and then turns with the box —
    # the same trick the accent stripe uses.
    for obj in made:
        obj.parent = box
    return made


# The backdrop EMITS rather than merely being lit. Two small area lights fall
# off with the square of distance, so a purely diffuse plane renders as a grey
# vertical gradient — measured at 190..252 across the frame against a flat 255
# in every reference render, which is a visible horizon where §1 calls for "a
# single, seamless white plane". Emission decouples the backdrop's brightness
# from the lights entirely, so it clips to white at every distance.
#
# 16 is where the gradient disappears completely (corner spread 61.5 -> 0.0,
# matching the references' 0.1). It is deliberately NOT a substitute for the key
# and fill: those still do all the modelling on the carton, and their 25W/8W are
# untouched. The plane doubles as the bounce card a real high-key set would use,
# which also corrected the front-vs-side face contrast from -3 (side lighter
# than front — backwards) to +9.
BACKDROP_EMISSION = 16.0


def build_background(hex_color: str):
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "background"
    mat = make_material("background_mat", hex_color or "#FFFFFF", roughness=0.9)
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None and "Emission Strength" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = hex_to_rgba(hex_color or "#FFFFFF")
        bsdf.inputs["Emission Strength"].default_value = BACKDROP_EMISSION
    plane.data.materials.append(mat)


LENS_MM = 85.0        # matches the documented Gemini optical calibration
SENSOR_MM = 36.0      # Blender's default sensor width
# How much of the half-FOV the carton's BOUNDING SPHERE is asked to subtend.
# Calibrated against the measured reference renders, whose dominant axis fills
# 76-88% of frame with the object centred at 50-52% height. (Note the "45-55%"
# quoted in reference_analysis.md §1 does not match a direct measurement of
# those same images.)
#
# This was 1.70 for as long as build_box() made half-size cartons: `radius`
# below is derived from the manifest's true millimetres, so the camera was
# already framing a full-size box while the box in the scene was half of one,
# and the constant had been tuned upward to absorb exactly that factor of 2.
# The old comment defended values above 1.0 as "expected and safe"; they were
# neither — they were the bug wearing a justification.
#
# 0.8365 = asin(sin(1.70 * half_fov) / 2) / half_fov, i.e. the value that puts
# a TRUE-scale carton at the same distance/size ratio the tuned constant had
# been producing. Framing is therefore unchanged: T1 measures 0.7561 of frame
# width before and after (tests/test_blender_carton.py pins it).
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


def setup_lighting(target_size: float):
    # Scene is macro-scale (objects ~0.05-0.3m, camera ~0.3-1m away). Blender's
    # AREA-light Watts are calibrated for room-scale scenes; at this proximity
    # the values previously here (800W/300W) clipped the whole frame to white
    # (found + fixed via the smoke-test render — see roadmap §9). Use small,
    # fixed studio-strobe-scale wattages instead of scaling energy with size.
    key = bpy.data.lights.new(name="key_light", type="AREA")
    key.energy = 25
    key.size = max(target_size * 2, 0.15)
    key_obj = bpy.data.objects.new("key_light", key)
    key_obj.location = (target_size * 2, -target_size * 2, target_size * 3)
    bpy.context.collection.objects.link(key_obj)

    fill = bpy.data.lights.new(name="fill_light", type="AREA")
    fill.energy = 8
    fill.size = max(target_size * 2, 0.15)
    fill_obj = bpy.data.objects.new("fill_light", fill)
    fill_obj.location = (-target_size * 2, -target_size * 1.5, target_size * 2)
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


def setup_render(out_path: str, engine: str, samples: int, res_x: int, res_y: int):
    scene = bpy.context.scene

    # Ask Blender to make the assignment rather than introspecting the enum.
    # RenderSettings.engine is a DYNAMIC enum: Blender builds its real item list
    # through an RNA callback at assignment time, and that list is NOT what
    # bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items returns.
    # That introspection yields only the static placeholder — ('BLENDER_EEVEE',)
    # on 5.1.2 — so it reported CYCLES "unavailable" on every install, including
    # ones where Cycles is enabled and renders fine. Every render therefore fell
    # through to EEVEE with `samples` silently never applied. The assignment
    # below consults the true list, and its error enumerates it for us.
    #
    # An unavailable engine is FATAL, not substituted. Engine choice changes
    # sampling, denoising and light falloff, so a quietly swapped renderer emits
    # off-spec packshots with nothing in the logs to say so — the same reasoning
    # that makes main.py force Stage 2 to fail when it exits 0 having produced
    # no PNG.
    #
    # SystemExit specifically: Blender prints an ordinary exception traceback and
    # still exits 0, which blender_renderer.py would read as a successful render.
    try:
        scene.render.engine = engine
    except (TypeError, ValueError) as exc:
        raise SystemExit(
            f"[render_driver] render engine '{engine}' is not available in this "
            f"Blender ({bpy.app.version_string}); refusing to substitute a "
            f"different one. Blender reports: {exc}. Set blender.engine_type in "
            f"config.yaml to an identifier from that list."
        )

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
    """Principled BSDF roughness of an object's first material, or None.

    Surfaced because "matte cardboard, not semi-gloss" is a checkable constraint
    (reference_analysis.md §4) and roughness is the only thing expressing it.
    """
    if not obj.data.materials:
        return None
    mat = obj.data.materials[0]
    if not mat.use_nodes:
        return None
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None or "Roughness" not in bsdf.inputs:
        return None
    return float(bsdf.inputs["Roughness"].default_value)


def _bounds_in_frame(obj, reference):
    """Axis-aligned bounds of obj's mesh expressed in `reference`'s local frame.

    Measured in the carton's own frame rather than in world space on purpose: a
    thin plate lying flat on a rotated box has a world-space AABB that pokes
    outside the box's world-space AABB even when it is perfectly glued on, so a
    world-space containment check reports false alarms. In the carton's frame
    "on the front face, at the bottom" is a plain interval comparison.
    """
    to_ref = reference.matrix_world.inverted() @ obj.matrix_world
    pts = [to_ref @ v.co for v in obj.data.vertices]
    return {
        "min": [min(p[i] for p in pts) for i in range(3)],
        "max": [max(p[i] for p in pts) for i in range(3)],
    }


def _world_corners(obj):
    """The 8 bound-box corners of `obj` in WORLD space.

    Seating and framing are the two questions that are genuinely about world
    space — where the carton sits relative to the backdrop at z=0, and where it
    lands in the camera's view — so they cannot use _bounds_in_frame above.
    """
    from mathutils import Vector
    return [obj.matrix_world @ Vector(c) for c in obj.bound_box]


def dump_scene(path: str, dims_m):
    """Write the measured geometry of the built scene as JSON.

    Everything is MEASURED off the evaluated scene, never recomputed from the
    job: a check that re-derived the expected numbers the way the driver does
    would pass no matter how wrong the scene was.
    """
    from bpy_extras.object_utils import world_to_camera_view

    scene = bpy.context.scene
    w, h, d = dims_m
    box = bpy.data.objects.get("carton")
    stripe = bpy.data.objects.get("accent_stripe")
    badge = bpy.data.objects.get("brand_badge")
    cam = scene.camera
    bpy.context.view_layer.update()

    out = {
        "carton": None,
        "stripe": None,
        "badge": None,
        # What the manifest ASKED for, so a test can compare built against
        # requested rather than against another derivation of the same input.
        "requested_mm": {"width": w * 1000.0, "height": h * 1000.0,
                         "depth": d * 1000.0},
        "sphere_fill": SPHERE_FILL,
        "template_id": JOB.get("template_id"),
        "pitch_deg": PITCH_DEG,
    }

    if box is not None:
        corners = _world_corners(box)
        world_min_z = min(c[2] for c in corners)
        out["carton"] = {
            "dimensions": list(box.dimensions),
            "self_bounds": _bounds_in_frame(box, box),
            "rotation_z_deg": math.degrees(box.matrix_world.to_euler().z),
            "base_color": _base_color(box),
            "roughness": _roughness(box),
            # Distance from the backdrop (z=0) to the lowest corner: 0 means the
            # carton rests on the plane, >0 means it floats and will throw the
            # detached contact shadow the references do not have.
            "ground_gap": world_min_z,
        }
        if stripe is not None:
            out["stripe"] = {
                "bounds_in_carton_frame": _bounds_in_frame(stripe, box),
                "base_color": _base_color(stripe),
                "roughness": _roughness(stripe),
            }
        if badge is not None:
            out["badge"] = {
                "bounds_in_carton_frame": _bounds_in_frame(badge, box),
                "base_color": _base_color(badge),
                "roughness": _roughness(badge),
            }

        if cam is not None:
            # Project the carton's corners through the real camera: 0..1 spans
            # the frame, so this is the silhouette's share of it. Lets SPHERE_FILL
            # be calibrated without measuring pixels in a finished render.
            ndc = [world_to_camera_view(scene, cam, c) for c in corners]
            xs = [p.x for p in ndc]
            ys = [p.y for p in ndc]
            out["framing"] = {
                "width_frac": max(xs) - min(xs),
                "height_frac": max(ys) - min(ys),
                "max_frac": max(max(xs) - min(xs), max(ys) - min(ys)),
                "centre_y_frac": (max(ys) + min(ys)) / 2.0,
            }

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

    # label_content is `required` in the manifest schema, so its absence means the
    # job bypassed the contract. Rendering an unlabelled carton is a silent
    # content failure — the strings are the reason this engine exists — so stop.
    label = JOB.get("label_content")
    if not label:
        raise SystemExit(
            "[render_driver] job has no 'label_content' block — it was not "
            "produced by src/render_manifest.py, where the schema marks it "
            "required. Regenerate it via Stage 1 or src.blender_renderer."
        )

    # Millimetres -> metres. Hoisted above the .blend branch because
    # --dump-scene reports against these whichever way the scene was built.
    dims_m = (float(carton["width_mm"]) / 1000.0,
              float(carton["height_mm"]) / 1000.0,
              float(carton["depth_mm"]) / 1000.0)

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
              f"x{carton['depth_mm']}mm (source: {carton.get('source', 'unknown')})")

        box, target_size = build_box(dims_m, palette)
        ink = make_material("label_ink", INK_HEX, roughness=0.7)
        placed = build_label(box, label, ink)
        print(f"[render_driver] label: {len(placed)} text object(s)")
        build_background(palette.get("background", "#FFFFFF"))
        setup_camera(dims_m)
        setup_lighting(target_size)

    # OUT_PATH is optional under --dump-scene, but setup_render still runs first
    # so the dumped framing reflects the real output resolution and aspect.
    setup_render(OUT_PATH or "", ENGINE, SAMPLES, RES_X, RES_Y)

    if DUMP_SCENE:
        dump_scene(DUMP_SCENE, dims_m)
        return

    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
