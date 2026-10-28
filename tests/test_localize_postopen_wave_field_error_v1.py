import numpy as np
import pytest

from scripts.diagnostics.localize_postopen_wave_field_error_v1 import field_profiles


def _state(changed=False):
    species = np.tile([.92, .08, 0.0, 0.0], (4, 1)).astype(float)
    if changed:
        species[2] = [.70, .10, 0.0, .20]
    return {"ducts": {"exhaust": np.tile([1.0, 0.0, 300000.0], (4, 1))},
            "species": {"ducts": {"exhaust": species}}}


def _duct():
    return {"id": "exhaust", "mesh": {"faces": [0., 1., 2., 3., 4.],
                                          "centers": [.5, 1.5, 2.5, 3.5],
                                          "volumes": [1., 1., 1., 1.]}}


def test_localizes_species_difference_to_quarter_duct_bin():
    profile = field_profiles(_state(), _state(changed=True), _duct(), 1.4)

    burned = profile["burned_absolute_fraction"]
    assert burned["overall"]["Linf"] == pytest.approx(.2)
    assert burned["overall"]["maximum_center_m"] == 2.5
    assert [row["cells"] for row in burned["quarter_duct_bins"]] == [1, 1, 1, 1]
    assert burned["quarter_duct_bins"][2]["norms"]["L1"] == pytest.approx(.2)
    assert burned["quarter_duct_bins"][0]["norms"]["L1"] == 0.0


def test_rejects_incompatible_common_grid_fields():
    a = _state()
    b = _state()
    b["ducts"]["exhaust"] = b["ducts"]["exhaust"][:3]

    with pytest.raises(ValueError, match="invalid common-grid"):
        field_profiles(a, b, _duct(), 1.4)
