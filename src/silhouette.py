"""Where the carton lands in frame, computed from geometry rather than measured.

Why this exists
---------------
Until now the only answer to "how much of the frame does the carton fill" came
from measuring pixels in a rendered image. That is exactly the measurement a
white carton on a 255 backdrop defeats: the brightly lit top face blends into
the background, so a landscape carton reads shorter than it is. Every landscape
row of the measured table in ``00_PROJECT_STATE/CURRENT_STATE.md`` is 5-9 points
low on height for that reason -- for the modal ``115x55x48`` carton it records
74/48 where the geometry says 76/57.

The carton is a box and the camera is deterministic, so the silhouette does not
have to be guessed at all. This module projects all eight corners through the
same camera ``05_assets/blender/render_driver.py`` builds and returns the
bounding box of the result.

It is checked, not asserted. The driver projects the carton's printed faces
itself and writes them beside each render as ``{stem}.view.json``;
``tests/test_silhouette.py`` requires this module to reproduce those pixels to
within a rounding error. If it ever stops doing so, the model is wrong and the
test says which corner.

The camera constants
--------------------
They are duplicated from the driver, because ``render_driver.py`` cannot be
imported outside Blender -- it does ``import bpy`` at module scope, and Blender's
bundled interpreter is the only place that resolves. Duplication without a check
is how two sources of truth begin to disagree, so the test reads the driver as
text and fails the moment a value parts company with its copy here.

One trap is worth naming. ``src/render_manifest.py`` also defines a
``VERTICAL_FAMILY``, and it is a *different set*: it includes ``T_BOTTLE_BOX``
because that carton stands upright, and it governs which edge is stood up. The
set below governs which CAMERA is used, and the driver excludes ``T_BOTTLE_BOX``
from it. Using the orientation set here would shoot that template with the wrong
pitch and rotation, and nothing downstream would notice.
"""
from __future__ import annotations

import math

# ── Camera, mirrored from 05_assets/blender/render_driver.py ────────────────
LENS_MM = 85.0
SENSOR_MM = 36.0
SPHERE_FILL = 0.8365

# (pitch_deg, rotation_deg)
CAMERA_VERTICAL = (20.0, 27.5)
CAMERA_DEFAULT = (25.0, 35.0)

# Which templates take the vertical camera. NOT the manifest's orientation
# family -- see the module docstring.
CAMERA_VERTICAL_TEMPLATES = {"T_VERT_VIAL", "T_VERT_DROPPER", "T_VERT_INHALER"}

DEFAULT_RESOLUTION = (2048, 2048)


def camera_for(template_id: str) -> tuple[float, float]:
    """(pitch_deg, rotation_deg) for a template, as the driver would choose."""
    return (CAMERA_VERTICAL if template_id in CAMERA_VERTICAL_TEMPLATES
            else CAMERA_DEFAULT)


def _projector(dims_mm, template_id, resolution):
    """A function mapping a local carton corner to image pixels.

    The carton spans x in [-w/2, w/2], y in [-d/2, d/2], z in [0, h] locally,
    is rotated about Z, and is framed by solving the camera distance from the
    bounding sphere -- which is why absolute size cancels out entirely.
    """
    w, h, d = (float(v) for v in dims_mm)
    res_x, res_y = resolution
    pitch_deg, rot_deg = camera_for(template_id)
    pitch, rot = math.radians(pitch_deg), math.radians(rot_deg)

    half_fov = math.atan((SENSOR_MM / 2.0) / LENS_MM)
    tan_half = math.tan(half_fov)
    radius = 0.5 * math.sqrt(w * w + h * h + d * d)
    distance = radius / math.sin(SPHERE_FILL * half_fov)

    # Camera at the driver's position, rotated (90deg - pitch) about X: it looks
    # along +Y and downward.
    cam = (0.0, -distance * math.cos(pitch), h / 2.0 + distance * math.sin(pitch))
    right = (1.0, 0.0, 0.0)
    up = (0.0, math.sin(pitch), math.cos(pitch))
    forward = (0.0, math.cos(pitch), -math.sin(pitch))

    def project(local):
        lx, ly, lz = local
        wx = lx * math.cos(rot) - ly * math.sin(rot)
        wy = lx * math.sin(rot) + ly * math.cos(rot)
        v = (wx - cam[0], wy - cam[1], lz - cam[2])
        x_cam = sum(a * b for a, b in zip(v, right))
        y_cam = sum(a * b for a, b in zip(v, up))
        z_cam = sum(a * b for a, b in zip(v, forward))
        ndc_x = x_cam / (z_cam * tan_half)
        ndc_y = y_cam / (z_cam * tan_half)
        # NDC runs -1..1 with y up; image pixels count from the top-left, y down.
        return [(ndc_x + 1.0) / 2.0 * res_x, (1.0 - (ndc_y + 1.0) / 2.0) * res_y]

    return project, (w, h, d)


def _order_quad(pairs):
    """[top-left, top-right, bottom-right, bottom-left], the driver's order.

    Split by LOCAL Z, not by projected y, for the reason ``_order_quad`` in the
    driver documents: on a wide shallow face the far vertical edge can project
    entirely above the near one, and sorting the pixels then pairs two corners
    of the same edge together and emits a self-intersecting quad.
    """
    by_z = sorted(pairs, key=lambda pair: pair[0][2])
    bottom = sorted((px for _, px in by_z[:2]), key=lambda p: p[0])
    top = sorted((px for _, px in by_z[2:]), key=lambda p: p[0])
    return [top[0], top[1], bottom[1], bottom[0]]


def _face(dims_mm, template_id, resolution, axis, take_min):
    project, (w, h, d) = _projector(dims_mm, template_id, resolution)
    extent = {0: w / 2.0, 1: d / 2.0}[axis]
    fixed = -extent if take_min else extent
    corners = []
    for other in (-{0: d, 1: w}[axis] / 2.0, {0: d, 1: w}[axis] / 2.0):
        for z in (0.0, h):
            local = (fixed, other, z) if axis == 0 else (other, fixed, z)
            corners.append((local, project(local)))
    return _order_quad(corners)


def front_face_px(dims_mm, template_id, resolution=DEFAULT_RESOLUTION):
    """The printed front face -- local -Y -- in image pixels, TL TR BR BL."""
    return _face(dims_mm, template_id, resolution, axis=1, take_min=True)


def side_panel_px(dims_mm, template_id, resolution=DEFAULT_RESOLUTION):
    """The visible side panel -- local -X -- in image pixels, TL TR BR BL."""
    return _face(dims_mm, template_id, resolution, axis=0, take_min=True)


def silhouette_px(dims_mm, template_id, resolution=DEFAULT_RESOLUTION):
    """(min_x, min_y, max_x, max_y) of the whole carton, in image pixels."""
    project, (w, h, d) = _projector(dims_mm, template_id, resolution)
    xs, ys = [], []
    for lx in (-w / 2.0, w / 2.0):
        for ly in (-d / 2.0, d / 2.0):
            for lz in (0.0, h):
                px, py = project((lx, ly, lz))
                xs.append(px)
                ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


def frame_fill(dims_mm, template_id, resolution=DEFAULT_RESOLUTION):
    """(width, height) of the silhouette as a percentage of the frame.

    Directly comparable with the numbers measured off the reference renders,
    and unlike them it cannot lose a face to the backdrop.
    """
    res_x, res_y = resolution
    x0, y0, x1, y1 = silhouette_px(dims_mm, template_id, resolution)
    return 100.0 * (x1 - x0) / res_x, 100.0 * (y1 - y0) / res_y


def silhouette_aspect(dims_mm, template_id, resolution=DEFAULT_RESOLUTION):
    """Silhouette width divided by its height. The art-direction target."""
    w_pct, h_pct = frame_fill(dims_mm, template_id, resolution)
    return w_pct / h_pct
