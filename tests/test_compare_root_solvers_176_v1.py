from scripts.diagnostics.compare_root_solvers_176_v1 import compare


def test_comparison_accepts_identical_checkpoint_values():
    snapshot = {"cycle": 40, "state": [1.0, 2.0], "ledger": {"mass": 0.0}}
    assert compare(snapshot, snapshot) == []


def test_comparison_uses_existing_numeric_equivalence_tolerance():
    left = {"state": [1.0]}
    right = {"state": [1.0 + 1.0e-11]}
    assert compare(left, right) == []


def test_comparison_rejects_divergent_state_or_checkpoint_shape():
    assert compare({"cycle": 40}, {"cycle": 41})
    assert compare({"state": [1.0]}, {"state": [1.0], "ledger": {}})
