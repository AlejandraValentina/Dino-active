import pytest

from scripts.diagnostics.match_postopen_gradient_peaks_v1 import local_peaks, match_peaks


def test_reports_every_local_gradient_peak_without_magnitude_cutoff():
    peaks = local_peaks([0, 0, 2, 5, 2, 0, 0], range(7))

    assert [row["cell_index"] for row in peaks] == [2, 4]
    assert [row["absolute_gradient"] for row in peaks] == pytest.approx([2.5, 2.5])


def test_matches_peaks_by_position_and_retains_unmatched_extrema():
    a = [{"x_m": 1.0, "absolute_gradient": 2.0},
         {"x_m": 4.0, "absolute_gradient": 1.0}]
    b = [{"x_m": 1.2, "absolute_gradient": 1.8}]

    result = match_peaks(a, b)

    assert len(result["matches"]) == 1
    assert result["matches"][0]["position_difference_m"] == pytest.approx(.2)
    assert result["unmatched_a"] == [a[1]]
    assert result["unmatched_b"] == []
    assert "no distance" in result["matching_rule"]
