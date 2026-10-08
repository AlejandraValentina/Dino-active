"""Explicit JSON checkpoint/restart and deterministic-state comparison."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import fields, is_dataclass

from ..gas1d.mesh import Mesh
from ..p5b import Chamber, DuctCell, _FinitePath
from .evidence import canonical_bytes, configuration_hash

_TYPES = {"Mesh": Mesh, "Chamber": Chamber, "DuctCell": DuctCell,
          "_FinitePath": _FinitePath}


def _encode(value):
    if value is None or type(value) in (str, bool, int, float):
        return value
    if isinstance(value, tuple):
        return {"__tuple__": [_encode(x) for x in value]}
    if isinstance(value, list):
        return [_encode(x) for x in value]
    if isinstance(value, dict):
        return {str(key): _encode(item) for key, item in value.items()}
    name = type(value).__name__
    if name in _TYPES:
        attrs = ({field.name: getattr(value, field.name) for field in fields(value)}
                 if is_dataclass(value) else value.__dict__)
        return {"__object__": name, "attributes": _encode(attrs)}
    raise TypeError(f"unsupported checkpoint object {name}")


def _decode(value):
    if isinstance(value, list):
        return [_decode(x) for x in value]
    if isinstance(value, dict):
        if set(value) == {"__tuple__"}:
            return tuple(_decode(x) for x in value["__tuple__"])
        if set(value) == {"__object__", "attributes"}:
            name = value["__object__"]
            if name not in _TYPES:
                raise ValueError("checkpoint contains an unapproved object type")
            attrs = _decode(value["attributes"])
            cls = _TYPES[name]
            if name == "Mesh":
                return cls(**attrs)
            result = cls.__new__(cls)
            result.__dict__.update(attrs)
            return result
        return {key: _decode(item) for key, item in value.items()}
    return value


def _p5_aux(system):
    gas = system.gas
    core = gas.core
    return {"gas_ledger": gas.ledger, "gas_history": gas.history,
            "gas_initial": gas._initial, "gas_previous": gas._previous_totals,
            "gas_last_external": gas._last_external,
            "gas_external_cumulative": gas._external_cumulative,
            "core_ledger": core.ledger, "core_history": core.history,
            "core_initial": core._initial, "core_previous": core._previous_totals,
            "core_applied": core._applied, "core_accepted_updates": core._accepted_updates,
            "verification_trace": system.verification_trace,
            "external_flux_trace": system.external_flux_trace}


def _restore_aux(system, aux):
    gas, core = system.gas, system.gas.core
    gas.ledger = aux["gas_ledger"]
    gas.history = aux["gas_history"]
    gas._initial = aux["gas_initial"]
    gas._previous_totals = aux["gas_previous"]
    gas._last_external = aux["gas_last_external"]
    gas._external_cumulative = aux["gas_external_cumulative"]
    core.ledger = aux["core_ledger"]
    core.history = aux["core_history"]
    core._initial = aux["core_initial"]
    core._previous_totals = aux["core_previous"]
    core._applied = aux["core_applied"]
    core._accepted_updates = aux["core_accepted_updates"]
    system.verification_trace = aux["verification_trace"]
    system.external_flux_trace = aux["external_flux_trace"]


def checkpoint_payload(system, detector, config, *, cycle_index, elapsed_time_s):
    value = {"schema": "REFERENCE_ENGINE_CHECKPOINT_V1",
             "configuration_hash": configuration_hash(config),
             "cycle_index": cycle_index, "elapsed_time_s": elapsed_time_s,
             "p6_snapshot": system.snapshot(), "p5_auxiliary": _p5_aux(system),
             "detector": detector.snapshot()}
    encoded = _encode(value)
    serialized = json.dumps(encoded, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
    return {"payload": encoded, "payload_sha256": hashlib.sha256(serialized).hexdigest()}


def restore_checkpoint(system, detector, checkpoint, config):
    encoded = checkpoint["payload"]
    serialized = json.dumps(encoded, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
    if hashlib.sha256(serialized).hexdigest() != checkpoint.get("payload_sha256"):
        raise ValueError("checkpoint payload hash mismatch")
    value = _decode(encoded)
    if value.get("schema") != "REFERENCE_ENGINE_CHECKPOINT_V1":
        raise ValueError("checkpoint schema mismatch")
    if value.get("configuration_hash") != configuration_hash(config):
        raise ValueError("checkpoint configuration mismatch")
    system.restore(value["p6_snapshot"])
    _restore_aux(system, value["p5_auxiliary"])
    detector.restore(value["detector"])
    return {"cycle_index": value["cycle_index"],
            "elapsed_time_s": value["elapsed_time_s"]}


def exact_restart_replay_equal(left, right):
    """Compare full decoded terminal state and persistent ledgers, not digests."""
    return canonical_bytes(_encode(left)) == canonical_bytes(_encode(right))


def replay_comparison(system_a, system_b):
    left = {"state": system_a.gas._state(), "species": system_a.species_mass,
            "gas_ledger": system_a.gas.ledger,
            "external": system_a._external, "fresh_delivery": system_a.fresh_delivered,
            "short_circuit": system_a.fresh_short_circuit,
            "p7_source_delta": system_a.p7_source_delta}
    right = {"state": system_b.gas._state(), "species": system_b.species_mass,
             "gas_ledger": system_b.gas.ledger,
             "external": system_b._external, "fresh_delivery": system_b.fresh_delivered,
             "short_circuit": system_b.fresh_short_circuit,
             "p7_source_delta": system_b.p7_source_delta}
    return {"passed": exact_restart_replay_equal(left, right),
            "left": _encode(left), "right": _encode(right)}
