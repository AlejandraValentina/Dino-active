"""Editable, versioned configurations for the supported integrated 2T engine.

This is a data/validation adapter. Constructing it never advances the solver.
Native physics remains owned by :mod:`motorsim.integrated_2t`.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import importlib
import inspect
import json
import math
import sys
from pathlib import Path
from typing import Any

from .integrated_2t import IntegratedEngine2T
from .mechanical import MechanicalLossModel

SCHEMA = "MOTORSIM_ENGINE_CONFIGURATION_V1"
_FIELDS = {"schema", "display_name", "provenance", "native_configuration",
           "native_configuration_sha256", "mechanical_loss_model",
           "operating_conditions", "units", "validation_state"}
UNITS = {"length": "SI; native geometry fields ending _mm are millimetres",
         "pressure": "Pa", "temperature": "K", "volume": "m^3",
         "mass": "kg", "time": "s", "angle": "degree unless field is explicitly radians",
         "speed": "rpm", "energy": "J", "power": "W", "torque": "N*m",
         "species_mass": "kg", "afr": "kg_air/kg_fuel", "load": "dimensionless"}
_IMPLEMENTATION_MODULES = (
    "motorsim._trajectory_store", "motorsim._evidence_io",
    "motorsim.crankcase", "motorsim.coupling", "motorsim.fuel_combustion",
    "motorsim.gas1d.boundary", "motorsim.gas1d.eos", "motorsim.gas1d.mesh",
    "motorsim.gas1d.open_end_plenum_v2", "motorsim.gas1d.riemann",
    "motorsim.integrated_2t", "motorsim.kinematics",
    "motorsim.network_components", "motorsim.p6_species",
    "motorsim.p7_prescribed", "motorsim.powervalve", "motorsim.reed",
    "motorsim.reed_coupling", "motorsim.thermal", "motorsim.two_stroke_ports",
    "motorsim.mechanical", "motorsim.engine_configuration",
    "motorsim.engine_variants", "motorsim.engineering_outputs",
    "motorsim.reference_harness.convergence", "motorsim.exploratory_workflow")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def implementation_source_hashes() -> dict[str, str]:
    """Hash the full workflow implementation, using a build manifest when frozen."""
    if getattr(sys, "frozen", False):
        root=Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        manifest_path=root/"motorsim"/"build.json"
        if not manifest_path.is_file():
            raise ValueError("packaged workflow source manifest is missing")
        payload=manifest_path.read_bytes(); manifest=json.loads(payload)
        hashes=manifest.get("workflow_source_hashes")
        if (not isinstance(hashes,dict) or set(hashes)!=set(_IMPLEMENTATION_MODULES) or
                any(not isinstance(value,str) or len(value)!=64 or
                    any(c not in "0123456789abcdef" for c in value)
                    for value in hashes.values())):
            raise ValueError("packaged workflow source manifest is invalid")
        return {**hashes,"dino.package_build_manifest":hashlib.sha256(payload).hexdigest()}
    hashes={}
    for module_name in _IMPLEMENTATION_MODULES:
        module=importlib.import_module(module_name)
        path=Path(inspect.getsourcefile(module))
        hashes[module.__name__]=hashlib.sha256(path.read_bytes().replace(b"\r\n",b"\n")).hexdigest()
    return hashes


def _finite_tree(value: Any, path: str = "configuration") -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (float, int)):
        if not math.isfinite(float(value)):
            raise ValueError(f"{path} must be finite")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} has a non-string key")
            _finite_tree(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _finite_tree(item, f"{path}[{i}]")


def validate_native(native: dict[str, Any]) -> IntegratedEngine2T:
    if not isinstance(native, dict):
        raise ValueError("native_configuration must be an object")
    _finite_tree(native)
    # The native constructor is the authoritative supported-capability and
    # geometry/topology validator. No solver integration occurs here.
    return IntegratedEngine2T.from_configuration_dict(deepcopy(native))


def _validate_operating_conditions(value: dict[str, Any]) -> None:
    if not isinstance(value, dict) or set(value) != {"reference_rpm", "load", "fuel_id", "afr"}:
        raise ValueError("operating_conditions schema must declare reference_rpm, load, fuel_id, afr")
    _finite_tree(value, "operating_conditions")
    rpm, load, afr = (value[k] for k in ("reference_rpm", "load", "afr"))
    if type(rpm) not in (int, float) or rpm <= 0:
        raise ValueError("operating_conditions.reference_rpm must be positive RPM")
    if type(load) not in (int, float) or load < 0:
        raise ValueError("operating_conditions.load must be a nonnegative dimensionless load")
    if type(afr) not in (int, float) or afr <= 0:
        raise ValueError("operating_conditions.afr must be positive kg_air/kg_fuel")
    if not isinstance(value["fuel_id"], str) or not value["fuel_id"].strip():
        raise ValueError("operating_conditions.fuel_id is required")


def create(*, native_configuration: dict[str, Any],
           mechanical_loss_model: dict[str, Any],
           operating_conditions: dict[str, Any],
           provenance: dict[str, Any], display_name: str = "Engine") -> dict[str, Any]:
    native = deepcopy(native_configuration)
    engine = validate_native(native)
    loss = MechanicalLossModel.from_dict(deepcopy(mechanical_loss_model))
    _validate_operating_conditions(operating_conditions)
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("provenance must be an explicit nonempty object")
    if "configuration_source" not in provenance or "fuel" not in provenance:
        raise ValueError("provenance must explicitly identify configuration_source and fuel")
    if not isinstance(provenance["configuration_source"], (str, dict)) or not isinstance(provenance["fuel"], dict):
        raise ValueError("configuration_source/fuel provenance types are invalid")
    if not provenance["fuel"].get("provenance"):
        raise ValueError("fuel provenance classification is required")
    _finite_tree(provenance, "provenance")
    doc = {"schema": SCHEMA, "display_name": str(display_name),
           "provenance": deepcopy(provenance), "native_configuration": native,
           "native_configuration_sha256": sha256(native),
           "mechanical_loss_model": loss.to_dict(),
           "operating_conditions": deepcopy(operating_conditions),
           "units": dict(UNITS),
           "validation_state": "VALIDATED_NO_SOLVER_STEPS"}
    validate(doc)
    return doc


def validate(document: dict[str, Any]) -> IntegratedEngine2T:
    if not isinstance(document, dict) or set(document) != _FIELDS or document.get("schema") != SCHEMA:
        raise ValueError("engine configuration schema/fields are invalid")
    if not isinstance(document["display_name"], str) or not isinstance(document["provenance"], dict):
        raise ValueError("display_name/provenance types are invalid")
    if document["units"] != UNITS:
        raise ValueError("unit declaration is missing or incompatible with the native adapter")
    _finite_tree(document)
    native = document["native_configuration"]
    if sha256(native) != document["native_configuration_sha256"]:
        raise ValueError("native configuration identity hash mismatch")
    engine = validate_native(native)
    MechanicalLossModel.from_dict(document["mechanical_loss_model"])
    _validate_operating_conditions(document["operating_conditions"])
    if document["validation_state"] != "VALIDATED_NO_SOLVER_STEPS":
        raise ValueError("unsupported validation_state")
    return engine


def identity(document: dict[str, Any]) -> str:
    validate(document)
    # Human-facing name is intentionally excluded from semantic identity.
    semantic = {k: v for k, v in document.items() if k != "display_name"}
    return sha256(semantic)


def to_solver_configuration(document: dict[str, Any]) -> dict[str, Any]:
    validate(document)
    return deepcopy(document["native_configuration"])


def resolve_for_operating_point(document: dict[str, Any], *, rpm: float | None = None
                               ) -> dict[str, Any]:
    """Resolve a saved project engine into one immutable native operating point.

    The returned envelope binds the selected project identity, effective native
    solver configuration, explicit loss model, fuel provenance and source
    modules. A requested RPM is an explicit override; it never mutates the
    saved project document.
    """
    validate(document)
    selected_rpm = document["operating_conditions"]["reference_rpm"] if rpm is None else rpm
    if type(selected_rpm) not in (int, float) or not math.isfinite(selected_rpm) or selected_rpm <= 0:
        raise ValueError("selected RPM must be positive finite numeric data")
    native = deepcopy(document["native_configuration"])
    native["reference_rpm"] = float(selected_rpm)
    engine = IntegratedEngine2T.from_configuration_dict(native)
    loss_model = MechanicalLossModel.from_dict(deepcopy(document["mechanical_loss_model"]))
    source_hashes = implementation_source_hashes()
    effective = {
        "schema": "DINO_EXECUTABLE_ENGINE_IDENTITY_V1",
        "project_engine_identity_sha256": identity(document),
        "native_configuration": native,
        "native_configuration_sha256": sha256(native),
        "solver_configuration_sha256": engine.configuration_identity["configuration_sha256"],
        "selected_rpm": float(selected_rpm),
        "operating_conditions": {**deepcopy(document["operating_conditions"]),
                                 "reference_rpm": float(selected_rpm)},
        "mechanical_loss_model": loss_model.to_dict(),
        "mechanical_loss_model_sha256": sha256(loss_model.to_dict()),
        "fuel_provenance": deepcopy(document["provenance"]["fuel"]),
        "configuration_provenance": deepcopy(document["provenance"]),
        "source_hashes": source_hashes,
    }
    effective["identity_sha256"] = sha256(effective)
    return effective
