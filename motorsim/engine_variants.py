"""Configuration variants and supported axisymmetric exhaust profiles."""
from __future__ import annotations

from copy import deepcopy
import math

from .engine_configuration import identity, validate
from .gas1d.mesh import segments_mesh


def compare_configurations(before: dict, after: dict) -> list[dict]:
    """Return semantic leaf changes, with SI/unit labels inferred from field names."""
    changes: list[dict] = []
    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict) and x.keys() == y.keys():
            for key in sorted(x): walk(x[key], y[key], path + "/" + key)
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (left, right) in enumerate(zip(x, y)): walk(left, right, path + f"/{i}")
        elif x != y:
            key = path.rsplit("/", 1)[-1]
            unit = ("mm" if key.endswith("_mm") else "m" if key.endswith("_m") else
                    "Pa" if key.endswith("_pa") else "rpm" if key.endswith("rpm") else
                    "kg_air/kg_fuel" if key == "afr" else "dimensionless" if key == "load" else
                    "SI/native" if isinstance(x, (int,float)) else "")
            changes.append({"path": path, "unit": unit, "before": x, "after": y})
    for section in ("native_configuration", "mechanical_loss_model", "operating_conditions"):
        walk(before[section], after[section], "/" + section)
    return changes


def variant(base: dict, *, display_name: str, native_patch: dict | None = None,
            mechanical_loss_model: dict | None = None,
            operating_conditions_patch: dict | None = None) -> dict:
    """Apply explicit native, loss-model, and/or operating-condition edits."""
    validate(base)
    if not any((native_patch, mechanical_loss_model, operating_conditions_patch)):
        raise ValueError("variant requires a nonempty explicit patch")
    result = deepcopy(base)
    native = deepcopy(base["native_configuration"])
    def merge(target, patch, prefix=""):
        for key, value in patch.items():
            if key not in target:
                raise ValueError(f"unsupported configuration path {prefix}/{key}")
            if isinstance(value, dict) and isinstance(target[key], dict): merge(target[key], value, prefix+"/"+key)
            else: target[key] = deepcopy(value)
    if native_patch is not None:
        if not isinstance(native_patch, dict) or not native_patch:
            raise ValueError("native_patch must be a nonempty object")
        merge(native, native_patch)
    result["display_name"] = display_name
    result["native_configuration"] = native
    from .engine_configuration import sha256
    result["native_configuration_sha256"] = sha256(native)
    if mechanical_loss_model is not None:
        result["mechanical_loss_model"] = deepcopy(mechanical_loss_model)
    if operating_conditions_patch is not None:
        if not isinstance(operating_conditions_patch, dict) or not operating_conditions_patch:
            raise ValueError("operating_conditions_patch must be a nonempty object")
        merge(result["operating_conditions"], operating_conditions_patch, "/operating_conditions")
    result["provenance"] = {**result["provenance"], "variant_parent_identity": identity(base)}
    validate(result)
    return result


def escape_sections(document: dict) -> list[dict]:
    validate(document)
    sections = document["native_configuration"]["geometry_identity"].get("chamber", {}).get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("native engine has no editable chamber sections")
    return deepcopy(sections)


def replace_escape_sections(document: dict, sections: list[dict], *, display_name: str | None = None) -> dict:
    """Build exact one-cell-per-section solver mesh using linear circular frusta.

    Section count must match existing cells so the initial state mapping is
    unambiguous. Geometry outside the represented axisymmetric profile fails.
    """
    old = escape_sections(document)
    if not isinstance(sections, list) or len(sections) != len(old):
        raise ValueError("escape edit must preserve cell/section count; state remapping is unsupported")
    normalized = []
    for i, row in enumerate(sections):
        required = {"name", "kind", "length_mm", "inlet_diameter_mm", "outlet_diameter_mm", "provenance"}
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError(f"escape section {i} schema is invalid")
        if row["kind"] not in {"header", "diffuser", "belly", "baffle_cone", "stinger", "linear"}:
            raise ValueError(f"escape section {i} kind is not represented by solver")
        vals = [row[k] for k in ("length_mm", "inlet_diameter_mm", "outlet_diameter_mm")]
        if any(type(v) not in (int,float) or not math.isfinite(v) or v <= 0 for v in vals):
            raise ValueError(f"escape section {i} dimensions must be finite positive mm")
        if not isinstance(row["provenance"], str) or not row["provenance"]:
            raise ValueError(f"escape section {i} provenance is required")
        if normalized and not math.isclose(normalized[-1]["outlet_diameter_mm"], row["inlet_diameter_mm"], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError(f"escape section {i} is discontinuous")
        normalized.append(deepcopy(row))
    native = deepcopy(document["native_configuration"])
    exhaust = next((d for d in native["ducts"] if d["id"] == "exhaust"), None)
    if exhaust is None or len(exhaust["mesh"]["volumes"]) != len(normalized):
        raise ValueError("exhaust duct mesh topology is not compatible with section representation")
    segments = [{"length": r["length_mm"], "start_diameter": r["inlet_diameter_mm"], "end_diameter": r["outlet_diameter_mm"]} for r in normalized]
    mesh = segments_mesh(segments, max(r["length_mm"] for r in normalized) / 1000.0)
    old_volumes = exhaust["mesh"]["volumes"]
    new_mesh = mesh.as_dict()
    # Keep the established axial origin, while scaling each extensive species
    # inventory with the cell volume at unchanged primitive density/composition.
    origin = exhaust["mesh"]["faces"][0]
    new_mesh["faces"] = [x + origin for x in new_mesh["faces"]]
    native["duct_species"]["exhaust"] = [
        [mass * new_mesh["volumes"][i] / old_volumes[i] for mass in row]
        for i, row in enumerate(native["duct_species"]["exhaust"])]
    exhaust["mesh"] = new_mesh
    native["geometry_identity"]["chamber"]["sections"] = normalized
    from .engine_configuration import create, sha256
    result = deepcopy(document)
    result["display_name"] = display_name or document["display_name"]
    result["native_configuration"] = native
    result["native_configuration_sha256"] = sha256(native)
    result["provenance"] = {**result["provenance"], "escape_geometry_adapter": "SEGMENTS_MESH_EXACT_FRUSTUM_V1"}
    validate(result)
    return result
