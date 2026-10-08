import json
from pathlib import Path


CASE = (Path(__file__).resolve().parents[1] /
        "configs/reference_cases/honda_cr250r_2007_partial_v1.json")


def test_honda_reference_manifest_contains_only_published_engine_parameters():
    value = json.loads(CASE.read_text(encoding="utf-8"))
    assert value["case_status"] == "DOCUMENTED_PARTIAL_NOT_SIMULATION_READY"
    parameters = value["documented_parameters"]
    assert parameters["bore"]["value"] == 66.4
    assert parameters["stroke"]["value"] == 72.0
    assert parameters["compression_ratio"]["value"] == 8.5
    assert parameters["induction"]["value"] == "six-petal crankcase reed-valve"
    assert all(item["provenance"] == "DOCUMENTED" for item in parameters.values())
    assert all(item["value"] is None and item["provenance"] == "UNKNOWN"
               for item in value["unknown_parameters"].values())
    assert value["simulation_readiness"]["ready"] is False
    assert value["claims"]["simulation_executed"] is False
