from pathlib import Path

from dev_orchestrator import roadmap_executor as executor


REPO = Path(__file__).resolve().parents[2]


def test_committed_p8_evidence_is_internally_consistent():
    payload, audit = executor._audit_p8(REPO)

    assert payload["status"] == "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL"
    assert payload["p9"] == "STOPPED"
    assert audit["anchors_complete"] is True
    assert audit["anchor_files_equal"] is True
    assert audit["csv_equal"] is True
    assert audit["restart_ok"] is True
    assert audit["replay_ok"] is True
    assert audit["p7_nonvacuous"] is True
    assert audit["gates_ok"] is True
    assert audit["closure_ok"] is True


def test_missing_p8_evidence_blocks_transition(tmp_path):
    state = executor.evaluate(tmp_path)

    assert state["current_phase"] == "P8"
    assert state["classification"] == "P8_EVIDENCE_INCONSISTENT_BLOCKED"
    assert state["gates"]["campaign"] == "BLOCKED"
    assert "Repair P8 evidence inconsistency" in state["next_action"]
