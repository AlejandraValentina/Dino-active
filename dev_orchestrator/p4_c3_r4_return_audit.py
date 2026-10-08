"""Explicit, non-campaign C3-R4 evidence runner.

R4 consumes an already captured C3 history.  It deliberately has no solver
entry point: producing evidence is a separate, explicitly authorized action.
"""
import json
from pathlib import Path

from dev_orchestrator.p4_c3_return_audit import (
    CONSERVATION_THRESHOLD,
    _momentum_audit,
    _riemann_audit,
    _select_return,
)


R4_OUTPUT = Path("results/p4-c3-r4-20260928")
R3_OUTPUT = Path("results/p4-c3-r3-20260928")
SUPERSEDES_FOR_ANALYSIS = "results/p4-c3-r3-20260928"


def ensure_safe_output(path=R4_OUTPUT, allow_existing=False):
    """Reject historical/R3 paths and existing output unless explicitly opted in."""
    target = Path(path)
    if target != R4_OUTPUT:
        raise ValueError("R4 output must be results/p4-c3-r4-20260928")
    if target.name in {R3_OUTPUT.name, "p4-c3-r2", "p4-c3-r1"}:
        raise ValueError("historical C3 output is not writable")
    if target.exists() and not allow_existing:
        raise FileExistsError(
            "R4 output already exists; refusing overwrite without explicit flag")
    return target


def _write_new(output, name, value, allow_existing=False):
    path = output / name
    if path.exists() and not allow_existing:
        raise FileExistsError("refusing to overwrite existing R4 artifact: " + str(path))
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run_r4(result, output=R4_OUTPUT, allow_existing=False):
    """Audit supplied evidence and write a fresh R4 result set.

    ``result`` must be the already persisted return-audit payload from the
    focal run.  This function never calls ``solve_c2_one`` and never mutates
    R3 artifacts.
    """
    output = ensure_safe_output(output, allow_existing=allow_existing)
    history = result["interface_history"]
    geometry = result["audit_geometry"]
    expected_time = result["expected_return_time"]
    selected, window = _select_return(history, expected_time)
    if selected is None:
        a_status = "INCONCLUSIVE"
        a = {"status": a_status,
             "status_reason": "No admissible return sample in preregistered window.",
             "criterion_authority": "P4-SCI-03/P4-SCI-04A"}
        selected_time = None
    else:
        selected_time, selected_info = selected
        a = _riemann_audit(selected_info)
    b2 = _momentum_audit(history, geometry)
    conservation = result["max_global_resid"] <= CONSERVATION_THRESHOLD
    admissibility = result.get("status") == "completed"
    # B2 is intentionally metric-only; therefore global C3 cannot close here.
    decision = {
        "classification": "P4_SCI_C3_INCONCLUSIVE",
        "global_status": "INCONCLUSIVE",
        "a_status": a["status"],
        "b2_status": b2["status"],
        "b2_metric_only": b2["status"] == "METRIC_ONLY",
        "b2_status_reason": b2["status_reason"],
        "return_snapshot": "PASS" if selected is not None else "INCONCLUSIVE",
        "conservation": "PASS" if conservation else "FAIL",
        "admissibility": "PASS" if admissibility else "FAIL",
        "e13": "NOT_EXECUTED",
        "p9": "STOPPED",
        "criterion_authority": "P4-SCI-03/P4-SCI-04A",
        "supersedes_for_analysis": SUPERSEDES_FOR_ANALYSIS,
    }
    output.mkdir(parents=True, exist_ok=allow_existing)
    _write_new(output, "metadata.json", {
        "run_id": "p4-c3-r4-20260928",
        "supersedes_for_analysis": SUPERSEDES_FOR_ANALYSIS,
        "r3_preserved": True,
        "campaign_executed": False,
    }, allow_existing=allow_existing)
    _write_new(output, "return_snapshot.json", {
        "status": "PASS" if selected is not None else "INCONCLUSIVE",
        "time": selected_time, "window": window,
    }, allow_existing=allow_existing)
    _write_new(output, "exact_riemann_comparison.json", a, allow_existing=allow_existing)
    _write_new(output, "momentum_control_volume.json", b2, allow_existing=allow_existing)
    _write_new(output, "decision.json", decision, allow_existing=allow_existing)
    return decision


def main():
    raise RuntimeError(
        "C3-R4 runner consumes supplied evidence; campaign execution is disabled")


if __name__ == "__main__":
    main()
