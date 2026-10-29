import math

import pytest

from motorsim.port_connection_v2 import _brent_root, root
from scripts.diagnostics.e2b_local_candidate_v1 import ROOT, _display_path


@pytest.mark.parametrize("zero", (0.125, 0.5, 0.875))
def test_brent_root_matches_bisection_on_smooth_bracketed_roots(zero):
    residual = lambda x: (x - zero) * (1.0 + x)
    got = _brent_root(residual, 0.0, 1.0)
    reference = root(residual, 0.0, 1.0)
    assert got == pytest.approx(zero, abs=2e-15)
    assert got == pytest.approx(reference, abs=2e-14)
    assert math.isfinite(residual(got))


def test_brent_root_preserves_exact_endpoint_and_nonpositive_side_contract():
    assert _brent_root(lambda x: x, 0.0, 1.0) == 0.0
    assert _brent_root(lambda x: x - 0.25, 0.0, 1.0,
                       nonpositive_endpoint=True) == pytest.approx(0.25)


def test_brent_root_rejects_unbracketed_or_nonfinite_residuals():
    with pytest.raises(ValueError, match="no bracket"):
        _brent_root(lambda x: x * x + 1.0, -1.0, 1.0)
    with pytest.raises(ValueError, match="no bracket"):
        _brent_root(lambda x: float("nan") if x in (0.0, 1.0) else x - 0.25,
                    0.0, 1.0)


def test_output_path_display_accepts_relative_and_absolute_paths(tmp_path):
    relative = _display_path(ROOT / "results" / "candidate" / "run.json")
    absolute = _display_path(tmp_path / "run.json")
    assert relative == "results/candidate/run.json"
    assert absolute == str((tmp_path / "run.json").resolve())
