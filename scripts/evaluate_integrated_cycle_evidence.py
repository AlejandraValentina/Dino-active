"""Evaluate saved integrated-cycle evidence without rerunning the engine."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT, PeriodicDetector, compare_cycles,
)
from motorsim.integrated_2t import audit_integrated_cycle_primary  # noqa: E402

PERIODICITY_CONTRACT = ROOT / "motorsim/reference_harness/convergence.py"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _comparison_summary(result: dict) -> dict:
    summary = {"status": result["status"]}
    if result["status"] == "INVALID":
        summary["reason"] = result["reason"]
        return summary
    metrics = result["metrics"]
    failed = [(name, value) for name, value in metrics.items()
              if not value["passed"]]
    summary["metric_count"] = len(metrics)
    summary["failed_metric_count"] = len(failed)
    if failed:
        name, metric = max(failed, key=lambda item: item[1]["value"] / item[1]["threshold"])
        summary["worst_failed_metric"] = {
            "name": name,
            "value": metric["value"],
            "threshold": metric["threshold"],
        }
    return summary


def evaluate(output_dir: Path, preregistration_path: Path | None = None) -> dict:
    output_dir = output_dir.resolve()
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    horizon = manifest.get("horizon_cycles")
    if (manifest.get("schema") != "MOTORSIM_COMMERCIAL_CYCLE_PRODUCER_MANIFEST_V1" or
            type(horizon) is not int or horizon < 2 or
            manifest.get("output_cycle_count") != horizon):
        raise ValueError("cycle producer manifest is malformed or incomplete")
    preregistration = None
    if preregistration_path is not None:
        preregistration_path = preregistration_path.resolve()
        relative = preregistration_path.relative_to(ROOT).as_posix()
        preregistration = json.loads(preregistration_path.read_text(encoding="utf-8-sig"))
        commit = manifest.get("preregistration_commit")
        committed = subprocess.run(
            ["git", "show", f"{commit}:{relative}"], cwd=ROOT,
            check=True, capture_output=True).stdout
        committed_document = json.loads(committed.decode("utf-8-sig"))
        if committed_document != preregistration:
            raise ValueError("preregistration differs from its recorded Git blob")
        subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                       cwd=ROOT, check=True, capture_output=True)
        if (_canonical_sha256(preregistration) != manifest.get("preregistration_sha256") or
                preregistration.get("fixture_id") != manifest.get("fixture_id") or
                preregistration.get("horizon_cycles") != horizon or
                preregistration.get("restart_cycle") != manifest.get("restart_cycle") or
                preregistration.get("cycle_convergence_contract_sha256") !=
                _sha256(PERIODICITY_CONTRACT)):
            raise ValueError("preregistration binding does not match cycle evidence")
        producer_commit = preregistration.get("producer_commit")
        if producer_commit is not None:
            producer_path = ROOT / "scripts/produce_integrated_cycle_evidence.py"
            relative_producer = producer_path.relative_to(ROOT).as_posix()
            producer_blob = subprocess.run(
                ["git", "show", f"{producer_commit}:{relative_producer}"], cwd=ROOT,
                check=True, capture_output=True).stdout.replace(b"\r\n", b"\n")
            producer_source = producer_path.read_bytes().replace(b"\r\n", b"\n")
            subprocess.run(["git", "merge-base", "--is-ancestor", producer_commit, "HEAD"],
                           cwd=ROOT, check=True, capture_output=True)
            if (producer_blob != producer_source or
                    manifest.get("producer_commit") != producer_commit or
                    manifest.get("producer_source_sha256") != _sha256_bytes(producer_source)):
                raise ValueError("producer source binding does not match cycle evidence")
    elif manifest.get("fixture_status") == "HISTORICAL_SUPERSEDED_BY_POSTHOC_AUDIT":
        raise ValueError("historical fixture evaluation requires its preregistration")
    if (manifest.get("detector_source_sha256") is not None and
            manifest["detector_source_sha256"] != _sha256(PERIODICITY_CONTRACT)):
        raise ValueError("periodicity detector source differs from campaign manifest")
    restart = json.loads((output_dir / "restart-audit.json").read_text(encoding="utf-8"))
    if restart.get("status") != "EXACT_REPLAY_PASS" or restart.get("snapshot_equal") is not True:
        raise ValueError("exact restart replay gate is not satisfied")

    detector = PeriodicDetector()
    detector_updates = []
    lag1 = []
    lag2 = []
    cycle_artifacts = []
    primary_audits = []
    primary_rejections = []
    prior = []
    configuration_hash = None
    for index in range(1, horizon + 1):
        path = output_dir / f"cycle-{index:03d}.json.gz"
        if not path.is_file():
            raise ValueError(f"missing cycle artifact {path.name}")
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            record = json.load(stream)
        schema = record.get("schema")
        if (schema not in {"MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V2",
                           "MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V3"} or
                record.get("cycle_index") != index or
                record.get("contract") != CONTRACT or
                record.get("cycle_start_deg") != (index - 1) * 360.0 or
                record.get("cycle_end_deg") != index * 360.0 or
                record.get("admissible") is not True):
            raise ValueError(f"cycle {index} fails identity, span, contract or admissibility")
        if schema == "MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V3":
            audit = audit_integrated_cycle_primary(record)
            if (record["evidence_binding"].get("runner_sha256") !=
                    manifest.get("producer_source_sha256")):
                raise ValueError(f"cycle {index} producer hash differs from campaign manifest")
            primary_audits.append({"cycle": index, **audit})
            primary_rejections.extend(record["rejected_trials"])
        elif preregistration is not None or manifest.get("fixture_id") != "TEST":
            raise ValueError("registered campaign requires auditable primary schema V3")
        else:
            # Isolated detector tests use minimal V2 projections; these cannot
            # satisfy a preregistered fixture campaign or a closure gate.
            primary_audits.append({"cycle": index,
                                   "status": "TEST_PROJECTION_ONLY_NO_PHYSICAL_AUDIT"})
        if configuration_hash is None:
            configuration_hash = record.get("configuration_hash")
        elif record.get("configuration_hash") != configuration_hash:
            raise ValueError(f"cycle {index} has a configuration identity mismatch")

        # The detector compares only these primary observables. Keeping the full
        # multi-megabyte trajectories in its history is unnecessary and costly.
        projection = {key: record[key] for key in
                      ("cycle_index", "configuration_hash", "contract", "observables")}
        if len(prior) >= 1:
            lag1.append({"older_cycle": index - 1, "later_cycle": index,
                         **_comparison_summary(compare_cycles(prior[-1], projection))})
        if len(prior) >= 2:
            lag2.append({"older_cycle": index - 2, "later_cycle": index,
                         **_comparison_summary(compare_cycles(prior[-2], projection))})

        if detector.classification is None:
            update = detector.update(projection)
            outcomes = update["outcomes"]
            row = {
                "cycle": index,
                "lag1": (_comparison_summary(outcomes["lag1"])
                         if "lag1" in outcomes else None),
                "lag2_branch": outcomes.get("lag2_branch"),
                "lag2": (_comparison_summary(outcomes["lag2"])
                         if "lag2" in outcomes else None),
                "lag1_streak": update["lag1_streak"],
                "branch_streaks": update["branch_streaks"],
                "classification": update["classification"],
            }
            detector_updates.append(row)
        prior.append(projection)
        prior = prior[-2:]
        cycle_artifacts.append({"cycle": index, "file": path.name,
                                "sha256": _sha256(path)})

    if (manifest.get("fixture_id") != "TEST" and
            primary_rejections != manifest.get("continuous_rejected_trials")):
        raise ValueError("cycle rejection logs differ from campaign runner manifest")

    lag1_counts = {status: sum(x["status"] == status for x in lag1)
                   for status in ("PASS", "FAIL", "INVALID")}
    lag2_counts = {status: sum(x["status"] == status for x in lag2)
                   for status in ("PASS", "FAIL", "INVALID")}
    return {
        "schema": "MOTORSIM_COMMERCIAL_CYCLE_EVALUATION_V1",
        "evidence_class": "SYNTHETIC_CONDITIONAL_ON_P4",
        "acceptance_claim": False,
        "fixture_id": manifest["fixture_id"],
        "horizon_cycles": horizon,
        "cycle_contract": CONTRACT,
        "configuration_hash": configuration_hash,
        "preregistration": (None if preregistration is None else {
            "commit": manifest["preregistration_commit"],
            "sha256": manifest["preregistration_sha256"],
            "producer_commit": manifest.get("producer_commit"),
            "producer_source_sha256": manifest.get("producer_source_sha256"),
        }),
        "restart_gate": {"status": restart["status"],
                         "restart_cycle": restart["restart_cycle"],
                         "compared_terminal_cycle": restart["compared_terminal_cycle"],
                         "snapshot_equal": restart["snapshot_equal"]},
        "cycle_artifacts": cycle_artifacts,
        "primary_evidence_audits": primary_audits,
        "decision_source_sha256": {
            "evaluator": _sha256_bytes(
                Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
            "detector_module": hashlib.sha256(inspect.getsource(
                sys.modules[PeriodicDetector.__module__]).encode("utf-8")).hexdigest(),
            "detector_contract_file": _sha256(PERIODICITY_CONTRACT),
        },
        "period_1_comparison_counts": lag1_counts,
        "period_2_comparison_counts": lag2_counts,
        "period_1_comparisons": lag1,
        "period_2_comparisons": lag2,
        "detector_updates": detector_updates,
        "detected_period": detector.detected_period,
        "converged_cycle": detector.converged_cycle,
        "classification": detector.classification or "NO_PERIODIC_CONVERGENCE_WITHIN_PREREGISTERED_HORIZON",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cycle_directory", type=Path)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.cycle_directory, args.preregistration)
        payload = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
        return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError,
            subprocess.CalledProcessError) as exc:
        parser.exit(2, f"evaluation blocked: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
