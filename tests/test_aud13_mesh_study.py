import math

from scripts.aud13_mesh_study import CHAMBER, run_mesh_study


def test_aud13_study_completes_and_preserves_exact_geometry_across_meshes():
    study = run_mesh_study()
    chamber, transfer = study["cases"]
    assert [row["cells"] for row in chamber["mesh_study"]] == [7, 33, 65, 130]
    assert [row["cells"] for row in transfer["mesh_study"]] == [2, 4, 8, 16, 32]
    expected_volume = sum(CHAMBER.mesh(0.005).volumes)
    assert all(abs(row["mesh_volume_m3"] - expected_volume) < 1e-15
               for row in chamber["mesh_study"])
    assert all(row["completed_time_s"] > 0 and row["steps"] > 0
               for case in study["cases"] for row in case["mesh_study"])
    assert all(all(math.isfinite(value) for value in row["max_normalized_ledger_residual"])
               for case in study["cases"] for row in case["mesh_study"])
    # Do not turn this diagnostic into an unapproved mesh-adequacy threshold.
    assert study["classification"] == "DIAGNOSTIC_NO_ACCEPTANCE_THRESHOLD_REGISTERED"
