"""CP2 source acceptance route used by the packaged Windows candidate."""
import json
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from motorsim.desktop.acceptance_cp2 import main


def test_cp2_acceptance_receipt_is_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    output = tmp_path / "acceptance"
    previous = os.environ.get("DINO_TEST_SETTINGS_ROOT")
    previous_license = os.environ.get("DINO_LICENSE_ROOT")
    try:
        assert main(["--output", str(output)]) == 0
        receipt = json.loads((output / "acceptance.json").read_text(encoding="utf-8"))
        assert receipt["result"] == "PASS"
        assert all(receipt["checks"].values())
        assert receipt["scientific_claims"]["experimental_validation"] == "NOT_PERFORMED"
    finally:
        for key, value in (("DINO_TEST_SETTINGS_ROOT", previous), ("DINO_LICENSE_ROOT", previous_license)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
