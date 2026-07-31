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
# Debug facility: build the scene, write measured geometry as JSON, skip the
# render. Lets the test suite and a human check real scale/seating/framing
# without waiting on Cycles. Never used by the normal render path.
DUMP_SCENE = _arg("--dump-scene")

if not JOB_PATH or not (OUT_PATH or DUMP_SCENE):
    raise SystemExit("[render_driver] --job and --out are required")

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


def build_box(dims_m, palette: dict):
    """The printed carton — i.e. the SECONDARY packaging, which is what a
    packshot shows — sized in metres, coloured from the SKU palette, with an
    accent stripe band on the front face (Row-6 rule, see
    docs/DESIGN_RATIONALE.md §2).

    Not to be confused with the primary package (the blister, bottle or syringe
    inside): that is a smaller object on different axes, and passing its
    dimensions here produces an undersized, sometimes misoriented box.
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

    body_mat = make_material("carton_body", palette.get("primary", "#FFFFFF"), roughness=0.5)
    box.data.materials.append(body_mat)

    accent_hex = palette.get("accent")
    if accent_hex:
        stripe_h = h * 0.08
        # y: the front face is at -d/2, and the band is 1mm thick, so offsetting
        # the centre by half that (0.0005) lays its back face exactly on the
        # face and leaves it standing 1mm proud — printed on the carton rather
        # than floating in front of it. This only lands on the face because the
        # carton above is built at true scale; against the old half-size box the
        # band hung d/4 (12mm on a T1) out in mid-air.
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0, -d / 2 - 0.0005, h * 0.55),
        )
        stripe = bpy.context.active_object
        stripe.name = "accent_stripe"
        # Same unit-cube convention as the carton: scale == edge length.
        stripe.scale = (w * 0.98, 0.001, stripe_h)
        bpy.ops.object.transform_apply(scale=True)
        stripe_mat = make_material("accent_stripe_mat", accent_hex, roughness=0.3)
        stripe.data.materials.append(stripe_mat)

    box.rotation_euler[2] = math.radians(ROTATION_DEG)
    if accent_hex:
        stripe.parent = box
    return box, max(w, h, d)


def build_background(hex_color: str):
    bpy.ops.mesh.primitive_plane_add(size=50, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = "background"
    mat = make_material("background_mat", hex_color or "#FFFFFF", roughness=0.9)
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


def _world_corners(obj):
    """The 8 bound-box corners of `obj` in WORLD space."""
    from mathutils import Vector
    return [obj.matrix_world @ Vector(c) for c in obj.bound_box]


def _extent(points):
    """axis-aligned {min,max,size} over a list of 3D points."""
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    return {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)]}


def dump_scene(path: str, dims_m):
    """Write measured scene geometry as JSON instead of rendering.

    Everything here is MEASURED off the evaluated scene (bound_box through
    matrix_world), never recomputed from the job — that is the whole point: it
    is the check that what Blender actually built matches the millimetres the
    manifest asked for.

    `framing` projects the carton's corners through the real camera with
    bpy_extras' world_to_camera_view, giving the silhouette's normalised extent
    (0..1 = frame edges). That is how SPHERE_FILL is calibrated without having
    to measure pixels in a finished render.
    """
    from bpy_extras.object_utils import world_to_camera_view

    scene = bpy.context.scene
    w, h, d = dims_m
    box = bpy.data.objects.get("carton")
    stripe = bpy.data.objects.get("accent_stripe")
    cam = scene.camera

    out = {
        "requested_mm": {"width": w * 1000.0, "height": h * 1000.0, "depth": d * 1000.0},
        "sphere_fill": SPHERE_FILL,
        "template_id": JOB.get("template_id"),
        "rotation_deg": ROTATION_DEG,
        "pitch_deg": PITCH_DEG,
    }

    if box is not None:
        corners = _world_corners(box)
        out["carton"] = {
            # dimensions is Blender's own local-space measure -> catches a
            # mis-scaled mesh directly, in metres.
            "dimensions": list(box.dimensions),
            "location": list(box.location),
            "world": _extent(corners),
        }
        # Seating: distance from the ground plane (z=0) to the lowest corner.
        # 0 means the carton sits on the plane; >0 means it floats.
        out["carton"]["ground_gap"] = out["carton"]["world"]["min"][2]

    if stripe is not None:
        sworld = _world_corners(stripe)
        out["stripe"] = {
            "dimensions": list(stripe.dimensions),
            "world": _extent(sworld),
        }
        if box is not None:
            inv = box.matrix_world.inverted()
            out["stripe"]["local"] = _extent([inv @ c for c in sworld])
            out["stripe"]["carton_local"] = _extent(
                [inv @ c for c in _world_corners(box)]
            )

    if cam is not None:
        out["camera"] = {
            "location": list(cam.location),
            "rotation_deg": [math.degrees(a) for a in cam.rotation_euler],
            "lens_mm": cam.data.lens,
        }
        if box is not None:
            ndc = [world_to_camera_view(scene, cam, c) for c in _world_corners(box)]
            xs = [p.x for p in ndc]
            ys = [p.y for p in ndc]
            out["framing"] = {
                "x_min": min(xs), "x_max": max(xs),
                "y_min": min(ys), "y_max": max(ys),
                "width_frac": max(xs) - min(xs),
                "height_frac": max(ys) - min(ys),
                "centre_y_frac": (max(ys) + min(ys)) / 2.0,
            }
            out["framing"]["max_frac"] = max(
                out["framing"]["width_frac"], out["framing"]["height_frac"]
            )

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"[render_driver] dumped scene measurements to {path}")


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
        build_background(palette.get("background", "#FFFFFF"))
        setup_camera(dims_m)
        setup_lighting(target_size)

    setup_render(OUT_PATH or "", ENGINE, SAMPLES, RES_X, RES_Y)

    # Measurement mode short-circuits the render. Placed AFTER setup_render so
    # the dumped framing reflects the real output resolution/aspect.
    if DUMP_SCENE:
        dump_scene(DUMP_SCENE, dims_m)
        return

    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
