"""PharmaGen PRO — the Stage 1 -> Stage 2 render-manifest contract.

This module is the single owner of the boundary described by
``schemas/render_manifest.schema.json``. Stage 1 uses it to emit manifests;
the render engines use it to load them. Neither side hand-assembles the shape,
so the two cannot drift apart independently.

Why the manifest exists
-----------------------
A renderer needs decisions, not raw passport data: which template was chosen,
how big the printed carton is, what text goes on the face. Two of those were
previously unavailable to Stage 2 without reaching into Stage 1:

* ``template_id`` required importing ``agent_1_router`` out of a 70 KB module.
* Carton dimensions were not available at all. ``primary_package`` is ``null``
  in every stored passport (it is computed at runtime and never persisted), so
  ``05_assets/blender/render_driver.py`` silently fell back to a guessed aspect
  ratio for the entire catalogue.

Carton, not primary package
---------------------------
The object being rendered is the printed cardboard box. That is the SECONDARY
packaging. The primary package -- the blister, bottle or syringe inside -- is a
different, smaller thing, and for elongated primaries ``resolve_secondary()``
also permutes the axes (``box_width = primary.depth + clearance``). Feeding
primary dimensions into carton geometry is therefore wrong in both scale and,
for some families, orientation. The manifest carries the carton so a consumer
cannot make that mistake.

Dimensions are resolved from the passport's own
``secondary_packaging.dimensions`` string wherever possible. That string IS the
carton size and is present for every SKU in the current catalogue; deriving the
same numbers by reversing into the primary package and back out again loses
precision to a rounding asymmetry in ``pharma_pkg.dimension_resolver``.
"""
from __future__ import annotations

import re
import json
import functools
from pathlib import Path

from src.design_group import load_design, reshape_to_design
from src.utils import product_code

MANIFEST_VERSION = "1.7"

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "render_manifest.schema.json"

# Template -> carton proportions (W:H:D), applied to a nominal long edge when a
# SKU carries no dimensional data whatsoever. Mirrors the documented Gemini
# template proportions so both engines target the same silhouette. This table
# lives here, and only here: 05_assets/blender/render_driver.py used to keep its
# own copy, which is exactly the duplicate-source-of-truth the manifest exists
# to remove.
TEMPLATE_RATIOS = {
    "T1":             (2.0, 1.0, 1.0),
    "T1_SMALL":       (2.0, 1.0, 1.0),
    "T1_LARGE":       (2.0, 1.0, 1.0),
    "T2":             (1.0, 3.0, 0.5),
    "T3":             (3.0, 1.0, 0.5),
    "T_BOTTLE_BOX":   (1.0, 2.2, 1.0),
    "T_MULTIPACK":    (2.0, 1.0, 1.0),
    "T_VERT_VIAL":    (1.0, 2.2, 1.0),
    "T_VERT_DROPPER": (1.0, 2.2, 1.0),
    "T_VERT_INHALER": (1.0, 2.2, 1.0),
}
DEFAULT_RATIO = (2.0, 1.0, 1.0)
NOMINAL_LONG_EDGE_MM = 100.0

# Templates whose carton stands upright. For these the largest extent is the
# HEIGHT, whatever order the passport's dimension string happens to use.
#
# This is not a guess. The dimension string does not encode orientation, and the
# curated reference renders prove it: the same "115x55x48mm" is rendered
# landscape for T1 (Atomoxetine) and portrait for T_VERT_INHALER (Ventolin), and
# the same "110x50x18mm" is landscape for T_MULTIPACK but portrait for
# T_VERT_DROPPER (Lumigan). All four vertical-family references are portrait
# while three of their four dimension strings lead with a number that is not the
# height. The template decides; the string only supplies the three extents.
VERTICAL_FAMILY = {
    "T_BOTTLE_BOX",
    "T_VERT_VIAL",
    "T_VERT_DROPPER",
    "T_VERT_INHALER",
}


# Silhouette aspect (width / height of the projected bounding box) that each
# template's curated reference actually shows. MEASURED 2026-08-09 with
# src.silhouette.measured_silhouette_aspect; the raw numbers, the instrument's
# uncertainty and three cautions about reading them are in
# 01_input_raster/reference_analysis.md section 10.
#
# Compare these against src.silhouette.visible_faces_aspect, never against
# silhouette_aspect: a reference draws its top face and our render cannot show
# one, so only the visible quantity is like for like. Using the whole box
# understates our width by 13-14% on the landscape templates.
#
# These are targets by the owner's decision, taken with the measurements in
# hand. One caution travels with them: the references draw the identical
# 115x55x48 carton three ways, at 1.3036, 1.3109 and 1.1480, so the 10 points
# separating T1_LARGE from T1 are scatter being adopted as art direction. The
# decision was to target all nine anyway. Recorded, not hidden.
#
# T2 is absent deliberately: zero SKU in the catalogue route to it, so there is
# no reference to measure and nothing to reshape.
TARGET_SILHOUETTE_ASPECT = {
    "T1":             1.3036,
    "T1_SMALL":       1.3109,
    "T1_LARGE":       1.1480,
    "T3":             1.5322,
    "T_BOTTLE_BOX":   0.6203,
    "T_MULTIPACK":    1.4066,
    "T_VERT_VIAL":    0.9224,
    "T_VERT_DROPPER": 0.7723,
    "T_VERT_INHALER": 0.8057,
}

# How far the solver may stretch the free edge, as a multiple of the anchor. The
# bracket only has to contain the answer; the flip guard below is what actually
# bounds the result.
_SOLVE_SPAN = (0.02, 50.0)
_SOLVE_STEPS = 200


def orient_for_template(extents: tuple[float, float, float], template_id: str) -> tuple[float, float, float]:
    """Assign three carton extents to the (width, height, depth) axes.

    Horizontal families keep the passport's own order, which already reads
    width-first for every SKU in the catalogue and legitimately includes some
    upright cartons (bottle-ish SKUs that routed to T1). Vertical families are
    re-seated so the longest edge stands up, with the wider of the two remaining
    extents facing the camera.
    """
    if template_id not in VERTICAL_FAMILY:
        return extents
    height, *rest = sorted(extents, reverse=True)
    width, depth = max(rest), min(rest)
    return width, height, depth


def _design_block(sku_id: str) -> dict | None:
    """The `design` block a manifest carries, or None outside the design group.

    Trimmed to what the driver needs: it runs inside Blender's own interpreter
    and can import nothing from this project, so whatever is not in the manifest
    does not exist as far as the renderer is concerned. Verification figures and
    provenance stay in the folder's design_spec.json, where a human reads them.
    """
    spec = load_design(sku_id)
    if spec is None:
        return None
    return {
        "spec_version": str(spec.get("spec_version", "")),
        "face_aspect": float(spec["face_aspect"]),
        "substrate": str(spec["substrate"]),
        "fields": spec.get("fields") or [],
        # Per-role type geometry, where the reference could be read. Partial by
        # nature: only rows identified against the reference's OWN strings are
        # measured, so a role that is absent here is one the renderer keeps on
        # the generic grid rather than one it may place freely.
        "type_rows": spec.get("type_rows") or {},
        "source_image": str(spec.get("source_image", "")),
    }


def reshape_to_art_direction(
    extents: tuple[float, float, float], template_id: str,
) -> tuple[tuple[float, float, float], bool]:
    """Solve the carton's shape onto its template's reference proportion.

    Returns ``(dimensions, was_reshaped)``. Call AFTER ``orient_for_template``:
    the anchor rule reads the width/height assignment that orientation makes.

    **Depth and the longer face edge are kept; the shorter one is solved.** Depth
    barely moves the silhouette -- it only adds the sliver of side panel the
    camera's 35-degree rotation shows -- so solving on it would need enormous
    changes for small effect and would turn slim cartons into cubes. The longer
    edge is kept because it is the one the eye reads as the carton's size, and
    because keeping it makes the result idempotent.

    **A reshape that would turn the PICTURE over is refused.** Two SKU in the
    catalogue, 55x100x55 and 45x80x45, are upright vials that routed to a
    landscape template; solving them onto T1's proportion stretches them past
    three times their width and lays the product on its side. The test is on
    which side of 1.0 the silhouette aspect falls, not on which box edge is
    longer -- those differ, and using the edges refuses cases that are fine.
    T_VERT_VIAL solves to 173x170: wider than tall as a box, yet its silhouette
    reads 0.92 because the camera looks down a portrait carton, so the picture
    stays upright and the reshape is correct. The caller records any refusal in
    ``carton.source`` -- "why were these two not reshaped" has to be readable
    from the data rather than from this docstring.

    Scale is untouched by construction: the camera frames from the bounding
    sphere, so only proportion is art-directable at all.
    """
    target = TARGET_SILHOUETTE_ASPECT.get(template_id)
    if target is None:
        return extents, False

    # The VISIBLE faces, not the whole box. A reference draws its top face and
    # our render cannot show one, so apparent shape matches apparent shape only
    # on this quantity -- see src/silhouette.visible_faces_aspect.
    from src.silhouette import visible_faces_aspect

    width, height, depth = (float(e) for e in extents)
    keep_width = width >= height
    anchor = width if keep_width else height

    def aspect_for(free: float) -> float:
        dims = (anchor, free, depth) if keep_width else (free, anchor, depth)
        return visible_faces_aspect(dims, template_id)

    lo, hi = (anchor * s for s in _SOLVE_SPAN)
    a_lo, a_hi = aspect_for(lo), aspect_for(hi)
    if (target - a_lo) * (target - a_hi) > 0:
        # The target lies outside anything this anchor can reach. Not expected
        # for any catalogue shape; refusing beats returning the nearest edge of
        # the bracket and calling it a solution.
        return extents, False

    for _ in range(_SOLVE_STEPS):
        mid = 0.5 * (lo + hi)
        if (target - aspect_for(lo)) * (target - aspect_for(mid)) <= 0:
            hi = mid
        else:
            lo = mid
    free = 0.5 * (lo + hi)

    passport_aspect = visible_faces_aspect((width, height, depth), template_id)
    if (target >= 1.0) != (passport_aspect >= 1.0):
        return extents, False          # the picture turned over; keep the passport

    return (anchor, free, depth) if keep_width else (free, anchor, depth), True


# ── the contract artifact ────────────────────────────────────────────────────
@functools.lru_cache(maxsize=1)
def load_schema() -> dict:
    """The canonical contract, read from disk and cached."""
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_manifest(manifest: dict) -> None:
    """Raise ``jsonschema.ValidationError`` if *manifest* violates the contract.

    Deliberately strict and deliberately not optional: a boundary that is only
    checked when a library happens to be installed is not enforced at all.
    """
    try:
        from jsonschema import Draft202012Validator
    except ImportError as e:  # pragma: no cover - environment problem, not logic
        raise ImportError(
            "jsonschema is required to validate render manifests. "
            "Install it with: python -m pip install -r requirements.txt"
        ) from e
    Draft202012Validator(load_schema()).validate(manifest)
    _reject_tangled_outlines(manifest)


def _reject_tangled_outlines(manifest: dict) -> None:
    """A design field's outline must be a region, not a drawing instruction.

    JSON Schema cannot say "does not cross itself", and the difference is not
    cosmetic: a self-intersecting ring means different things under different
    fill rules, and this project's two sides use different ones -- PIL's
    even-odd scanline on the measuring side, Blender's tessellation on the
    rendering side. On `340-min` they disagreed by 1.33% of the face and our
    packshot carried a magenta wedge the real carton does not have.

    Checked on write AND on load, like the rest of the contract, so a manifest
    produced before `simple_ring` fails by name here rather than quietly
    rendering the wedge again.
    """
    from src.design_group import ring_crossings

    for field in ((manifest.get("design") or {}).get("fields") or []):
        for i, part in enumerate(field.get("parts") or []):
            outline = part.get("outline") or []
            if len(outline) < 4:
                continue
            hits = ring_crossings([(float(p[0]), float(p[1])) for p in outline])
            if hits:
                raise ValueError(
                    f"{manifest.get('sku_id')}: design field "
                    f"{field.get('role')!r} part {i} has an outline that "
                    f"crosses itself at {hits[:3]} -- that is not a region, and "
                    f"the driver and the QA raster would fill different areas. "
                    f"Regenerate the manifest; src.design_group.simple_ring "
                    f"repairs it at load.")


# ── carton resolution ────────────────────────────────────────────────────────
def _parse_dimension_string(text: str) -> tuple[float, float, float] | None:
    """Parse a "115x55x48mm"-style string into (width, height, depth) in mm.

    Returns ``None`` unless exactly three numbers are present -- two numbers is
    an under-specified box, four is something this function does not understand,
    and guessing at either would be worse than falling through to derivation.
    """
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(text or ""))]
    if len(nums) != 3:
        return None
    if any(n <= 0 for n in nums):
        return None
    return nums[0], nums[1], nums[2]


def _resolve_passport_dimensions(passport: dict, template_id: str) -> dict:
    """The carton's real size in mm, plus where it came from.

    Tried in descending order of fidelity; always succeeds, because a consumer
    freed from null-handling is the main thing the contract buys.
    """
    # 1. The passport's own secondary-packaging string IS the carton size.
    secondary = passport.get("secondary_packaging") or {}
    parsed = _parse_dimension_string(secondary.get("dimensions", ""))
    if parsed:
        w, h, d = orient_for_template(parsed, template_id)
        return {"width_mm": w, "height_mm": h, "depth_mm": d,
                "source": "passport_secondary"}

    # 2. No usable string: classify the primary package and size a carton
    #    around it, reusing the existing owner of that calculation.
    try:
        from src.passport_generator import get_primary_package
        from pharma_pkg.dimension_resolver import resolve_secondary
        secondary_tpl = resolve_secondary(get_primary_package(passport))
        return {"width_mm": float(secondary_tpl.box_width_mm),
                "height_mm": float(secondary_tpl.box_height_mm),
                "depth_mm": float(secondary_tpl.box_depth_mm),
                "source": "derived_from_primary"}
    except Exception:
        # 3. Last resort: the template's documented aspect ratio. Reaching here
        #    means the SKU has no dimensional data at all; the whole-catalogue
        #    test asserts that no current SKU does.
        rw, rh, rd = TEMPLATE_RATIOS.get(template_id, DEFAULT_RATIO)
        longest = max(rw, rh, rd)
        scale = NOMINAL_LONG_EDGE_MM / longest
        return {"width_mm": rw * scale, "height_mm": rh * scale,
                "depth_mm": rd * scale, "source": "template_ratio"}


def resolve_carton(passport: dict, template_id: str) -> dict:
    """The carton as Stage 2 receives it: scene geometry AND the real size.

    The two are separate on purpose and the separation is the whole of contract
    1.3. ``width_mm``/``height_mm``/``depth_mm`` are solved onto the template's
    measured reference proportion and exist to build the box.
    ``passport_dimensions`` are untouched and exist to be printed. A consumer
    that prints the first set puts invented measurements on pharmaceutical
    packaging, which is the same act this project already refuses when it
    declines to print a plausible LOT or EXP.
    """
    secondary = passport.get("secondary_packaging") or {}
    # Construction data travels with the dimensions on every resolution path:
    # the side panel is drawn from it, and a carton that reached the renderer
    # with its features stripped would quietly lose the zones it declares.
    extras = {
        "features": [str(f) for f in (secondary.get("features") or [])],
        "material": str(secondary.get("material") or ""),
    }
    passport_dims = _resolve_passport_dimensions(passport, template_id)
    real = (passport_dims["width_mm"], passport_dims["height_mm"],
            passport_dims["depth_mm"])

    # A design spec wins over the template's proportion, because it IS the
    # target: those eleven SKU are rendered against real photography, and the
    # per-template constant was fitted to nine AI reference renders that the
    # photographs disagree with. Note the two solve different quantities --
    # front face here, whole silhouette there; see design_group.reshape_to_design.
    design = load_design(passport.get("sku_id", ""))
    if design is not None:
        geometry = reshape_to_design(real, float(design["face_aspect"]))
        source = "design_spec"
    else:
        geometry, reshaped = reshape_to_art_direction(real, template_id)
        if reshaped:
            source = "art_direction"
        elif template_id in TARGET_SILHOUETTE_ASPECT:
            source = "art_direction_declined_orientation"
        else:
            source = passport_dims["source"]

    return {"width_mm": geometry[0], "height_mm": geometry[1],
            "depth_mm": geometry[2], "passport_dimensions": passport_dims,
            "source": source, **extras}


# ── provider ─────────────────────────────────────────────────────────────────
def build_manifest(passport: dict) -> dict:
    """Compile one passport into a render manifest.

    Does not validate -- callers that persist or consume a manifest should call
    :func:`validate_manifest`, so that a failure is attributed to the side that
    caused it.
    """
    from src.passport_generator import agent_1_router

    template_id, is_bottle_override = agent_1_router(passport)
    palette = (passport.get("branding") or {}).get("palette") or {}
    label = passport.get("label_content") or {}

    return {
        "manifest_version": MANIFEST_VERSION,
        "sku_id": str(passport.get("sku_id", "")),
        # What identifies the row and what is printed on the pack are two
        # questions; conflating them put `.jpg` on all 391 cartons. See
        # utils.product_code.
        "product_code": product_code(passport.get("sku_id", "")),
        "template_id": template_id,
        "is_bottle_override": bool(is_bottle_override),
        "packaging_geometry": str(passport.get("packaging_geometry") or "BOX"),
        "carton": resolve_carton(passport, template_id),
        **({"design": design} if (design := _design_block(passport.get("sku_id", ""))) else {}),
        "palette": {
            "primary": palette.get("primary"),
            "accent": palette.get("accent"),
            "background": palette.get("background"),
        },
        "label_content": {
            "brand_name_display": str(label.get("brand_name_display", "")),
            # The passport keeps the ingredient at its TOP level, not inside
            # label_content, so this one is not read off `label` like its
            # siblings. The label_content fallback is there for a future passport
            # that carries a display-specific override.
            "active_ingredient_display": str(
                label.get("active_ingredient_display")
                or passport.get("active_ingredient")
                or ""),
            "dosage_display": str(label.get("dosage_display", "")),
            "unit_count_display": str(label.get("unit_count_display", "")),
        },
    }


# ── persistence ──────────────────────────────────────────────────────────────
def manifest_path_for(stem: str, manifests_dir: Path) -> Path:
    """Manifest location for a passport stem, following the -min convention."""
    return Path(manifests_dir) / f"{stem}.json"


def write_manifest(manifest: dict, path: Path) -> None:
    """Validate, then persist. Never writes a manifest that breaks the contract."""
    validate_manifest(manifest)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def load_manifest(path: Path) -> dict:
    """Read and validate a manifest written earlier by Stage 1."""
    with open(path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    validate_manifest(manifest)
    return manifest
