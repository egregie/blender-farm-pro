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
DUMP_SCENE = _arg("--dump-scene")
ENGINE     = _arg("--engine-type", "CYCLES")
SAMPLES    = int(_arg("--samples", "64"))
RES_X      = int(_arg("--res-x", "2048"))
RES_Y      = int(_arg("--res-y", "2048"))

if not JOB_PATH or not (OUT_PATH or DUMP_SCENE):
    raise SystemExit("[render_driver] --job and --out are required "
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


# The carton body is WHITE on every SKU, whatever branding.palette.primary says.
# This is the [SURFACE COLOUR MANDATE] the Gemini prompt templates already
# enforce (src/passport_generator.py) and which direct inspection of the
# reference renders confirmed (01_input_raster/reference_analysis.md §5): brand
# colour appears in exactly two places on the front face and nowhere else.
CARTON_WHITE = "#FFFFFF"

# Matte, uncoated cardstock. The references show no print sheen anywhere — not
# on the body and not on the printed accent either — so the same value is used
# for the ink; 0.5 read as semi-gloss (reference_analysis.md §4, §8).
CARTON_ROUGHNESS = 0.7

# Accent stripe: full-width band at the very bottom edge of the front face, 8%
# of face height (documented 8-12%). "Row 6" in the front-panel grid.
STRIPE_HEIGHT_FRAC = 0.08

# Brand badge: small square in the top-right corner of the front face,
# "approximately 6-8% of panel width", set in from the corner by a small margin.
BADGE_WIDTH_FRAC = 0.07
BADGE_MARGIN_FRAC = 0.03


def _decorate_front_face(name, hex_color, x_centre, z_centre, width, height,
                         y_front, depth):
    """Add one printed element welded to the carton's front face (-Y).

    Placement is passed in already resolved against the carton's MEASURED
    bounds, so an element cannot drift off the face if the box's own size ever
    changes. The slab is embedded into the carton and protrudes by a hair, which
    keeps it flush-looking at macro scale while avoiding coplanar z-fighting.
    """
    eps = depth * 0.002          # protrusion: ~0.05mm on a 24mm-deep carton
    embed = depth * 0.02
    thickness = eps + embed
    bpy.ops.mesh.primitive_cube_add(
        size=1.0,
        location=(x_centre, y_front + (embed - eps) / 2.0, z_centre),
    )
    obj = bpy.context.active_object
    obj.name = name
    # primitive_cube_add(size=1.0) spans -0.5..0.5, so `scale` IS the final span.
    obj.scale = (width, thickness, height)
    bpy.ops.object.transform_apply(scale=True)
    obj.data.materials.append(
        make_material(f"{name}_mat", hex_color, roughness=CARTON_ROUGHNESS)
    )
    return obj


def _bounds(obj):
    """World-space axis-aligned bounds of an object, as (min, max) triples."""
    from mathutils import Vector
    pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


def build_box(dims_m, palette: dict):
    """The printed carton — i.e. the SECONDARY packaging, which is what a
    packshot shows — sized in metres, WHITE-bodied, carrying the two and only
    two pieces of brand colour the art direction allows on a front face: a
    full-width accent stripe along the very bottom edge, and a small square
    brand badge in the top-right corner.

    The "Row 6" rule those two come from is defined in the front-panel grid in
    src/passport_generator.py (see the layout comment above `grid_lines`, and
    the [SURFACE COLOUR MANDATE] in the prompt templates), confirmed visually in
    01_input_raster/reference_analysis.md §5, and written up in
    docs/DESIGN_RATIONALE.md §7. Note the two elements take DIFFERENT colours:
    the stripe is palette.accent, the badge is palette.primary
    (`badge_bg_hex = primary_hex`).

    Not to be confused with the primary package (the blister, bottle or syringe
    inside): that is a smaller object on different axes, and passing its
    dimensions here produces an undersized, sometimes misoriented box.
    """
    w, h, d = dims_m
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h / 2))
    box = bpy.context.active_object
    box.name = "carton"
    box.scale = (w / 2, d / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)

    box.data.materials.append(
        make_material("carton_body", CARTON_WHITE, roughness=CARTON_ROUGHNESS)
    )

    # Decoration is positioned against the box's MEASURED bounds, not against
    # `dims_m`. The two are not the same today — the cube primitive's scaling
    # convention leaves the built box at half the requested size — and deriving
    # placement from the requested dims is what left the stripe hanging in the
    # air in front of the carton instead of printed on it.
    (bx0, by0, bz0), (bx1, by1, bz1) = _bounds(box)
    face_w, face_h, face_d = bx1 - bx0, bz1 - bz0, by1 - by0

    accent_hex = palette.get("accent")
    if accent_hex:
        stripe_h = face_h * STRIPE_HEIGHT_FRAC
        _decorate_front_face(
            "accent_stripe", accent_hex,
            x_centre=(bx0 + bx1) / 2.0,      # full width, centred
            z_centre=bz0 + stripe_h / 2.0,   # flush with the very bottom edge
            width=face_w, height=stripe_h, y_front=by0, depth=face_d,
        )

    # The badge takes the BRAND colour (palette.primary), not the accent.
    badge_hex = palette.get("primary") or accent_hex
    if badge_hex:
        badge = face_w * BADGE_WIDTH_FRAC
        margin = face_w * BADGE_MARGIN_FRAC
        _decorate_front_face(
            "brand_badge", badge_hex,
            x_centre=bx1 - margin - badge / 2.0,   # top-RIGHT corner: +X is
            z_centre=bz1 - margin - badge / 2.0,   # screen-right for this camera
            width=badge, height=badge, y_front=by0, depth=face_d,
        )

    box.rotation_euler[2] = math.radians(ROTATION_DEG)
    for child_name in ("accent_stripe", "brand_badge"):
        child = bpy.data.objects.get(child_name)
        if child is not None:
            child.parent = box
    return box, max(w, h, d)


def build_background(hex_color: str):
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "background"
    mat = make_material("background_mat", hex_color or "#FFFFFF", roughness=0.9)
    plane.data.materials.append(mat)


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


def _linear_to_hex(rgba) -> str:
    """Inverse of hex_to_rgba's transfer function, for readable dump output."""
    def enc(c):
        c = max(0.0, min(1.0, float(c)))
        s = c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055
        return int(round(s * 255))
    return "#{:02X}{:02X}{:02X}".format(*(enc(c) for c in rgba[:3]))


def _material_info(obj) -> dict:
    if not obj.data.materials:
        return {}
    mat = obj.data.materials[0]
    bsdf = mat.node_tree.nodes.get("Principled BSDF") if mat.use_nodes else None
    if bsdf is None:
        return {"name": mat.name}
    base = bsdf.inputs["Base Color"].default_value
    return {
        "name": mat.name,
        "base_color_hex": _linear_to_hex(base),
        "base_color_linear": [round(c, 6) for c in base[:3]],
        "roughness": round(float(bsdf.inputs["Roughness"].default_value), 4),
    }


def _local_aabb(child, parent) -> dict:
    """The child's axis-aligned bounds expressed in the PARENT's local frame.

    Placement has to be checked here, not in world space: the carton is rotated
    about Z for the 3/4 view, so a world-space z alone cannot distinguish "on
    the front face" from "floating beside it", and world x/y mix width and
    depth together.
    """
    from mathutils import Vector
    to_local = parent.matrix_world.inverted()
    corners = [to_local @ (child.matrix_world @ Vector(c)) for c in child.bound_box]
    lo = [min(c[i] for c in corners) for i in range(3)]
    hi = [max(c[i] for c in corners) for i in range(3)]
    return {
        "min": [round(v, 6) for v in lo],
        "max": [round(v, 6) for v in hi],
        "centre": [round((lo[i] + hi[i]) / 2, 6) for i in range(3)],
        "size": [round(hi[i] - lo[i], 6) for i in range(3)],
    }


def dump_scene(path: str, dims_m):
    """Write measured geometry as JSON instead of rendering.

    Exists so the carton's art-direction invariants (white body, bottom stripe,
    top-right badge, framing) can be asserted by the normal unittest suite:
    those are geometric facts, and reading them out of the built scene is both
    cheaper and far less brittle than pixel-inspecting a render.
    """
    import bpy_extras.object_utils as _obj_utils
    from mathutils import Vector

    # matrix_world is lazily evaluated: the carton's Z rotation and the
    # parenting of the printed elements are both set after the objects are
    # created, so without this the matrices read here are still the pre-rotation
    # ones and every world-space measurement (camera framing especially) is
    # silently wrong.
    bpy.context.view_layer.update()

    w, h, d = dims_m
    scene = bpy.context.scene
    box = bpy.data.objects["carton"]
    cam = scene.camera

    # The carton's OWN measured bounds, in its own local frame. Everything else
    # is normalised against these rather than against the requested dims: the
    # box's origin convention is a side effect of transform_apply (which zeroes
    # location, leaving the mesh centred at z = h/2 in local space), so assuming
    # an origin here would silently mis-score every placement.
    box_aabb = _local_aabb(box, box)
    bx0, by0, bz0 = box_aabb["min"]
    bx1, by1, bz1 = box_aabb["max"]
    bw, bd, bh = box_aabb["size"]

    out = {
        "template_id": JOB.get("template_id"),
        "carton": {
            "dims_m": {"width": w, "height": h, "depth": d},
            "measured_local_aabb": box_aabb,
            "measured_matches_requested": [
                round(bw - w, 9) == 0, round(bh - h, 9) == 0, round(bd - d, 9) == 0,
            ],
            "seated_on_floor": round(min(
                (box.matrix_world @ Vector(c)).z for c in box.bound_box), 6),
            "world_location": [round(v, 6) for v in box.location],
            "rotation_z_deg": round(math.degrees(box.rotation_euler[2]), 4),
            "material": _material_info(box),
        },
    }

    # Placement of every decorated element, normalised against the carton's
    # measured front face so assertions read in the same units the art direction
    # is written in: x = 0 at face centre and +/-0.5 at the left/right edges,
    # y = 0 at the bottom edge and 1.0 at the top.
    for name in ("accent_stripe", "brand_badge"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            out[name] = None
            continue
        aabb = _local_aabb(obj, box)
        cx, cy, cz = aabb["centre"]
        out[name] = {
            "local_aabb": aabb,
            "face_x_fraction": round((cx - (bx0 + bx1) / 2) / bw, 6),  # 0 = centred
            "face_y_fraction": round((cz - bz0) / bh, 6),              # 0 = bottom edge
            "bottom_y_fraction": round((aabb["min"][2] - bz0) / bh, 6),
            "height_fraction": round(aabb["size"][2] / bh, 6),
            "width_fraction": round(aabb["size"][0] / bw, 6),
            # Front face is -Y. A printed element must STRADDLE that plane:
            # protruding by a hair (so it is visible and does not z-fight) while
            # still embedded in the carton (so it cannot float away from it).
            "protrusion_m": round(by0 - aabb["min"][1], 6),
            "embed_m": round(aabb["max"][1] - by0, 6),
            "straddles_front_face": aabb["min"][1] <= by0 <= aabb["max"][1],
            "material": _material_info(obj),
        }

    if cam is not None:
        pts = [_obj_utils.world_to_camera_view(scene, cam, box.matrix_world @ Vector(c))
               for c in box.bound_box]
        xs, ys = [p.x for p in pts], [p.y for p in pts]
        out["camera"] = {
            "location": [round(v, 6) for v in cam.location],
            "lens_mm": round(cam.data.lens, 4),
            "rotation_euler_deg": [round(math.degrees(a), 4) for a in cam.rotation_euler],
        }
        out["framing"] = {
            "fill_x": round(max(xs) - min(xs), 6),
            "fill_y": round(max(ys) - min(ys), 6),
            "centre_x": round((max(xs) + min(xs)) / 2, 6),
            "centre_y": round((max(ys) + min(ys)) / 2, 6),
        }

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"[render_driver] dumped scene measurements to {path}")


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

    # Optional Phase-2 hand-authored .blend override (loaded instead of the
    # procedural build below, if the loader finds a matching file).
    # Resolved before the branch so --dump-scene can report against these
    # whichever way the scene was built.
    dims_m = (float(carton["width_mm"]) / 1000.0,
              float(carton["height_mm"]) / 1000.0,
              float(carton["depth_mm"]) / 1000.0)

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
        build_background(palette.get("background", "#FFFFFF"))
        setup_camera(dims_m)
        setup_lighting(target_size)

    # Applied before the dump as well: framing is measured with
    # world_to_camera_view, which normalises against the render's aspect ratio,
    # so measuring before the resolution is set would score the carton against
    # Blender's factory 1920x1080 frame instead of the square one it renders to.
    setup_render(OUT_PATH or "", ENGINE, SAMPLES, RES_X, RES_Y)

    if DUMP_SCENE:
        dump_scene(DUMP_SCENE, dims_m)
        return

    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
