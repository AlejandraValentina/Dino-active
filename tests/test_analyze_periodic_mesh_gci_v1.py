import copy

from scripts.diagnostics.analyze_periodic_mesh_gci_v1 import analyze


def _cases():
    values = ((10.0, 18.0), (10.2, 18.4), (10.25, 18.5))
    return [dict(grid_total_cells=grid, periodic_detector_status="PASS_PERIOD_1",
                 primary_audit_status="PASS", replay_exact=True,
                 maximum_normalized_conservation_residual=1e-14,
                 physics_identity_sha256="a" * 64, period_cycles=1,
                 imep_bar=metrics[0], modeled_brake_power_kw=metrics[1],
                 source_artifact={"path": f"{grid}.json", "sha256": "b" * 64})
            for grid, metrics in zip((44, 88, 176), values)]


def test_computes_gci_only_for_three_audited_monotone_periodic_grids():
    result = analyze(_cases())
    assert result["classification"] in ("PASS", "PARTIAL_GCI_ABOVE_2_PERCENT")
    assert set(result["metrics"]) == {"imep_bar", "modeled_brake_power_kw"}
    assert all(0.5 <= metric["observed_order"] <= 2.5
               for metric in result["metrics"].values())
    assert result["predictive_claim"] is False
    assert result["candidate_promotion"] is False


def test_nonperiodic_case_fails_closed_without_gci():
    cases = _cases()
    cases[1]["periodic_detector_status"] = "TRANSIENT_AT_BUDGET"
    result = analyze(cases)
    assert result["classification"] == "PARTIAL_NO_GCI"
    assert result["metrics"] == {}


def test_nonmonotone_metric_fails_closed():
    cases = _cases()
    cases[1]["imep_bar"] = 9.9
    result = analyze(cases)
    assert result["classification"] == "PARTIAL_NO_GCI"
    assert "not strictly monotone" in result["reason"]


def test_physics_identity_mismatch_fails_closed():
    cases = _cases()
    cases[2]["physics_identity_sha256"] = "c" * 64
    assert analyze(cases)["classification"] == "PARTIAL_NO_GCI"


def test_grid_must_be_the_preregistered_triplet():
    cases = _cases()
    cases[2]["grid_total_cells"] = 352
    try:
        analyze(cases)
    except ValueError as exc:
        assert "44/88/176" in str(exc)
    else:
        raise AssertionError("wrong grid accepted")
