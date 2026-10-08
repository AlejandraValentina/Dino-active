"""Generate the synthetic KT100 V2 client config from the preserved V1 data."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from motorsim.project import Project

ROOT = Path(__file__).resolve().parents[1]
V1_PATH = ROOT / "configs/fixtures/kt100_model_fixture_v1.json"
OUT_PATH = ROOT / "configs/fixtures/kt100_hybrid_model_fixture_v2.json"


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _state(p, t, fractions, reason):
    return {"pressure_Pa": p, "temperature_K": t, "velocity_m_s": 0.0,
            "species_mass_fractions": fractions,
            "provenance": "SYNTHETIC_ASSUMPTION", "reason": reason}


def build():
    v1_bytes = V1_PATH.read_bytes()
    v1 = json.loads(v1_bytes)
    project = Project.from_dict(v1["engine_geometry_and_project"])
    initial = v1["boundaries"]["initial_states_pty"]
    p_atm = v1["boundaries"]["ambient_pressure_Pa"]
    t_atm = v1["boundaries"]["ambient_temperature_K"]

    def marked(pty, name):
        p, t, fresh = pty
        return _state(p, t, {"fresh_air": fresh, "fuel": 0.0,
                             "residual": 1.0 - fresh, "burned": 0.0},
                      f"P6 four-species mapping of V1 synthetic 0D initial {name}; no fuel chemistry inferred")

    atmosphere = {"fresh_air": 1.0, "fuel": 0.0, "residual": 0.0, "burned": 0.0}
    config = {
        "schema": "motorsim-reference-engine-v1",
        "fixture_id": "KT100_HYBRID_MODEL_FIXTURE_V2",
        "classification": "EXPLORATORY_SYNTHETIC_OPERATING_POINTS",
        "reference_case_id": v1["reference_case_id"],
        "base_v1": {"path": "configs/fixtures/kt100_model_fixture_v1.json",
                    "sha256": hashlib.sha256(v1_bytes).hexdigest(),
                    "provenance_sha256": v1["provenance_sha256"]},
        "claims": {"experimental_validation": "NOT_PERFORMED",
                   "predictive_validation": "NOT_CLAIMED",
                   "p9_status_effect": "NONE",
                   "prohibited": ["KT100_VALIDATED", "YAMAHA_PERFORMANCE_PREDICTED",
                                  "EXPERIMENTALLY_VALIDATED", "PREDICTIVELY_VALIDATED", "P9_PASS"]},
        "engine": {"project": project.to_dict()},
        "transfer_ducts": [
            {"name": "transfer1 synthetic duct", "length": 100.0,
             "start_diameter": 12.0, "end_diameter": 12.0,
             "provenance": "SYNTHETIC_ASSUMPTION",
             "reason": "P5-C requires finite transfer storage; V1 has transfer ports but no duct dimensions.",
             "sensitivity": "high: length and area affect wave travel and delivered mass"},
            {"name": "transfer2 synthetic duct", "length": 100.0,
             "start_diameter": 12.0, "end_diameter": 12.0,
             "provenance": "SYNTHETIC_ASSUMPTION",
             "reason": "P5-C requires a second finite path; V1 has no transfer-duct dimensions.",
             "sensitivity": "high: length and area affect wave travel and delivered mass"}],
        "port_flow_model": {"name": "existing P4 ideal effective-area baseline",
                            "configurable_discharge_coefficients": False,
                            "v1_0d_coefficients_applied": False,
                            "provenance": "MODEL_FORM_DIFFERENCE",
                            "reason": "The product P4/P5-C port-flux interface has no discharge-coefficient parameter; V1 legacy 0D coefficients are not silently transferred."},
        "boundaries": {"atmosphere_pressure_Pa": p_atm,
                       "atmosphere_temperature_K": t_atm,
                       "atmosphere_species_mass_fractions": atmosphere,
                       "atmosphere_provenance": "V1 documented fixture default: fresh_air=1; other species=0"},
        "initial_states": {
            "intake": marked(initial[0], "intake"),
            "crankcase": marked(initial[1], "crankcase"),
            "cylinder": marked(initial[2], "cylinder"),
            "exhaust": marked(initial[3], "exhaust"),
            "transfer1": marked(initial[1], "transfer1 copied from V1 crankcase state"),
            "transfer2": marked(initial[1], "transfer2 copied from V1 crankcase state")},
        "initial_state_provenance": "SYNTHETIC_ASSUMPTION: preserve V1 pressure/temperature/fresh-marker values; transfer states copy crankcase values because V1 has no finite transfer states",
        "numerics": {"cfl": 0.4, "dx_target_m": 0.03,
                     "max_cycles": 400, "gas_R_J_kgK": v1["thermodynamics"]["R_J_kgK"],
                     "gamma": v1["thermodynamics"]["gamma"],
                     "float_format": "binary64", "fastmath": False,
                     "parallel": False},
        "operating_points_rpm": [5000, 7000, 9000, 11000, 13000],
        "operating_point": {"rpm": 5000},
        "combustion": {"physical_event_phase_deg": v1["combustion"]["event_start_deg"],
                        "duration_deg": v1["combustion"]["duration_deg"],
                        "heat_per_burned_mass_J_kg": v1["combustion"]["heat_per_bookkeeping_burned_kg_J"],
                        "provenance": "SYNTHETIC_ASSUMPTION",
                        "fuel_chemistry": "NOT_MODELED"},
        "convergence_contract": "REFERENCE_PERIODIC_CONVERGENCE_V1",
        "evidence": {"checkpoint_cadence_cycles": 5,
                     "trajectory_persistence": "all accepted steps",
                     "checkpoint_restart": True, "independent_replay": True},
        "sensitivity_plan": {"run_after_base_campaign_only": True,
                             "calibration": False,
                             "parameters": ["rod_length_mm", "exhaust_lengths"],
                             "relative_variants": [0.95, 1.0, 1.05]}}
    return config


if __name__ == "__main__":
    OUT_PATH.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    print(OUT_PATH.relative_to(ROOT))
