from __future__ import annotations

import hashlib
import json
from pathlib import Path

from motorsim.mechanical_loss_binding_v1 import canonical_sha256
from scripts.full_rpm_sweep_v1_campaign import _ensure_campaign_provenance
from scripts.verify_full_rpm_sweep_v1_artifacts import verify_campaign


ROOT = Path(__file__).resolve().parents[1]
PREREG_PATH = ROOT / "results/full-rpm-sweep-v1/preregistration.json"


def test_external_bundle_verifies_without_repo_paths(tmp_path):
    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))
    root = tmp_path / "campaign"
    receipt = _ensure_campaign_provenance(root, prereg, canonical_sha256(prereg))
    points = []
    for variant in prereg["variants"]:
        for rpm in prereg["rpm_grid"]["points_rpm"]:
            points.append({"point_id": f"{variant['variant_id']}@{rpm}RPM",
                           "variant_id": variant["variant_id"], "rpm": rpm,
                           "classification": "NOT_STARTED", "result_path": None,
                           "checkpoint_path": None})
    provenance_path = root / "provenance/manifest.json"
    manifest = {
        "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_SUMMARY",
        "campaign_id": receipt["campaign_id"],
        "pre-registration_sha256": canonical_sha256(prereg),
        "campaign_status": "PREPARED", "campaigns_started": 0,
        "provenance_manifest": "provenance/manifest.json",
        "provenance_manifest_sha256": hashlib.sha256(provenance_path.read_bytes()).hexdigest(),
        "completed_or_checkpointed_points": points,
    }
    (root / "campaign.json").write_text(json.dumps(manifest), encoding="utf-8")
    report = verify_campaign(root)
    assert report["all_pass"] is True
    assert report["campaign_points"] == 30
    assert report["results_checked"] == 0
