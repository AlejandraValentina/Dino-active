"""Adversarial source/bundle provenance tests; no solver runs or real builds."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

from motorsim import source_provenance as source
from test_c01_c03_provenance_boundary import _committed_tree, _git

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
import build_provenance as provenance
import build_windows as recipe
import bundle_inputs as declaration


def _root(tmp_path):
    root = tmp_path / "repository"
    _committed_tree(root)
    return root


def test_source_closure_tracks_shared_dependency_and_runtime_data(tmp_path):
    root = _root(tmp_path)
    before = source.capture_source_identity(root)
    assert before["status"] == "COMPLETE" and before["dirty"] is False
    assert {"motorsim/kinematics.py", "motorsim/gas1d/mesh.py",
            "configs/dino4t/example_single_cylinder_500cc.json"} <= {x["path"] for x in before["files"]}
    (root / "motorsim/kinematics.py").write_bytes(b"changed shared numerical source\n")
    after = source.capture_source_identity(root)
    assert after["dirty"] is True and after["inventory_sha256"] != before["inventory_sha256"]
    assert after["code_commit"] == before["code_commit"]
    assert after["reproducible_by_commit"] is False
    data = root / "motorsim/desktop/templates/single_cylinder_2t_starter_v1.json"
    data.write_bytes(b'{"changed": 1}\r\n')
    entry = next(x for x in source.capture_source_identity(root)["files"] if x["path"] == data.relative_to(root).as_posix())
    assert entry["sha256"] == hashlib.sha256(data.read_bytes()).hexdigest()
    assert "canonical_code_sha256" not in entry


def test_ignored_untracked_source_cannot_claim_clean(tmp_path):
    root = _root(tmp_path)
    (root / ".gitignore").write_text("ignored_runtime.py\n", encoding="utf-8")
    (root / "motorsim/ignored_runtime.py").write_text("untracked = True\n", encoding="utf-8")
    captured = source.capture_source_identity(root)
    assert captured["status"] == "COMPLETE" and captured["dirty"] is True
    assert any(x["path"] == "motorsim/ignored_runtime.py" for x in captured["files"])


@pytest.mark.parametrize("policy", [".gitattributes", ".gitignore"])
def test_git_policy_preimages_are_bound_and_dirty_policies_are_detected(tmp_path, policy):
    root = _root(tmp_path)
    path = root / policy
    path.write_bytes(b"# committed policy\n")
    _git(root, "add", policy)
    _git(root, "-c", "user.name=Provenance test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "policy preimage")
    captured = source.capture_source_identity(root)
    assert captured["status"] == "COMPLETE" and captured["dirty"] is False
    entry = next(x for x in captured["files"] if x["path"] == policy)
    assert entry["role"] == "GIT_POLICY" and "canonical_code_sha256" not in entry
    assert next(x for x in provenance.input_manifest(root)["files"] if x["path"] == policy)["role"] == "GIT_POLICY"
    assert any(x.source == path and x.destination == "."
               for x in declaration.bundle_data_inputs(root, "dino", tmp_path / "generated"))
    path.write_bytes(b"# altered identity policy\n")
    assert source.capture_source_identity(root)["dirty"] is True
    with pytest.raises(RuntimeError, match="gitattributes|gitignore"):
        provenance.ensure_packaged_inputs_clean(root)


@pytest.mark.parametrize("policy", [".gitattributes", ".gitignore"])
def test_missing_tracked_git_policy_is_incomplete(tmp_path, policy):
    root = _root(tmp_path)
    path = root / policy
    path.write_bytes(b"# tracked policy\n")
    _git(root, "add", policy)
    _git(root, "-c", "user.name=Provenance test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "tracked policy")
    path.unlink()
    captured = source.capture_source_identity(root)
    assert captured["status"] == "INCOMPLETE" and captured["dirty"] is not False
    assert any(policy in issue for issue in captured["issues"])
    with pytest.raises(RuntimeError, match="gitattributes|gitignore"):
        provenance.ensure_packaged_inputs_clean(root)


def test_git_failure_and_missing_dependency_never_claim_clean(monkeypatch, tmp_path):
    root = _root(tmp_path)
    (root / "motorsim/gas1d/mesh.py").unlink()
    captured = source.capture_source_identity(root)
    assert captured["status"] == "INCOMPLETE" and captured["dirty"] is not False
    monkeypatch.setattr(source, "_git", lambda *args: (_ for _ in ()).throw(OSError("no git")))
    unknown = source.capture_source_identity(root)
    assert unknown["status"] == "INCOMPLETE" and unknown["dirty"] is None
    assert unknown["code_commit"] is None


def test_eol_policies_distinguish_raw_bytes_from_canonical_python(tmp_path):
    root = _root(tmp_path)
    target = root / "motorsim/kinematics.py"
    target.write_bytes(b"x = 1\ny = 2\n")
    first = source.capture_source_identity(root)
    target.write_bytes(b"x = 1\r\ny = 2\r\n")
    second = source.capture_source_identity(root)
    assert first["inventory_sha256"] != second["inventory_sha256"]
    assert first["canonical_code_inventory_sha256"] == second["canonical_code_inventory_sha256"]


def test_source_capture_race_cannot_publish_false_clean(monkeypatch, tmp_path):
    root = _root(tmp_path)
    collect = source._collect
    calls = 0
    def changing_tree(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            (root / "motorsim/kinematics.py").write_bytes(b"changed during capture\n")
        return collect(*args, **kwargs)
    monkeypatch.setattr(source, "_collect", changing_tree)
    captured = source.capture_source_identity(root)
    assert captured["status"] == "INCOMPLETE" and captured["dirty"] is True
    assert captured["stable_during_capture"] is False
    assert "SOURCE_CHANGED_DURING_CAPTURE" in captured["issues"]


def test_packaged_identity_requires_every_actual_preimage(monkeypatch, tmp_path):
    root = _root(tmp_path)
    snapshot = source.capture_source_identity(root)
    metadata = {"source_commit": snapshot["code_commit"], "packaged_inputs_clean": True,
                "source_identity": snapshot}
    (root / "motorsim/build.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr(source, "_git", lambda *args: (_ for _ in ()).throw(OSError("no git")))
    packaged = source.capture_source_identity(root, build_metadata=metadata)
    assert packaged["status"] == "COMPLETE" and packaged["dirty"] is False
    assert packaged["origin"] == "PACKAGED_PREIMAGES"
    (root / "motorsim/kinematics.py").write_text("modified packaged source\n", encoding="utf-8")
    invalid = source.capture_source_identity(root, build_metadata=metadata)
    assert invalid["status"] == "INCOMPLETE" and invalid["dirty"] is True
    assert "PACKAGED_SOURCE_PREIMAGE_MISMATCH" in invalid["issues"]


def test_sparse_legacy_build_metadata_is_unknown_not_clean(tmp_path):
    root = _root(tmp_path)
    captured = source.capture_source_identity(root, build_metadata={
        "source_commit": "a" * 40, "packaged_inputs_clean": True})
    assert captured["status"] == "INCOMPLETE" and captured["dirty"] is None
    assert captured["code_commit"] is None


def test_historical_source_validator_is_pure_and_rejects_internal_mutations(monkeypatch, tmp_path):
    root = _root(tmp_path)
    record = source.capture_source_identity(root)
    monkeypatch.setattr(source, "_collect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("current files consulted")))
    assert source.validate_source_identity(record) == []
    for mutate in (
        lambda x: x.update(dirty=0),
        lambda x: x.update(stable_during_run=False),
        lambda x: x.update(code_commit="not a revision"),
        lambda x: x["files"][0].update(size_bytes=True),
        lambda x: x["files"][0].update(sha256="0" * 64),
        lambda x: x["files"].reverse(),
        lambda x: x["files"].pop(),
        lambda x: x.update(byte_policy={"raw": "normalized data"}),
    ):
        changed = copy.deepcopy(record)
        mutate(changed)
        assert source.validate_source_identity(changed)


def test_packaged_missing_or_extra_runtime_preimage_is_not_clean(tmp_path):
    root = _root(tmp_path)
    original = source.capture_source_identity(root)
    metadata = {"source_commit": original["code_commit"], "packaged_inputs_clean": True,
                "source_identity": original}
    (root / "motorsim/unregistered-runtime.json").write_bytes(b"{}")
    assert source.capture_source_identity(root, build_metadata=metadata)["dirty"] is True
    (root / "motorsim/unregistered-runtime.json").unlink()
    (root / "motorsim/gas1d/mesh.py").unlink()
    missing = source.capture_source_identity(root, build_metadata=metadata)
    assert missing["status"] == "INCOMPLETE" and missing["dirty"] is not False


@pytest.mark.parametrize("anchor", [
    "motorsim/dino4t/validation.py", "motorsim/dino4t/artifacts.py",
    "motorsim/desktop/four_stroke_artifacts.py", "motorsim/desktop/four_stroke_comparison.py",
])
def test_record_cannot_omit_verifier_after_regenerating_inventory_digests(tmp_path, anchor):
    root = _root(tmp_path)
    record = source.capture_source_identity(root)
    record.update(source._inventory([x for x in record["files"] if x["path"] != anchor]))
    assert any("omits a required" in issue for issue in source.validate_source_identity(record))


def test_native_model_metadata_does_not_use_the_legacy_model_id():
    root = Path(__file__).resolve().parents[1]
    value = provenance.package_model_metadata(root)
    assert value["models"]["four_stroke"] == "DINO4T_FOUNDATION_V1"
    assert value["legacy_models"]["four_stroke"].startswith("three-cv-")
    native = value["native_engine_models"]["four_stroke"]
    assert native["api"] == "DINO4T_API_V1"
    assert native["example_components"]["cylinder"] == "TWO_ZONE_EQUILIBRIUM_V1"
    assert native["example_components"]["valve_boundary"] == "QUASI_STEADY_RESTRICTION_V2"


def test_deleted_mandatory_native_config_is_rejected(tmp_path):
    root = _root(tmp_path)
    (root / "configs/dino4t/example_single_cylinder_500cc.json").unlink()
    with pytest.raises(FileNotFoundError, match="example_single_cylinder_500cc"):
        provenance.input_manifest(root)


def test_spec_consumption_is_covered_by_the_shared_manifest(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    generated = tmp_path / "generated"
    generated.mkdir()
    (generated / "build.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MOTORSIM_BUILD_INPUTS", str(generated))
    consumed = []
    def analysis(scripts, **kwargs):
        consumed.extend(Path(p) for p, destination in kwargs["datas"])
        return SimpleNamespace(pure=[], scripts=[], binaries=[], datas=list(kwargs["datas"]))
    namespace = {"SPECPATH": str(root / "packaging"), "Analysis": analysis,
                 "EXE": lambda *a, **k: None, "PYZ": lambda *a, **k: None,
                 "COLLECT": lambda *a, **k: None}
    exec(compile((root / "packaging/MotorSim.spec").read_bytes(), "MotorSim.spec", "exec"), namespace)
    manifest = {root / x["path"] for x in provenance.input_manifest(root)["files"]}
    assert set(consumed) - {generated / "build.json"} <= manifest
    assert root / "configs/dino4t/example_single_cylinder_500cc.json" in consumed


def test_new_declared_spec_data_automatically_enters_guard_and_manifest(monkeypatch, tmp_path):
    root = _root(tmp_path)
    custom = root / "new-data/custom.dat"
    custom.parent.mkdir()
    custom.write_bytes(b"explicit future input")
    _git(root, "add", ".")
    _git(root, "-c", "user.name=Provenance test", "-c", "user.email=test@example.invalid", "commit", "-qm", "declared data")
    changed = dict(declaration.STATIC_DATA)
    changed["dino"] = (*changed["dino"], ("new-data/custom.dat", "native-data"))
    monkeypatch.setattr(declaration, "STATIC_DATA", changed)
    assert "new-data/custom.dat" in {x["path"] for x in provenance.input_manifest(root)["files"]}
    assert any(x.source == custom for x in declaration.bundle_data_inputs(root, "dino", tmp_path / "generated"))
    custom.write_bytes(b"dirty new declared input")
    with pytest.raises(RuntimeError, match="custom.dat"):
        provenance.ensure_packaged_inputs_clean(root)


def test_external_consumed_bytes_and_copied_outputs_are_bound(tmp_path):
    root = _root(tmp_path)
    external = tmp_path / "outside.csv"
    external.write_bytes(b"original raw external data\r\n")
    inputs = [declaration.ConsumedInput(external, "case/trace.csv", "Ejemplos/Datos/trace.csv")]
    before = provenance.input_manifest(root, inputs)
    assert before["consumed_files"][0]["origin"] == "EXPLICIT_BYTE_INPUT"
    assert before["consumed_files"][0]["git_bound"] is False
    assert before["consumed_files"][0]["repository_path"] is None
    bundle = tmp_path / "bundle"
    copied = provenance.copy_consumed_inputs(bundle, inputs, before)
    provenance.verify_copied_files(copied)
    (bundle / "Ejemplos/Datos/trace.csv").write_bytes(b"altered output")
    with pytest.raises(RuntimeError, match="Final copied preimage"):
        provenance.verify_copied_files(copied)
    external.write_bytes(b"mutated after snapshot")
    with pytest.raises(RuntimeError, match="pre-build byte snapshot"):
        provenance.copy_consumed_inputs(bundle, inputs, before)
    with pytest.raises(RuntimeError, match="changed during the build"):
        provenance.verify_input_snapshot(root, before, inputs)


def test_final_guard_rejects_new_repository_input(tmp_path):
    root = _root(tmp_path)
    before = provenance.input_manifest(root)
    provenance.verify_input_snapshot(root, before)
    (root / "configs/dino4t/new.json").write_bytes(b"{}")
    with pytest.raises(RuntimeError, match="new.json"):
        provenance.verify_input_snapshot(root, before)


def test_ignored_static_data_cannot_be_git_bound_clean(tmp_path):
    root = _root(tmp_path)
    (root / ".gitignore").write_text("ignored.dat\n", encoding="utf-8")
    _git(root, "add", ".gitignore")
    _git(root, "-c", "user.name=Provenance test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "committed ignore policy")
    (root / "packaging/ignored.dat").write_bytes(b"silently ignored consumed input")
    with pytest.raises(RuntimeError, match="ignored.dat"):
        provenance.ensure_packaged_inputs_clean(root)


def test_explicit_local_untracked_data_does_not_claim_git_identity(tmp_path):
    root = _root(tmp_path)
    local = root / "local-results/data.csv"
    local.parent.mkdir()
    local.write_bytes(b"data identified by its bytes")
    item = declaration.ConsumedInput(local, "local-data.csv", "Ejemplos/data.csv")
    recorded = provenance.input_manifest(root, [item])["consumed_files"][0]
    assert recorded["origin"] == "EXPLICIT_BYTE_INPUT" and recorded["git_bound"] is False
    assert recorded["repository_path"] == "local-results/data.csv"


@pytest.mark.parametrize("logical", ["", "../escape", "/absolute", "C:/absolute", "back\\slash", "a/./b"])
def test_consumed_inputs_require_unambiguous_portable_labels(tmp_path, logical):
    with pytest.raises(ValueError):
        declaration.ConsumedInput(tmp_path / "source", logical)


def test_optional_periodic_plan_binds_project_and_every_copied_file(tmp_path):
    parent = tmp_path / "external"
    parent.mkdir()
    refs = []
    for index in range(6):
        folder = parent / str(index)
        folder.mkdir()
        result = folder / "custom-result.json"
        result.write_text(json.dumps({"periodicity": "PERIOD_1"}), encoding="utf-8")
        (folder / "secondary-trace.csv").write_bytes(b"full precise raw trace\r\n")
        refs.append({"path": f"./{index}/custom-result.json", "artifact_sha256": hashlib.sha256(result.read_bytes()).hexdigest()})
    project = parent / "project.json"
    project.write_text(json.dumps({"result_references": refs}), encoding="utf-8")
    portable, inputs = recipe.periodic_example_plan(project)
    assert len(inputs) == 13  # project + every result/secondary file, not just the six summaries
    assert all(x["path"].endswith("custom-result.json") for x in portable["result_references"])
    assert {x.source.name for x in inputs} == {"project.json", "custom-result.json", "secondary-trace.csv"}


def test_spec_output_verification_checks_actual_raw_preimages(tmp_path):
    root = _root(tmp_path)
    generated = tmp_path / "generated"
    generated.mkdir()
    metadata = generated / "build.json"
    metadata.write_bytes(b'{"clean":true}')
    manifest = provenance.input_manifest(root)
    bundle = tmp_path / "bundle"
    for target in ("gui", "dino", "worker"):
        for item in declaration.bundle_data_inputs(root, target, generated):
            output = bundle / "_internal" / item.destination / item.source.name
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(item.source, output)
    digest = hashlib.sha256(metadata.read_bytes()).hexdigest()
    provenance.verify_bundle_data(root, generated, bundle, manifest, digest)
    (bundle / "_internal/configs/dino4t/example_single_cylinder_500cc.json").write_bytes(b"wrong copied native config")
    with pytest.raises(RuntimeError, match="Packaged data preimage"):
        provenance.verify_bundle_data(root, generated, bundle, manifest, digest)
