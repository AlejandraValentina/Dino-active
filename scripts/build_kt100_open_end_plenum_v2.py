"""Create the separately versioned, preregistered KT100 V2 boundary config."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "configs/fixtures/kt100_hybrid_model_fixture_v2.json"
OUTPUT = ROOT / "configs/fixtures/kt100_open_end_plenum_v2.json"
CAPABILITY = "OPEN_END_PLENUM_V2"


def build():
    base_bytes = BASE.read_bytes()
    config = json.loads(base_bytes)
    config = copy.deepcopy(config)
    config["fixture_id"] = "KT100_HYBRID_MODEL_FIXTURE_V2_OPEN_END_PLENUM_V2"
    config["base_v2"] = {
        "path": "configs/fixtures/kt100_hybrid_model_fixture_v2.json",
        "sha256": hashlib.sha256(base_bytes).hexdigest(),
        "changes": ["external boundary capability identity only"],
    }
    config["boundaries"]["external_boundary_capability"] = CAPABILITY
    config["boundaries"]["external_boundary_provenance"] = "SYNTHETIC_ASSUMPTION"
    config["boundary_model"] = {
        "id": CAPABILITY,
        "provenance": "SYNTHETIC_ASSUMPTION",
        "description": "ideal, isentropic, lossless stationary atmosphere/large plenum; not calibrated WB40",
    }
    return config


def main():
    config = build()
    OUTPUT.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print(OUTPUT.relative_to(ROOT))
    print(hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
