"""Scavenging diagnostics derived from P6 four-species masses and ledgers.

No transport or thermodynamic state is changed here. A zero ratio denominator
is represented explicitly as undefined rather than as a fabricated zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import fsum, inf, isfinite, pi
from typing import Any

SPECIES = ("fresh_air", "fuel", "residual", "burned")


def _number(value: Any, label: str, *, nonnegative=True) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label}: se requiere número, sin booleanos ni texto.")
    try:
        finite = isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{label}: debe ser finito.")
    result = float(value)
    if nonnegative and result < 0.0:
        raise ValueError(f"{label}: no puede ser negativo.")
    if not isfinite(result):
        raise ValueError(f"{label}: fuera de rango.")
    return result


def reference_charge_mass(bore_mm: float, stroke_mm: float,
                          ambient_pressure_pa: float,
                          ambient_temperature_k: float,
                          gas_constant_j_kgk: float = 287.0) -> float:
    """Ambient fresh-air mass in swept volume for one cylinder, in kg."""
    bore = _number(bore_mm, "bore_mm") * 1e-3
    stroke = _number(stroke_mm, "stroke_mm") * 1e-3
    pressure = _number(ambient_pressure_pa, "ambient_pressure_pa")
    temperature = _number(ambient_temperature_k, "ambient_temperature_k")
    gas_constant = _number(gas_constant_j_kgk, "gas_constant_j_kgk")
    if min(bore, stroke, pressure, temperature, gas_constant) <= 0.0:
        raise ValueError("La geometría y el estado ambiente deben ser positivos.")
    volume = pi * bore * bore * stroke / 4.0
    result = pressure * volume / (gas_constant * temperature)
    return _number(result, "reference_charge_mass_kg")


def _species_mass(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        raise ValueError(f"{label}: se requieren cuatro masas P6 en orden {SPECIES}.")
    result = tuple(_number(item, f"{label}.{name}")
                   for name, item in zip(SPECIES, value))
    try:
        total = fsum(result)
    except OverflowError as exc:
        raise ValueError(f"{label}: masa total fuera de rango.") from exc
    if not isfinite(total):
        raise ValueError(f"{label}: masa total fuera de rango.")
    return result


@dataclass(frozen=True)
class RatioResult:
    value: float | None
    status: str
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "status": self.status, "reason": self.reason}


def _ratio(numerator: float, denominator: float) -> RatioResult:
    if denominator == 0.0:
        return RatioResult(None, "UNDEFINED", "ZERO_DENOMINATOR")
    value = numerator / denominator
    if not isfinite(value):
        raise ValueError("El cociente calculado está fuera de rango numérico.")
    return RatioResult(value, "AVAILABLE")


@dataclass(frozen=True)
class ScavengingInput:
    reference_mass_kg: float
    fresh_delivered_kg: float
    fresh_short_circuit_kg: float
    species_at_transfer_close_kg: tuple[float, float, float, float]
    species_at_exhaust_close_kg: tuple[float, float, float, float]


def calculate_scavenging_metrics(inputs: ScavengingInput) -> dict[str, Any]:
    """Calculate cycle metrics from authoritative masses and P6 ledgers.

    `species_at_transfer_close_kg` is sampled after the last transfer closes;
    `species_at_exhaust_close_kg` is sampled after the last exhaust aperture
    closes. `fresh_delivered_kg` is the gross positive fresh-air-plus-fuel
    flow across transfer outlets; repeated crossings are not deduplicated.
    `fresh_short_circuit_kg` is gross positive fresh species flow outward
    across the exhaust while transfer and exhaust are open. Reverse exhaust
    flow is excluded. Neither value is a unique-molecule or net-mass count.
    """
    reference = _number(inputs.reference_mass_kg, "reference_mass_kg")
    delivered = _number(inputs.fresh_delivered_kg, "fresh_delivered_kg")
    lost = _number(inputs.fresh_short_circuit_kg, "fresh_short_circuit_kg")
    transfer = _species_mass(inputs.species_at_transfer_close_kg,
                             "species_at_transfer_close_kg")
    exhaust = _species_mass(inputs.species_at_exhaust_close_kg,
                            "species_at_exhaust_close_kg")
    transfer_total = fsum(transfer)
    exhaust_total = fsum(exhaust)
    transfer_fresh = fsum(transfer[:2])
    exhaust_fresh = fsum(exhaust[:2])
    retained = exhaust_fresh

    metrics = {
        "delivery_ratio": _ratio(delivered, reference),
        "trapping_efficiency": _ratio(retained, delivered),
        "scavenging_efficiency": _ratio(retained, exhaust_total),
        "charging_efficiency": _ratio(retained, reference),
        "trapping_ratio": _ratio(delivered, retained),
        "residual_fraction": _ratio(exhaust[2], exhaust_total),
        "purity_at_transfer_close": _ratio(transfer_fresh, transfer_total),
        "purity_at_exhaust_close": _ratio(exhaust_fresh, exhaust_total),
        "short_circuit_fraction": _ratio(lost, delivered),
    }
    return {
        "schema": "MOTORSIM_2T_SCAVENGING_METRICS_V1",
        "basis": "P6 four-species inventories and gross crossing ledgers",
        "flow_semantics": {
            "fresh_delivered": "gross positive fresh_air + fuel across transfer outlets; recrossings counted",
            "fresh_short_circuit": "gross outward fresh_air + fuel across exhaust while transfer and exhaust are open; reverse flow excluded",
            "net_unique_fresh_mass": "NOT_AVAILABLE",
        },
        "species_order": list(SPECIES),
        "masses_kg": {"reference": reference, "fresh_delivered": delivered,
                      "fresh_retained": retained, "fresh_lost": lost,
                      "transfer_close_total": transfer_total,
                      "exhaust_close_total": exhaust_total,
                      "transfer_close_fresh": transfer_fresh,
                      "exhaust_close_fresh": exhaust_fresh,
                      "exhaust_close_residual": exhaust[2]},
        "ratios": {name: value.to_dict() for name, value in metrics.items()},
        "formulae": {
            "delivery_ratio": "gross_fresh_delivered / reference_mass",
            "trapping_efficiency": "fresh_retained / fresh_delivered",
            "scavenging_efficiency": "fresh_retained / exhaust_close_total",
            "charging_efficiency": "fresh_retained / reference_mass",
            "trapping_ratio": "fresh_delivered / fresh_retained",
            "residual_fraction": "exhaust_close_residual / exhaust_close_total",
            "purity_at_transfer_close": "transfer_close_fresh / transfer_close_total",
            "purity_at_exhaust_close": "exhaust_close_fresh / exhaust_close_total",
            "short_circuit_fraction": "gross_fresh_short_circuit / gross_fresh_delivered",
        },
    }


def calculate_scavenging_metrics_v2(inputs: ScavengingInput) -> dict[str, Any]:
    """Apply explicit single-zone semantics without clipping derived metrics.

    Gross crossing ledgers can count a parcel more than once, so they do not
    always identify a physical retained fraction. A bounded metric outside its
    domain is therefore UNDEFINED in this schema rather than exposed as an
    efficiency greater than one or silently clipped.
    """
    result = calculate_scavenging_metrics(inputs)
    bounded = ("trapping_efficiency", "scavenging_efficiency",
               "charging_efficiency", "residual_fraction",
               "purity_at_transfer_close", "purity_at_exhaust_close",
               "short_circuit_fraction")
    for name in bounded:
        ratio = result["ratios"][name]
        if ratio["status"] == "AVAILABLE" and not 0.0 <= ratio["value"] <= 1.0:
            ratio["value"] = None
            ratio["status"] = "UNDEFINED"
            ratio["reason"] = "OUTSIDE_PHYSICAL_DOMAIN_WITH_GROSS_CROSSING_BASIS"
    result["schema"] = "MOTORSIM_2T_SCAVENGING_METRICS_V2"
    result["assumption"] = "SINGLE_ZONE_PERFECT_MIXING_SCAVENGING_ASSUMPTION"
    result["domain_policy"] = "MARK_UNDEFINED_OUT_OF_DOMAIN; NEVER_CLIP"
    return result


def scavenging_input_from_cycle(cycle: dict[str, Any], *, reference_mass_kg: float,
                                transfer_close_angle_deg: float,
                                exhaust_close_angle_deg: float) -> ScavengingInput:
    """Reconstruct inputs from a cycle's primary trajectory and P6 cumulative ledgers.

    Close angles are scheduler angles already resolved from the engine geometry.
    A cycle lacking an exact event snapshot or trajectory-terminal binding is
    rejected; summary values are cross-checked against cumulative primary data.
    """
    if not isinstance(cycle, dict) or cycle.get("schema") != "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1":
        raise ValueError("No es evidencia primaria de ciclo del harness.")
    transfer_angle = _number(transfer_close_angle_deg, "transfer_close_angle_deg",
                             nonnegative=False)
    exhaust_angle = _number(exhaust_close_angle_deg, "exhaust_close_angle_deg",
                            nonnegative=False)
    trajectory = cycle.get("trajectory")
    terminal = cycle.get("terminal_state")
    if not isinstance(trajectory, list) or not trajectory or not isinstance(terminal, dict):
        raise ValueError("Falta la trayectoria primaria o el estado terminal.")
    if not isinstance(trajectory[-1], dict):
        raise ValueError("El último paso de trayectoria no es objeto.")
    if (cycle.get("trajectory_terminal_state") != terminal.get("gas_conservative") or
            cycle.get("trajectory_last_species_mass") != terminal.get("species_mass") or
            trajectory[-1].get("state") != cycle.get("trajectory_last_state") or
            trajectory[-1].get("species_mass") != cycle.get("trajectory_last_species_mass")):
        raise ValueError("La trayectoria no coincide con el estado terminal primario.")

    def state_at(target: float, label: str) -> tuple[float, float, float, float]:
        matches = []
        previous = -inf
        for index, row in enumerate(trajectory):
            if not isinstance(row, dict):
                raise ValueError(f"trajectory[{index}] no es objeto.")
            angle = _number(row.get("angle_deg"), f"trajectory[{index}].angle_deg",
                            nonnegative=False)
            if angle <= previous:
                raise ValueError("Los ángulos de la trayectoria deben crecer estrictamente.")
            previous = angle
            if abs(angle - target) <= 1e-9:
                matches.append(row)
        if len(matches) != 1:
            raise ValueError(f"Falta snapshot único en {label}={target:.12g}°.")
        by_component = matches[0].get("species_mass")
        if not isinstance(by_component, dict):
            raise ValueError(f"Falta estado P6 de species en {label}.")
        cylinder = by_component.get("cylinder")
        if not isinstance(cylinder, list) or len(cylinder) != 1:
            raise ValueError(f"Estado del cilindro inválido en {label}.")
        return _species_mass(cylinder[0], f"{label}.cylinder_species")

    start = cycle.get("cycle_start_cumulative")
    last = trajectory[-1]
    observables = cycle.get("observables")
    if not isinstance(start, dict) or not isinstance(observables, dict):
        raise ValueError("Faltan ledgers P6 acumulados u observables.")
    cycle_start_angle = _number(start.get("angle_deg"),
                                "cycle_start_cumulative.angle_deg",
                                nonnegative=False)
    cycle_end_angle = _number(cycle.get("scheduler_angle_deg"),
                              "scheduler_angle_deg", nonnegative=False)
    terminal_angle = _number(last.get("angle_deg"), "trajectory terminal angle",
                             nonnegative=False)
    if (abs(cycle_end_angle - cycle_start_angle - 360.0) > 1e-8 or
            abs(terminal_angle - cycle_end_angle) > 1e-9 or
            _number(trajectory[0].get("angle_deg"), "trajectory first angle",
                    nonnegative=False) <= cycle_start_angle):
        raise ValueError("La evidencia primaria no contiene un ciclo completo de 360°.")
    delivery_start = _number(start.get("fresh_delivery"), "start.fresh_delivery")
    short_start = _number(start.get("fresh_short_circuit"),
                          "start.fresh_short_circuit")
    delivery_end = _number(last.get("fresh_delivery_cumulative_kg"),
                            "last.fresh_delivery_cumulative_kg")
    short_end = _number(last.get("fresh_short_circuit_cumulative_kg"),
                        "last.fresh_short_circuit_cumulative_kg")
    delivered, short = delivery_end - delivery_start, short_end - short_start
    if delivered < 0.0 or short < 0.0:
        raise ValueError("Los ledgers P6 acumulados retroceden dentro del ciclo.")
    summary_delivery = _number(observables.get("fresh_delivery_kg"),
                               "observables.fresh_delivery_kg")
    summary_short = _number(observables.get("fresh_short_circuit_kg"),
                             "observables.fresh_short_circuit_kg")
    if summary_delivery != delivered or summary_short != short:
        raise ValueError("Los observables frescos no coinciden con los ledgers P6.")
    return ScavengingInput(
        reference_mass_kg=reference_mass_kg,
        fresh_delivered_kg=delivered,
        fresh_short_circuit_kg=short,
        species_at_transfer_close_kg=state_at(transfer_angle, "transfer_close"),
        species_at_exhaust_close_kg=state_at(exhaust_angle, "exhaust_close"),
    )


def scavenging_metrics_from_cycle(cycle: dict[str, Any], *, reference_mass_kg: float,
                                  transfer_close_angle_deg: float,
                                  exhaust_close_angle_deg: float) -> dict[str, Any]:
    """Auditable convenience path from trajectory-bound primary cycle evidence."""
    inputs = scavenging_input_from_cycle(
        cycle, reference_mass_kg=reference_mass_kg,
        transfer_close_angle_deg=transfer_close_angle_deg,
        exhaust_close_angle_deg=exhaust_close_angle_deg)
    return calculate_scavenging_metrics(inputs)


def scavenging_metrics_from_generic_ports(cycle: dict[str, Any], *, ports,
                                          reference_mass_kg: float) -> dict[str, Any]:
    """Bind exact P6 cycle snapshots to the generic geometry's last closures.

    Transfer purity is sampled after the last transfer duct closes; exhaust
    purity is sampled after the last exhaust duct closes. The accepted primary
    trajectory must contain exact event-angle rows. No interpolation or nearest
    sample selection is performed.
    """
    from .two_stroke_ports import TwoStrokePortSet
    if not isinstance(ports, TwoStrokePortSet):
        raise ValueError("Se requiere GENERIC_2T_PORTS_V1 validado.")
    ports.validate()
    if not isinstance(cycle, dict) or cycle.get("schema") != "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1":
        raise ValueError("No es evidencia primaria de ciclo del harness.")
    start = cycle.get("cycle_start_cumulative")
    if not isinstance(start, dict):
        raise ValueError("Falta identidad angular inicial del ciclo.")
    cycle_start = _number(start.get("angle_deg"), "cycle_start_cumulative.angle_deg",
                          nonnegative=False)
    cycle_end = cycle_start + 360.0

    def last_close(role: str) -> float:
        duct_ids = [duct.id for duct in ports.ducts if duct.role == role]
        closes = []
        for duct_id in duct_ids:
            for base_angle in ports.duct_closing_angles(duct_id):
                target = cycle_start + ((base_angle - cycle_start) % 360.0)
                if target <= cycle_start + 1e-9:
                    target += 360.0
                if target <= cycle_end + 1e-9:
                    closes.append(target)
        if not closes:
            raise ValueError(f"La geometría no define cierre de {role} dentro del ciclo.")
        return max(closes)

    return scavenging_metrics_from_cycle(
        cycle, reference_mass_kg=reference_mass_kg,
        transfer_close_angle_deg=last_close("transfer"),
        exhaust_close_angle_deg=last_close("exhaust"))


def scavenging_series_from_primary_cycles(cycles: list[dict[str, Any]], *, ports,
                                         reference_mass_kg: float) -> dict[str, Any]:
    """Audit a contiguous run of complete primary cycles without claiming period.

    Each cycle is independently bound to geometry-derived exact closure rows
    and P6 cumulative delivery/short-circuit ledgers. Periodic convergence is a
    separate campaign contract and is not inferred by this diagnostic series.
    """
    if not isinstance(cycles, list) or not cycles:
        raise ValueError("Se requiere una secuencia de ciclos primarios completos.")
    rows = []
    configuration = None
    for expected_index, cycle in enumerate(cycles, 1):
        if cycle.get("cycle_index") != expected_index:
            raise ValueError("Los ciclos deben ser contiguos desde el índice uno.")
        if cycle.get("configuration_hash") is None:
            raise ValueError("Cada ciclo debe estar ligado a una configuración.")
        if configuration is None:
            configuration = cycle["configuration_hash"]
        elif cycle["configuration_hash"] != configuration:
            raise ValueError("La configuración cambió dentro de la serie.")
        rows.append({"cycle_index": expected_index,
                     "metrics": scavenging_metrics_from_generic_ports(
                         cycle, ports=ports, reference_mass_kg=reference_mass_kg)})
    return {"schema": "MOTORSIM_2T_SCAVENGING_SERIES_V1",
            "configuration_hash": configuration,
            "periodicity": "NOT_EVALUATED",
            "cycles": rows}


def scavenging_engineering_records(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Translate audited scavenging metrics to the stable output-schema shape."""
    if (not isinstance(metrics, dict) or metrics.get("schema") not in {
            "MOTORSIM_2T_SCAVENGING_METRICS_V1",
            "MOTORSIM_2T_SCAVENGING_METRICS_V2"}):
        raise ValueError("Scavenging metric schema is invalid.")
    ratios = metrics.get("ratios")
    masses = metrics.get("masses_kg")
    if not isinstance(ratios, dict) or not isinstance(masses, dict):
        raise ValueError("Scavenging metrics lack ratios or masses.")
    schema = metrics["schema"]
    source_label = f"{schema} P6 gross crossing ledger"
    if schema == "MOTORSIM_2T_SCAVENGING_METRICS_V2":
        source_label += (
            f"; assumption={metrics.get('assumption')}; "
            f"domain_policy={metrics.get('domain_policy')}")
    result = {}
    for source, target in (("delivery_ratio", "delivery_ratio"),
                           ("trapping_efficiency", "trapping_efficiency"),
                           ("scavenging_efficiency", "scavenging_efficiency"),
                           ("charging_efficiency", "charging_efficiency"),
                           ("trapping_ratio", "trapping_ratio"),
                           ("residual_fraction", "residual_fraction"),
                           ("purity_at_transfer_close", "purity_at_transfer_close"),
                           ("purity_at_exhaust_close", "purity_at_exhaust_close"),
                           ("short_circuit_fraction", "short_circuit_fraction")):
        row = ratios.get(source)
        if not isinstance(row, dict) or row.get("status") not in {"AVAILABLE", "UNDEFINED"}:
            raise ValueError(f"Scavenging ratio {source} is missing or invalid.")
        available = row["status"] == "AVAILABLE"
        result[target] = {"value": row.get("value") if available else None,
                          "status": "DEFINED" if available else "UNDEFINED",
                          "reason": None if available else row.get("reason"),
                          "source": source_label}
    for source, target in (("fresh_delivered", "fresh_delivery_kg"),
                           ("fresh_retained", "fresh_retained_kg"),
                           ("fresh_lost", "fresh_short_circuit_kg"),
                           ("fresh_lost", "fresh_lost_kg")):
        value = _number(masses.get(source), f"masses_kg.{source}")
        result[target] = {"value": value, "status": "DEFINED", "reason": None,
                          "source": source_label}
    return result
