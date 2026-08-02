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


def build_box(dims_m, palette: dict):
    """The printed carton — i.e. the SECONDARY packaging, which is what a
    packshot shows — sized in metres, with an accent stripe band welded to the
    bottom of the front face (Row-6 rule, see docs/DESIGN_RATIONALE.md §2) and a
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
    box.scale = (w / 2, d / 2, h / 2)
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
    primary_hex = palette.get("primary")
    if primary_hex:
        # Sized off the SHORTER front-face edge. Measured against the references
        # that holds to 21-37%, where sizing from face height alone spreads
        # 12-29% and from face width 7-37% — a wide flat T3 and a tall narrow
        # T_VERT_VIAL only agree on the short edge.
        side = BADGE_SIDE_FRAC * min(face_w, face_h)
        badge_x = right_x - BADGE_MARGIN_RIGHT_FRAC * face_w - side / 2
        badge_z = top_z - BADGE_MARGIN_TOP_FRAC * face_h - side / 2
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
# above 1.0 are expected and safe: the sphere circumscribes a flat carton, so
# the box's own silhouette stays well inside the frame. Calibrated against the
# measured reference renders, whose dominant axis fills 76-88% of frame with the
# object centred at 50-52% height; 1.7 puts the four sampled templates at
# 74-79%. (Note the "45-55%" quoted in reference_analysis.md §1 does not match
# a direct measurement of those same images.)
SPHERE_FILL = 1.70


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
#     landscape cartons (w >= h)  want -2.71 .. -2.76      -> -2.75
#     portrait  cartons (h >  w)  want -2.87 .. -2.88      -> -2.88
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
FILM_EXPOSURE_LANDSCAPE = -2.75
FILM_EXPOSURE_PORTRAIT = -2.88


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
    valid_engines = {e.identifier for e in
                     bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    if engine not in valid_engines:
        print(f"[render_driver] WARNING: engine '{engine}' unavailable "
              f"({sorted(valid_engines)}); falling back to CYCLES", file=sys.stderr)
        engine = "CYCLES" if "CYCLES" in valid_engines else sorted(valid_engines)[0]
    scene.render.engine = engine
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
    pts = [to_ref @ v.co for v in obj.data.vertices]
    return {
        "min": [min(p[i] for p in pts) for i in range(3)],
        "max": [max(p[i] for p in pts) for i in range(3)],
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
        "lighting": lighting,
        # Read back off the scene rather than echoing the FILM_* constants, so
        # the dump reports what Blender actually holds.
        "film": {"view_transform": view.view_transform,
                 "exposure": view.exposure},
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

        box, target_size = build_box(dims_m, palette)
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
    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
