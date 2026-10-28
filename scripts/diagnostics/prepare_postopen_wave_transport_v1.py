"""Read-only integrity and cost assessment for the recorded39 post-opening arc.

This preparation performs no solver steps.  It binds existing FAST recipes and
terminals so a later, separately activated runner can replay from native input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


CASES = ("p0-88", "p0-176", "p0-352", "p0-176-timehalf")
PHASE_START = 13680.0
PHASE_END = 13740.0
TARGET_END = 13830.0


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(source_root: Path) -> dict:
    """Check source-bound recipes and produce a cost estimate, without replay."""
    source_root = Path(source_root)
    manifest = _load(source_root / "manifest.json")
    bound = manifest.get("files", {})
    cases = []
    total_projected = 0.0
    for name in CASES:
        prefix = f"run/{name}"
        required = [f"{prefix}/{file}" for file in
                    ("configuration.json", "initial-checkpoint.json", "recipe.json",
                     "terminal-state.json", "receipt.json", "frames.json")]
        for relative in required:
            path = source_root / relative
            if relative not in bound or not path.is_file() or _sha(path) != bound[relative]:
                raise ValueError(f"source manifest mismatch: {relative}")
        folder = source_root / "run" / name
        receipt = _load(folder / "receipt.json")
        initial = _load(folder / "initial-checkpoint.json")
        terminal = _load(folder / "terminal-state.json")
        recipe = _load(folder / "recipe.json")
        frames = _load(folder / "frames.json")
        if receipt.get("status") != "COMPLETE" or receipt.get("error") is not None:
            raise ValueError(f"source case is not complete: {name}")
        if terminal.get("schema") != "FAST_RECIPE_V1_TERMINAL_STATE":
            raise ValueError(f"source terminal is not FAST recipe evidence: {name}")
        if initial.get("schema") != terminal.get("engine_schema"):
            raise ValueError(f"initial/terminal engine identity differs: {name}")
        if len(recipe) != receipt.get("accepted_steps") or terminal.get("accepted_steps") != len(recipe):
            raise ValueError(f"recipe step count differs from receipt: {name}")
        if not recipe or frames[0]["angle"] != PHASE_START or frames[-1]["angle"] != PHASE_END:
            raise ValueError(f"phase coverage differs: {name}")
        if terminal.get("crank_angle_unwrapped_deg") != PHASE_END:
            raise ValueError(f"FAST terminal phase differs: {name}")
        cursor = PHASE_START
        for row in recipe:
            if row.get("angle_start_deg") != cursor or row.get("angle_end_deg", 0) <= cursor:
                raise ValueError(f"recipe is discontinuous: {name}")
            cursor = row["angle_end_deg"]
        if cursor != PHASE_END:
            raise ValueError(f"recipe does not reach phase 60: {name}")
        measured = float(receipt["wall_s"])
        projected = measured * ((TARGET_END - PHASE_START) / (PHASE_END - PHASE_START))
        total_projected += projected
        cases.append({
            "name": name,
            "source_phase_deg": [0.0, 60.0],
            "target_phase_deg": [0.0, 150.0],
            "accepted_source_steps": len(recipe),
            "source_wall_s": measured,
            "projected_replay_plus_extension_s": projected,
            "manifest_sha256": {relative: bound[relative] for relative in required},
            "recovery": "Recreate from initial-checkpoint.json; replay every accepted/rejected recipe row; compare each accepted row and FAST terminal before advancing.",
        })
    return {
        "schema": "DINO_POSTOPEN_WAVE_TRANSPORT_PREPARATION_V1",
        "source_manifest": "results/predictive-reliability-v1/preopen-wave-transport-run-v1/manifest.json",
        "source_manifest_sha256": _sha(source_root / "manifest.json"),
        "cases": cases,
        "requested_observation_phases_deg": [90.0, 120.0, 150.0],
        "cost": {
            "measured_source_cases_s": total_projected / 2.5,
            "linear_replay_plus_extension_projection_s": total_projected,
            "projection_margin_fraction": 0.30,
            "projection_with_margin_s": total_projected * 1.30,
            "proposed_total_admission_cap_s": 600.0,
            "proposed_per_case_cap_s": 210.0,
            "fits_proposed_caps": total_projected * 1.30 <= 600.0 and
                                  max(c["projected_replay_plus_extension_s"] * 1.30
                                      for c in cases) <= 210.0,
        },
        "planned_controls": [
            "P0 spatial cases: 88/176/352 cells at the recorded 0.0625 degree cap.",
            "P0 temporal control: 176 cells at the recorded 0.03125 degree cap.",
            "No P1 case; no periodic extension; no changes to solver, closures, detector, CFL or rc7.",
            "Compare pressure, density, species markers and face fluxes at common 90/120/150 degree phases; retain nonmonotone/local results without forcing GCI.",
        ],
        "solver_steps_executed": 0,
        "activation": "PREPARATION_ONLY_NOT_AUTHORIZED_FOR_SOLVER_EXECUTION",
        "qualification": "Cost is a linear projection from recorded 0-60 degree case timings; the later arc may have different rejection/cost behavior. Recipe integrity must be reverified by an activated runner before any continuation.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve existing output: {args.output}")
    result = prepare(args.source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "cases": len(result["cases"]),
                      "projected_s": result["cost"]["linear_replay_plus_extension_projection_s"],
                      "with_margin_s": result["cost"]["projection_with_margin_s"],
                      "solver_steps": 0}))


if __name__ == "__main__":
    main()
