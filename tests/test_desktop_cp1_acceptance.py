"""CP1 source acceptance route also used by the packaged Windows candidate."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from motorsim.desktop.acceptance_cp1 import main


def test_cp1_acceptance_receipt_is_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    output = tmp_path / "acceptance"
    previous = os.environ.get("DINO_TEST_SETTINGS_ROOT")
    try:
        assert main(["--output", str(output)]) == 0
        receipt = json.loads((output / "acceptance.json").read_text(encoding="utf-8"))
        assert receipt["result"] == "PASS"
        assert all(receipt["checks"].values())
        assert receipt["scientific_claims"]["experimental_validation"] == "NOT_PERFORMED"
    finally:
        if previous is None:
            os.environ.pop("DINO_TEST_SETTINGS_ROOT", None)
        else:
            os.environ["DINO_TEST_SETTINGS_ROOT"] = previous
