"""Read-only falsification probes for frozen Dino 8b371e2 integration findings.

Run with the reviewed repository's pinned Windows Python environment:
  .venv-build/Scripts/python.exe independent_integration_probes.py --repo REPO --output EXTERNAL.json

This executes no solver integration and makes no changes to the reviewed repo.
Fixture writes and miniature Git commits are confined to external temporary dirs.
Exit 0 means the historical defect hypotheses were reproduced, not that product
acceptance passed. Do not use these expected defects as future product contracts.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

sys.dont_write_bytecode = True
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    if args.output and args.output.resolve().is_relative_to(repo):
        parser.error("output must be outside reviewed repository")
    initial_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo)
    sys.path.insert(0, str(repo))
    from PySide6.QtWidgets import QApplication
    from motorsim import engine_platform
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_desktop import FourStrokeConfigEditor, FourStrokeResults
    from motorsim.desktop.four_stroke_project import project_from_example
    from motorsim.dino4t import runner

    app = QApplication.instance() or QApplication([])
    probe_root = Path(tempfile.mkdtemp(prefix="dino-independent-integration-audit-"))
    if probe_root.resolve().is_relative_to(repo):
        raise RuntimeError("temporary fixtures must be outside repository")
    result = {
        "schema": "DINO_INDEPENDENT_INTEGRATION_AUDIT_PROBES_V1",
        "reviewed_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "fixture_root": str(probe_root), "solver_integrations": 0,
        "note": "Expected historical defects are being falsified; FINDINGS_REPRODUCED is not product PASS."
    }

    project = project_from_example("audit-no-op-editor")
    project["base_engine"]["geometry"]["rod_mm"] = 180.12345678912345
    project["base_identity_sha256"] = engine_platform.identity("4T", project["base_engine"])
    context = DesktopContext(project)
    before = deepcopy(context.engine())
    editor = FourStrokeConfigEditor(context)
    editor.apply()
    result["no_op_editor"] = {
        "before": before["geometry"]["rod_mm"],
        "after": context.engine()["geometry"]["rod_mm"],
        "identity_changed": engine_platform.identity("4T", before) != engine_platform.identity("4T", context.engine()),
    }
    editor.close()

    source_root = repo / "results/dino4t-ab-engineering-v1/runs"
    project = json.loads((source_root / "dino4t-synthetic-ab-v1.dino.json").read_text(encoding="utf-8"))
    fixture_refs = []
    for index, ref in enumerate(project["run_references"]):
        source = source_root / "runs" / ref["run_id"]
        target = probe_root / "real-result-copies" / ref["run_id"]
        artifacts = target / "artifacts"
        artifacts.mkdir(parents=True)
        for name in ("summary.json", "config_resolved.json", "trace_last_cycle.csv"):
            shutil.copy2(source / "artifacts" / name, artifacts / name)
        meta = json.loads((source / "run.json").read_text(encoding="utf-8"))
        meta.update(summary_path=str(artifacts / "summary.json"),
                    config_path=str(artifacts / "config_resolved.json"),
                    trace_path=str(artifacts / "trace_last_cycle.csv"))
        (target / "run.json").write_text(json.dumps(meta), encoding="utf-8")
        fixture_ref = deepcopy(ref)
        fixture_ref["path"] = str(artifacts / "summary.json")
        fixture_refs.append(fixture_ref)
        if index == 0:
            original_trace_sha = digest(artifacts / "trace_last_cycle.csv")
            (artifacts / "trace_last_cycle.csv").write_text(
                "theta,p,p_intake_port,p_exhaust_port\n"
                "0,4200000,2400000,1700000\n"
                "720,4200000,2400000,1700000\n", encoding="utf-8")
            changed_trace_sha = digest(artifacts / "trace_last_cycle.csv")
    project["run_references"] = fixture_refs
    context = DesktopContext(project)
    view = FourStrokeResults(context)
    view.select_run(0)
    result["trace_tamper"] = {
        "loaded": len(view.loaded), "history": view.history.item(0).text(),
        "plotted_cylinder_bar": view.pressure_plot.series[0]["points"][0]["value"],
        "summary_digest_preserved": digest(fixture_refs[0]["path"]) == fixture_refs[0]["result_sha256"],
        "original_trace_sha256": original_trace_sha, "changed_trace_sha256": changed_trace_sha,
    }
    view.refresh()
    before_stale = {"loaded": len(view.loaded), "summary_rows": view.summary.rowCount(),
                    "pressure_series": len(view.pressure_plot.series)}
    for ref in context.project["run_references"]:
        ref["path"] = str(probe_root / "does-not-exist-summary.json")
    view.refresh()
    result["stale_detail"] = {
        "before": before_stale,
        "after": {"loaded": len(view.loaded), "selected_history": view.history.currentItem().text(),
                  "summary_rows": view.summary.rowCount(), "pressure_series": len(view.pressure_plot.series),
                  "first_metric": view.summary.item(0, 0).text(), "first_value": view.summary.item(0, 1).text()},
    }
    result["pressure_axis"] = {"series_x_key": "theta", "series_has_x_label": False,
                               "shared_plot_fallback": "RPM",
                               "basis": "four_stroke_desktop.py pressure series and plot.py x_label fallback"}
    view.close()
    app.processEvents()

    fixture = probe_root / "miniature-git-scope"
    (fixture / "motorsim/dino4t").mkdir(parents=True)
    (fixture / "configs/dino4t").mkdir(parents=True)
    fake_runner = fixture / "motorsim/dino4t/runner.py"
    shared = fixture / "motorsim/kinematics.py"
    omitted = fixture / "configs/dino4t/example_single_cylinder_500cc.json"
    fake_runner.write_text("# probe\n")
    shared.write_text("# original shared dependency\n")
    omitted.write_text('{"synthetic":1}\n')

    def git(*command):
        return subprocess.check_output(["git", *command], cwd=fixture, text=True, stderr=subprocess.DEVNULL)

    git("init", "-q")
    git("add", ".")
    git("-c", "user.name=Audit Fixture", "-c", "user.email=audit@example.invalid", "commit", "-qm", "scope fixture")
    shared.write_text("# changed shared dependency\n")
    with patch.object(runner, "__file__", str(fake_runner)):
        result["source_dirty_scope"] = {"root_status": git("status", "--porcelain").strip(),
                                        "reported_4t_code_dirty": runner._git_dirty()}
    shared.write_text("# original shared dependency\n")
    omitted.write_text('{"synthetic":2}\n')
    provenance = runpy.run_path(str(repo / "packaging/build_provenance.py"))
    provenance["ensure_packaged_inputs_clean"](fixture)
    result["packaging_dirty_scope"] = {
        "root_status": git("status", "--porcelain").strip(), "ensure_packaged_inputs_clean": "accepted",
        "fingerprint": provenance["unrelated_dirty_fingerprint"](fixture),
    }
    manifest = provenance["input_manifest"](repo)
    needle = "configs/dino4t/example_single_cylinder_500cc.json"
    result["manifest_omission"] = {
        "consumed_by_spec": needle in (repo / "packaging/MotorSim.spec").read_text(encoding="utf-8"),
        "present_in_manifest": needle in [item["path"] for item in manifest["files"]],
        "manifest_sha256": manifest["sha256"], "count": len(manifest["files"]),
    }
    final_status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo)
    result["reviewed_repository_status_unchanged"] = initial_status == final_status
    reproduced = {
        "INT-01": result["no_op_editor"]["identity_changed"],
        "INT-02": result["trace_tamper"]["loaded"] == 2 and result["trace_tamper"]["plotted_cylinder_bar"] == 42.0,
        "INT-03": result["stale_detail"]["after"]["loaded"] == 0 and result["stale_detail"]["after"]["summary_rows"] > 0
                  and result["stale_detail"]["after"]["pressure_series"] > 0,
        "INT-04": not result["manifest_omission"]["present_in_manifest"]
                  and result["packaging_dirty_scope"]["ensure_packaged_inputs_clean"] == "accepted",
        "INT-05": result["source_dirty_scope"]["reported_4t_code_dirty"] is False,
    }
    result["findings_reproduced"] = reproduced
    result["result"] = "FINDINGS_REPRODUCED" if all(reproduced.values()) else "HYPOTHESIS_NOT_REPRODUCED"
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))
    return 0 if all(reproduced.values()) and result["reviewed_repository_status_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
