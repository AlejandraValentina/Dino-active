from copy import deepcopy

import pytest

from motorsim.full_rpm_evidence_impl2 import (
    decode_segmented_primary,
    encode_segmented_primary,
)


def test_segment_round_trip_is_canonical_and_preserves_all_row_fields():
    primary = {
        "schema": "MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V3",
        "conservation": {"mass_residual_kg": 0.0},
        "trajectory": [
            {"angle_deg": 0.0, "state": {"p": [1.0, 2.0]}, "optional": None},
            {"angle_deg": 1.0, "state": {"p": [3.0, 4.0]}, "extra": {"q": 5}},
        ],
    }
    rebuilt = decode_segmented_primary(encode_segmented_primary(primary))
    assert rebuilt == primary


def test_segment_mutation_is_detected_by_bound_canonical_hash():
    segment = encode_segmented_primary({"trajectory": [{"angle_deg": 0.0}]})
    changed = deepcopy(segment)
    changed["columns"]["angle_deg"][0] = 0.1
    with pytest.raises(ValueError, match="canonical hash"):
        decode_segmented_primary(changed)


def test_segment_rejects_shape_mismatch():
    segment = encode_segmented_primary({"trajectory": [{"angle_deg": 0.0}]})
    segment["columns"]["angle_deg"].append(2.0)
    with pytest.raises(ValueError, match="invalid segmented"):
        decode_segmented_primary(segment)
