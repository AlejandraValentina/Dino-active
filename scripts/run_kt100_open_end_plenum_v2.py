"""Run the one preregistered KT100 open-end-plenum campaign (r6)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.reference_harness.campaign import run_fixed_points
from motorsim.reference_harness.evidence import write_json_gzip

PREREGISTRATION_COMMIT = "80fcf626e160ad582cacfafae2102a72b2df7bed"
CONFIG = ROOT / "configs/fixtures/kt100_open_end_plenum_v2.json"
OUTPUT = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r6-open-end-plenum-v2"


def assert_preregistration_precedes_campaign():
    subprocess.run(["git", "merge-base", "--is-ancestor",
                    PREREGISTRATION_COMMIT, "HEAD"], cwd=ROOT, check=True)
    receipt_path = "results/2t-commercial-core-20261002/preregistration/open-end-plenum-v2.json"
    receipt = json.loads((ROOT / receipt_path).read_text(encoding="utf-8"))
    committed = json.loads(subprocess.check_output(
        ["git", "show", f"{PREREGISTRATION_COMMIT}:{receipt_path}"],
        cwd=ROOT, text=True, encoding="utf-8"))
    if committed != receipt:
        raise RuntimeError("working preregistration differs from its frozen commit")
    if receipt.get("campaign_started") is not False or receipt.get("status") != "PREREGISTERED_BEFORE_IMPLEMENTATION_AND_KT100_CAMPAIGN":
        raise RuntimeError("OPEN_END_PLENUM_V2 preregistration gate is not intact")
    if receipt.get("campaign", {}).get("output", "").rstrip("/") != str(OUTPUT.relative_to(ROOT)).replace("\\", "/"):
        raise RuntimeError("campaign output differs from its preregistered destination")


def main():
    assert_preregistration_precedes_campaign()
    if not CONFIG.is_file():
        raise FileNotFoundError("run scripts/build_kt100_open_end_plenum_v2.py first")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to reuse campaign directory: {OUTPUT}")
    results = run_fixed_points(config, OUTPUT)
    write_json_gzip(OUTPUT / "campaign-summary.json.gz", results)
    for result in results:
        print(result["rpm"], result["classification"],
              result["complete_cycles"], result["converged_cycle"])


if __name__ == "__main__":
    main()
