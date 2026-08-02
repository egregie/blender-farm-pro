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
  ``assets/blender/render_driver.py`` silently fell back to a guessed aspect
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

MANIFEST_VERSION = "1.2"

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "render_manifest.schema.json"

# Template -> carton proportions (W:H:D), applied to a nominal long edge when a
# SKU carries no dimensional data whatsoever. Mirrors the documented Gemini
# template proportions so both engines target the same silhouette. This table
# lives here, and only here: assets/blender/render_driver.py used to keep its
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


def resolve_carton(passport: dict, template_id: str) -> dict:
    """Carton dimensions in mm, plus where they came from.

    Tried in descending order of fidelity; always succeeds, because a consumer
    freed from null-handling is the main thing the contract buys.
    """
    # 1. The passport's own secondary-packaging string IS the carton size.
    secondary = passport.get("secondary_packaging") or {}
    # Construction data travels with the dimensions, on every path below: the
    # side panel is drawn from it, and a carton that reached the renderer with
    # its features stripped would quietly lose the zones it declares.
    extras = {
        "features": [str(f) for f in (secondary.get("features") or [])],
        "material": str(secondary.get("material") or ""),
    }
    parsed = _parse_dimension_string(secondary.get("dimensions", ""))
    if parsed:
        w, h, d = orient_for_template(parsed, template_id)
        return {"width_mm": w, "height_mm": h, "depth_mm": d,
                "source": "passport_secondary", **extras}

    # 2. No usable string: classify the primary package and size a carton
    #    around it, reusing the existing owner of that calculation.
    try:
        from src.passport_generator import get_primary_package
        from pharma_pkg.dimension_resolver import resolve_secondary
        secondary_tpl = resolve_secondary(get_primary_package(passport))
        return {"width_mm": float(secondary_tpl.box_width_mm),
                "height_mm": float(secondary_tpl.box_height_mm),
                "depth_mm": float(secondary_tpl.box_depth_mm),
                "source": "derived_from_primary", **extras}
    except Exception:
        # 3. Last resort: the template's documented aspect ratio. Reaching here
        #    means the SKU has no dimensional data at all; the whole-catalogue
        #    test asserts that no current SKU does.
        rw, rh, rd = TEMPLATE_RATIOS.get(template_id, DEFAULT_RATIO)
        longest = max(rw, rh, rd)
        scale = NOMINAL_LONG_EDGE_MM / longest
        return {"width_mm": rw * scale, "height_mm": rh * scale,
                "depth_mm": rd * scale, "source": "template_ratio", **extras}


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
        "template_id": template_id,
        "is_bottle_override": bool(is_bottle_override),
        "packaging_geometry": str(passport.get("packaging_geometry") or "BOX"),
        "carton": resolve_carton(passport, template_id),
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
