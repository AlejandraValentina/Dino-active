import numpy as np
import pytest

from scripts.diagnostics.track_postopen_exhaust_wavefront_v1 import gradient_summary


def test_linear_profile_has_constant_gradient_and_centered_total_variation():
    centers = np.array([.5, 1.5, 2.5, 3.5])
    faces = np.arange(5, dtype=float)
    result = gradient_summary(2.0 * centers + 1.0, centers, faces)

    assert result["maximum_absolute_gradient_per_m"] == pytest.approx(2.0)
    assert result["integrated_absolute_gradient"] == pytest.approx(8.0)
    assert result["absolute_gradient_centroid_m"] == pytest.approx(2.0)
    assert result["absolute_gradient_width_std_m"] == pytest.approx(np.sqrt(1.25))


def test_flat_profile_has_no_threshold_defined_front():
    centers = np.array([.5, 1.5, 2.5, 3.5])
    faces = np.arange(5, dtype=float)
    result = gradient_summary(np.ones(4), centers, faces)

    assert result["integrated_absolute_gradient"] == 0.0
    assert result["maximum_gradient_location_m"] is None
    assert result["absolute_gradient_centroid_m"] is None
