"""Preregistered, audit-friendly period-1/period-2 detector."""
from __future__ import annotations

from copy import deepcopy
from math import isfinite

CONTRACT = "REFERENCE_PERIODIC_CONVERGENCE_V1"
CONTRACT_V2 = "REFERENCE_PERIODIC_CONVERGENCE_V2"
STREAK = 3
THRESHOLDS = {
    "chamber_mass_relative": 0.002,
    "chamber_total_energy_relative": 0.002,
    "chamber_pressure_relative": 0.005,
    "chamber_temperature_relative": 0.005,
    "duct_cell_mass_relative": 0.002,
    "duct_cell_total_energy_relative": 0.002,
    "duct_cell_pressure_relative": 0.005,
    "duct_cell_temperature_relative": 0.005,
    "duct_cell_species_mass_fraction_absolute": 0.002,
    "duct_cell_velocity_over_sound_speed_absolute": 0.005,
    "global_species_inventory_over_total_mass": 0.002,
    "work_relative_floor_1J": 0.005,
    "fresh_delivery_fraction_of_cycle_start_mass": 0.002,
    "fresh_short_circuit_fraction_of_cycle_start_mass": 0.002,
    "p7_burned_species_fraction_of_cycle_start_mass": 0.002,
    "p7_heat_fraction_of_cycle_start_energy": 0.002,
}


def _number(value):
    return type(value) in (int, float) and isfinite(value)


def _relative(a, b, floor=0.0):
    if not _number(a) or not _number(b) or a < 0 or b < 0:
        raise ValueError("INVALID numeric observable")
    denominator = max(floor, abs(a), abs(b))
    if denominator == 0:
        return 0.0
    return abs(a - b) / denominator


def compare_cycles(older, later):
    """Recompute every preregistered observable; no summary PASS is trusted."""
    try:
        if not isinstance(older, dict) or not isinstance(later, dict):
            raise ValueError("cycle record must be an object")
        if type(older.get("cycle_index")) is not int or type(later.get("cycle_index")) is not int:
            raise ValueError("cycle index must be an integer")
        if older.get("cycle_index") >= later.get("cycle_index"):
            raise ValueError("cycle identity is not increasing")
        if older.get("configuration_hash") != later.get("configuration_hash"):
            raise ValueError("configuration identity mismatch")
        if older.get("contract") != CONTRACT or later.get("contract") != CONTRACT:
            raise ValueError("contract identity mismatch")
        a, b = older["observables"], later["observables"]
        metrics = {}

        def rel(name, x, y, threshold, floor=0.0):
            value = _relative(x, y, floor)
            metrics[name] = {"value": value, "threshold": threshold,
                             "passed": value <= threshold}

        for chamber in ("cylinder", "crankcase"):
            for key, threshold_name in (("mass_kg", "chamber_mass_relative"),
                                        ("total_energy_J", "chamber_total_energy_relative"),
                                        ("pressure_Pa", "chamber_pressure_relative"),
                                        ("temperature_K", "chamber_temperature_relative")):
                rel(f"{chamber}.{key}", a["chambers"][chamber][key],
                    b["chambers"][chamber][key], THRESHOLDS[threshold_name])

        if set(a["ducts"]) != set(b["ducts"]):
            raise ValueError("duct identity mismatch")
        for duct in sorted(a["ducts"]):
            if len(a["ducts"][duct]) != len(b["ducts"][duct]):
                raise ValueError("duct mesh shape mismatch")
            for i, (ca, cb) in enumerate(zip(a["ducts"][duct], b["ducts"][duct])):
                prefix = f"ducts.{duct}[{i}]"
                for key, threshold_name in (("mass_kg", "duct_cell_mass_relative"),
                                            ("total_energy_J", "duct_cell_total_energy_relative"),
                                            ("pressure_Pa", "duct_cell_pressure_relative"),
                                            ("temperature_K", "duct_cell_temperature_relative")):
                    rel(f"{prefix}.{key}", ca[key], cb[key], THRESHOLDS[threshold_name])
                sa, sb = ca["species_mass_fractions"], cb["species_mass_fractions"]
                if len(sa) != 4 or len(sb) != 4:
                    raise ValueError("duct species shape mismatch")
                for j, name in enumerate(("fresh_air", "fuel", "residual", "burned")):
                    if not _number(sa[j]) or not _number(sb[j]) or not 0 <= sa[j] <= 1 or not 0 <= sb[j] <= 1:
                        raise ValueError("INVALID duct species fraction")
                    value = abs(sa[j] - sb[j])
                    metrics[f"{prefix}.species.{name}"] = {
                        "value": value,
                        "threshold": THRESHOLDS["duct_cell_species_mass_fraction_absolute"],
                        "passed": value <= THRESHOLDS["duct_cell_species_mass_fraction_absolute"]}
                va, vb = ca["velocity_over_sound_speed"], cb["velocity_over_sound_speed"]
                if not _number(va) or not _number(vb):
                    raise ValueError("INVALID normalized duct velocity")
                value = abs(va - vb)
                limit = THRESHOLDS["duct_cell_velocity_over_sound_speed_absolute"]
                metrics[f"{prefix}.velocity_over_sound_speed"] = {
                    "value": value, "threshold": limit, "passed": value <= limit}

        if len(a["global_species_kg"]) != 4 or len(b["global_species_kg"]) != 4:
            raise ValueError("global species shape mismatch")
        normalizer = b["cycle_start_total_mass_kg"]
        if not _number(normalizer) or normalizer <= 0:
            raise ValueError("invalid later-cycle start mass")
        for i, name in enumerate(("fresh_air", "fuel", "residual", "burned")):
            if not _number(a["global_species_kg"][i]) or not _number(b["global_species_kg"][i]):
                raise ValueError("INVALID global species inventory")
            value = abs(a["global_species_kg"][i] - b["global_species_kg"][i]) / normalizer
            limit = THRESHOLDS["global_species_inventory_over_total_mass"]
            metrics[f"global_species.{name}"] = {"value": value, "threshold": limit,
                                                   "passed": value <= limit}

        rel("work_J", a["work_J"], b["work_J"], THRESHOLDS["work_relative_floor_1J"], 1.0)
        for key, threshold_name in (("fresh_delivery_kg", "fresh_delivery_fraction_of_cycle_start_mass"),
                                    ("fresh_short_circuit_kg", "fresh_short_circuit_fraction_of_cycle_start_mass"),
                                    ("p7_burned_produced_kg", "p7_burned_species_fraction_of_cycle_start_mass")):
            if not _number(a[key]) or not _number(b[key]) or a[key] < 0 or b[key] < 0:
                raise ValueError(f"INVALID {key}")
            value = abs(a[key] - b[key]) / normalizer
            limit = THRESHOLDS[threshold_name]
            metrics[key] = {"value": value, "threshold": limit, "passed": value <= limit}
        energy_norm = b["cycle_start_total_energy_J"]
        if not _number(energy_norm) or energy_norm <= 0:
            raise ValueError("invalid later-cycle start energy")
        heat_a, heat_b = a["p7_heat_J"], b["p7_heat_J"]
        if not _number(heat_a) or not _number(heat_b) or heat_a < 0 or heat_b < 0:
            raise ValueError("INVALID P7 heat")
        heat_diff = abs(heat_a - heat_b) / energy_norm
        heat_limit = THRESHOLDS["p7_heat_fraction_of_cycle_start_energy"]
        metrics["p7_heat_J"] = {"value": heat_diff, "threshold": heat_limit,
                                 "passed": heat_diff <= heat_limit}
        return {"status": "PASS" if all(m["passed"] for m in metrics.values()) else "FAIL",
                "metrics": metrics, "contract": CONTRACT,
                "older_cycle": older["cycle_index"], "later_cycle": later["cycle_index"]}
    except (AttributeError, KeyError, TypeError, ValueError, IndexError) as exc:
        return {"status": "INVALID", "reason": str(exc), "contract": CONTRACT}


class PeriodicDetector:
    """Restartable detector with period-1 precedence and independent A/B streaks."""
    def __init__(self, state=None):
        self.history = []
        self.lag1_streak = 0
        self.branch_streaks = {"A": 0, "B": 0}
        self.detected_period = None
        self.converged_cycle = None
        if state is not None:
            self.restore(state)

    def update(self, record):
        if self.detected_period is not None:
            raise ValueError("detector already converged")
        index = len(self.history) + 1
        if record.get("cycle_index") != index:
            raise ValueError("complete-cycle indexes must be contiguous from one")
        self.history.append(deepcopy(record))
        outcomes = {}
        if index >= 2:
            lag1 = compare_cycles(self.history[-2], self.history[-1])
            outcomes["lag1"] = lag1
            self.lag1_streak = self.lag1_streak + 1 if lag1["status"] == "PASS" else 0
            if self.lag1_streak >= STREAK:
                self.detected_period = 1
                self.converged_cycle = index
        if index >= 3:
            lag2 = compare_cycles(self.history[-3], self.history[-1])
            branch = "A" if (index - 1) % 2 == 0 else "B"
            outcomes["lag2_branch"] = branch
            outcomes["lag2"] = lag2
            self.branch_streaks[branch] = (self.branch_streaks[branch] + 1
                                           if lag2["status"] == "PASS" else 0)
            if (self.detected_period is None and
                    self.branch_streaks["A"] >= STREAK and self.branch_streaks["B"] >= STREAK):
                self.detected_period = 2
                self.converged_cycle = index
        return {"outcomes": outcomes, "classification": self.classification,
                "lag1_streak": self.lag1_streak,
                "branch_streaks": dict(self.branch_streaks)}

    @property
    def classification(self):
        return f"PERIOD_{self.detected_period}" if self.detected_period else None

    def snapshot(self):
        return {"contract": CONTRACT, "history": deepcopy(self.history),
                "lag1_streak": self.lag1_streak,
                "branch_streaks": dict(self.branch_streaks),
                "detected_period": self.detected_period,
                "converged_cycle": self.converged_cycle}

    def restore(self, state):
        if state.get("contract") != CONTRACT:
            raise ValueError("detector contract mismatch")
        history = state.get("history")
        if not isinstance(history, list) or any(x.get("cycle_index") != i + 1 for i, x in enumerate(history)):
            raise ValueError("detector history identity mismatch")
        self.history = deepcopy(history)
        self.lag1_streak = state["lag1_streak"]
        self.branch_streaks = dict(state["branch_streaks"])
        if set(self.branch_streaks) != {"A", "B"}:
            raise ValueError("detector branch state malformed")
        self.detected_period = state["detected_period"]
        self.converged_cycle = state["converged_cycle"]
        if (type(self.lag1_streak) is not int or self.lag1_streak < 0 or
                any(type(value) is not int or value < 0 for value in self.branch_streaks.values()) or
                self.detected_period not in (None, 1, 2) or
                (self.converged_cycle is not None and type(self.converged_cycle) is not int)):
            raise ValueError("detector state contains invalid numeric/period fields")
        replayed = PeriodicDetector()
        for record in history:
            replayed.update(record)
        if replayed.snapshot() != self.snapshot():
            raise ValueError("persisted detector state does not match its complete history")


def compare_cycles_v2(older, later):
    """V2 comparison: preserve V1 metrics but allow signed indicated work.

    Cycle primary records retain their V1 data contract. Only detector
    semantics are versioned: work uses the same 1 J floor and 0.005 relative
    threshold, with absolute magnitude in the denominator and a signed
    difference in the numerator.
    """
    try:
        if not isinstance(older, dict) or not isinstance(later, dict):
            raise ValueError("cycle record must be an object")
        work_a = older["observables"]["work_J"]
        work_b = later["observables"]["work_J"]
        if not _number(work_a) or not _number(work_b):
            raise ValueError("INVALID signed work observable")
        safe_older, safe_later = deepcopy(older), deepcopy(later)
        safe_older["observables"]["work_J"] = 1.0
        safe_later["observables"]["work_J"] = 1.0
        result = compare_cycles(safe_older, safe_later)
        if result["status"] == "INVALID":
            result["contract"] = CONTRACT_V2
            return result
        denominator = max(1.0, abs(work_a), abs(work_b))
        work_metric = abs(work_a - work_b) / denominator
        threshold = THRESHOLDS["work_relative_floor_1J"]
        result["metrics"]["work_J"] = {
            "value": work_metric, "threshold": threshold,
            "passed": work_metric <= threshold}
        result["status"] = ("PASS" if all(metric["passed"]
                            for metric in result["metrics"].values()) else "FAIL")
        result["contract"] = CONTRACT_V2
        return result
    except (AttributeError, KeyError, TypeError, ValueError, IndexError) as exc:
        return {"status": "INVALID", "reason": str(exc), "contract": CONTRACT_V2}


class PeriodicDetectorV2:
    """Restartable period-1/2 detector for signed-work cycle records."""
    def __init__(self, state=None):
        self.history = []
        self.lag1_streak = 0
        self.branch_streaks = {"A": 0, "B": 0}
        self.detected_period = None
        self.converged_cycle = None
        if state is not None:
            self.restore(state)

    def update(self, record):
        if self.detected_period is not None:
            raise ValueError("detector already converged")
        index = len(self.history) + 1
        if record.get("cycle_index") != index:
            raise ValueError("complete-cycle indexes must be contiguous from one")
        self.history.append(deepcopy(record))
        outcomes = {}
        if index >= 2:
            lag1 = compare_cycles_v2(self.history[-2], self.history[-1])
            outcomes["lag1"] = lag1
            self.lag1_streak = self.lag1_streak + 1 if lag1["status"] == "PASS" else 0
            if self.lag1_streak >= STREAK:
                self.detected_period = 1
                self.converged_cycle = index
        if index >= 3:
            lag2 = compare_cycles_v2(self.history[-3], self.history[-1])
            branch = "A" if (index - 1) % 2 == 0 else "B"
            outcomes["lag2_branch"] = branch
            outcomes["lag2"] = lag2
            self.branch_streaks[branch] = (self.branch_streaks[branch] + 1
                                           if lag2["status"] == "PASS" else 0)
            if (self.detected_period is None and
                    self.branch_streaks["A"] >= STREAK and
                    self.branch_streaks["B"] >= STREAK):
                self.detected_period = 2
                self.converged_cycle = index
        return {"outcomes": outcomes, "classification": self.classification,
                "lag1_streak": self.lag1_streak,
                "branch_streaks": dict(self.branch_streaks)}

    @property
    def classification(self):
        return f"PERIOD_{self.detected_period}" if self.detected_period else None

    def snapshot(self):
        return {"contract": CONTRACT_V2, "history": deepcopy(self.history),
                "lag1_streak": self.lag1_streak,
                "branch_streaks": dict(self.branch_streaks),
                "detected_period": self.detected_period,
                "converged_cycle": self.converged_cycle}

    def restore(self, state):
        if not isinstance(state, dict) or state.get("contract") != CONTRACT_V2:
            raise ValueError("detector contract mismatch")
        history = state.get("history")
        if (not isinstance(history, list) or
                any(not isinstance(item, dict) or item.get("cycle_index") != i + 1
                    for i, item in enumerate(history))):
            raise ValueError("detector history identity mismatch")
        branch_streaks = state.get("branch_streaks")
        if not isinstance(branch_streaks, dict) or set(branch_streaks) != {"A", "B"}:
            raise ValueError("detector branch state malformed")
        lag1_streak = state.get("lag1_streak")
        detected_period = state.get("detected_period")
        converged_cycle = state.get("converged_cycle")
        if (type(lag1_streak) is not int or lag1_streak < 0 or
                any(type(value) is not int or value < 0
                    for value in branch_streaks.values()) or
                detected_period not in (None, 1, 2) or
                (converged_cycle is not None and type(converged_cycle) is not int)):
            raise ValueError("detector state contains invalid numeric/period fields")
        replayed = PeriodicDetectorV2()
        for record in history:
            replayed.update(record)
        candidate = {"contract": CONTRACT_V2, "history": deepcopy(history),
                     "lag1_streak": lag1_streak,
                     "branch_streaks": dict(branch_streaks),
                     "detected_period": detected_period,
                     "converged_cycle": converged_cycle}
        if replayed.snapshot() != candidate:
            raise ValueError("persisted detector state does not match its complete history")
        self.history = deepcopy(history)
        self.lag1_streak = lag1_streak
        self.branch_streaks = dict(branch_streaks)
        self.detected_period = detected_period
        self.converged_cycle = converged_cycle
