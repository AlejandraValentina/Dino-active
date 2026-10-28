import json

import pytest

from scripts.diagnostics.analyze_periodic_transient_endpoints_v1 import analyze


def make_cycle(cycle, maximum, p90, *, passed=False):
    return {
        "cycle": cycle,
        "statistics": {"maximum": maximum, "p90": p90, "median": .1,
                       "failed": 0 if passed else 1, "count": 4},
        "comparison": {
            "status": "PASS" if passed else "FAIL",
            "metrics": {
                "ducts.exhaust[2].species.burned": {
                    "value": .004 if not passed else .001,
                    "threshold": .002,
                    "passed": passed,
                }
            },
        },
        "work_J": 120.0 + cycle,
        "conservation": {
            "mass": {"initial": .003, "final": .0029, "residual": 1e-15},
            "energy": {"initial": 1200.0, "final": 1300.0, "residual": -1e-14},
            "species": {"fresh_air": {"residual": 1e-15}, "fuel": {"residual": 0.0}},
        },
    }


def write_cycles(path, rows):
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def test_finds_176_descending_tail_but_does_not_authorize_execution(tmp_path):
    p88 = write_cycles(tmp_path / "88.json", [make_cycle(i, 3.0, 1.0) for i in range(7, 11)])
    p176 = write_cycles(tmp_path / "176.json", [make_cycle(35, 7.0, 1.3),
                                                  make_cycle(36, 4.1, .83),
                                                  make_cycle(37, 3.5, .54)])

    result = analyze(p88, p176)

    assert result["classification"] == "TRANSIENT_NO_GCI"
    assert result["gci"] is None
    assert result["continuation_review"]["176_trend_disposition"] == "TREND_SUPPORTS_SEPARATE_PREREGISTRATION_REVIEW"
    assert result["continuation_review"]["execution_authorized_by_this_review"] is False
    assert result["windows"][1]["endpoint"]["top_endpoint_failures"][0]["normalized_error_over_threshold"] == 2
    assert result["windows"][1]["all_saved_cycles_conservation_residual_le_1e-12"] is True


def test_does_not_support_continuation_when_tail_does_not_strictly_descend(tmp_path):
    p88 = write_cycles(tmp_path / "88.json", [make_cycle(i, 3.0, 1.0) for i in range(7, 11)])
    p176 = write_cycles(tmp_path / "176.json", [make_cycle(35, 7.0, 1.3),
                                                  make_cycle(36, 4.1, .83),
                                                  make_cycle(37, 4.2, .80)])

    result = analyze(p88, p176)

    assert result["continuation_review"]["176_trend_disposition"] == "NO_TREND_BASIS_FOR_CONTINUATION"


def test_rejects_non_monotone_cycle_identity(tmp_path):
    p88 = write_cycles(tmp_path / "88.json", [make_cycle(8, 3, 1), make_cycle(8, 2, .8)])
    p176 = write_cycles(tmp_path / "176.json", [make_cycle(35, 7, 1.3), make_cycle(36, 4, .8), make_cycle(37, 3, .5)])

    with pytest.raises(ValueError, match="increasing integers"):
        analyze(p88, p176)


def test_rejects_conservation_residual_above_registered_limit(tmp_path):
    bad = make_cycle(37, 3, .5)
    bad["conservation"]["energy"]["residual"] = 1e-8
    p88 = write_cycles(tmp_path / "88.json", [make_cycle(8, 3, 1)])
    p176 = write_cycles(tmp_path / "176.json", [bad])

    result = analyze(p88, p176)

    assert result["windows"][1]["all_saved_cycles_conservation_residual_le_1e-12"] is False


def test_reports_when_budget_cannot_fit_minimum_detector_streak(tmp_path):
    p88 = write_cycles(tmp_path / "88.json", [make_cycle(8, 3, 1)])
    p176 = write_cycles(tmp_path / "176.json", [make_cycle(35, 7, 1.3),
                                                  make_cycle(36, 4.1, .83),
                                                  make_cycle(37, 3.5, .54)])
    detector = tmp_path / "detector.json"
    detector.write_text(json.dumps({"contract": "REFERENCE_PERIODIC_CONVERGENCE_V2",
                                    "history": [{"cycle_index": i} for i in range(7)],
                                    "lag1_streak": 0, "branch_streaks": {"A": 0, "B": 0}}))
    partial = tmp_path / "partial.json"
    partial.write_text(json.dumps({"status": "ERROR", "completed_new_cycles": 0,
                                   "timing_seconds": {"solver": 120.0}}))
    window = tmp_path / "window.json"
    window.write_text(json.dumps({"status": "TRANSIENT_AT_BUDGET", "completed_new_cycles": 7,
                                  "timing_seconds": {"solver": 849.0}}))

    result = analyze(p88, p176, detector_path=detector, partial_receipt_path=partial,
                     window_receipt_path=window, per_grid_cap_s=1200)

    budget = result["176_budget_feasibility"]
    assert budget["minimum_future_cycles_for_period_1_if_every_next_comparison_passes"] == 3
    assert budget["minimum_future_cycles_for_period_2_if_every_next_comparison_passes"] == 6
    assert budget["classification"] == "CURRENT_PER_GRID_BUDGET_CANNOT_REACH_PERIODICITY"
    assert result["continuation_review"]["176_trend_disposition"] == "NO_CONTINUATION_WITHIN_CURRENT_PER_GRID_BUDGET"
