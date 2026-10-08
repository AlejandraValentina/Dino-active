"""Regenerate and audit the strictly synthetic P9 pipeline fixtures."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.p9_pipeline import audit_dataset
from motorsim.p9_synthetic import generate_fixture

FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "p9_synthetic"
RESULT_ROOT = ROOT / "results" / "p9-pipeline-qualification-20261001"
EXPECTED = {
    "pass": "P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA",
    "fail": "PIPELINE_EXPECTED_FAIL",
    "inconclusive": "PIPELINE_EXPECTED_INCONCLUSIVE",
}


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def main() -> int:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    audits = {}
    fixture_rows = []
    for name, expected in EXPECTED.items():
        fixture = generate_fixture(FIXTURE_ROOT / f"synthetic_{name}", name)
        audit = audit_dataset(fixture)
        if audit["status"] != expected or audit["status"] == "P9_PASS":
            raise SystemExit(f"{name}: expected {expected}, got {audit['status']}")
        _write(RESULT_ROOT / f"{name}_audit.json", audit)
        audits[name] = audit["status"]
        manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
        fixture_rows.append({
            "scenario": name, "status": audit["status"],
            "operating_points": len(audit.get("operating_points", [])),
            "cycles_per_point": manifest["cycles_per_point"],
            "synthetic_label": manifest["synthetic_label"],
            "raw_files": [{"path": record["path"], "sha256": record["sha256"],
                           "size_bytes": record["size_bytes"]}
                          for record in manifest["raw_files"]],
        })
    spec_path = ROOT / "openspec" / "changes" / "p9-experimental-validation" / "specs" / "p9-experimental-validation" / "spec.md"
    spec_sha256 = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    prereg = json.loads((ROOT / "results" / "p9-readiness-20261001" / "preregistration.json").read_text(encoding="utf-8"))
    if spec_sha256 != prereg["frozen_openspec"]["spec_sha256"]:
        raise SystemExit("frozen P9 OpenSpec hash does not match preregistration")
    receipt = {
        "schema": "motorsim-p9-synthetic-pipeline-qualification-v1",
        "date": "2026-10-01", "scenarios": fixture_rows,
        "audits": audits, "frozen_contract_sha256": spec_sha256,
        "p9_status": "P9_PREREGISTERED_AWAITING_EXPERIMENTAL_DATA",
        "experimental_validation": "NOT_PERFORMED",
        "predictive_validation": "NOT_CLAIMED",
        "no_real_dataset_ingested": True, "no_motorsim_simulation_run": True,
        "no_calibration_or_comparison_performed": True,
        "p9_pass_emitted": False,
    }
    _write(RESULT_ROOT / "receipt.json", receipt)
    _write(RESULT_ROOT / "decision.json", {
        "classification": "P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA",
        "scope": "software pipeline only", "p9_experimental_decision": "NOT_PERFORMED",
        "reason": "all fixtures are explicitly synthetic and are ineligible for P9 decision-making",
        "receipt": "receipt.json",
    })
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
