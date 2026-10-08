"""Run the frozen five-point KT100 V2 exploratory synthetic campaign."""
from __future__ import annotations

import json
from pathlib import Path

from motorsim.reference_harness.campaign import run_fixed_points
from motorsim.reference_harness.evidence import write_json_gzip

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/fixtures/kt100_hybrid_model_fixture_v2.json"
OUTPUT = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r5"


def main():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    results = run_fixed_points(config, OUTPUT)
    write_json_gzip(OUTPUT / "campaign-summary.json.gz", results)
    for result in results:
        print(result["rpm"], result["classification"],
              result["complete_cycles"], result["converged_cycle"])


if __name__ == "__main__":
    main()
