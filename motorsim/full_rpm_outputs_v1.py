"""Engineering-output adapter for preflighted FULL_RPM_SWEEP_V1 points."""
from __future__ import annotations

import math
from typing import Any

from .mechanical_loss_binding_v1 import ResolvedMechanicalLossV1


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data, excluding booleans")
    result = float(value)
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _defined(value: float, units: str, source: str) -> dict[str, Any]:
    return {"status": "DEFINED", "value": value, "units": units,
            "reason": None, "definition_version": "FULL_RPM_SWEEP_V1_OUTPUTS",
            "source": source}


def _undefined(reason: str, units: str, source: str) -> dict[str, Any]:
    return {"status": "UNDEFINED", "value": None, "units": units,
            "reason": reason, "definition_version": "FULL_RPM_SWEEP_V1_OUTPUTS",
            "source": source}


def compute_full_rpm_outputs_v1(
    *,
    cylinder_indicated_work_j: float,
    net_piston_gas_work_j: float,
    swept_displacement_m3: float,
    rpm: float,
    air_delivered_kg: float | None,
    fuel_delivered_kg: float,
    stoichiometric_afr: float | None,
    mechanical_loss: ResolvedMechanicalLossV1,
    primary_id: str,
    primary_sha256: str,
    cycle_index: int,
    load: float = 1.0,
) -> dict[str, Any]:
    """Compute 2T outputs only with a resolved explicit loss-model binding."""
    if not isinstance(mechanical_loss, ResolvedMechanicalLossV1):
        raise ValueError("MISSING_EXPLICIT_MECHANICAL_LOSS_MODEL")
    if not isinstance(primary_id, str) or not primary_id.strip():
        raise ValueError("primary_id is required")
    if (not isinstance(primary_sha256, str) or len(primary_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in primary_sha256)):
        raise ValueError("primary_sha256 must be a lowercase SHA-256 digest")
    if type(cycle_index) is not int or cycle_index < 1:
        raise ValueError("cycle_index must be a positive integer")

    indicated_work = _finite(cylinder_indicated_work_j,
                             "cylinder_indicated_work_j")
    net_work = _finite(net_piston_gas_work_j, "net_piston_gas_work_j")
    displacement = _finite(swept_displacement_m3,
                           "swept_displacement_m3")
    speed = _finite(rpm, "rpm")
    fuel = _finite(fuel_delivered_kg, "fuel_delivered_kg", nonnegative=True)
    air = (None if air_delivered_kg is None else
           _finite(air_delivered_kg, "air_delivered_kg", nonnegative=True))
    stoich = (None if stoichiometric_afr is None else
              _finite(stoichiometric_afr, "stoichiometric_afr"))
    if stoich is not None and stoich <= 0.0:
        raise ValueError("stoichiometric_afr must be positive")
    load_value = _finite(load, "load", nonnegative=True)
    if displacement <= 0.0 or speed <= 0.0:
        raise ValueError("swept displacement and RPM must be positive")

    performance = mechanical_loss.model.evaluate_2t_net_piston_work(
        net_piston_gas_work_j=net_work,
        displacement_m3=displacement,
        rpm=speed,
        load=load_value,
    )
    frequency_hz = speed / 60.0  # accepted 2T contract: one 360-degree cycle/rev
    indicated_power = indicated_work * frequency_hz
    indicated_torque = indicated_work / (2.0 * math.pi)
    source = (f"primary:{primary_id};sha256:{primary_sha256};cycle:{cycle_index};"
              f"fixture:{mechanical_loss.fixture_id};"
              f"fixture_sha256:{mechanical_loss.fixture_sha256};"
              f"model:MECHANICAL_LOSS_MODEL_V1;"
              f"model_sha256:{mechanical_loss.model_sha256}")

    outputs = {
        "IMEP": _defined(indicated_work / displacement, "Pa", source),
        "FMEP": _defined(performance["friction_mep_pa"], "Pa", source),
        "BMEP": _defined(performance["brake_mep_pa"], "Pa", source),
        "indicated_power": _defined(indicated_power, "W", source),
        "indicated_torque": _defined(indicated_torque, "N*m", source),
        "brake_power": _defined(performance["brake_power_w"], "W", source),
        "brake_torque": _defined(performance["brake_torque_nm"], "N*m", source),
    }

    if air is None:
        outputs["AFR"] = _undefined("MISSING_AIR_DELIVERY", "kg/kg", source)
        outputs["lambda"] = _undefined("MISSING_AIR_DELIVERY", "1", source)
        outputs["phi"] = _undefined("MISSING_AIR_DELIVERY", "1", source)
    elif fuel <= 0.0:
        outputs["AFR"] = _undefined("ZERO_FUEL_DELIVERY", "kg/kg", source)
        outputs["lambda"] = _undefined("ZERO_FUEL_DELIVERY", "1", source)
        outputs["phi"] = _undefined("ZERO_FUEL_DELIVERY", "1", source)
    else:
        afr = air / fuel
        outputs["AFR"] = _defined(afr, "kg/kg", source)
        if stoich is None:
            outputs["lambda"] = _undefined("MISSING_STOICHIOMETRIC_AFR", "1", source)
            outputs["phi"] = _undefined("MISSING_STOICHIOMETRIC_AFR", "1", source)
        else:
            lam = afr / stoich
            outputs["lambda"] = _defined(lam, "1", source)
            outputs["phi"] = (_defined(1.0 / lam, "1", source)
                               if lam > 0.0 else
                               _undefined("ZERO_LAMBDA", "1", source))

    if fuel <= 0.0:
        outputs["ISFC"] = _undefined("ZERO_FUEL_DELIVERY", "g/kWh", source)
        outputs["BSFC"] = _undefined("ZERO_FUEL_DELIVERY", "g/kWh", source)
    else:
        fuel_metric_numerator = fuel * frequency_hz * 3.6e9
        outputs["ISFC"] = (
            _defined(fuel_metric_numerator / indicated_power, "g/kWh", source)
            if indicated_power > 0.0 else
            _undefined("NONPOSITIVE_INDICATED_POWER", "g/kWh", source))
        brake_power = performance["brake_power_w"]
        outputs["BSFC"] = (
            _defined(fuel_metric_numerator / brake_power, "g/kWh", source)
            if brake_power > 0.0 else
            _undefined("NONPOSITIVE_BRAKE_POWER", "g/kWh", source))

    return {
        "schema": "FULL_RPM_SWEEP_V1_ENGINEERING_OUTPUTS",
        "rpm": speed,
        "cycle_convention": "2T_360_DEG_ONE_CYCLE_PER_REV",
        "swept_displacement_m3": displacement,
        "cylinder_indicated_work_j": indicated_work,
        "net_piston_gas_work_j": net_work,
        "fuel_delivered_kg": fuel,
        "mechanical_loss_provenance": mechanical_loss.provenance,
        "performance": performance,
        "outputs": outputs,
    }
