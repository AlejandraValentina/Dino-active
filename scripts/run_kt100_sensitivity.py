"""Run the four preregistered +/-5% KT100 fixture sensitivity variants once."""
import json
from pathlib import Path
import time

from motorsim.kt100_reference import FIXTURE_ID, SIMULATION_ID
from scripts.run_kt100_reference_study import run_point

ANCHOR_RPM = 9000
VARIANTS = (
    ("rod", 0.95, 1.0), ("rod", 1.05, 1.0),
    ("exhaust", 1.0, 0.95), ("exhaust", 1.0, 1.05),
)


def main():
    output = Path("results/kt100-reference-v1-20261001/sensitivity-runs")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for axis, rod_scale, exhaust_scale in VARIANTS:
        started = time.monotonic()
        try:
            result = run_point(ANCHOR_RPM, rod_scale=rod_scale,
                               exhaust_scale=exhaust_scale, replay=False)
        except Exception as exc:
            result = {"rpm": ANCHOR_RPM, "error": f"{type(exc).__name__}: {exc}",
                      "convergence_status": "INCOMPLETE_OR_ERROR"}
        result["sensitivity_variant"] = {"axis": axis, "rod_scale": rod_scale,
                                          "exhaust_scale": exhaust_scale}
        result["sensitivity_elapsed_wall_seconds"] = time.monotonic() - started
        results.append(result)
        safe = f"{axis}-{rod_scale:g}-{exhaust_scale:g}"
        (output / f"{safe}.json").write_text(json.dumps(result, ensure_ascii=False,
            sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print(json.dumps({"variant": safe,
            "status": result.get("convergence_status"),
            "cycles": result.get("cycles_completed"),
            "work_J": result.get("indicated_work_last_completed_cycle_J"),
            "error": result.get("error")}, allow_nan=False), flush=True)
    payload = {"schema": "kt100-reference-sensitivity-results-v1",
        "case_id": SIMULATION_ID, "fixture_id": FIXTURE_ID,
        "preregistration": "../sensitivity-preregistration.json",
        "anchor_rpm": ANCHOR_RPM, "interpretation": "descriptive, synthetic, non-confirmatory; no fitting",
        "results": results}
    (output / "sensitivity.json").write_text(json.dumps(payload, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")


if __name__ == "__main__":
    main()
