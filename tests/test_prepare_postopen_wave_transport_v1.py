import hashlib
import json

import pytest

from scripts.diagnostics.prepare_postopen_wave_transport_v1 import CASES, prepare


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(tmp_path):
    root = tmp_path / "source"
    files = {}
    for name in CASES:
        p = f"run/{name}"
        recipe = [{"angle_start_deg": float(a), "angle_end_deg": float(a + 15)}
                  for a in (13680, 13695, 13710, 13725)]
        values = {
            "configuration.json": {"id": name},
            "initial-checkpoint.json": {"schema": "ENGINE", "angle": 13680},
            "recipe.json": recipe,
            "terminal-state.json": {"schema": "FAST_RECIPE_V1_TERMINAL_STATE",
                                    "engine_schema": "ENGINE", "accepted_steps": 4,
                                    "crank_angle_unwrapped_deg": 13740},
            "receipt.json": {"status": "COMPLETE", "error": None,
                             "accepted_steps": 4, "wall_s": 10.0},
            "frames.json": [{"angle": 13680}, {"angle": 13740}],
        }
        for filename, value in values.items():
            files[f"{p}/{filename}"] = _write(root / f"{p}/{filename}", value)
    _write(root / "manifest.json", {"schema": "test", "files": files})
    return root


def test_preparation_binds_four_complete_cases_and_projects_cost_without_solver(tmp_path):
    result = prepare(_source(tmp_path))
    assert len(result["cases"]) == 4
    assert result["solver_steps_executed"] == 0
    assert result["cost"]["linear_replay_plus_extension_projection_s"] == 100.0
    assert result["cost"]["projection_with_margin_s"] == 130.0
    assert result["cost"]["fits_proposed_caps"]


def test_rejects_modified_recipe_even_if_case_receipt_says_complete(tmp_path):
    root = _source(tmp_path)
    recipe = root / "run" / CASES[0] / "recipe.json"
    recipe.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="manifest mismatch"):
        prepare(root)


def test_rejects_discontinuous_recipe(tmp_path):
    root = _source(tmp_path)
    recipe_path = root / "run" / CASES[0] / "recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe[1]["angle_start_deg"] += 0.125
    _write(recipe_path, recipe)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"][f"run/{CASES[0]}/recipe.json"] = hashlib.sha256(
        recipe_path.read_bytes()).hexdigest()
    _write(manifest_path, manifest)
    with pytest.raises(ValueError, match="discontinuous"):
        prepare(root)
