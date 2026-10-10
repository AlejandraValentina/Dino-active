from __future__ import annotations

import concurrent.futures
import copy
import gzip
import hashlib
import json
import multiprocessing
import os
import shutil
import time
from pathlib import Path

import pytest

from scripts import full_rpm_sweep_v1_campaign as campaign


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PREREG_PATH = REPO_ROOT / "results/full-rpm-sweep-v1/preregistration.json"


def _write_text(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n",
                    encoding="utf-8")


def _diagnostic_real_fixture(root: Path) -> tuple[dict, dict, str]:
    """Clone a frozen integrated-engine config into an isolated diagnostic root."""
    source_prereg = json.loads(SOURCE_PREREG_PATH.read_text(encoding="utf-8"))
    source_variant = source_prereg["variants"][0]
    source_fixture_path = REPO_ROOT / source_variant["source_fixture_path"]
    source_fixture = json.loads(source_fixture_path.read_text(encoding="utf-8"))
    config = source_fixture["engine_configuration"]
    model = source_fixture["mechanical_loss_model"]
    fixture_id = "IMPL2_REAL_RUN_POINT_DIAGNOSTIC_A"
    fixture = {
        "fixture_id": fixture_id,
        "engine_configuration": config,
        "engine_configuration_sha256": campaign.canonical_sha256(config),
        "mechanical_loss_model": model,
    }
    fixture_relative = "diagnostic/fixture-a.json"
    fixture_path = root / fixture_relative
    _write_text(fixture_path, fixture)
    fixture_bytes = fixture_path.read_bytes()
    fixture_sha = hashlib.sha256(fixture_bytes).hexdigest()
    config_sha = campaign.canonical_sha256(config)
    model_sha = campaign.canonical_sha256(model)
    variant = copy.deepcopy(source_variant)
    variant.update({
        "variant_id": "IMPL2_REAL_RUN_POINT_DIAGNOSTIC_A",
        "fixture_id": fixture_id,
        "source_fixture_path": fixture_relative,
        "fixture_sha256": fixture_sha,
        "engine_configuration_sha256": config_sha,
        "declared_configuration_sha256": config_sha,
        "mechanical_loss_model": model,
        "mechanical_loss_model_sha256": model_sha,
    })
    prereg = {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_DIAGNOSTIC_PREREGISTRATION",
        "rpm_grid": {"points_rpm": [4000, 4100]},
        "horizon": {"max_complete_cycles_per_point": 3},
        "periodicity": {"contract": source_prereg["periodicity"]["contract"]},
        "periodicity_source_sha256": source_prereg["periodicity_source_sha256"],
        "variants": [variant],
    }
    prereg_relative = "diagnostic/preregistration.json"
    _write_text(root / prereg_relative, prereg)
    # _point_contract_hashes binds the production output adapter by path. This
    # copy is for test provenance only and does not alter or shadow source code.
    adapter_target = root / "motorsim/full_rpm_outputs_v1.py"
    adapter_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / "motorsim/full_rpm_outputs_v1.py", adapter_target)
    return prereg, variant, prereg_relative


def _real_run_point_spawn(root: str, prereg: dict, variant: dict, rpm: int,
                          output: str, resume: bool, cancel_event=None,
                          crash_at_checkpoint_replace: bool = False) -> dict:
    """Spawn entry point that executes the production _run_point function."""
    from scripts import full_rpm_sweep_v1_campaign as worker_campaign

    worker_campaign.ROOT = Path(root)
    worker_campaign.PREREGISTRATION = "diagnostic/preregistration.json"
    if crash_at_checkpoint_replace:
        real_replace = worker_campaign.os.replace

        def die_before_checkpoint_publish(source, destination):
            if Path(destination).name == "checkpoint.json":
                os._exit(91)
            return real_replace(source, destination)

        worker_campaign.os.replace = die_before_checkpoint_publish
    return worker_campaign._run_point(
        prereg, worker_campaign.canonical_sha256(prereg), variant, rpm,
        Path(output), resume=resume, started=time.monotonic(),
        budget_seconds=1800, update_campaign_manifest=False,
        cancel_event=cancel_event)


def _initial_manifest(output: Path, prereg: dict, variant: dict) -> Path:
    points = [{"point_id": f"{variant['variant_id']}@{rpm}RPM",
               "variant_id": variant["variant_id"], "rpm": rpm,
               "classification": "NOT_STARTED"}
              for rpm in prereg["rpm_grid"]["points_rpm"]]
    manifest_path = output / "campaign.json"
    campaign._write_json_atomic(manifest_path, {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_DIAGNOSTIC_MANIFEST",
        "campaigns_started": 0,
        "campaign_status": "PREPARED",
        "completed_or_checkpointed_points": points,
    })
    return manifest_path


def _coordinator_record(output: Path, rpm: int, result: dict) -> None:
    """Test coordinator is the only writer of the shared manifest."""
    manifest_path = output / "campaign.json"
    manifest = campaign._read_json(manifest_path)
    point_id = result["point_id"]
    row = next(item for item in manifest["completed_or_checkpointed_points"]
               if item["point_id"] == point_id)
    row.update({"classification": result["classification"],
                "cycles_completed": result.get("cycles_completed"),
                "next_cycle": result.get("next_cycle")})
    point_dir = output / row["variant_id"] / f"rpm-{rpm:05d}"
    checkpoint = point_dir / "checkpoint.json"
    result_path = point_dir / "result.json"
    row["checkpoint_path"] = (str(checkpoint.relative_to(output))
                              if checkpoint.is_file() else None)
    row["result_path"] = (str(result_path.relative_to(output))
                          if result_path.is_file() else None)
    if checkpoint.is_file():
        row["checkpoint_sha256"] = campaign._sha256(checkpoint.read_bytes())
    else:
        row.pop("checkpoint_sha256", None)
    if result_path.is_file():
        row["result_sha256"] = campaign._sha256(result_path.read_bytes())
    else:
        row.pop("result_sha256", None)
    campaign._write_json_atomic(manifest_path, manifest)


def _primary_rows(output: Path, variant_id: str, rpm: int, cycles: int) -> list[dict]:
    point_dir = output / variant_id / f"rpm-{rpm:05d}"
    rows = []
    for cycle in range(1, cycles + 1):
        primary_path = point_dir / f"cycle-{cycle:03d}.json.gz"
        assert primary_path.is_file()
        primary = json.loads(gzip.decompress(primary_path.read_bytes()))
        audit = campaign.audit_integrated_cycle_primary(primary)
        assert audit["recomputed"] is True
        conservation = primary["conservation"]
        assert abs(conservation["mass_residual_kg"]) < 1e-12
        assert abs(conservation["energy_residual_J"]) < 1e-9
        assert max(abs(value) for value in conservation["species_residual_kg"]) < 1e-12
        rows.append(primary)
    actual_cycles = sorted(path.name for path in point_dir.glob("cycle-*.json.gz"))
    assert actual_cycles == [f"cycle-{cycle:03d}.json.gz"
                             for cycle in range(1, cycles + 1)]
    assert sorted(path.name for path in (point_dir / "cycle-metrics").glob("cycle-*.json")) == [
        f"cycle-{cycle:03d}.json" for cycle in range(1, cycles + 1)]
    for previous, following in zip(rows, rows[1:]):
        assert previous["checkpoint_binding"]["end_fuel_combustion"] == \
            following["checkpoint_binding"]["start_fuel_combustion"]
        assert previous["checkpoint_binding"]["end_ledger"] == \
            following["checkpoint_binding"]["start_ledger"]
    return rows


def test_atomic_writers_use_unique_temps_flush_and_clean_on_replace_error(tmp_path, monkeypatch):
    target = tmp_path / "atomic.json"
    first = campaign._atomic_temp_path(target)
    second = campaign._atomic_temp_path(target)
    assert first != second
    assert campaign._ATOMIC_TEMP_RE.fullmatch(first.name)
    campaign._write_json_atomic(target, {"generation": 1})
    assert campaign._read_json(target) == {"generation": 1}
    with pytest.raises(OSError):
        with monkeypatch.context() as scoped:
            scoped.setattr(campaign.os, "replace",
                           lambda *_: (_ for _ in ()).throw(OSError("injected replace failure")))
            campaign._write_json_atomic(target, {"generation": 2})
    assert campaign._read_json(target) == {"generation": 1}
    assert not list(tmp_path.glob(".*.tmp"))

    primary = tmp_path / "cycle-001.json.gz"
    campaign._write_primary_gzip(primary, {"cycle": 1})
    assert json.loads(gzip.decompress(primary.read_bytes())) == {"cycle": 1}
    original_primary = primary.read_bytes()
    with pytest.raises(OSError):
        with monkeypatch.context() as scoped:
            scoped.setattr(campaign.os, "replace",
                           lambda *_: (_ for _ in ()).throw(OSError("injected gzip replace failure")))
            campaign._write_primary_gzip(primary, {"cycle": 2})
    assert primary.read_bytes() == original_primary
    assert not list(tmp_path.glob(".*.tmp"))


def _crash_atomic_first_write(root: str) -> None:
    from scripts import full_rpm_sweep_v1_campaign as child_campaign

    root_path = Path(root)
    target = root_path / "diagnostic" / "checkpoint.json"
    real_replace = child_campaign.os.replace

    def terminate_before_publish(source, destination):
        if Path(destination) == target:
            os._exit(92)
        return real_replace(source, destination)

    child_campaign.os.replace = terminate_before_publish
    child_campaign._write_json_atomic(target, {"schema": "CHECKPOINT_TEST", "cycle": 1})


def _crash_primary_first_write(target_path: str) -> None:
    from scripts import full_rpm_sweep_v1_campaign as child_campaign

    target = Path(target_path)
    real_replace = child_campaign.os.replace

    def terminate_before_publish(source, destination):
        if Path(destination) == target:
            os._exit(93)
        return real_replace(source, destination)

    child_campaign.os.replace = terminate_before_publish
    child_campaign._write_primary_gzip(target, {"incomplete": True})


def test_orphan_first_write_is_preserved_and_quarantined_after_abrupt_exit(tmp_path):
    context = multiprocessing.get_context("spawn")
    point_dir = tmp_path / "point"
    point_dir.mkdir()
    process = context.Process(target=_crash_atomic_first_write, args=(str(tmp_path),))
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 92
    assert not (tmp_path / "diagnostic/checkpoint.json").exists()
    orphan_candidates = list((tmp_path / "diagnostic").glob(".checkpoint.json.*.tmp"))
    assert len(orphan_candidates) == 1
    original_bytes = orphan_candidates[0].read_bytes()
    moved = campaign._quarantine_orphan_atomic_temps(tmp_path / "diagnostic")
    assert len(moved) == 1
    quarantined, target_name = moved[0]
    assert target_name == "checkpoint.json"
    assert quarantined.read_bytes() == original_bytes
    assert json.loads(quarantined.read_text(encoding="utf-8"))["cycle"] == 1


def test_real_run_point_restarts_only_from_orphan_temp_and_rejects_unknown_partial(
        tmp_path, monkeypatch):
    context = multiprocessing.get_context("spawn")
    sandbox = tmp_path / "repo-sandbox-first-primary"
    sandbox.mkdir()
    prereg, variant, _ = _diagnostic_real_fixture(sandbox)
    output = sandbox / "artifacts/first-primary"
    output.mkdir(parents=True)
    _initial_manifest(output, prereg, variant)
    rpm = prereg["rpm_grid"]["points_rpm"][0]
    point = output / variant["variant_id"] / f"rpm-{rpm:05d}"
    point.mkdir(parents=True)
    primary = point / "cycle-001.json.gz"
    worker = context.Process(target=_crash_primary_first_write, args=(str(primary),))
    worker.start()
    worker.join(timeout=20)
    assert worker.exitcode == 93
    assert not primary.exists()
    assert len(list(point.glob(".cycle-001.json.gz.*.tmp"))) == 1

    monkeypatch.setattr(campaign, "ROOT", sandbox)
    monkeypatch.setattr(campaign, "PREREGISTRATION", "diagnostic/preregistration.json")
    monkeypatch.setattr(campaign, "_advance_to_bounded",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(
                            campaign._CampaignDeadlineReached()))
    resumed = campaign._run_point(
        prereg, campaign.canonical_sha256(prereg), variant, rpm, output,
        resume=True, started=time.monotonic(), budget_seconds=1800,
        update_campaign_manifest=False)
    assert resumed["classification"] == "INTERRUPTED_CHECKPOINTED"
    assert not primary.exists()
    assert len(list((point / "_orphaned_atomic_writes").iterdir())) == 1
    assert (point / "checkpoint.json").is_file()
    assert campaign._load_checkpoint((point / "checkpoint.json"),
                                     resumed["bindings"])["next_cycle"] == 1

    unknown_rpm = prereg["rpm_grid"]["points_rpm"][1]
    unknown = output / variant["variant_id"] / f"rpm-{unknown_rpm:05d}"
    unknown.mkdir(parents=True)
    (unknown / "debug-notes.txt").write_text("unrecognized partial state", encoding="utf-8")
    with pytest.raises(FileExistsError, match="unrecognized partial point state"):
        campaign._run_point(
            prereg, campaign.canonical_sha256(prereg), variant, unknown_rpm, output,
            resume=True, started=time.monotonic(), budget_seconds=1800,
            update_campaign_manifest=False)


def test_real_run_point_spawn_interrupt_resume_matches_sequential_and_coordinator_hashes(
        tmp_path, monkeypatch):
    context = multiprocessing.get_context("spawn")
    sandbox = tmp_path / "repo-sandbox"
    sandbox.mkdir()
    prereg, variant, _ = _diagnostic_real_fixture(sandbox)
    prereg_sha = campaign.canonical_sha256(prereg)
    parallel_output = sandbox / "artifacts/parallel"
    parallel_output.mkdir(parents=True)
    manifest_path = _initial_manifest(parallel_output, prereg, variant)
    manifest_before_workers = manifest_path.read_bytes()
    point_rpms = prereg["rpm_grid"]["points_rpm"]

    with context.Manager() as manager:
        cancel_event = manager.Event()
        with concurrent.futures.ProcessPoolExecutor(
                max_workers=2, mp_context=context) as executor:
            futures = {rpm: executor.submit(
                _real_run_point_spawn, str(sandbox), prereg, variant, rpm,
                str(parallel_output), False, cancel_event)
                       for rpm in point_rpms}
            deadline = time.monotonic() + 600
            while time.monotonic() < deadline:
                statuses = []
                for rpm in point_rpms:
                    status_path = (parallel_output / variant["variant_id"] /
                                   f"rpm-{rpm:05d}" / "checkpoint-status.json")
                    if status_path.is_file():
                        statuses.append(campaign._read_json(status_path))
                if len(statuses) == len(point_rpms) and all(
                        status.get("cycles_completed", 0) >= 1 for status in statuses):
                    cancel_event.set()
                    break
                time.sleep(0.05)
            else:
                pytest.fail("real _run_point workers did not reach their first checkpoints")
            interrupted = {rpm: future.result(timeout=600)
                           for rpm, future in futures.items()}

    # Workers were configured update_campaign_manifest=False. The bytes must
    # remain untouched until this single coordinator records both checkpoints.
    assert manifest_path.read_bytes() == manifest_before_workers
    assert all(result["classification"] == "INTERRUPTED_CHECKPOINTED"
               for result in interrupted.values())
    for rpm, result in interrupted.items():
        point = parallel_output / variant["variant_id"] / f"rpm-{rpm:05d}"
        checkpoint = point / "checkpoint.json"
        assert checkpoint.is_file()
        assert result["cycles_completed"] >= 1
        _coordinator_record(parallel_output, rpm, result)
        manifest = campaign._read_json(manifest_path)
        row = next(item for item in manifest["completed_or_checkpointed_points"]
                   if item["rpm"] == rpm)
        assert row["checkpoint_sha256"] == campaign._sha256(checkpoint.read_bytes())

    resumed = {}
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=context) as executor:
        futures = {rpm: executor.submit(
            _real_run_point_spawn, str(sandbox), prereg, variant, rpm,
            str(parallel_output), True, None)
                   for rpm in point_rpms}
        resumed = {rpm: future.result(timeout=900) for rpm, future in futures.items()}
    for rpm, result in resumed.items():
        assert result["classification"] == "NO_CONVERGENCE_WITHIN_HORIZON"
        _coordinator_record(parallel_output, rpm, result)

    parallel_manifest = campaign._read_json(manifest_path)
    parallel_science = {}
    for rpm in point_rpms:
        row = next(item for item in parallel_manifest["completed_or_checkpointed_points"]
                   if item["rpm"] == rpm)
        point = parallel_output / variant["variant_id"] / f"rpm-{rpm:05d}"
        result_path = point / "result.json"
        checkpoint_path = point / "checkpoint.json"
        assert row["result_sha256"] == campaign._sha256(result_path.read_bytes())
        assert row["checkpoint_sha256"] == campaign._sha256(checkpoint_path.read_bytes())
        result = campaign._read_json(result_path)
        primary_rows = _primary_rows(parallel_output, variant["variant_id"], rpm, 3)
        parallel_science[rpm] = (result, primary_rows)

    # Same production _run_point, same preregistered test config, single
    # process, no cancellation. Timing receipts may differ; science may not.
    sequential_output = sandbox / "artifacts/sequential"
    sequential_output.mkdir(parents=True)
    _initial_manifest(sequential_output, prereg, variant)
    monkeypatch.setattr(campaign, "ROOT", sandbox)
    monkeypatch.setattr(campaign, "PREREGISTRATION", "diagnostic/preregistration.json")
    sequential_science = {}
    for rpm in point_rpms:
        result = campaign._run_point(
            prereg, prereg_sha, variant, rpm, sequential_output, resume=False,
            started=time.monotonic(), budget_seconds=1800,
            update_campaign_manifest=False)
        assert result["classification"] == "NO_CONVERGENCE_WITHIN_HORIZON"
        _coordinator_record(sequential_output, rpm, result)
        sequential_rows = _primary_rows(sequential_output, variant["variant_id"], rpm, 3)
        sequential_science[rpm] = (result, sequential_rows)

    for rpm in point_rpms:
        parallel_result, parallel_rows = parallel_science[rpm]
        sequential_result, sequential_rows = sequential_science[rpm]
        assert parallel_result["cycle_primaries"] == sequential_result["cycle_primaries"]
        assert [campaign._sha256(campaign._canonical_bytes(row)) for row in parallel_rows] == [
            campaign._sha256(campaign._canonical_bytes(row)) for row in sequential_rows]
        assert {key: value for key, value in parallel_result.items()
                if key != "performance_metrics"} == {
                    key: value for key, value in sequential_result.items()
                    if key != "performance_metrics"}

    # An otherwise valid checkpoint copied from another RPM must fail before
    # restore or any new cycle is written.
    mismatched_output = sandbox / "artifacts/mismatched"
    mismatched_output.mkdir(parents=True)
    _initial_manifest(mismatched_output, prereg, variant)
    source_rpm, target_rpm = point_rpms
    source_checkpoint = (parallel_output / variant["variant_id"] /
                         f"rpm-{source_rpm:05d}" / "checkpoint.json")
    target_dir = mismatched_output / variant["variant_id"] / f"rpm-{target_rpm:05d}"
    target_dir.mkdir(parents=True)
    shutil.copyfile(source_checkpoint, target_dir / "checkpoint.json")
    _coordinator_record(mismatched_output, target_rpm, {
        "point_id": f"{variant['variant_id']}@{target_rpm}RPM",
        "classification": "INTERRUPTED_CHECKPOINTED",
        "cycles_completed": 1, "next_cycle": 2})
    with pytest.raises(ValueError, match="checkpoint binding hash mismatch"):
        campaign._run_point(
            prereg, prereg_sha, variant, target_rpm, mismatched_output,
            resume=True, started=time.monotonic(), budget_seconds=1800,
            update_campaign_manifest=False)


def test_real_run_point_abrupt_worker_exit_recovers_first_checkpoint_write(tmp_path,
                                                                          monkeypatch):
    context = multiprocessing.get_context("spawn")
    sandbox = tmp_path / "repo-sandbox-crash"
    sandbox.mkdir()
    prereg, variant, _ = _diagnostic_real_fixture(sandbox)
    output = sandbox / "artifacts/crash-recovery"
    output.mkdir(parents=True)
    _initial_manifest(output, prereg, variant)
    rpm = prereg["rpm_grid"]["points_rpm"][0]
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=1, mp_context=context) as executor:
        future = executor.submit(
            _real_run_point_spawn, str(sandbox), prereg, variant, rpm,
            str(output), False, None, True)
        with pytest.raises((concurrent.futures.process.BrokenProcessPool, OSError)):
            future.result(timeout=600)
    point = output / variant["variant_id"] / f"rpm-{rpm:05d}"
    assert not (point / "checkpoint.json").exists()
    assert list(point.glob(".checkpoint.json.*.tmp"))
    assert (point / "cycle-001.json.gz").is_file()
    assert (point / "cycle-metrics/cycle-001.json").is_file()

    monkeypatch.setattr(campaign, "ROOT", sandbox)
    monkeypatch.setattr(campaign, "PREREGISTRATION", "diagnostic/preregistration.json")
    recovered = campaign._run_point(
        prereg, campaign.canonical_sha256(prereg), variant, rpm, output,
        resume=True, started=time.monotonic(), budget_seconds=1800,
        update_campaign_manifest=False)
    assert recovered["classification"] == "INTERRUPTED_CHECKPOINTED"
    assert recovered["recovered_from_orphaned_atomic_checkpoint"] is True
    preserved = list((point / "_orphaned_atomic_writes").iterdir())
    assert len(preserved) == 1
    _coordinator_record(output, rpm, recovered)
    result = campaign._run_point(
        prereg, campaign.canonical_sha256(prereg), variant, rpm, output,
        resume=True, started=time.monotonic(), budget_seconds=1800,
        update_campaign_manifest=False)
    assert result["classification"] == "NO_CONVERGENCE_WITHIN_HORIZON"
    _coordinator_record(output, rpm, result)
    final_manifest = campaign._read_json(output / "campaign.json")
    row = final_manifest["completed_or_checkpointed_points"][0]
    assert row["result_sha256"] == campaign._sha256((point / "result.json").read_bytes())
    assert row["checkpoint_sha256"] == campaign._sha256((point / "checkpoint.json").read_bytes())
    primaries = _primary_rows(output, variant["variant_id"], rpm, 3)
    assert all(campaign.audit_integrated_cycle_primary(primary)["recomputed"] is True
               for primary in primaries)
