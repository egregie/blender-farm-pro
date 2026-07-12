"""PharmaGen PRO — Blender scene driver (EXPERIMENTAL, runs INSIDE Blender).

Invoked headless by src/blender_renderer.py:
    blender --background --factory-startup --python render_driver.py -- \
        --job <job.json> --out <out.png> --engine-type CYCLES --samples 64 \
        --res-x 2048 --res-y 2048

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

if not JOB_PATH or not OUT_PATH:
    raise SystemExit("[render_driver] --job and --out are required")

with open(JOB_PATH, "r", encoding="utf-8") as f:
    JOB = json.load(f)

# ── Template -> box proportions (W:H:D) ───────────────────────────────────────
# Mirrors the documented Gemini template proportions (docs/ARCHITECTURE.md
# "Template System" table + the P22 vertical family), so a Blender render and
# a Gemini render of the same SKU target the same silhouette.
TEMPLATE_RATIOS = {
    "T1":            (2.0, 1.0, 1.0),
    "T1_SMALL":      (2.0, 1.0, 1.0),
    "T1_LARGE":      (2.0, 1.0, 1.0),
    "T2":            (1.0, 3.0, 0.5),
    "T3":            (3.0, 1.0, 0.5),
    "T_BOTTLE_BOX":  (1.0, 2.2, 1.0),
    "T_MULTIPACK":   (2.0, 1.0, 1.0),
    "T_VERT_VIAL":   (1.0, 2.2, 1.0),
    "T_VERT_DROPPER":(1.0, 2.2, 1.0),
    "T_VERT_INHALER":(1.0, 2.2, 1.0),
}
DEFAULT_RATIO = (2.0, 1.0, 1.0)

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
    """Primary carton (box) sized in metres, coloured from the SKU palette,
    with an accent stripe band on the front face (Row-6 rule, see
    docs/DESIGN_RATIONALE.md §2)."""
    w, h, d = dims_m
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, h / 2))
    box = bpy.context.active_object
    box.name = "carton"
    box.scale = (w / 2, d / 2, h / 2)
    bpy.ops.object.transform_apply(scale=True)

    body_mat = make_material("carton_body", palette.get("primary", "#FFFFFF"), roughness=0.5)
    box.data.materials.append(body_mat)

    accent_hex = palette.get("accent")
    if accent_hex:
        stripe_h = h * 0.08
        bpy.ops.mesh.primitive_cube_add(
            size=1.0, location=(0, -d / 2 - 0.0005, h * 0.55),
        )
        stripe = bpy.context.active_object
        stripe.name = "accent_stripe"
        stripe.scale = (w / 2 * 0.98, 0.001, stripe_h / 2)
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


def setup_camera(target_size: float):
    distance = max(target_size * 3.0, 0.3)
    pitch = math.radians(PITCH_DEG)
    cam_x = distance * math.sin(pitch) * 0.0  # camera stays on the -Y axis, tilted down via rotation
    cam_y = -distance * math.cos(pitch)
    cam_z = distance * math.sin(pitch) + target_size * 0.5

    bpy.ops.object.camera_add(location=(cam_x, cam_y, cam_z))
    cam = bpy.context.active_object
    cam.name = "camera"
    cam.data.lens = 85  # 85mm, matches the documented Gemini optical calibration
    cam.data.dof.aperture_fstop = 8.0  # f/8, same documented value

    constraint = cam.constraints.new(type="TRACK_TO")
    constraint.target = bpy.data.objects.get("carton")
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"

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


def main():
    clear_scene()

    palette = JOB.get("palette", {}) or {}
    pp = JOB.get("primary_package", {}) or {}
    template_id = JOB.get("template_id", "T1")
    ratio = TEMPLATE_RATIOS.get(template_id, DEFAULT_RATIO)

    # Optional Phase-2 hand-authored .blend override (loaded instead of the
    # procedural build below, if the loader finds a matching file).
    scenes_dir = Path(_arg("--scenes-dir", "")) if _arg("--scenes-dir") else None
    blend_override = (scenes_dir / f"{template_id}.blend") if scenes_dir else None
    if blend_override and blend_override.exists():
        bpy.ops.wm.open_mainfile(filepath=str(blend_override))
        # A hand-authored scene is expected to already own camera/lights/materials;
        # only the render settings are still applied below.
    else:
        if pp.get("width_mm") and pp.get("height_mm") and pp.get("depth_mm"):
            dims_m = (float(pp["width_mm"]) / 1000.0,
                     float(pp["height_mm"]) / 1000.0,
                     float(pp["depth_mm"]) / 1000.0)
        else:
            # Data-absent fallback: apply the template's documented aspect
            # ratio to a nominal 100mm long edge.
            base = 0.1
            rw, rh, rd = ratio
            longest = max(rw, rh, rd)
            dims_m = (base * rw / longest, base * rh / longest, base * rd / longest)

        box, target_size = build_box(dims_m, palette)
        build_background(palette.get("background", "#FFFFFF"))
        setup_camera(target_size)
        setup_lighting(target_size)

    setup_render(OUT_PATH, ENGINE, SAMPLES, RES_X, RES_Y)
    bpy.ops.render.render(write_still=True)
    print(f"[render_driver] wrote {OUT_PATH}")


main()
