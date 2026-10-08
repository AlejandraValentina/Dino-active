"""Create a compact, reproducible KT100 campaign decision and source inventory."""
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "kt100-reference-v1-20261001"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def admissibility_summary(point):
    checked = []
    for cycle in point.get("cycle_summaries", []):
        state = cycle.get("state", [])
        finite = len(state) == 12 and all(isinstance(v, (int, float)) and math.isfinite(v) for v in state)
        physical = finite and all(state[3*i] > 0 and state[3*i+1] > 0 and
            0 <= state[3*i+2] <= state[3*i] for i in range(4))
        checked.append({"cycle": cycle.get("cycle"), "finite": finite,
                        "physical_four_cv_end_state": physical})
    return {"checked_completed_cycles": len(checked),
        "all_completed_cycle_end_states_admissible": bool(checked) and all(
            row["physical_four_cv_end_state"] for row in checked),
        "cycles": checked,
        "scope": "cycle-end states in stored 0D trace; not a four-species/1D admissibility gate"}


def main():
    campaign = read(OUT / "campaign.json")
    sensitivity = read(OUT / "sensitivity-runs" / "sensitivity.json")
    base = next(row for row in campaign["results"] if row.get("rpm") == 9000)
    base_work = base.get("indicated_work_last_completed_cycle_J")
    rows = []
    for row in sensitivity["results"]:
        work = row.get("indicated_work_last_completed_cycle_J")
        rows.append({"variant": row["sensitivity_variant"],
            "status": row.get("convergence_status"),
            "cycles": row.get("cycles_completed"),
            "work_J": work,
            "work_change_percent_vs_9000_baseline": None if not base_work or work is None else 100*(work/base_work-1),
            "peak_pressure_Pa": row.get("peak_pressure_last_completed_cycle_Pa"),
            "peak_pressure_change_percent_vs_9000_baseline": None if not base.get("peak_pressure_last_completed_cycle_Pa") or row.get("peak_pressure_last_completed_cycle_Pa") is None else 100*(row["peak_pressure_last_completed_cycle_Pa"]/base["peak_pressure_last_completed_cycle_Pa"]-1),
            "balances_passed": (row.get("mass_energy_and_passive_marker_balances") or {}).get("balances_passed")})
    manifest_path = ROOT / "configs" / "reference" / "kt100_reference_v1_provenance.json"
    fixture_path = ROOT / "configs" / "fixtures" / "kt100_model_fixture_v1.json"
    p9_spec_path = ROOT / "openspec" / "changes" / "p9-experimental-validation" / "specs" / "p9-experimental-validation" / "spec.md"
    manifest = read(manifest_path)
    (OUT / "fixture-config.json").write_bytes(fixture_path.read_bytes())
    (OUT / "source-inventory.json").write_text(json.dumps(manifest["sources"],
        ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    campaign["fixture_config_sha256"] = sha(OUT / "fixture-config.json")
    (OUT / "campaign.json").write_text(json.dumps(campaign, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    preflight_path = ROOT / "results" / "kt100-reference-v1-20261001-smoke" / "anchor-5000.json"
    environment = {"python": sys.version, "platform": platform.platform(),
                   "machine": platform.machine(), "processor": platform.processor(),
                   "logical_cpus": __import__("os").cpu_count()}
    (OUT / "campaign-environment.json").write_text(json.dumps(environment,
        ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    receipt = {
        "schema": "kt100-reference-decision-v1",
        "reference_case_status": "KT100_REFERENCE_CASE_V1_READY",
        "model_fixture_status": "KT100_MODEL_FIXTURE_V1_EXECUTABLE_0D_EXPLORATORY; not fully verified",
        "selection": manifest["selected_variant"],
        "campaign_classification": "SYNTHETIC_NON_CONFIRMATORY",
        "campaign_environment": "campaign-environment.json",
        "converged_period1_points": [r["rpm"] for r in campaign["results"] if r.get("convergence_status") == "PERIOD_1_CONVERGED"],
        "not_converged_points": [{"rpm":r.get("rpm"), "cycles":r.get("cycles_completed"), "stop":r.get("stop_reason")} for r in campaign["results"] if r.get("convergence_status") == "NOT_CONVERGED"],
        "admissibility_by_rpm": [{"rpm":r.get("rpm"), **admissibility_summary(r)} for r in campaign["results"]],
        "sensitivity": {"anchor_rpm": 9000, "preregistration": "sensitivity-preregistration.json", "variants": rows},
        "limits": [
            "This is the existing application four-control-volume 0D path, not the P5-C/P6 1D hybrid topology.",
            "E13-R1 is a 1D sensor contract and was not applied to 0D; native 0D period-1 convergence is not represented as E13 qualification.",
            "P5-C preflight using the custom full topology stopped with invalid species state; its diagnostic is preserved separately and no solver physics was changed.",
            "The 0D API has no restart facility; same-initial-state replay was exact but does not satisfy restart verification.",
            "Fresh delivery and fresh short-circuit are not separately ledgered by this 0D topology; four P6 species are not modeled; CFL is not applicable.",
            "Therefore KT100_MODEL_FIXTURE_V1 is not fully verified against all requested gates and no Yamaha performance claim is made."
        ],
        "full_topology_preflight": {"artifact": str(preflight_path.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha(preflight_path), "error": read(preflight_path).get("error"),
            "classification": "FAILED_PRECHECK_INVALID_SPECIES_STATE"},
        "p9_effect": "NONE",
        "p9_status": "P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA",
        "p9_contract_spec_sha256": sha(p9_spec_path),
        "experimental_validation": "NOT_PERFORMED",
        "predictive_validation": "NOT_CLAIMED",
        "artifacts": {
            "manifest_sha256": sha(manifest_path),
            "fixture_config_sha256": sha(fixture_path),
            "p9_contract_spec_sha256": sha(p9_spec_path),
            "campaign_fixture_config_sha256": sha(OUT / "fixture-config.json"),
            "campaign_sha256": sha(OUT / "campaign.json"),
            "sensitivity_sha256": sha(OUT / "sensitivity-runs" / "sensitivity.json"),
            "source_inventory_sha256": sha(OUT / "source-inventory.json")
        }
    }
    (OUT / "decision.json").write_text(json.dumps(receipt, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"converged_period1_points": receipt["converged_period1_points"],
        "not_converged_points": receipt["not_converged_points"],
        "decision": receipt["model_fixture_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
