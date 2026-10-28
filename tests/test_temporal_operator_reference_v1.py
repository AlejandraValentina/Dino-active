import pytest

from scripts.diagnostics.temporal_operator_reference_v1 import build_result, integrate_decay


def test_ssprk2_matches_analytical_decay_and_second_order_range():
    result = build_result()
    assert result["analytical_value"] == pytest.approx(2.718281828459045 ** -1)
    assert result["acceptance"]["all_orders_in_range"]
    assert all(1.9 <= order <= 2.1 for order in result["observed_orders"])


@pytest.mark.parametrize("dt", [0.0, -0.1, float("nan"), float("inf")])
def test_rejects_invalid_step_size(dt):
    with pytest.raises(ValueError):
        integrate_decay(dt)


def test_rejects_nondividing_step_size():
    with pytest.raises(ValueError, match="divide"):
        integrate_decay(0.3)
