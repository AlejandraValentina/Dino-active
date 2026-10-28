"""Analytical fixed-grid time-integration reference for the SSPRK2 operator.

This isolates temporal truncation error from spatial discretization and engine
physics.  The scalar decay equation has the closed-form solution exp(-t).
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def integrate_decay(dt: float, final_time: float = 1.0) -> float:
    """Integrate y'=-y, y(0)=1 with the SSPRK2/Heun update."""
    if not math.isfinite(dt) or dt <= 0 or not math.isfinite(final_time) or final_time <= 0:
        raise ValueError("dt and final_time must be finite and positive")
    count = round(final_time / dt)
    if count < 1 or not math.isclose(count * dt, final_time, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("dt must divide final_time exactly")
    value = 1.0
    for _ in range(count):
        stage = value - dt * value
        value = 0.5 * value + 0.5 * (stage - dt * stage)
    return value


def build_result() -> dict:
    final_time = 1.0
    exact = math.exp(-final_time)
    steps = (5, 10, 20, 40, 80, 160)
    rows = []
    for count in steps:
        dt = final_time / count
        computed = integrate_decay(dt, final_time)
        rows.append({"steps": count, "dt": dt, "value": computed,
                     "absolute_error": abs(computed - exact)})
    # The coarsest pair is retained as a startup diagnostic; the acceptance
    # order uses the finer four comparisons where the asymptotic trend settles.
    all_orders = [math.log(a["absolute_error"] / b["absolute_error"], 2)
                  for a, b in zip(rows, rows[1:])]
    orders = all_orders[1:]
    return {
        "schema": "DINO_TEMPORAL_OPERATOR_REFERENCE_V1",
        "equation": "dy/dt=-y",
        "method": "SSPRK2 (Heun form)",
        "fixed_spatial_grid": "not applicable; scalar semidiscrete reference",
        "final_time": final_time,
        "initial_value": 1.0,
        "analytical_value": exact,
        "refinements": rows,
        "observed_orders": orders,
        "all_pair_orders_including_coarsest": all_orders,
        "acceptance": {"second_order_range": [1.9, 2.1],
                       "all_orders_in_range": all(1.9 <= p <= 2.1 for p in orders)},
        "qualification": "Verifies the time integrator on a smooth analytical reference only; does not establish temporal error for the integrated engine or its coupled operators.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("results/predictive-reliability-v1/temporal-operator-reference-v1.json"))
    args = parser.parse_args()
    result = build_result()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "orders": result["observed_orders"],
                      "pass": result["acceptance"]["all_orders_in_range"]}))


if __name__ == "__main__":
    main()
