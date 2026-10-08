"""Instrument, but do not alter, the five preserved KT100 r5 V1 failures."""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import InvalidState
from motorsim.reference_harness.runtime import advance_cycle, build_system
from scripts.build_kt100_hybrid_fixture_v2 import V1_PATH as V1_CONFIG
from scripts.build_kt100_hybrid_fixture_v2 import build as build_v2

OUTPUT = ROOT / "results/2t-commercial-core-20261002/aud-11-kt100-r5-failure-face-instrumentation-v2.json"
R5_ROOT = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r5"
RPMS = (5000, 7000, 9000, 11000, 13000)


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite instrumentation: {OUTPUT}")
    config = build_v2()
    config_bytes = V1_CONFIG.read_bytes()
    failures = []
    original_flux = Boundary.flux

    def observed_flux(self, interior, normal, eos):
        try:
            return original_flux(self, interior, normal, eos)
        except InvalidState as exc:
            if self.kind == "reservoir":
                rho, velocity, pressure, marker = interior
                sound = eos.sound_speed(interior)
                w = normal * velocity
                invariant = w + 2.0 * sound / (eos.gamma - 1.0)
                h0 = eos.cp * self.T0
                j_rest = 2.0 * ((eos.gamma - 1.0) * h0) ** 0.5 / (eos.gamma - 1.0)
                failures.append({
                    "exception": str(exc), "kind": self.kind,
                    "selected_branch": "V1_RESERVOIR_SUBSONIC_INFLOW_REJECTED",
                    "normal": normal, "interior_primitive": [rho, velocity, pressure, marker],
                    "temperature_K": pressure / (rho * eos.R),
                    "sound_speed_m_s": sound, "normal_velocity_m_s": w,
                    "entropy_parameter_p_over_rho_gamma": pressure / rho ** eos.gamma,
                    "outgoing_invariant_Jplus_m_s": invariant,
                    "reservoir_rest_invariant_m_s": j_rest,
                    "invariant_excess_m_s": invariant - j_rest,
                    "ambient_pressure_Pa": self.p0,
                    "reservoir_stagnation_temperature_K": self.T0,
                    "reservoir_entropy_parameter_p_over_rho_gamma": (
                        self.p0 / (self.p0 / (eos.R * self.T0)) ** eos.gamma),
                    "reservoir_species_mass_fractions": {
                        "fresh_air": 1.0, "fuel": 0.0,
                        "residual": 0.0, "burned": 0.0},
                    "characteristic_residual_m_s": invariant - j_rest,
                })
            raise

    Boundary.flux = observed_flux
    points = []
    try:
        for rpm in RPMS:
            point_config = copy.deepcopy(config)
            point_config["operating_point"]["rpm"] = rpm
            historical_path = R5_ROOT / f"rpm-{rpm}" / "failure.json.gz"
            historical = json.loads(gzip.decompress(historical_path.read_bytes()))
            system, model, offset = build_system(point_config)
            before = len(failures)
            try:
                advance_cycle(system, model, point_config, offset, 1)
                status = "UNEXPECTEDLY_COMPLETED"
            except InvalidState as exc:
                status = "REPRODUCED_V1_FAILURE"
                error = str(exc)
            point_failures = failures[before:]
            reproduced_exactly = (
                status == "REPRODUCED_V1_FAILURE" and
                len(system.gas.history) == historical["accepted_steps"] and
                system.gas.angle == historical["angle_deg"] and
                error == historical["message"])
            points.append({
                "rpm": rpm, "status": status,
                "angle_deg": system.gas.angle,
                "accepted_steps": len(system.gas.history),
                "matches_preserved_r5_failure_exactly": reproduced_exactly,
                "error": error if status == "REPRODUCED_V1_FAILURE" else None,
                "failing_face": point_failures[-1] if point_failures else None,
                "boundary_failures_observed": len(point_failures),
            })
    finally:
        Boundary.flux = original_flux

    expected_failure = {
        "status": "KT100_R5_FAILURE_FACE_INSTRUMENTATION_V1",
        "classification": "PRE_CAMPAIGN_DIAGNOSTIC_ONLY",
        "boundary_used": "LEGACY_CHARACTERISTIC_V1",
        "source_config": "configs/fixtures/kt100_hybrid_model_fixture_v2.json",
        "source_config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "preserved_receipts": "results/kt100-hybrid-model-fixture-v2-harness-20261002-r5/",
        "points": points,
    }
    if any(point["status"] != "REPRODUCED_V1_FAILURE" or
           not point["matches_preserved_r5_failure_exactly"] or
           point["boundary_failures_observed"] != 1 or
           point["failing_face"] is None for point in points):
        expected_failure["classification"] = "INSTRUMENTATION_INCOMPLETE"
    OUTPUT.write_text(json.dumps(expected_failure, indent=2) + "\n",
                      encoding="utf-8", newline="\n")
    print(expected_failure["classification"])
    for point in points:
        print(point["rpm"], point["status"], point["accepted_steps"],
              point["angle_deg"], point["failing_face"])


if __name__ == "__main__":
    main()
