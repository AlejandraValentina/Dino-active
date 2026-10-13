"""Read-only administrative preflight for the proposed IMPL2 identity.

This module validates identities and execution boundaries. It never creates
campaign artifacts or advances an engine.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .mechanical_loss_binding_v1 import resolve_mechanical_loss_v1


IDENTITY = Path("results/full-rpm-sweep-v1/implementation-v2-identity.json")
PROPOSAL = Path("results/full-rpm-sweep-v1/implementation-v2-preregistration-proposal.json")
PREREGISTRATION = Path("results/full-rpm-sweep-v1/preregistration.json")
CAMPAIGN_IDENTITY = Path("results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json")
CAMPAIGN_PREREGISTRATION = Path("results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json")


def audit_impl2_campaign_preflight(repository_root: str | Path, *,
                                   artifact_root: str | Path | None = None) -> dict[str, Any]:
    """Audit the frozen campaign identity and all 30 configurations without solver work."""
    from .full_rpm_sweep_v1 import preflight_full_rpm_sweep_v1, rpm_points

    root = Path(repository_root).resolve()
    identity_path = root / CAMPAIGN_IDENTITY
    prereg_path = root / CAMPAIGN_PREREGISTRATION
    identity = _json(identity_path)
    prereg = _json(prereg_path)
    if identity.get("implementation_version") != "FULL_RPM_SWEEP_V1_IMPL2":
        raise ValueError("IMPLEMENTATION_IDENTITY_MISMATCH")
    if prereg.get("implementation_version") != identity.get("implementation_version"):
        raise ValueError("PREREGISTRATION_IMPLEMENTATION_MISMATCH")
    prereg_hash = _sha256(prereg_path)
    actual_source = {name: _sha256(root / rel) for name, rel in
                     identity["source_paths"].items()}
    report = preflight_full_rpm_sweep_v1(prereg_path, repository_root=root)
    variants = prereg.get("variants", [])
    expected_root = str(identity.get("artifact_root", ""))
    selected_root = str(Path(artifact_root or os.environ.get(
        "DINO_ARTIFACT_ROOT", "E:/Dino-artifacts")).resolve() /
        "engine-physics-v1" / "full-rpm-sweep-v1-impl2")
    checks = {
        "explicit_impl2_identity": identity.get("implementation_version") == "FULL_RPM_SWEEP_V1_IMPL2",
        "campaign_not_authorized_or_started": identity.get("campaign_authorized") is False and
            identity.get("campaign_started") is False and prereg.get("campaigns_started") == 0,
        "preregistration_sha256": identity.get("preregistration_sha256") == prereg_hash,
        "source_hashes_exact": actual_source == identity.get("source_hashes"),
        "v1_isolation": identity.get("v1_artifacts_reusable") is False and
            identity.get("artifact_root") != "${DINO_ARTIFACT_ROOT}/engine-physics-v1/full-rpm-sweep-v1",
        "artifact_root_identity_match": expected_root == "${DINO_ARTIFACT_ROOT}/engine-physics-v1/full-rpm-sweep-v1-impl2",
        "artifact_root_selected": selected_root.endswith("engine-physics-v1\\full-rpm-sweep-v1-impl2") or
            selected_root.endswith("engine-physics-v1/full-rpm-sweep-v1-impl2"),
        "fast_disabled": prereg.get("evidence_pipeline") == "CONVENTIONAL_FULL_AUDIT" and
            prereg.get("fast_recipe_enabled") is False,
        "30_points_two_variants": len(variants) == 2 and len(rpm_points(prereg)) == 15,
        "runner_and_output_adapter_bound": all(actual_source.get(k) for k in
            ("runner", "output_adapter", "campaign_preflight")),
        "two_to_four_workers_within_preregistration":
            1 <= int(prereg.get("parallel_execution", {}).get("recommended_workers", 0)) <=
            int(prereg.get("parallel_execution", {}).get("maximum_workers", 0)) <= 4,
        "checkpoint_restart_contract": identity.get("checkpoint_schema") ==
            "FULL_RPM_SWEEP_V1_IMPL2_POINT_CHECKPOINT" and
            prereg.get("budget", {}).get("checkpoint_after_each_accepted_cycle") is True and
            prereg.get("budget", {}).get("resume_requires_exact_configuration_solver_detector_hashes") is True,
    }
    checks["underlying_scientific_preflight"] = report.get("preflight_status") == "PASS"
    report.update({"schema": "FULL_RPM_SWEEP_V1_IMPL2_CAMPAIGN_PREFLIGHT_V1",
                   "implementation_version": "FULL_RPM_SWEEP_V1_IMPL2",
                   "implementation_identity_sha256": _sha256(identity_path),
                   "preregistration_sha256": prereg_hash,
                   "artifact_root": selected_root,
                   "campaign_started": False,
                   "campaign_authorized": False,
                   "checks": checks,
                   "preflight_status": "PASS" if all(checks.values()) else "FAIL_CLOSED",
                   "campaigns_started": 0,
                   "solver_steps_started": 0})
    return report


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def audit_impl2_preflight(repository_root: str | Path, *, artifact_root: str | Path | None = None) -> dict[str, Any]:
    """Validate proposal/configuration identities without starting any point."""
    root = Path(repository_root).resolve()
    identity = _json(root / IDENTITY)
    proposal = _json(root / PROPOSAL)
    prereg_path = root / PREREGISTRATION
    prereg = _json(prereg_path)
    checks: dict[str, Any] = {}

    impl = identity.get("implementation_version")
    checks["implementation_identity"] = impl == "FULL_RPM_SWEEP_V1_IMPL2"
    checks["proposal_identity"] = proposal.get("implementation_version") == impl
    checks["proposal_not_authorized"] = (
        identity.get("campaign_started") is False
        and identity.get("status") == "PROPOSED_NOT_AUTHORIZED_NOT_EXECUTED"
        and proposal.get("campaign_started") is False
        and proposal.get("campaign_execution_authorized") is False
        and proposal.get("status") == "PROPOSAL_NOT_ACTIVE_NOT_AUTHORIZED"
    )
    impl_hashes = identity.get("source_identity", {}).get("solver_dependency_hashes", {})
    actual_solver_hashes = {
        name: _sha256(root / (name.replace(".", "/") + ".py"))
        for name in impl_hashes
    }
    checks["solver_dependency_hashes"] = actual_solver_hashes == impl_hashes
    source = identity.get("source_identity", {})
    source_files = {
        "campaign_runner_sha256": "scripts/full_rpm_sweep_v1_campaign.py",
        "geometry_benchmark_script_sha256": "scripts/benchmark_full_rpm_sweep_v1_geometry_cache.py",
        "sampling_profiler_sha256": "scripts/profile_full_rpm_sweep_v2_sampling.py",
        "segmented_evidence_codec_sha256": "motorsim/full_rpm_evidence_impl2.py",
        "fast_evidence_parallel_benchmark_sha256": "scripts/benchmark_full_rpm_sweep_v2_architecture.py",
    }
    actual_source_hashes = {}
    for field, relative in source_files.items():
        path = root / relative
        if path.is_file():
            actual_source_hashes[field] = _sha256(path)
    checks["producer_and_benchmark_hashes"] = actual_source_hashes == {
        field: source.get(field) for field in source_files
    }

    proposal_variants = proposal.get("unchanged_scientific_contract", {}).get("variants", [])
    prereg_variants = prereg.get("variants", [])
    checks["explicit_configuration_and_loss_models"] = (
        len(proposal_variants) == len(prereg_variants) == 2
        and all(isinstance(v.get("mechanical_loss_model"), dict) for v in proposal_variants)
        and all(isinstance(v.get("mechanical_loss_model"), dict) for v in prereg_variants)
    )
    resolved = []
    for variant in prereg_variants:
        result = resolve_mechanical_loss_v1(
            preregistration_path=prereg_path,
            variant_id=variant["variant_id"], repository_root=root,
        )
        resolved.append({
            "variant_id": variant["variant_id"],
            "fixture_sha256": result.fixture_sha256,
            "engine_configuration_sha256": result.engine_configuration_sha256,
            "mechanical_loss_model_sha256": result.model_sha256,
            "fallback_used": result.provenance["fallback_used"],
        })
    checks["mechanical_model_provenance"] = all(not row["fallback_used"] for row in resolved)

    prereg_hash = hashlib.sha256(prereg_path.read_bytes()).hexdigest()
    checks["preregistration_binding"] = (
        identity.get("based_on_preregistration_sha256") == prereg_hash
        and proposal.get("source_preregistration_file_sha256") == prereg_hash
    )
    compat = identity.get("compatibility", {})
    checks["v1_isolation_and_fail_closed"] = (
        compat.get("v1_checkpoints_reusable") is False
        and compat.get("v1_dependency_hash_set_matches") is False
        and compat.get("v1_workspace_preflight") == "FAIL_CLOSED_SOURCE_HASH_MISMATCH"
        and compat.get("distinct_campaign_id_and_output_root") is True
        and compat.get("v1_primaries_and_manifest") == "PRESERVED_READ_ONLY"
    )

    root_template = identity.get("artifact_root", "")
    checks["distinct_artifact_root"] = (
        "full-rpm-sweep-v1-impl2" in root_template
        and root_template != "${DINO_ARTIFACT_ROOT}/engine-physics-v1/full-rpm-sweep-v1"
    )
    external = Path(artifact_root or os.environ.get("DINO_ARTIFACT_ROOT", "E:/Dino-artifacts")).resolve()
    output = external / "engine-physics-v1" / "full-rpm-sweep-v1-impl2"
    historical = external / "engine-physics-v1" / "full-rpm-sweep-v1"
    checks["artifact_paths_isolated"] = not output.is_relative_to(historical) and not historical.is_relative_to(output)
    observed = []
    if output.exists():
        observed = [str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()]
    campaign_artifact_paths = [name for name in observed
                               if Path(name).name == "campaign.json"
                               or Path(name).name in {"checkpoint.json", "result.json"}]
    baseline_diagnostic_files = [name for name in observed
                                 if "legacy-primary" in Path(name).name]
    checks["no_v1_campaign_artifacts_or_campaign_started"] = (
        identity.get("campaign_started") is False
        and not campaign_artifact_paths
        and all(name.startswith("diagnostics\\") or name.startswith("diagnostics/")
                for name in baseline_diagnostic_files)
    )

    from scripts.full_rpm_sweep_v1_campaign import _parallel_worker_plan
    try:
        import psutil
        available_memory = int(psutil.virtual_memory().available)
    except ImportError as exc:
        raise RuntimeError("psutil is required for resource-bounded IMPL2 preflight") from exc
    worker_plans = {
        str(count): _parallel_worker_plan(
            count, 4096 * 1024 * 1024, available_memory_bytes=available_memory
        )
        for count in (1, 2, 4)
    }
    checks["worker_memory_bounds"] = all(
        1 <= plan["effective_workers"] <= int(count)
        and plan["effective_workers"] * plan["reserve_per_worker_bytes"]
        <= min(plan["memory_budget_bytes"], plan["available_memory_bytes"])
        for count, plan in worker_plans.items()
    )

    checks["checkpoint_restart_evidence_present"] = (
        (root / "results/full-rpm-sweep-v1/parallel-restart-validation-receipt.json").is_file()
        and (root / "tests/test_full_rpm_sweep_v1_impl2_checkpoint_d1d2.py").is_file()
    )
    checks["no_campaign_execution"] = True
    return {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_NON_EXECUTING_PREFLIGHT_V1",
        "implementation_version": impl,
        "status": "PASS" if all(checks.values()) else "FAIL_CLOSED",
        "campaign_started": False,
        "campaign_execution_authorized": False,
        "no_campaign_execution": True,
        "artifact_root": str(output),
        "observed_impl2_files": observed,
        "worker_plans_4gib_budget": worker_plans,
        "resolved_configurations": resolved,
        "checks": checks,
    }
