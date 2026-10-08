"""Stable JSON-ready schema for available 2T engineering outputs."""
from __future__ import annotations

import math
from typing import Any
from urllib.parse import quote, unquote

SCHEMA = "MOTORSIM_ENGINEERING_OUTPUTS_V1"
SCHEMA_V2 = "MOTORSIM_ENGINEERING_OUTPUTS_V2"
SCHEMA_V3 = "MOTORSIM_ENGINEERING_OUTPUTS_V3"
SCHEMA_V4 = "MOTORSIM_ENGINEERING_OUTPUTS_V4"
SCHEMA_V5 = "MOTORSIM_ENGINEERING_OUTPUTS_V5"
DEPENDENCIES = {"INDEPENDENT_OF_P4", "CONDITIONAL_ON_P4", "REVALIDATED_ON_P4_PASS"}
CHANNEL_UNITS = {
    "cylinder_pressure_pa": "Pa", "crankcase_pressure_pa": "Pa",
    "cylinder_temperature_k": "K", "crankcase_temperature_k": "K",
    "cylinder_mass_kg": "kg", "fresh_air_mass_kg": "kg", "fuel_mass_kg": "kg",
    "residual_mass_kg": "kg", "burned_mass_kg": "kg",
    "cylinder_volume_m3": "m^3", "crankcase_volume_m3": "m^3",
    "intake_port_area_m2": "m^2", "transfer_port_area_m2": "m^2",
    "exhaust_port_area_m2": "m^2", "intake_mass_flow_kg_s": "kg/s",
    "transfer_mass_flow_kg_s": "kg/s", "exhaust_mass_flow_kg_s": "kg/s",
    "intake_pressure_pa": "Pa", "transfer_pressure_pa": "Pa",
    "exhaust_pressure_pa": "Pa", "intake_mach": "1", "transfer_mach": "1",
    "exhaust_mach": "1", "combustion_fraction": "1",
    "heat_release_w": "W", "wall_heat_transfer_w": "W",
    "duct_temperature_k": "K", "duct_pressure_pa": "Pa",
    "duct_mass_flow_kg_s": "kg/s", "duct_mach": "1",
}
METRIC_UNITS = {
    "indicated_work_j": "J", "gross_work_j": "J", "net_work_j": "J",
    "indicated_power_w": "W", "brake_power_w": "W",
    "indicated_torque_nm": "N*m", "brake_torque_nm": "N*m",
    "imep_pa": "Pa", "bmep_pa": "Pa", "fmep_pa": "Pa",
    "delivery_ratio": "1", "trapping_efficiency": "1",
    "scavenging_efficiency": "1", "charging_efficiency": "1",
    "trapping_ratio": "1", "residual_fraction": "1",
    "purity_at_transfer_close": "1", "purity_at_exhaust_close": "1",
    "short_circuit_fraction": "1", "fresh_delivery_kg": "kg",
    "fresh_retained_kg": "kg", "fresh_short_circuit_kg": "kg",
    "fresh_lost_kg": "kg", "peak_pressure_pa": "Pa",
    "angle_of_peak_pressure_deg": "degCA", "afr": "1",
    "equivalence_ratio": "1", "fuel_flow_kg_s": "kg/s",
    "fuel_delivered_per_cycle_kg": "kg",
    "fresh_air_intake_delivered_per_cycle_kg": "kg",
    "fuel_short_circuited_per_cycle_kg": "kg",
    "fuel_consumed_by_p7_per_cycle_kg": "kg",
    "fuel_unburned_terminal_global_kg": "kg",
    "cylinder_fuel_species_at_exhaust_close_kg": "kg",
    "fuel_species_balance_residual_kg": "kg",
    "isfc_g_kwh": "g/kWh", "bsfc_g_kwh": "g/kWh",
    "wall_heat_loss_j": "J", "energy_balance_residual_j": "J",
    "ca10_deg": "degCA", "ca50_deg": "degCA", "ca90_deg": "degCA",
}
METRIC_UNITS_V2 = {**METRIC_UNITS, "brake_work_j": "J"}
METRIC_UNITS_V3 = {
    **METRIC_UNITS_V2,
    "gross_fresh_charge_delivery_kg": "kg",
    "gross_fresh_charge_short_circuit_kg": "kg",
    "gross_intake_air_fuel_ratio": "1",
    "p7_fuel_consumption_flow_kg_s": "kg/s",
}
METRIC_UNITS_V4 = {
    **METRIC_UNITS_V3,
    "cylinder_fuel_species_at_last_port_close_kg": "kg",
    "cylinder_fresh_air_species_at_last_port_close_kg": "kg",
    "fresh_air_fuel_species_ratio_at_last_port_close": "1",
}
METRIC_UNITS_V5 = {
    **METRIC_UNITS_V4,
    "cylinder_indicated_work_j": "J",
    "crankcase_gas_work_j": "J",
    "net_piston_gas_work_j": "J",
    "net_piston_mep_pa": "Pa",
    "trapped_air_kg": "kg",
    "trapped_fuel_kg": "kg",
    "fuel_burned_per_cycle_kg": "kg",
    "fuel_unburned_at_ignition_snapshot_kg": "kg",
}
PERIODIC_METRICS_V5 = frozenset({
    "indicated_power_w", "indicated_torque_nm", "imep_pa",
    "brake_work_j", "brake_power_w", "brake_torque_nm", "bmep_pa", "fmep_pa",
    "isfc_g_kwh", "bsfc_g_kwh", "net_piston_mep_pa",
})


def _metric_unit(name: str, schema: str) -> str | None:
    return {SCHEMA: METRIC_UNITS, SCHEMA_V2: METRIC_UNITS_V2,
            SCHEMA_V3: METRIC_UNITS_V3, SCHEMA_V4: METRIC_UNITS_V4,
            SCHEMA_V5: METRIC_UNITS_V5}[schema].get(name)


def _integrated_channel_unit(name: str) -> str | None:
    """Resolve integrated V2 fixed channels and path-addressed duct channels."""
    if name in CHANNEL_UNITS:
        return CHANNEL_UNITS[name]
    if name == "crankcase_mass_kg":
        return "kg"
    parts = name.split(":") if isinstance(name, str) else ()
    if len(parts) == 3 and parts[0] == "network" and parts[1]:
        try:
            volume_id = unquote(parts[1])
            if quote(volume_id, safe="") != parts[1]:
                return None
        except (ValueError, TypeError):
            return None
        return {"mass_kg": "kg", "pressure_pa": "Pa", "temperature_k": "K",
                "fresh_air_mass_kg": "kg", "fuel_mass_kg": "kg",
                "residual_mass_kg": "kg", "burned_mass_kg": "kg"}.get(parts[2])
    if len(parts) == 3 and parts[0] == "reed" and parts[1]:
        try:
            reed_id = unquote(parts[1])
            if quote(reed_id, safe="") != parts[1]:
                return None
        except (ValueError, TypeError):
            return None
        return {"position_m": "m", "velocity_m_s": "m/s",
                "mechanical_energy_j": "J", "dissipation_j": "J"}.get(parts[2])
    if len(parts) != 5 or parts[0] != "duct" or not parts[1]:
        return None
    try:
        duct_id = unquote(parts[1])
        if quote(duct_id, safe="") != parts[1]:
            return None
        index = int(parts[3])
        if index < 0 or str(index) != parts[3]:
            return None
    except (ValueError, TypeError):
        return None
    if parts[2] == "cell":
        return {"pressure_pa": "Pa", "temperature_k": "K", "mach": "1",
                "fresh_air_mass_kg": "kg", "fuel_mass_kg": "kg",
                "residual_mass_kg": "kg", "burned_mass_kg": "kg"}.get(parts[4])
    if parts[2] == "face" and parts[4] == "mass_flow_kg_s":
        return "kg/s"
    return None


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    return float(value)


def _build_engineering_output(*, rpm: float, cycle_number: int,
                              angles_deg: tuple[float, ...],
                              channels: dict[str, dict[str, Any]],
                              cycle_metrics: dict[str, dict[str, Any]],
                              dependency_status: str,
                              cycle_period_deg: float,
                              schema: str,
                              configuration_sha256: str | None = None,
                              periodicity_status: str = "NOT_EVALUATED") -> dict[str, Any]:
    speed = _finite(rpm, "rpm")
    period = _finite(cycle_period_deg, "cycle_period_deg")
    if speed <= 0 or period != 360.0:
        raise ValueError("This output contract requires positive RPM and a 360-degree 2T cycle")
    if type(cycle_number) is not int or cycle_number < 1:
        raise ValueError("cycle_number must be a positive integer")
    if dependency_status not in DEPENDENCIES:
        raise ValueError("dependency_status must be explicit")
    if not isinstance(angles_deg, tuple) or len(angles_deg) < 2:
        raise ValueError("A crank-angle trace requires at least two samples")
    angles = tuple(_finite(value, "angle_deg") for value in angles_deg)
    if any(right <= left for left, right in zip(angles, angles[1:])):
        raise ValueError("Crank-angle samples must increase strictly")
    if not math.isclose(angles[-1] - angles[0], period, rel_tol=0, abs_tol=16*math.ulp(period)):
        raise ValueError("Crank-angle trace must span one complete 2T cycle")
    if not isinstance(channels, dict) or not isinstance(cycle_metrics, dict):
        raise ValueError("Channels and cycle metrics must be mappings")

    trace = {}
    for name, record in channels.items():
        unit = (CHANNEL_UNITS.get(name) if schema == SCHEMA else
                _integrated_channel_unit(name))
        if unit is None or not isinstance(record, dict) or set(record) != {"values", "source"}:
            raise ValueError(f"Unsupported or malformed crank-angle channel: {name}")
        values = record["values"]
        if not isinstance(values, (tuple, list)) or len(values) != len(angles):
            raise ValueError(f"Channel {name} sample count does not match angle trace")
        source = record["source"]
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Channel {name} requires source provenance")
        trace[name] = {"unit": unit, "source": source,
                       "values": [_finite(value, name) for value in values]}

    metrics = {}
    for name, record in cycle_metrics.items():
        unit = _metric_unit(name, schema)
        allowed_record_keys = ({"value", "status", "reason", "source", "provenance",
                                "periodicity_dependency", "definition_version"}
                               if schema == SCHEMA_V5 else
                               {"value", "status", "reason", "source"})
        if unit is None or not isinstance(record, dict) or set(record) != allowed_record_keys:
            raise ValueError(f"Unsupported or malformed cycle metric: {name}")
        status, value, reason, source = (record[key] for key in ("status", "value", "reason", "source"))
        if schema == SCHEMA_V5:
            required = {"value", "status", "reason", "source", "provenance",
                        "periodicity_dependency", "definition_version"}
            if set(record) != required:
                raise ValueError(f"V5 metric {name} lacks explicit provenance/dependency metadata")
            if record["provenance"] not in {
                    "DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
                    "SYNTHETIC_ASSUMPTION", "UNKNOWN"}:
                raise ValueError(f"V5 metric {name} provenance is invalid")
            if record["periodicity_dependency"] not in {"REQUIRED", "NOT_REQUIRED"}:
                raise ValueError(f"V5 metric {name} periodicity dependency is invalid")
            expected_dependency = "REQUIRED" if name in PERIODIC_METRICS_V5 else "NOT_REQUIRED"
            if record["periodicity_dependency"] != expected_dependency:
                raise ValueError(f"V5 metric {name} has an invalid periodicity dependency")
            if not isinstance(record["definition_version"], str) or not record["definition_version"].strip():
                raise ValueError(f"V5 metric {name} definition version is required")
            if (record["periodicity_dependency"] == "REQUIRED" and
                    periodicity_status != "PERIOD_1" and status == "DEFINED"):
                # V5 metrics describe one 360-degree cycle.  A period-2
                # classification needs a separately defined two-cycle
                # aggregate; V5 has no binding for such an aggregate.
                raise ValueError(
                    f"V5 metric {name} requires an accepted period-1 cycle")
        if not isinstance(source, str) or not source.strip():
            raise ValueError(f"Metric {name} requires source provenance")
        if status == "DEFINED":
            value = _finite(value, name)
            if reason is not None:
                raise ValueError(f"Defined metric {name} cannot have an undefined reason")
            if schema == SCHEMA_V5:
                if record["provenance"] == "UNKNOWN":
                    raise ValueError(f"V5 metric {name} cannot be DEFINED with UNKNOWN provenance")
                if name in {"afr", "bsfc_g_kwh"} and value <= 0.0:
                    raise ValueError(f"V5 metric {name} must be positive")
                if name in {"trapping_efficiency", "scavenging_efficiency",
                            "charging_efficiency", "residual_fraction",
                            "purity_at_transfer_close", "purity_at_exhaust_close",
                            "short_circuit_fraction"} and not 0.0 <= value <= 1.0:
                    raise ValueError(f"V5 metric {name} is outside [0,1]")
        elif status == "UNDEFINED":
            if value is not None or not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"Undefined metric {name} requires null value and reason")
        else:
            raise ValueError(f"Metric {name} status must be DEFINED or UNDEFINED")
        metrics[name] = {"value": value, "unit": unit,
                         "status": status, "reason": reason, "source": source}
        if schema == SCHEMA_V5:
            metrics[name].update({key: record[key] for key in (
                "provenance", "periodicity_dependency", "definition_version")})

    output = {"schema": schema,
              "operating_point": {"cycle_convention": "2T_360_DEG_ONE_CYCLE_PER_REV",
                                  "rpm": speed, "cycle_number": cycle_number,
                                  "dependency_status": dependency_status},
              "crank_angle_trace": {"angle_deg": list(angles), "channels": trace},
              "cycle_metrics": metrics,
              "claims": {"periodicity": periodicity_status if schema == SCHEMA_V5 else "NOT_EVALUATED",
                         "experimental_validation": "NOT_PERFORMED",
                         "predictive_validation": "NOT_CLAIMED"}}
    if schema in (SCHEMA_V2, SCHEMA_V3, SCHEMA_V4, SCHEMA_V5):
        if (not isinstance(configuration_sha256, str) or
                len(configuration_sha256) != 64 or
                any(ch not in "0123456789abcdef" for ch in configuration_sha256)):
            raise ValueError("V2 integrated output requires a lowercase configuration SHA-256")
        output["configuration_sha256"] = configuration_sha256
    return output


def build_engineering_output(*, rpm: float, cycle_number: int,
                             angles_deg: tuple[float, ...],
                             channels: dict[str, dict[str, Any]],
                             cycle_metrics: dict[str, dict[str, Any]],
                             dependency_status: str,
                             cycle_period_deg: float = 360.0) -> dict[str, Any]:
    """Build the unchanged fixed-channel engineering-output V1 record."""
    return _build_engineering_output(
        rpm=rpm, cycle_number=cycle_number, angles_deg=angles_deg,
        channels=channels, cycle_metrics=cycle_metrics,
        dependency_status=dependency_status, cycle_period_deg=cycle_period_deg,
        schema=SCHEMA)


def build_integrated_engineering_output_v2(*, rpm: float, cycle_number: int,
                                           angles_deg: tuple[float, ...],
                                           channels: dict[str, dict[str, Any]],
                                           cycle_metrics: dict[str, dict[str, Any]],
                                           dependency_status: str,
                                           configuration_sha256: str,
                                           cycle_period_deg: float = 360.0) -> dict[str, Any]:
    """Build path-addressed integrated output without changing the V1 contract."""
    return _build_engineering_output(
        rpm=rpm, cycle_number=cycle_number, angles_deg=angles_deg,
        channels=channels, cycle_metrics=cycle_metrics,
        dependency_status=dependency_status, cycle_period_deg=cycle_period_deg,
        schema=SCHEMA_V2, configuration_sha256=configuration_sha256)


def build_integrated_engineering_output_v3(*, rpm: float, cycle_number: int,
                                           angles_deg: tuple[float, ...],
                                           channels: dict[str, dict[str, Any]],
                                           cycle_metrics: dict[str, dict[str, Any]],
                                           dependency_status: str,
                                           configuration_sha256: str,
                                           cycle_period_deg: float = 360.0) -> dict[str, Any]:
    """Build integrated output with explicit gross-delivery/fuel-consumption names."""
    return _build_engineering_output(
        rpm=rpm, cycle_number=cycle_number, angles_deg=angles_deg,
        channels=channels, cycle_metrics=cycle_metrics,
        dependency_status=dependency_status, cycle_period_deg=cycle_period_deg,
        schema=SCHEMA_V3, configuration_sha256=configuration_sha256)


def build_integrated_engineering_output_v4(*, rpm: float, cycle_number: int,
                                           angles_deg: tuple[float, ...],
                                           channels: dict[str, dict[str, Any]],
                                           cycle_metrics: dict[str, dict[str, Any]],
                                           dependency_status: str,
                                           configuration_sha256: str,
                                           cycle_period_deg: float = 360.0) -> dict[str, Any]:
    """V4 adds event-specific cylinder species at the last port closure."""
    return _build_engineering_output(
        rpm=rpm, cycle_number=cycle_number, angles_deg=angles_deg,
        channels=channels, cycle_metrics=cycle_metrics,
        dependency_status=dependency_status, cycle_period_deg=cycle_period_deg,
        schema=SCHEMA_V4, configuration_sha256=configuration_sha256)


def build_integrated_engineering_output_v5(*, rpm: float, cycle_number: int,
                                           angles_deg: tuple[float, ...],
                                           channels: dict[str, dict[str, Any]],
                                           cycle_metrics: dict[str, dict[str, Any]],
                                           dependency_status: str,
                                           configuration_sha256: str,
                                           periodicity_status: str = "NOT_EVALUATED",
                                           cycle_period_deg: float = 360.0) -> dict[str, Any]:
    """V5 carries metric definition, provenance and periodicity dependency."""
    if periodicity_status not in {
            "NOT_EVALUATED", "PERIOD_1", "PERIOD_2", "NO_CONVERGENCE", "INVALID"}:
        raise ValueError("V5 periodicity status is invalid")
    return _build_engineering_output(
        rpm=rpm, cycle_number=cycle_number, angles_deg=angles_deg,
        channels=channels, cycle_metrics=cycle_metrics,
        dependency_status=dependency_status, cycle_period_deg=cycle_period_deg,
        schema=SCHEMA_V5, configuration_sha256=configuration_sha256,
        periodicity_status=periodicity_status)


def _validate_engineering_output(value: Any, schema: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != schema:
        raise ValueError("Engineering output schema is invalid")
    if schema in (SCHEMA_V2, SCHEMA_V3, SCHEMA_V4, SCHEMA_V5):
        config_hash = value.get("configuration_sha256")
        if (not isinstance(config_hash, str) or len(config_hash) != 64 or
                any(ch not in "0123456789abcdef" for ch in config_hash)):
            raise ValueError("Integrated output configuration hash is invalid")
    op = value.get("operating_point")
    trace = value.get("crank_angle_trace")
    if (not isinstance(op, dict) or set(op) != {"cycle_convention", "rpm", "cycle_number",
                                                "dependency_status"}
            or op["cycle_convention"] != "2T_360_DEG_ONE_CYCLE_PER_REV"
            or not isinstance(trace, dict) or set(trace) != {"angle_deg", "channels"}
            or not isinstance(trace["channels"], dict)):
        raise ValueError("Engineering output sections are missing")
    claims = value.get("claims")
    if (not isinstance(claims, dict) or claims != {
                  "periodicity": claims.get("periodicity"),
                  "experimental_validation": "NOT_PERFORMED",
                  "predictive_validation": "NOT_CLAIMED"} or
            (schema != SCHEMA_V5 and claims["periodicity"] != "NOT_EVALUATED") or
            (schema == SCHEMA_V5 and claims["periodicity"] not in {
                "NOT_EVALUATED", "PERIOD_1", "PERIOD_2", "NO_CONVERGENCE", "INVALID"})):
        raise ValueError("Engineering output claim controls were altered")
    metrics = value.get("cycle_metrics")
    if not isinstance(metrics, dict):
        raise ValueError("Engineering output metrics are malformed")
    for name, row in trace["channels"].items():
        unit = (CHANNEL_UNITS.get(name) if schema == SCHEMA else
                _integrated_channel_unit(name))
        if not isinstance(row, dict) or row.get("unit") != unit:
            raise ValueError(f"Channel {name} unit does not match schema")
    for name, row in metrics.items():
        if not isinstance(row, dict) or row.get("unit") != _metric_unit(name, schema):
            raise ValueError(f"Metric {name} unit does not match schema")
    args = dict(
        rpm=op.get("rpm"), cycle_number=op.get("cycle_number"),
        angles_deg=tuple(trace.get("angle_deg", ())), channels={
            name: {"values": row.get("values"), "source": row.get("source")}
            for name, row in trace.get("channels", {}).items()},
        cycle_metrics={name: {key: row.get(key) for key in
                              (("value", "status", "reason", "source", "provenance",
                                "periodicity_dependency", "definition_version")
                               if schema == SCHEMA_V5 else
                               ("value", "status", "reason", "source"))}
                       for name, row in metrics.items()},
        dependency_status=op.get("dependency_status"),
        cycle_period_deg=360.0)
    if schema == SCHEMA:
        return build_engineering_output(**args)
    if schema == SCHEMA_V2:
        return build_integrated_engineering_output_v2(
            **args, configuration_sha256=value["configuration_sha256"])
    if schema == SCHEMA_V3:
        return build_integrated_engineering_output_v3(
            **args, configuration_sha256=value["configuration_sha256"])
    if schema == SCHEMA_V5:
        return build_integrated_engineering_output_v5(
            **args, configuration_sha256=value["configuration_sha256"],
            periodicity_status=claims["periodicity"])
    return build_integrated_engineering_output_v4(
        **args, configuration_sha256=value["configuration_sha256"])


def validate_engineering_output(value: Any) -> dict[str, Any]:
    """Validate only the frozen, fixed-channel V1 output contract."""
    return _validate_engineering_output(value, SCHEMA)


def validate_integrated_engineering_output_v2(value: Any) -> dict[str, Any]:
    """Validate strict path-addressed V2 output and configuration identity."""
    return _validate_engineering_output(value, SCHEMA_V2)


def validate_integrated_engineering_output_v3(value: Any) -> dict[str, Any]:
    """Validate explicit V3 fuel and gross-flow semantics."""
    return _validate_engineering_output(value, SCHEMA_V3)


def validate_integrated_engineering_output_v4(value: Any) -> dict[str, Any]:
    """Validate event-specific cylinder species output and V3 semantics."""
    return _validate_engineering_output(value, SCHEMA_V4)


def validate_integrated_engineering_output_v5(value: Any) -> dict[str, Any]:
    """Validate explicit metric provenance and periodicity-dependent outputs."""
    return _validate_engineering_output(value, SCHEMA_V5)
