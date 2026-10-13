from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from motorsim.fast_recipe_v1 import (
    FastRecipeError,
    advance_cycle,
    build_recipe,
    canonical_bytes,
    read_recipe,
    reconstruct_primary,
    validate_recipe,
    write_recipe_atomic,
)
from motorsim.integrated_2t import (
    IntegratedEngine2T,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
    _integrated_nominal_step_end,
    _integrated_scheduled_angles,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"


@pytest.fixture(scope="module")
def recipe_bundle() -> dict:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    configuration = copy.deepcopy(fixture["engine_configuration"])
    configuration["reference_rpm"] = 4000.0

    conventional = IntegratedEngine2T.from_configuration_dict(configuration)
    conventional_start = conventional.snapshot()
    _, conventional_rejected = advance_cycle(conventional, 1, capture_trace=True,
                                               profile_capture=True)
    conventional_end = conventional.snapshot()
    conventional_primary = make_integrated_cycle_primary(
        conventional, conventional_start, conventional_end, 1,
        rejected_trials=conventional_rejected,
        runner_sha256="1" * 64)
    conventional_audit = audit_integrated_cycle_primary(conventional_primary)
    assert conventional_audit["recomputed"] is True

    fast = IntegratedEngine2T.from_configuration_dict(configuration)
    start = fast.snapshot()
    capture_timing: dict[str, float] = {}
    accepted, rejected = advance_cycle(fast, 1, capture_trace=False,
                                      timing=capture_timing)
    terminal = fast.fast_recipe_terminal_state()
    fast.compact_fast_recipe_cycle()
    next_checkpoint = fast.snapshot()
    recipe = build_recipe(
        configuration=configuration,
        cycle_index=1,
        cycle_start_snapshot=start,
        accepted_steps=accepted,
        rejected_trials=rejected,
        terminal_state=terminal,
        next_cycle_checkpoint=next_checkpoint,
        capture_runner_sha256="2" * 64,
    )
    return {"configuration": configuration, "conventional": conventional,
            "conventional_primary": conventional_primary,
            "conventional_end": conventional_end, "fast": fast,
            "fast_terminal": terminal, "recipe": recipe,
            "capture_timing": capture_timing}


def test_fast_recipe_reconstructs_canonical_primary_and_passes_existing_auditor(
    recipe_bundle: dict,
) -> None:
    recipe = recipe_bundle["recipe"]
    validate_recipe(recipe)
    primary = reconstruct_primary(recipe)
    audit = audit_integrated_cycle_primary(primary)

    assert audit["recomputed"] is True
    normalized_fast = copy.deepcopy(primary)
    normalized_conventional = copy.deepcopy(recipe_bundle["conventional_primary"])
    normalized_fast["evidence_binding"].pop("runner_sha256")
    normalized_conventional["evidence_binding"].pop("runner_sha256")
    assert canonical_bytes(normalized_fast) == canonical_bytes(normalized_conventional)
    assert primary["evidence_binding"]["runner_sha256"] == "2" * 64
    assert canonical_bytes(primary["conservation"]) == canonical_bytes(
        recipe_bundle["conventional_primary"]["conservation"])
    assert recipe["status"] == "CAPTURED_UNAUDITED"
    assert primary["observables"]
    assert primary["checkpoint_binding"]["end_accepted_steps"] == len(
        recipe["accepted_steps"])


def test_fast_cycle_terminal_state_and_ledgers_match_conventional(recipe_bundle: dict) -> None:
    timing = recipe_bundle["capture_timing"]
    assert timing["cycle_wall_seconds"] > 0
    assert timing["physical_advance_seconds"] >= 0
    assert timing["recipe_schedule_capture_seconds"] >= 0
    fast_state = recipe_bundle["fast_terminal"]
    conventional_state = recipe_bundle["conventional_end"]
    assert canonical_bytes(fast_state["state"]) == canonical_bytes(conventional_state["state"])
    assert canonical_bytes(fast_state["ledger"]) == canonical_bytes(conventional_state["ledger"])
    assert fast_state["accepted_steps"] == conventional_state["accepted_steps"]
    assert fast_state["rejected_steps"] == conventional_state["rejected_steps"]
    assert fast_state["time_s"] == conventional_state["time_s"]


def test_cycle_checkpoint_restore_continues_identically(recipe_bundle: dict) -> None:
    checkpoint = recipe_bundle["recipe"]["next_cycle_checkpoint"]
    uninterrupted = IntegratedEngine2T.from_configuration_dict(
        recipe_bundle["configuration"])
    resumed = IntegratedEngine2T.from_configuration_dict(recipe_bundle["configuration"])
    uninterrupted.restore(checkpoint)
    resumed.restore(checkpoint)
    target = _integrated_nominal_step_end(
        resumed, resumed.crank_angle_unwrapped_deg,
        720.0, _integrated_scheduled_angles(resumed, 720.0))
    delta = target - resumed.crank_angle_unwrapped_deg
    dt = delta / (6.0 * resumed.reference_rpm)
    uninterrupted.step(dt, delta, capture_trace=False)
    resumed.step(dt, delta, capture_trace=False)
    assert canonical_bytes(uninterrupted.state) == canonical_bytes(resumed.state)
    assert canonical_bytes(uninterrupted.ledger) == canonical_bytes(resumed.ledger)


def test_corrupt_recipe_rejected_before_any_engine_is_mutated(recipe_bundle: dict) -> None:
    recipe = copy.deepcopy(recipe_bundle["recipe"])
    recipe["accepted_steps"][0]["dt_s"] *= 2
    receiver = IntegratedEngine2T.from_configuration_dict(recipe_bundle["configuration"])
    before = receiver.snapshot()
    with pytest.raises(FastRecipeError, match="digest mismatch"):
        validate_recipe(recipe)
    assert receiver.snapshot() == before


def test_incompatible_configuration_and_cross_solver_hash_fail_closed(recipe_bundle: dict) -> None:
    recipe = copy.deepcopy(recipe_bundle["recipe"])
    other_configuration = copy.deepcopy(recipe_bundle["configuration"])
    other_configuration["reference_rpm"] += 100
    with pytest.raises(FastRecipeError, match="configuration"):
        validate_recipe(recipe, configuration=other_configuration)

    recipe = copy.deepcopy(recipe_bundle["recipe"])
    recipe["solver_dependency_hashes"]["motorsim.integrated_2t"] = "0" * 64
    recipe.pop("recipe_sha256")
    recipe["recipe_sha256"] = hashlib.sha256(canonical_bytes(recipe)).hexdigest()
    with pytest.raises(FastRecipeError, match="solver dependency"):
        validate_recipe(recipe)


def test_recipe_atomic_persistence_and_file_hash_binding(
    recipe_bundle: dict, tmp_path: Path,
) -> None:
    target = tmp_path / "cycle-001.recipe.json"
    file_sha = write_recipe_atomic(target, recipe_bundle["recipe"])
    restored = read_recipe(target, expected_file_sha256=file_sha)
    assert restored["recipe_sha256"] == recipe_bundle["recipe"]["recipe_sha256"]
    with pytest.raises(FastRecipeError, match="artifact hash"):
        read_recipe(target, expected_file_sha256="0" * 64)

    payload = target.read_bytes()
    target.write_bytes(payload[:-2] + b"  ")
    with pytest.raises(FastRecipeError):
        read_recipe(target)


def test_fast_step_does_not_create_a_restorable_midcycle_snapshot(
    recipe_bundle: dict,
) -> None:
    engine = IntegratedEngine2T.from_configuration_dict(recipe_bundle["configuration"])
    engine.step(1e-7, engine.reference_rpm * 6.0 * 1e-7, capture_trace=False)
    with pytest.raises(ValueError, match="not a restorable checkpoint"):
        engine.snapshot()
