"""Contractual period-1/period-2 convergence detector (E13-R1).

The detector is deliberately independent of the solver.  It consumes completed
cycle records and preserves only JSON-safe scientific identity and streak state.
"""
from __future__ import annotations

from bisect import bisect_right
from math import isfinite
from typing import Any

THRESHOLDS = {"work": .005, "cylinder": .005, "sensor_max": .005,
              "port": .002, "inventories": .002}


def _rel(a, b, floor=0.0):
    return abs(a - b) / max(abs(a), abs(b), floor)


def _curve(row, key, index=None):
    hs = row.get("history") or []
    if not hs:
        raise ValueError("INCOMPLETE_ANGULAR_HISTORY")
    xs = [h["angle"] - row["begin"] for h in hs]
    if xs[0] > .5 or xs[-1] != 360.0:
        raise ValueError("INCOMPLETE_ANGULAR_HISTORY")
    ys = [h[key] if index is None else h[key][index][0] for h in hs]
    out = []
    for phase in (i * .5 for i in range(1, 721)):
        j = bisect_right(xs, phase)
        if j == 0 or j == len(xs):
            out.append(ys[0] if j == 0 else ys[-1])
        else:
            out.append(ys[j - 1] + (ys[j] - ys[j - 1]) *
                       (phase - xs[j - 1]) / (xs[j] - xs[j - 1]))
    return out


def compare_cycles(previous: dict, current: dict) -> dict:
    """Return the exact E13 metric vector for two completed cycle records."""
    try:
        a, b = previous["state"], current["state"]
        inventories = []
        for k in (0, 3, 6):
            inventories.extend((_rel(a[k], b[k]), _rel(a[k + 1], b[k + 1]),
                                abs(a[k + 2] / a[k] - b[k + 2] / b[k])))
        pa = [sum(c[j] for c in previous["cells"]) for j in (0, 2, 3)]
        pb = [sum(c[j] for c in current["cells"]) for j in (0, 2, 3)]
        inventories.extend((_rel(pa[0], pb[0]), _rel(pa[1], pb[1]),
                            abs(pa[2] - pb[2]) / max(pa[0], pb[0])))
        def pressure(key, index=None):
            x, y = _curve(previous, key, index), _curve(current, key, index)
            return max(abs(i - j) for i, j in zip(x, y)) / max(map(abs, x + y))
        metrics = {
            "work": _rel(previous["work_indicated_J"], current["work_indicated_J"], 1.),
            "cylinder": pressure("p_cyl"),
            "sensor": [pressure("sensors_p_u_M_Y", i) for i in range(3)],
            "sensor_max": 0.0,
            "port": _rel(previous["port_integral"][0], current["port_integral"][0],
                           current["initial_cylinder_mass"]),
            "inventories": inventories,
        }
        metrics["sensor_max"] = max(metrics["sensor"])
        # Legacy P4 field names remain aliases for existing reports/tests.
        metrics["cylinder_pressure"] = metrics["cylinder"]
        metrics["sensor_pressure"] = metrics["sensor"]
        metrics["port_mass"] = metrics["port"]
        metrics["passed"] = (metrics["work"] <= .005 and metrics["cylinder"] <= .005
                              and metrics["sensor_max"] <= .005 and metrics["port"] <= .002
                              and max(inventories) <= .002)
        return metrics
    except (KeyError, IndexError, TypeError, ZeroDivisionError, ValueError) as exc:
        return {"status": "INVALID", "reason": str(exc) or "INVALID_METRICS", "passed": False}


def identity(record: dict) -> dict:
    keys = ("configuration_hash", "scientific_contract_id", "solver", "backend",
            "mesh", "geometry", "rpm", "operating_point", "cycle_convention",
            "anchor_cycle", "branch_map")
    return {k: record.get(k) for k in keys}


def identity_match(a: dict, b: dict) -> bool:
    ia, ib = identity(a), identity(b)
    # Missing legacy identity is explicitly invalid; it must not extend a streak.
    return all(ia[k] is not None and ia[k] == ib[k] for k in ia)


class PeriodicityDetector:
    """Stateful E13-R1 detector with independent lag-1 and lag-2 branches."""
    def __init__(self, anchor_cycle=None, branch_map=None):
        self.anchor_cycle = anchor_cycle
        self.branch_map = branch_map or {"A": "A", "B": "B"}
        self.lag1_streak = 0
        self.branch_A_streak = 0
        self.branch_B_streak = 0
        self.detected_period = None
        self.converged_cycle = None
        self.history_identity = None
        self.last_metrics = None

    def update(self, current: dict, lag1: dict | None = None,
               lag2: dict | None = None, branch: str | None = None) -> dict:
        if self.history_identity is None:
            self.history_identity = identity(current)
        if not identity_match(self.history_identity, current):
            result = {"status": "INVALID", "reason": "IDENTITY_MISMATCH", "passed": False}
            self.lag1_streak = 0
            if branch == "A": self.branch_A_streak = 0
            if branch == "B": self.branch_B_streak = 0
            self.last_metrics = result
            return result
        result = lag1 or (compare_cycles(lag1, current) if lag1 else
                          {"status": "INVALID", "reason": "MISSING_LAG1", "passed": False})
        if result.get("status") == "INVALID": self.lag1_streak = 0
        elif result.get("passed"): self.lag1_streak += 1
        else: self.lag1_streak = 0
        if self.lag1_streak >= 3:
            self.detected_period, self.converged_cycle = 1, current.get("cycle")
        if lag2 is not None and branch in ("A", "B"):
            if lag2.get("status") == "INVALID" or not lag2.get("passed"):
                if branch == "A": self.branch_A_streak = 0
                else: self.branch_B_streak = 0
            elif branch == "A": self.branch_A_streak += 1
            else: self.branch_B_streak += 1
            if self.branch_A_streak >= 3 and self.branch_B_streak >= 3 and self.detected_period != 1:
                self.detected_period, self.converged_cycle = 2, current.get("cycle")
        self.last_metrics = result
        result = dict(result, lag1_streak=self.lag1_streak,
                      branch_A_streak=self.branch_A_streak,
                      branch_B_streak=self.branch_B_streak,
                      detected_period=self.detected_period)
        return result

    def to_json(self) -> dict:
        return {"anchor_cycle": self.anchor_cycle, "branch_map": self.branch_map,
                "lag1_streak": self.lag1_streak, "branch_A_streak": self.branch_A_streak,
                "branch_B_streak": self.branch_B_streak, "detected_period": self.detected_period,
                "converged_cycle": self.converged_cycle, "history_identity": self.history_identity,
                "last_metrics": self.last_metrics}

    @classmethod
    def from_json(cls, data):
        d = cls(data.get("anchor_cycle"), data.get("branch_map"))
        for k in ("lag1_streak", "branch_A_streak", "branch_B_streak", "detected_period", "converged_cycle", "history_identity", "last_metrics"):
            if k in data: setattr(d, k, data[k])
        return d
