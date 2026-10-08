import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from dev_orchestrator.p8_durable_audit import (
    SCHEMA, audit_anchor_primary, audit_campaign, canonical_bytes,
)


def _primary(rpm):
    dt = 60.0 / rpm
    ledger = {
        "fresh_air_converted": 1.0e-8, "fuel_converted": 0.0,
        "burned_produced": 1.0e-8, "residual_unchanged": 0.0,
        "source_mass_residual": 0.0, "heat_added": 0.008,
        "heat_burn_residual": 0.0, "heat_accumulation_roundoff": 0.0,
    }
    traces = []
    for stage in (0, 1):
        traces.append({"step_index": 1, "stage_index": stage, "interfaces": [
            {"interface_name": "tr1<->cylinder", "gas_mass_flux": 2.0,
             "donor_species_fractions": {"fresh_air": 0.5, "fuel": 0.0,
                                         "residual": 0.5, "burned": 0.0}},
            {"interface_name": "cylinder<->exhaust", "gas_mass_flux": 1.0,
             "donor_species_fractions": {"fresh_air": 0.25, "fuel": 0.0,
                                         "residual": 0.75, "burned": 0.0}},
        ]})
    boundary_trace = []
    for stage in (0, 1):
        for boundary_index, component, incoming in (
                (0, "intake", True), (1, "exhaust", False)):
            boundary_trace.append({
                "step_index": 1, "stage_index": stage,
                "boundary_index": boundary_index, "component": component,
                "incoming": incoming, "mass_flux": 0.0, "dt": dt,
                "species_before": [1.0, 0.0, 0.0, 0.0],
                "species_after": [1.0, 0.0, 0.0, 0.0],
                "delta_species_mass": [0.0, 0.0, 0.0, 0.0],
            })
    fresh = dt
    short = 0.25 * dt
    terminal = {
        "angle": 540.0,
        "elapsed_time_s": dt,
        "cycle_index": 1,
        "conservative_state": [[1.0, 0.0, 10.0, 1.0, 0.01]],
        "species_masses": {"cylinder": [[0.99999999, 0.0, 0.0, 1.0e-8]]},
        "species_initial": [1.0, 0.0, 0.0, 0.0],
        "species_external": [0.0, 0.0, 0.0, 0.0],
        "gas_external_cumulative": {"mass": 0.0, "energy": 0.0, "species": 0.0},
        "gas_last_external": {"mass": 0.0, "energy": 0.0, "species": 0.0},
        "gas_ledger": {"external_mass": 0.0, "external_energy": 0.0},
        "gas_initial": {"mass": 1.0, "energy": 9.992, "species": 0.0},
        "gas_previous_totals": {"mass": 1.0, "energy": 10.0, "species": 0.0},
        "fresh_delivered": fresh, "fresh_delivered_tr1": fresh,
        "fresh_delivered_tr2": 0.0, "fresh_short_circuit": short,
        "p7_events": [{"start": 350.0, "fresh_air": 1.0, "fuel": 0.0,
                        "ledger": ledger}],
        "p7_source_delta": [-1.0e-8, 0.0, 0.0, 1.0e-8],
        "p7_enabled": True, "p7_angular_rate_deg_s": 6.0 * rpm,
        "external_flux_trace": [
            {"stage_index": stage,
             "atmosphere_intake": {"species_flux": {name: 0.0 for name in ("fresh_air", "fuel", "residual", "burned")}},
             "exhaust_atmosphere": {"species_flux": {name: 0.0 for name in ("fresh_air", "fuel", "residual", "burned")}}}
            for stage in (0, 1)],
        "p8_boundary_species_trace": boundary_trace,
        "verification_trace": traces,
    }
    primary = {
        "schema": SCHEMA, "rpm": rpm,
        "configuration": {"mechanics": "S2T-0D-01", "cfl": 0.4,
                          "eos_R_J_kgK": 287.0, "eos_gamma": 1.35,
                          "preparation_deg": [180.0, 900.0],
                          "measured_deg": [180.0, 540.0],
                          "p7_deg": [350.0, 390.0],
                          "restart_probe_deg": 370.0,
                          "float_format": "binary64"},
        "terminal": terminal,
        "gas_history": [{"angle": 540.0, "angle_start": 180.0,
                         "dt": dt, "stage_work_rates": [[0.0, 0.0], [0.0, 0.0]],
                         "stage_external": [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                         "stage_exhaust_external": [[0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0]],
                         "prescribed_heat": 0.008,
                         "totals": {"mass": 1.0, "energy": 10.0, "species": 0.0},
                         "stage_states": [
                             [[1.0, 0.0, 9.992, 1.0, 0.01], [1.0, 0.0, 10.0, 1.0, 0.01]],
                             [[1.0, 0.0, 9.992, 1.0, 0.01], [1.0, 0.0, 10.0, 1.0, 0.01]],
                             [[1.0, 0.0, 10.0, 1.0, 0.01], [1.0, 0.0, 10.0, 1.0, 0.01]],
                         ]}],
        "accepted_steps": [{"dt": dt, "achieved_cfl": 0.2}],
    }
    history_record = primary["gas_history"][0]
    terminal["conservative_state"] = copy.deepcopy(history_record["stage_states"][2])
    history_record["p8_accepted_state"] = {
        "step_index": 1, "dt": dt, "achieved_cfl": 0.2,
        "angle": 540.0, "elapsed_time_s": dt, "cycle_index": 1,
        "conservative_state": copy.deepcopy(history_record["stage_states"][2]),
        "species_masses": copy.deepcopy(terminal["species_masses"]),
        "species_initial": copy.deepcopy(terminal["species_initial"]),
        "species_external": copy.deepcopy(terminal["species_external"]),
        "gas_external_cumulative": copy.deepcopy(terminal["gas_external_cumulative"]),
        "gas_last_external": copy.deepcopy(terminal["gas_last_external"]),
        "gas_ledger": copy.deepcopy(terminal["gas_ledger"]),
        "gas_initial": copy.deepcopy(terminal["gas_initial"]),
        "gas_previous_totals": copy.deepcopy(terminal["gas_previous_totals"]),
        "fresh_delivered": fresh, "fresh_delivered_tr1": fresh,
        "fresh_delivered_tr2": 0.0, "fresh_short_circuit": short,
        "p7_events": copy.deepcopy(terminal["p7_events"]),
        "p7_source_delta": copy.deepcopy(terminal["p7_source_delta"]),
        "p7_enabled": True, "p7_angular_rate_deg_s": 6.0 * rpm,
    }
    terminal["gas_history"] = primary["gas_history"]
    terminal["accepted_steps"] = primary["accepted_steps"]
    primary["producer_terminal_digest"] = hashlib.sha256(canonical_bytes(terminal)).hexdigest()
    restart_events = [[350.0, 1.0, 0.0, ledger]]
    primary["restart"] = {
        "checkpoint_angle_deg": 370.0,
        "checkpoint_state": {"angle": 370.0, "conservative_state": terminal["conservative_state"]},
        "terminal_state": {
            "angle": terminal["angle"],
            "elapsed_time_s": terminal["elapsed_time_s"],
            "cycle_index": terminal["cycle_index"],
            "conservative_state": terminal["conservative_state"],
            "species_mass": terminal["species_masses"],
            "species_initial": terminal["species_initial"],
            "species_external": terminal["species_external"],
            "gas_initial": terminal["gas_initial"],
            "gas_previous_totals": terminal["gas_previous_totals"],
            "gas_external_cumulative": terminal["gas_external_cumulative"],
            "gas_last_external": terminal["gas_last_external"],
            "gas_ledger": terminal["gas_ledger"],
            "p7_events": restart_events,
            "p7_source_delta": terminal["p7_source_delta"],
            "p7_enabled": True,
            "p7_angular_rate_deg_s": terminal["p7_angular_rate_deg_s"],
            "p8_boundary_species_trace": terminal["p8_boundary_species_trace"],
            "fresh_delivered": fresh, "fresh_delivered_tr1": fresh,
            "fresh_delivered_tr2": 0.0, "fresh_short_circuit": short,
        },
    }
    return primary


def _anchor(rpm, primary):
    terminal = primary["terminal"]
    digest = primary["producer_terminal_digest"]
    return {
        "rpm": rpm, "fresh_mass_delivered_kg": terminal["fresh_delivered"],
        "fresh_short_circuit_mass_kg": terminal["fresh_short_circuit"],
        "W_cycle_J": 0.0, "P_indicated_W": 0.0, "T_indicated_Nm": 0.0,
        "p_max_Pa": (1.35 - 1.0) * 10.0 / 0.01, "prescribed_heat_J": 0.008,
        "global_mass_residual_kg": 0.0,
        "global_energy_residual_J": 10.0 - 9.992 - 0.008,
        "species_residual_kg": 0.0, "achieved_CFL_max": 0.2,
        "p7_ledger": terminal["p7_events"][0]["ledger"],
        "p7_capture": {"captured_fresh_kg": 1.0, "burned_produced_kg": 1.0e-8,
                        "prescribed_heat_J": 0.008},
        "replay_terminal_digests": {"first": digest, "second": digest},
        "deterministic_replay": {
            "executed": True, "state_equal": True, "preparation_state_equal": True,
            "metrics_equal": True, "p7_ledger_equal": True,
            "fresh_delivery_equal": True, "short_circuit_equal": True,
            "external_accounting_equal": True,
        },
        "gates": {key: True for key in (
            "finite", "geometry_rebased", "admissible", "species", "p7_one_event",
            "p7_nonvacuous", "p7_source_admissible", "p7_heat_consistent", "cfl",
            "source_heat_consistent", "prescribed_heat_matches_ledger",
            "global_mass_conservation", "global_energy_conservation",
            "prepared_initial_state", "restart", "deterministic_replay")},
        "restart": {key: True for key in (
            "executed", "checkpoint_inside_p7", "state_equal", "species_mass_equal",
            "p7_ledger_equal", "external_equal", "fresh_delivery_equal",
            "short_circuit_equal")},
    }


def _coherently_mutate_terminal(primary, mutate):
    terminal = primary["terminal"]
    mutate(terminal)
    restart = primary["restart"]["terminal_state"]
    mapping = {
        "angle": "angle", "elapsed_time_s": "elapsed_time_s",
        "cycle_index": "cycle_index", "conservative_state": "conservative_state",
        "species_masses": "species_mass", "species_initial": "species_initial",
        "species_external": "species_external", "gas_initial": "gas_initial",
        "gas_previous_totals": "gas_previous_totals",
        "gas_external_cumulative": "gas_external_cumulative",
        "gas_last_external": "gas_last_external", "gas_ledger": "gas_ledger",
        "p7_source_delta": "p7_source_delta", "p7_enabled": "p7_enabled",
        "p7_angular_rate_deg_s": "p7_angular_rate_deg_s",
        "fresh_delivered": "fresh_delivered", "fresh_delivered_tr1": "fresh_delivered_tr1",
        "fresh_delivered_tr2": "fresh_delivered_tr2",
        "fresh_short_circuit": "fresh_short_circuit",
    }
    for terminal_key, restart_key in mapping.items():
        restart[restart_key] = copy.deepcopy(terminal[terminal_key])
    restart["p7_events"] = [[event["start"], event["fresh_air"], event["fuel"],
                              copy.deepcopy(event["ledger"])]
                             for event in terminal["p7_events"]]
    primary["producer_terminal_digest"] = hashlib.sha256(canonical_bytes(terminal)).hexdigest()


def _add_terminal_value(terminal, path, increment):
    value = terminal
    for part in path[:-1]:
        value = value[part]
    value[path[-1]] += increment


def _write_campaign(root):
    anchors = []
    for rpm in (2500, 5000, 8000, 11000, 15000):
        primary_a = _primary(rpm)
        primary_b = copy.deepcopy(primary_a)
        row = _anchor(rpm, primary_a)
        refs = {}
        for label, primary in (("first", primary_a), ("second", primary_b)):
            raw = gzip.compress(json.dumps(primary, separators=(",", ":"), allow_nan=False).encode(), mtime=0)
            filename = f"primary-{rpm}-{label}.json.gz"
            (root / filename).write_bytes(raw)
            refs[label] = {"schema": SCHEMA, "path": filename,
                           "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}
        row["primary_evidence"] = refs
        anchors.append(row)
    campaign = {
        "status": "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL",
        "closure": "P8_READY_FOR_P9_DATA", "failures": [],
        "semantics": {"metric_semantics": "BOUNDED_TRANSIENT_INDICATED",
                      "experimental_validation": "NOT_PERFORMED",
                      "periodic_convergence": "NOT_GRANTED_BY_P4",
                      "independent_review": "INDEPENDENT_REVIEW_PENDING",
                      "conditional_on_p4": True, "steady_state": False},
        "provenance": {
            "mechanics": "S2T-0D-01", "initial_angle_deg": 180,
            "topology": "frozen P5-C/P6/P7 full-topology fixture",
            "synthetic_not_measured": True,
            "preparation": {"cycles": 2, "start_angle_deg": 180.0,
                            "end_angle_deg": 900.0, "p7_enabled": False,
                            "prescribed_heat_J": 0.0,
                            "measured_window": [180.0, 540.0],
                            "rebase": [900.0, 180.0]},
        },
        "p4": "BLOCKED / NOT_GRANTED", "p9": "STOPPED", "anchors": anchors,
    }
    (root / "p8-wide-rpm.json").write_text(json.dumps(campaign, indent=2))
    for anchor in anchors:
        (root / f"anchor-{anchor['rpm']}.json").write_text(json.dumps(anchor, indent=2))
    (root / "p8-wide-rpm.csv").write_text("rpm\n2500\n5000\n8000\n11000\n15000\n")
    return campaign


class P8DurableAuditTests(unittest.TestCase):
    def test_unmodified_primary_evidence_reaudits(self):
        primary = _primary(2500)
        anchor = _anchor(2500, primary)
        self.assertTrue(audit_anchor_primary(anchor, primary, copy.deepcopy(primary))["passed"])

    def test_primary_terminal_state_mutation_changes_digest_and_blocks_replay(self):
        first = _primary(2500)
        second = copy.deepcopy(first)
        anchor = _anchor(2500, first)
        first["terminal"]["conservative_state"][0][0] += 0.25
        result = audit_anchor_primary(anchor, first, second)
        self.assertFalse(result["passed"])
        self.assertIn("trajectory_terminal_mismatch", result["reason"])

    def test_coherent_terminal_restart_digest_mutations_leave_history_bound(self):
        mutations = {
            "mass": lambda t: _add_terminal_value(t, ("conservative_state", 0, 0), 0.25),
            "momentum": lambda t: _add_terminal_value(t, ("conservative_state", 0, 1), 0.25),
            "energy": lambda t: _add_terminal_value(t, ("conservative_state", 0, 2), 0.25),
            "species": lambda t: _add_terminal_value(t, ("species_masses", "cylinder", 0, 0), 0.25),
            "species_external": lambda t: _add_terminal_value(t, ("species_external", 0), 0.25),
            "gas_ledger": lambda t: _add_terminal_value(t, ("gas_external_cumulative", "mass"), 0.25),
            "gas_last_external": lambda t: _add_terminal_value(t, ("gas_last_external", "mass"), 0.25),
            "gas_step_ledger": lambda t: _add_terminal_value(t, ("gas_ledger", "external_mass"), 0.25),
            "p7_ledger": lambda t: _add_terminal_value(t, ("p7_events", 0, "ledger", "heat_added"), 0.25),
            "fresh_delivery": lambda t: _add_terminal_value(t, ("fresh_delivered",), 0.25),
            "short_circuit": lambda t: _add_terminal_value(t, ("fresh_short_circuit",), 0.25),
            "time": lambda t: _add_terminal_value(t, ("elapsed_time_s",), 0.25),
            "cycle": lambda t: _add_terminal_value(t, ("cycle_index",), 1),
            "angle": lambda t: _add_terminal_value(t, ("angle",), 1),
        }
        for name, mutation in mutations.items():
            with self.subTest(name=name):
                first = _primary(2500)
                second = copy.deepcopy(first)
                anchor = _anchor(2500, first)
                _coherently_mutate_terminal(first, mutation)
                _coherently_mutate_terminal(second, mutation)
                result = audit_anchor_primary(anchor, first, second)
                self.assertFalse(result["passed"])
                self.assertIn("trajectory_terminal_mismatch", result["reason"])

    def test_restart_terminal_must_match_validated_original_terminal(self):
        first = _primary(2500)
        second = copy.deepcopy(first)
        anchor = _anchor(2500, first)
        first["restart"]["terminal_state"]["conservative_state"] = copy.deepcopy(
            first["restart"]["terminal_state"]["conservative_state"])
        first["restart"]["terminal_state"]["conservative_state"][0][0] += 0.25
        result = audit_anchor_primary(anchor, first, second)
        self.assertFalse(result["passed"])
        self.assertIn("restart terminal state differs", result["reason"])

    def test_full_campaign_attack_updates_digest_restart_hashes_and_summaries_but_fails_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            campaign = _write_campaign(root)
            campaign_anchor = campaign["anchors"][0]
            individual_path = root / "anchor-2500.json"
            individual_anchor = json.loads(individual_path.read_text())
            for label in ("first", "second"):
                reference = campaign_anchor["primary_evidence"][label]
                path = root / reference["path"]
                primary = json.loads(gzip.decompress(path.read_bytes()))
                _coherently_mutate_terminal(
                    primary,
                    lambda terminal: _add_terminal_value(
                        terminal, ("conservative_state", 0, 0), 0.25))
                raw = gzip.compress(json.dumps(primary, separators=(",", ":"),
                                                allow_nan=False).encode(), mtime=0)
                path.write_bytes(raw)
                updated = {"schema": SCHEMA, "path": reference["path"],
                           "sha256": hashlib.sha256(raw).hexdigest(),
                           "size_bytes": len(raw)}
                campaign_anchor["primary_evidence"][label] = updated
                individual_anchor["primary_evidence"][label] = updated
                campaign_anchor["replay_terminal_digests"][label] = primary["producer_terminal_digest"]
                individual_anchor["replay_terminal_digests"][label] = primary["producer_terminal_digest"]
            campaign["anchors"][0] = campaign_anchor
            (root / "p8-wide-rpm.json").write_text(json.dumps(campaign, indent=2))
            individual_path.write_text(json.dumps(individual_anchor, indent=2))
            result = audit_campaign(root)
            self.assertFalse(result["passed"])
            self.assertIn("trajectory_terminal_mismatch", result["anchors"][2500]["reason"])

    def test_all_fresh_short_and_digest_summary_mutation_patterns_block(self):
        for field, replacement in (
            ("fresh_mass_delivered_kg", 99.0),
            ("fresh_short_circuit_mass_kg", 88.0),
        ):
            for target in ("consolidated", "individual", "both"):
                with self.subTest(field=field, target=target):
                    with tempfile.TemporaryDirectory() as td:
                        root = Path(td)
                        campaign = _write_campaign(root)
                        if target in ("consolidated", "both"):
                            campaign["anchors"][0][field] = replacement
                        if target in ("individual", "both"):
                            path = root / "anchor-2500.json"
                            row = json.loads(path.read_text())
                            row[field] = replacement
                            path.write_text(json.dumps(row, indent=2))
                        (root / "p8-wide-rpm.json").write_text(json.dumps(campaign, indent=2))
                        self.assertFalse(audit_campaign(root)["passed"])

    def test_digest_changes_in_one_or_all_summary_copies_block(self):
        for target in ("consolidated", "individual", "both"):
            with self.subTest(target=target):
                with tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    campaign = _write_campaign(root)
                    if target in ("consolidated", "both"):
                        campaign["anchors"][0]["replay_terminal_digests"]["first"] = "0" * 64
                    if target in ("individual", "both"):
                        path = root / "anchor-2500.json"
                        row = json.loads(path.read_text())
                        row["replay_terminal_digests"]["first"] = "0" * 64
                        path.write_text(json.dumps(row, indent=2))
                    (root / "p8-wide-rpm.json").write_text(json.dumps(campaign, indent=2))
                    self.assertFalse(audit_campaign(root)["passed"])

    def test_coherent_derived_mutation_in_all_campaign_copies_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            campaign = _write_campaign(root)
            anchor = campaign["anchors"][0]
            for summary in (anchor, json.loads((root / "anchor-2500.json").read_text())):
                summary["fresh_mass_delivered_kg"] = 99.0
                summary["fresh_short_circuit_mass_kg"] = 88.0
                summary["replay_terminal_digests"]["first"] = "0" * 64
            campaign["anchors"][0] = anchor
            (root / "p8-wide-rpm.json").write_text(json.dumps(campaign, indent=2))
            (root / "anchor-2500.json").write_text(json.dumps(anchor, indent=2))
            self.assertFalse(audit_campaign(root)["passed"])

    def test_individual_only_mutation_blocks_campaign(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write_campaign(root)
            path = root / "anchor-2500.json"
            anchor = json.loads(path.read_text())
            anchor["fresh_mass_delivered_kg"] += 1.0
            path.write_text(json.dumps(anchor, indent=2))
            self.assertFalse(audit_campaign(root)["passed"])

    def test_primary_artifact_hash_and_primary_digest_are_checked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            campaign = _write_campaign(root)
            self.assertTrue(audit_campaign(root)["passed"])
            ref = campaign["anchors"][0]["primary_evidence"]["first"]
            path = root / ref["path"]
            primary = json.loads(gzip.decompress(path.read_bytes()))
            primary["terminal"]["verification_trace"][0]["interfaces"][1]["gas_mass_flux"] += 0.5
            raw = gzip.compress(json.dumps(primary, separators=(",", ":")).encode(), mtime=0)
            path.write_bytes(raw)
            # Updating all stored file hashes does not make the changed raw
            # preimage agree with the independently retained result digest.
            for summary_name in ("p8-wide-rpm.json", "anchor-2500.json"):
                summary_path = root / summary_name
                summary = json.loads(summary_path.read_text())
                row = summary["anchors"][0] if summary_name == "p8-wide-rpm.json" else summary
                row["primary_evidence"]["first"]["sha256"] = hashlib.sha256(raw).hexdigest()
                row["primary_evidence"]["first"]["size_bytes"] = len(raw)
                summary_path.write_text(json.dumps(summary, indent=2))
            self.assertFalse(audit_campaign(root)["passed"])

    def test_primary_digest_must_be_recomputed_not_trusted(self):
        primary = _primary(2500)
        anchor = _anchor(2500, primary)
        primary["producer_terminal_digest"] = "f" * 64
        anchor["replay_terminal_digests"] = {"first": "f" * 64, "second": "f" * 64}
        self.assertFalse(audit_anchor_primary(anchor, primary, copy.deepcopy(primary))["passed"])


if __name__ == "__main__":
    unittest.main()
