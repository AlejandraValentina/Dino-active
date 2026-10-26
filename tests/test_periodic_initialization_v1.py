import json
from copy import deepcopy
from pathlib import Path

import pytest

from motorsim.engine_configuration import resolve_for_operating_point
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.periodic_initialization_v1 import (
    _transfer_state_to_native, _without_operating_rpm,
)


ROOT = Path(__file__).resolve().parents[1]


def _engine_document():
    project = json.loads((ROOT / "configs/reference_cases/functional_reed_125cc_v1.dino.json")
                         .read_text(encoding="utf-8"))
    return project["base_engine"]


def test_transfer_preserves_conservative_inventory_and_uses_target_rpm():
    document = _engine_document()
    source_native = resolve_for_operating_point(document, rpm=9000)["native_configuration"]
    target_native = resolve_for_operating_point(document, rpm=9100)["native_configuration"]
    source = IntegratedEngine2T.from_configuration_dict(source_native)
    target = IntegratedEngine2T.from_configuration_dict(target_native)

    transferred, source_inventory, target_inventory = _transfer_state_to_native(
        target_native, source, target, 9100.0)
    initialized = IntegratedEngine2T.from_configuration_dict(transferred)

    assert source_inventory == target_inventory
    assert initialized.inventory() == source_inventory
    assert initialized.reference_rpm == 9100.0
    assert initialized.cycle == 0
    assert initialized.crank_angle_unwrapped_deg == 0.0
    assert initialized.time_s == 0.0
    assert initialized.ledger["external_mass_kg"] == 0.0
    assert initialized.trace == []


def test_transfer_rejects_non_rpm_configuration_change():
    document = _engine_document()
    source_native = resolve_for_operating_point(document, rpm=9000)["native_configuration"]
    target_native = deepcopy(resolve_for_operating_point(document, rpm=9100)["native_configuration"])
    target_native["max_cfl"] = 0.3
    # Configuration identity construction is sufficient to exercise the
    # transfer compatibility guard; no solver steps or result files are used.
    source = IntegratedEngine2T.from_configuration_dict(source_native)
    target = IntegratedEngine2T.from_configuration_dict(target_native)

    with pytest.raises(ValueError, match="differ beyond RPM"):
        _transfer_state_to_native(target_native, source, target, 9100.0)


def test_transfer_rejects_an_unrelated_power_valve_map_change():
    document = _engine_document()
    source_native = resolve_for_operating_point(document, rpm=9000)["native_configuration"]
    target_native = deepcopy(resolve_for_operating_point(document, rpm=9100)["native_configuration"])
    target_native["port_binding"]["powervalve"]["position"][0] = 0.9
    source = IntegratedEngine2T.from_configuration_dict(source_native)
    target = IntegratedEngine2T.from_configuration_dict(target_native)

    with pytest.raises(ValueError, match="power-valve change"):
        _transfer_state_to_native(target_native, source, target, 9100.0)


def test_compatibility_normalization_keeps_every_non_rpm_identity_field():
    document = _engine_document()
    source = IntegratedEngine2T.from_configuration_dict(
        resolve_for_operating_point(document, rpm=9000)["native_configuration"])
    target = IntegratedEngine2T.from_configuration_dict(
        resolve_for_operating_point(document, rpm=9100)["native_configuration"])
    assert _without_operating_rpm(source.configuration_identity) == \
        _without_operating_rpm(target.configuration_identity)
    altered = deepcopy(target.configuration_identity)
    altered["eos"]["gamma"] += 0.001
    assert _without_operating_rpm(source.configuration_identity) != \
        _without_operating_rpm(altered)
