"""Fail-closed warm initialization from a completed periodic point.

This creates a new operating-point configuration from conservative physical
state. It deliberately does not restore a source checkpoint as a continuation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import math

from .engine_configuration import identity, resolve_for_operating_point, sha256, validate
from .integrated_2t import IntegratedEngine2T

SCHEMA = "DINO_PERIODIC_STATE_INITIALIZATION_V1"
_EXPECTED_KEYS = {"manifest_sha256", "checkpoint_sha256", "result_sha256",
                  "source_run_id", "source_variant_label", "source_rpm"}


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"periodic source artifact must be a JSON object: {path.name}")
    return value


def _without_operating_rpm(identity_value: dict) -> dict:
    result = deepcopy(identity_value)
    result.pop("configuration_sha256", None)
    result.pop("reference_rpm", None)
    valve = result.get("port_binding", {}).get("powervalve")
    if valve is not None:
        valve.pop("rpm", None)
        valve.pop("position", None)
    return result


def _power_valve_change_is_rpm_only(source_identity: dict,
                                   target_identity: dict,
                                   target_rpm: float) -> bool:
    source = source_identity.get("port_binding", {}).get("powervalve")
    target = target_identity.get("port_binding", {}).get("powervalve")
    if source is None or target is None:
        return source is target
    source_static = {k: v for k, v in source.items() if k not in {"rpm", "position"}}
    target_static = {k: v for k, v in target.items() if k not in {"rpm", "position"}}
    if source_static != target_static:
        return False
    source_rpm, source_position = source.get("rpm"), source.get("position")
    target_rpm_map, target_position = target.get("rpm"), target.get("position")
    if (not isinstance(source_rpm, list) or not isinstance(source_position, list) or
            not isinstance(target_rpm_map, list) or not isinstance(target_position, list) or
            len(source_rpm) != len(source_position) or
            len(target_rpm_map) != len(target_position)):
        return False
    if target_rpm_map == source_rpm and target_position == source_position:
        return source_rpm[0] <= target_rpm <= source_rpm[-1]
    return (len(target_rpm_map) == len(source_rpm) + 1 and
            target_rpm_map[:-1] == source_rpm and
            target_position[:-1] == source_position and
            target_rpm_map[-1] == target_rpm and
            target_position[-1] == source_position[-1])


def _state_digest(state: dict) -> str:
    return hashlib.sha256(_canonical_bytes(state)).hexdigest()


def _transfer_state_to_native(target_native: dict, source_engine: IntegratedEngine2T,
                              target_engine: IntegratedEngine2T,
                              target_rpm: float) -> tuple[dict, dict, dict]:
    """Map validated physical state into target initial conditions without stepping."""
    if (_without_operating_rpm(source_engine.configuration_identity) !=
            _without_operating_rpm(target_engine.configuration_identity)):
        raise ValueError("source and target differ beyond RPM and its explicit power-valve map")
    if not _power_valve_change_is_rpm_only(
            source_engine.configuration_identity,
            target_engine.configuration_identity, float(target_rpm)):
        raise ValueError("target power-valve change is not the existing RPM map or its explicit endpoint hold")
    if source_engine.dynamic_reed_binding is not None or "dynamic_reed" in source_engine.state:
        raise ValueError("dynamic-reed state transfer is not supported by this initializer")
    source_state = source_engine.state
    source_inventory = source_engine.inventory(source_state)
    if set(source_state["chambers"]) != {"crankcase", "cylinder"}:
        raise ValueError("periodic source chamber topology is unsupported")
    geometry0 = target_engine._geometry(0.0, float(target_rpm))
    native = deepcopy(target_native)
    native["initial_chambers"]["species"] = {
        name: list(values) for name, values in source_state["species"]["chambers"].items()}
    for name in ("crankcase", "cylinder"):
        mass, internal_energy, source_volume = source_state["chambers"][name]
        target_volume = (geometry0.crankcase_volume_m3 if name == "crankcase"
                         else geometry0.cylinder_volume_m3)
        if not math.isclose(source_volume, target_volume, rel_tol=0.0, abs_tol=1e-18):
            raise ValueError(f"periodic source {name} volume does not match target phase geometry")
        native["initial_chambers"][name] = [
            mass / source_volume, 0.0,
            (target_engine.eos.gamma - 1.0) * internal_energy / source_volume,
            1.0]

    if set(source_state["ducts"]) != set(native["initial_duct_states"]):
        raise ValueError("periodic source duct topology differs from target")
    for duct_id, cells in source_state["ducts"].items():
        target_mesh = next(row["mesh"] for row in native["ducts"]
                           if row["id"] == duct_id)
        if len(cells) != len(target_mesh["volumes"]):
            raise ValueError(f"periodic source {duct_id} cell count differs from target mesh")
        native["initial_duct_states"][duct_id] = [
            # The fourth Euler entry is a legacy fresh marker, not a conserved
            # physical field here; four-species masses are authoritative.
            list(target_engine.eos.primitive((q[0], q[1], q[2], q[0])))
            for q in cells]
        native["duct_species"][duct_id] = [list(values) for values in
            source_state["species"]["ducts"][duct_id]]

    source_nodes = source_state["network_volumes"]
    target_nodes = {row["node"]["id"]: row for row in native["network_volumes"]}
    if set(source_nodes) != set(target_nodes):
        raise ValueError("periodic source network-volume topology differs from target")
    for node_id, row in target_nodes.items():
        mass, energy, volume = source_nodes[node_id]
        if volume != row["node"]["volume_m3"]:
            raise ValueError(f"periodic source network volume differs for {node_id}")
        row["initial_state"] = {"mass_kg": mass, "internal_energy_j": energy,
                                "species_mass_kg": list(
                                    source_state["species"]["network_volumes"][node_id])}

    initialized_engine = IntegratedEngine2T.from_configuration_dict(native)
    target_inventory = initialized_engine.inventory()
    for field, left, right in (
        ("mass_kg", source_inventory["mass_kg"], target_inventory["mass_kg"]),
        ("energy_J", source_inventory["energy_J"], target_inventory["energy_J"]),
    ):
        if not math.isclose(left, right, rel_tol=2e-14, abs_tol=1e-18):
            raise ValueError(f"periodic state transfer changed total {field}")
    for index, (left, right) in enumerate(zip(source_inventory["species_kg"],
                                               target_inventory["species_kg"])):
        if not math.isclose(left, right, rel_tol=2e-14, abs_tol=1e-20):
            raise ValueError(f"periodic state transfer changed species inventory {index}")
    if (initialized_engine.cycle != 0 or initialized_engine.time_s != 0.0 or
            initialized_engine.angle_deg != 0.0 or initialized_engine.trace or
            initialized_engine.ledger.get("external_mass_kg") != 0.0 or
            initialized_engine.fuel_combustion_events or
            initialized_engine.fuel_combustion_event is not None):
        raise ValueError("warm initialization did not create a clean new-run state")
    return native, source_inventory, target_inventory


def initialize_from_periodic_run(target_document: dict, source_run: str | Path, *,
                                 expected_source: dict, target_rpm: float,
                                 target_variant_label: str) -> tuple[dict, dict]:
    """Create a new target document whose initial state comes from a periodic run.

    ``expected_source`` must be copied from durable, already accepted evidence;
    self-reported hashes in the source directory are not treated as anchors.
    The returned provenance binds the new run to those source artifacts.
    """
    validate(target_document)
    if set(expected_source) != _EXPECTED_KEYS:
        raise ValueError("periodic source receipt binding fields are incomplete")
    for key in ("manifest_sha256", "checkpoint_sha256", "result_sha256"):
        value = expected_source[key]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError(f"periodic source {key} is not a SHA-256 digest")
    if (not isinstance(expected_source["source_run_id"], str) or
            not expected_source["source_run_id"] or
            not isinstance(expected_source["source_variant_label"], str) or
            expected_source["source_variant_label"] != target_variant_label or
            type(expected_source["source_rpm"]) not in (int, float) or
            not math.isfinite(expected_source["source_rpm"]) or
            expected_source["source_rpm"] <= 0 or
            type(target_rpm) not in (int, float) or not math.isfinite(target_rpm) or
            target_rpm <= 0 or target_rpm == expected_source["source_rpm"]):
        raise ValueError("periodic source/target operating-point identity is invalid")

    run_dir = Path(source_run).expanduser().resolve(strict=True)
    if not run_dir.is_dir():
        raise ValueError("periodic source must be an existing run directory")
    run_manifest_path = run_dir / "run.json"
    result_path = run_dir / "result.json"
    checkpoint_path = run_dir / "checkpoint.json"
    native_path = run_dir / "native-configuration.json"
    if not all(path.is_file() for path in
               (run_manifest_path, result_path, checkpoint_path, native_path)):
        raise ValueError("periodic source run is missing a required bound artifact")
    manifest = _read_json(run_manifest_path)
    result = _read_json(result_path)
    checkpoint = _read_json(checkpoint_path)
    source_native = _read_json(native_path)
    raw_result = result_path.read_bytes()
    raw_checkpoint = checkpoint_path.read_bytes()
    if (hashlib.sha256(raw_result).hexdigest() != expected_source["result_sha256"] or
            manifest.get("result_sha256") != expected_source["result_sha256"]):
        raise ValueError("periodic source result hash mismatch")
    if (hashlib.sha256(raw_checkpoint).hexdigest() != expected_source["checkpoint_sha256"] or
            manifest.get("checkpoint_sha256") != expected_source["checkpoint_sha256"]):
        raise ValueError("periodic source checkpoint hash mismatch")
    if (manifest.get("status") != "COMPLETE" or
            manifest.get("classification") != "PERIODIC_EXPLORATORY" or
            manifest.get("periodicity") != "PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED" or
            result.get("classification") != manifest.get("classification") or
            result.get("periodicity") != manifest.get("periodicity") or
            result.get("status") != "COMPLETE" or
            manifest.get("bindings") != result.get("bindings")):
        raise ValueError("source is not a completed periodic exploratory result")
    bindings = manifest.get("bindings", {})
    if (bindings.get("run_id") != expected_source["source_run_id"] or
            bindings.get("variant_label") != expected_source["source_variant_label"] or
            result.get("preflight", {}).get("rpm") != expected_source["source_rpm"] or
            bindings.get("configuration_sha256") != sha256(source_native)):
        raise ValueError("periodic source run/configuration identity mismatch")
    checkpoint_schema = checkpoint.get("schema")
    checkpoint_binding = checkpoint.get("bindings", {})
    if checkpoint_schema == "DINO_EXPLORATORY_CHECKPOINT_V1":
        checkpoint_binding_valid = checkpoint_binding == bindings
    elif checkpoint_schema == "DINO_MINIMAL_EXPLORATORY_CHECKPOINT_V1":
        checkpoint_binding_valid = (
            checkpoint_binding.get("configuration_file_sha256") == sha256(source_native) and
            checkpoint_binding.get("configuration_canonical_sha256") == sha256(source_native) and
            checkpoint_binding.get("rpm") == expected_source["source_rpm"] and
            checkpoint_binding.get("native_configuration_identity") ==
            checkpoint.get("engine_snapshot", {}).get("configuration_identity"))
    else:
        checkpoint_binding_valid = False
    if (not checkpoint_binding_valid or
            checkpoint.get("next_cycle") != manifest.get("cycles_completed", -1) + 1):
        raise ValueError("periodic source checkpoint chronology/binding mismatch")

    # The receipt's manifest hash is for the final producing invocation, not
    # the wrapper run.json. Bind and verify that exact child manifest too.
    checkpoint_artifact = manifest.get("checkpoint_artifact")
    if (not isinstance(checkpoint_artifact, str) or Path(checkpoint_artifact).is_absolute() or
            ".." in Path(checkpoint_artifact).parts):
        raise ValueError("periodic source checkpoint artifact path is unsafe")
    child_dir = (run_dir / checkpoint_artifact).resolve().parent
    if not child_dir.is_relative_to(run_dir) or not (child_dir / "manifest.json").is_file():
        raise ValueError("periodic source invocation manifest is missing")
    child_manifest = child_dir / "manifest.json"
    if hashlib.sha256(child_manifest.read_bytes()).hexdigest() != expected_source["manifest_sha256"]:
        raise ValueError("periodic source invocation-manifest hash mismatch")
    child_checkpoint = (run_dir / checkpoint_artifact).resolve()
    if (not child_checkpoint.is_relative_to(run_dir) or
            not child_checkpoint.is_file() or
            hashlib.sha256(child_checkpoint.read_bytes()).hexdigest() !=
            expected_source["checkpoint_sha256"]):
        raise ValueError("periodic source invocation-checkpoint hash mismatch")

    source_engine = IntegratedEngine2T.from_configuration_dict(source_native)
    snapshot = checkpoint.get("engine_snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("configuration_identity") != source_engine.configuration_identity:
        raise ValueError("periodic source engine identity does not match its native configuration")
    # Validate the source as an authentic same-run checkpoint before extracting
    # its physical state. This exact restore is only a validation operation.
    source_engine.restore(snapshot)
    if (source_engine.angle_deg != 0.0 or
            not math.isclose(source_engine.crank_angle_unwrapped_deg % 360.0,
                             0.0, rel_tol=0.0, abs_tol=1e-10) or
            source_engine.cycle != manifest.get("cycles_completed") or
            checkpoint.get("next_cycle") != source_engine.cycle + 1):
        raise ValueError("periodic source checkpoint is not at a complete-cycle phase boundary")

    effective_target = resolve_for_operating_point(target_document, rpm=float(target_rpm))
    target_native = deepcopy(effective_target["native_configuration"])
    target_engine = IntegratedEngine2T.from_configuration_dict(target_native)
    source_state = source_engine.state
    target_native, source_inventory, target_inventory = _transfer_state_to_native(
        target_native, source_engine, target_engine, float(target_rpm))

    target_document_out = deepcopy(target_document)
    target_document_out["native_configuration"] = target_native
    target_document_out["native_configuration_sha256"] = sha256(target_native)
    source_state_sha = _state_digest(source_state)
    provenance = {
        "schema": SCHEMA,
        "initializer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_project_id": bindings["project_id"],
        "source_run_id": bindings["run_id"],
        "source_variant_label": bindings["variant_label"],
        "source_rpm": float(expected_source["source_rpm"]),
        "target_rpm": float(target_rpm),
        "source_result_sha256": expected_source["result_sha256"],
        "source_checkpoint_sha256": expected_source["checkpoint_sha256"],
        "source_invocation_manifest_sha256": expected_source["manifest_sha256"],
        "source_state_sha256": source_state_sha,
        "target_configuration_sha256": target_document_out["native_configuration_sha256"],
        "transfer_kind": "NEW_RUN_FROM_PERIODIC_CONSERVED_STATE",
        "reset": ["clock", "ledger", "trace", "combustion_event_history",
                  "periodicity_detector"],
    }
    target_document_out["provenance"]["periodic_state_initialization"] = provenance
    validate(target_document_out)

    if identity(target_document_out) == identity(target_document):
        raise ValueError("warm initialization failed to create a distinct target identity")
    initialized_engine = IntegratedEngine2T.from_configuration_dict(target_native)
    return target_document_out, {
        "provenance": provenance,
        "source_inventory": source_inventory,
        "target_initial_inventory": target_inventory,
        "inventory_equal": source_inventory == target_inventory,
        "source_total_cycle": source_engine.cycle,
        "new_run_start_cycle": initialized_engine.cycle,
        "source_initial_state_sha256": source_engine.configuration_identity[
            "initial_state_sha256"],
        "target_solver_identity_sha256": effective_target["identity_sha256"],
        "warm_run_solver_identity_sha256": resolve_for_operating_point(
            target_document_out, rpm=float(target_rpm))["identity_sha256"],
    }
