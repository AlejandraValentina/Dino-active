"""Offline P4-C3-R5 identity auditor.

This module consumes persisted diagnostics and never calls the product
reconstruction or product Riemann operators.  It is intentionally an audit
tool, not an acquisition entry point; the focal C3-R5 run remains separately
authorized.
"""
import hashlib
import json
import math
import platform
import struct
import sys
from pathlib import Path

from motorsim.gas1d.eos import IdealGas
from dev_orchestrator.reference.exact_riemann import ExactRiemann
from dev_orchestrator.reference.hllc_audit import hllc as audit_hllc


CONTRACT = "P4-C3-R5"
INCONCLUSIVE = "INCONCLUSIVE"
CONSERVATION_THRESHOLD = 1e-10  # existing P4/C2 ledger criterion
EOS = IdealGas(R=287.0, gamma=1.35)
EXPLICIT_SOLVER_FAILURES = frozenset({
    "failed", "failed_numerically", "solver_failed", "error", "exception",
})


def runtime_binding(source_paths=None):
    """Return the durable runtime/source identity required by B0/B1/B2."""
    if source_paths is None:
        source_paths = (
            "dev_orchestrator/p4_sci_04b.py",
            "dev_orchestrator/p4_c3_r5_audit.py",
            "dev_orchestrator/reference/hllc_audit.py",
            "dev_orchestrator/reference/exact_riemann.py",
            "motorsim/gas1d/second_order.py",
            "motorsim/gas1d/riemann.py",
            "motorsim/gas1d/eos.py",
        )
    hashes = {}
    for path in source_paths:
        path = Path(path)
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "python": sys.version,
        "python_version": list(sys.version_info[:5]),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "sys_float_info": {name: getattr(sys.float_info, name)
                           for name in ("max", "min", "epsilon", "radix", "mant_dig")},
        "source_sha256": hashes,
    }


def canonical_binary64(values):
    """Canonical little-endian IEEE-754 binary64 sequence, including count."""
    leaves = []

    def visit(value):
        if isinstance(value, (list, tuple)):
            for nested in value:
                visit(nested)
        else:
            leaves.append(struct.pack("<d", float(value)))

    visit(values)
    return struct.pack("<Q", len(leaves)) + b"".join(leaves)


def canonical_digest(values):
    payload = canonical_binary64(values)
    return {"count": struct.unpack("<Q", payload[:8])[0],
            "sha256": hashlib.sha256(payload).hexdigest(),
            "encoding": "count-u64-le + IEEE-754 binary64 little-endian"}


def _minmod(a, b):
    if a == 0.0 or b == 0.0 or (a > 0.0) != (b > 0.0):
        return 0.0
    return a if abs(a) <= abs(b) else b


def _admissible(state, eos=EOS):
    try:
        eos.validate(tuple(state))
        return all(math.isfinite(float(v)) for v in state)
    except (ValueError, OverflowError, ZeroDivisionError):
        return False


def _chamber_primitive(chamber, volume, eos=EOS):
    mass, energy, fresh = chamber
    return (mass / volume, 0.0, (eos.gamma - 1.0) * energy / volume,
            fresh / mass)


def reconstruct_all_faces(states, geometry, chamber_state, *, eos=EOS):
    """Independently duplicate the frozen primitive MUSCL stencil for all faces."""
    states = [tuple(row) for row in states]
    centers, faces = geometry["centers"], geometry["faces"]
    length = faces[-1] - faces[0]
    left_faces, right_faces, downgraded = [], [], []
    for i, (x, state) in enumerate(zip(centers, states)):
        if i:
            xl, wl = centers[i - 1], states[i - 1]
        else:
            xl, wl = 2.0 * faces[0] - x, state
        if i + 1 < len(states):
            xr, wr = centers[i + 1], states[i + 1]
        else:
            xr, wr = 2.0 * faces[-1] - x, (state[0], -state[1], state[2], state[3])
        slopes = [_minmod((v - l) / (x - xl), (r - v) / (xr - x))
                  for l, v, r in zip(wl, state, wr)]
        left = tuple(v + s * (faces[i] - x) for v, s in zip(state, slopes))
        right = tuple(v + s * (faces[i + 1] - x) for v, s in zip(state, slopes))
        try:
            eos.validate(left)
            eos.validate(right)
        except (ValueError, OverflowError, ZeroDivisionError):
            left = right = state
            downgraded.append(i)
        left_faces.append(left)
        right_faces.append(right)

    wall_left = right_faces[-1]
    wall_right = (wall_left[0], -wall_left[1], wall_left[2], wall_left[3])
    chamber = _chamber_primitive(chamber_state, geometry["chamber_volume"], eos)
    pairs = [{"index": 0, "kind": "interface", "left": list(chamber),
              "right": list(left_faces[0])}]
    pairs.extend({"index": i, "kind": "interior", "left": list(right_faces[i - 1]),
                  "right": list(left_faces[i])} for i in range(1, len(states)))
    pairs.append({"index": len(states), "kind": "wall", "left": list(wall_left),
                  "right": list(wall_right)})
    return {"faces": pairs, "downgraded_cells": downgraded}


def audit_b0(stage, geometry, *, eos=EOS):
    if not isinstance(stage, dict):
        return {"status": INCONCLUSIVE, "reason": "missing_b0_stage_evidence"}
    captured = stage.get("r5_momentum")
    if (not isinstance(captured, dict)
            or not isinstance(captured.get("faces"), list)
            or not isinstance(captured.get("downgraded_cells"), list)):
        return {"status": INCONCLUSIVE, "reason": "missing_b0_face_evidence"}
    try:
        expected = reconstruct_all_faces(stage["primitive"], geometry,
                                         stage["chamber_state"], eos=eos)
    except (KeyError, IndexError, TypeError, ValueError, ZeroDivisionError,
            OverflowError, AttributeError, struct.error) as exc:
        return {"status": INCONCLUSIVE, "reason": "b0_reconstruction_error", "error": str(exc)}
    try:
        if (len(captured["faces"]) != len(expected["faces"])
                or not all(isinstance(face, dict) for face in captured["faces"])
                or not all(_valid_float_sequence(face.get("left"), 4)
                           and _valid_float_sequence(face.get("right"), 4)
                           for face in captured["faces"])):
            return {"status": INCONCLUSIVE, "reason": "malformed_b0_face_values",
                    "expected": expected, "captured": captured}
        face_identity = all(
            a.get("index") == b.get("index")
            and a.get("kind") == b.get("kind")
            and _exact_float_sequence(a["left"], b["left"])
            and _exact_float_sequence(a["right"], b["right"])
            for a, b in zip(captured["faces"], expected["faces"]))
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, struct.error) as exc:
        return {"status": INCONCLUSIVE, "reason": "malformed_b0_face_values",
                "error": str(exc), "expected": expected, "captured": captured}
    checks = {
        "face_states_exact": face_identity,
        "downgraded_cells_exact": captured.get("downgraded_cells") == expected["downgraded_cells"],
        "face_count": len(captured["faces"]) == len(expected["faces"]),
    }
    return {"status": "PASS" if all(checks.values()) else INCONCLUSIVE, "checks": checks,
            "expected": expected, "captured": captured}


def _product_flux(face, audit_flux):
    """Apply only the already-frozen wall flux projection to the audit result."""
    area = face["area"]
    scaled = tuple(area * value for value in audit_flux)
    if face["kind"] == "wall":
        return (0.0, scaled[1], 0.0, 0.0)
    return scaled


def audit_b1(stage, geometry, *, eos=EOS):
    b0 = audit_b0(stage, geometry, eos=eos)
    if b0["status"] != "PASS":
        return {"status": b0["status"], "reason": "b0_not_passed", "b0": b0}
    captured = stage["r5_momentum"].get("riemann")
    if not isinstance(captured, list):
        return {"status": INCONCLUSIVE, "reason": "missing_b1_riemann_evidence", "b0": b0}
    if len(captured) != len(b0["expected"]["faces"]):
        return {"status": INCONCLUSIVE, "reason": "b1_face_count_mismatch", "b0": b0}
    rows = []
    for face, product in zip(b0["expected"]["faces"], captured):
        if (not isinstance(product, dict)
                or not all(key in product for key in ("index", "kind", "flux", "waves", "reason"))
                or not _valid_float_sequence(product.get("flux"), 4)
                or not _valid_wave_sequence(product.get("waves"))
                or not _valid_reason(product.get("reason"))):
            return {"status": INCONCLUSIVE, "reason": "malformed_b1_face_values", "b0": b0}
        try:
            flux, waves, reason = audit_hllc(tuple(face["left"]), tuple(face["right"]), eos)
            face_with_area = dict(face, area=geometry["areas"][face["index"]])
            expected = {"index": face["index"], "kind": face["kind"],
                        "flux": list(_product_flux(face_with_area, flux)),
                        "waves": list(waves), "reason": reason}
        except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
            return {"status": INCONCLUSIVE, "reason": "b1_evaluation_error", "error": str(exc), "b0": b0}
        rows.append({"index": face["index"], "checks": {
            "index_kind": product.get("index") == expected["index"] and product.get("kind") == expected["kind"],
            "flux_exact": _exact_float_sequence(product.get("flux", ()), expected["flux"]),
            "waves_exact": _exact_wave_sequence(product.get("waves", ()), expected["waves"]),
            "fallback_reason_exact": product.get("reason") == expected["reason"],
        }, "expected": expected, "product": product})
    checks = [row["checks"] for row in rows]
    all_checks = [check for item in checks for check in item]
    reasons_match = all(item["fallback_reason_exact"] for item in checks)
    exact = all(all(item.values()) for item in checks)
    return {"status": "PASS" if exact else ("FAIL" if not reasons_match else INCONCLUSIVE),
            "rows": rows, "b0": b0, "product_flux_fields_used": []}


def _exact_float_sequence(actual, expected):
    try:
        return canonical_binary64(actual) == canonical_binary64(expected)
    except (TypeError, ValueError, OverflowError, struct.error):
        return False


def _exact_wave_sequence(actual, expected):
    if not _valid_wave_sequence(actual) or not _valid_wave_sequence(expected):
        return False
    for left, right in zip(actual, expected):
        if left is None or right is None:
            if left is not None or right is not None:
                return False
        elif not _exact_float_sequence([left], [right]):
            return False
    return True


def _finite_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(float(value)))


def _valid_float_sequence(values, length):
    return (isinstance(values, (list, tuple))
            and len(values) == length
            and all(_finite_number(value) for value in values))


def _valid_wave_sequence(values):
    return (isinstance(values, (list, tuple)) and len(values) == 3
            and _finite_number(values[0]) and _finite_number(values[2])
            and (values[1] is None or _finite_number(values[1])))


def _valid_reason(value):
    return value is None or isinstance(value, str)


def audit_b2(stage_a, stage_b, after, geometry, *, eos=EOS):
    """Safely audit B2; malformed/mixed evidence is always INCONCLUSIVE."""
    try:
        if not all(isinstance(item, dict) for item in (stage_a, stage_b, after)):
            return {"status": INCONCLUSIVE, "reason": "missing_b2_stage_state"}
        dt_a, dt_b = stage_a.get("dt"), stage_b.get("dt")
        if (not isinstance(dt_a, (int, float)) or not isinstance(dt_b, (int, float))
                or not math.isfinite(float(dt_a)) or not math.isfinite(float(dt_b))
                or dt_a <= 0.0 or dt_b <= 0.0
                or canonical_binary64([dt_a]) != canonical_binary64([dt_b])):
            return {"status": INCONCLUSIVE, "reason": "stage_dt_missing_or_different"}
        n = len(stage_a.get("primitive", ()))
        if n < 1:
            return {"status": INCONCLUSIVE, "reason": "missing_b2_primitive_state"}
        for label, stage in (("stage_a", stage_a), ("stage_b", stage_b)):
            primitive = stage.get("primitive")
            conservative = stage.get("conservative")
            momentum = stage.get("r5_momentum")
            if (not isinstance(primitive, list) or len(primitive) != n
                    or not all(_valid_float_sequence(row, 4) for row in primitive)
                    or not isinstance(conservative, list) or len(conservative) != n
                    or not all(isinstance(row, (list, tuple)) and len(row) >= 2
                               and all(_finite_number(value) for value in row)
                               for row in conservative)
                    or not isinstance(momentum, dict)
                    or not isinstance(momentum.get("source"), list)
                    or not isinstance(momentum.get("rhs"), list)
                    or len(momentum["source"]) != n or len(momentum["rhs"]) != n
                    or not all(_finite_number(value) for value in momentum["source"])
                    or not all(_finite_number(value) for value in momentum["rhs"])):
                return {"status": INCONCLUSIVE,
                        "reason": f"malformed_{label}_b2_evidence"}
        provisional = stage_b.get("provisional")
        final_rows = after.get("conservative")
        if (not isinstance(provisional, list) or len(provisional) != n
                or not isinstance(final_rows, list) or len(final_rows) != n
                or not all(isinstance(row, (list, tuple)) and len(row) >= 2
                           and all(_finite_number(value) for value in row)
                           for row in provisional + final_rows)):
            return {"status": INCONCLUSIVE, "reason": "malformed_b2_output_state"}
        return _audit_b2_impl(stage_a, stage_b, after, geometry, eos=eos)
    except (KeyError, IndexError, TypeError, ValueError, OverflowError,
            ZeroDivisionError, struct.error) as exc:
        return {"status": INCONCLUSIVE, "reason": "malformed_b2_evidence",
                "error": str(exc)}


def _audit_b2_impl(stage_a, stage_b, after, geometry, *, eos=EOS):
    required = (stage_a, stage_b, after)
    if (not all(isinstance(item, dict) for item in required)
            or "provisional" not in stage_b):
        return {"status": INCONCLUSIVE, "reason": "missing_b2_stage_state"}
    for stage in (stage_a, stage_b):
        if not isinstance(stage.get("r5_momentum"), dict) or not all(
                key in stage["r5_momentum"] for key in ("source", "rhs")):
            return {"status": INCONCLUSIVE, "reason": "missing_b2_product_momentum_evidence"}
    b1_a, b1_b = audit_b1(stage_a, geometry, eos=eos), audit_b1(stage_b, geometry, eos=eos)
    if b1_a["status"] != "PASS" or b1_b["status"] != "PASS":
        status = "FAIL" if "FAIL" in (b1_a["status"], b1_b["status"]) else INCONCLUSIVE
        return {"status": status, "reason": "b1_not_passed", "stage_a": b1_a, "stage_b": b1_b}
    rows = []
    for label, stage, b1, input_rows, output_rows in (
        ("stage_a", stage_a, b1_a, stage_a["conservative"], stage_b["conservative"]),
        ("stage_b", stage_b, b1_b, stage_b["conservative"], stage_b["provisional"]),
    ):
        product = stage["r5_momentum"]
        fluxes = [row["expected"]["flux"] for row in b1["rows"]]
        source = [stage["primitive"][i][2] *
                  (geometry["areas"][i + 1] - geometry["areas"][i])
                  for i in range(len(stage["primitive"]))]
        rhs = [fluxes[i][1] - fluxes[i + 1][1] + source[i]
               for i in range(len(source))]
        expected_output = [row[1] + stage["dt"] * rhs[i]
                           for i, row in enumerate(input_rows)]
        checks = {
            "source_exact": _exact_float_sequence(product.get("source"), source),
            "rhs_exact": _exact_float_sequence(product.get("rhs"), rhs),
            "stage_update_exact": _exact_float_sequence([row[1] for row in output_rows], expected_output),
        }
        rows.append({"stage": label, "checks": checks, "source": source, "rhs": rhs,
                     "expected_output": expected_output})
    q0 = [row[1] for row in stage_a["conservative"]]
    q2 = [row[1] for row in stage_b["provisional"]]
    final_expected = [0.5 * q0[i] + 0.5 * q2[i] for i in range(len(q0))]
    final_actual = [row[1] for row in after["conservative"]]
    final_check = _exact_float_sequence(final_actual, final_expected)
    exact = final_check and all(all(row["checks"].values()) for row in rows)
    return {"status": "PASS" if exact else INCONCLUSIVE,
            "rows": rows, "final_ssprk2_exact": final_check,
            "final_expected": final_expected, "final_actual": final_actual,
            "control_volume_residual": [final_actual[i] - final_expected[i] for i in range(len(q0))]}


def _sign(value):
    return 1 if value > 0.0 else -1 if value < 0.0 else 0


def audit_a(return_info, *, eos=EOS):
    """C1 qualitative A gate over one persisted reconstructed interface pair."""
    if not isinstance(return_info, dict):
        return {"status": INCONCLUSIVE, "reason": "malformed_a_evidence"}
    stages = return_info.get("audit_stages")
    if not isinstance(stages, dict) or not isinstance(stages.get("stage_a"), dict):
        return {"status": INCONCLUSIVE, "reason": "malformed_a_evidence"}
    stage = stages["stage_a"]
    momentum = stage.get("r5_momentum", {})
    if not isinstance(momentum, dict):
        return {"status": INCONCLUSIVE, "reason": "malformed_a_evidence"}
    faces = momentum.get("faces", [])
    interface_rows = ([face for face in faces
                       if isinstance(face, dict) and face.get("kind") == "interface"]
                      if isinstance(faces, list) else [])
    riemann_rows = momentum.get("riemann", [])
    product_rows = ([row for row in riemann_rows
                     if isinstance(row, dict) and row.get("kind") == "interface"]
                    if isinstance(riemann_rows, list) else [])
    if (len(interface_rows) != 1 or interface_rows[0].get("index") != 0
            or len(product_rows) != 1 or product_rows[0].get("index") != 0):
        return {"status": INCONCLUSIVE,
                "reason": "mixed_or_missing_interface_provenance"}
    interface = interface_rows[0]
    product = product_rows[0]
    if (not _valid_float_sequence(interface.get("left"), 4)
            or not _valid_float_sequence(interface.get("right"), 4)
            or not _valid_float_sequence(product.get("flux"), 4)
            or not _valid_wave_sequence(product.get("waves"))
            or not _valid_reason(product.get("reason"))):
        return {"status": INCONCLUSIVE, "reason": "malformed_a_evidence"}
    try:
        left, right = tuple(interface["left"]), tuple(interface["right"])
        audit_flux, audit_waves, audit_reason = audit_hllc(left, right, eos)
        exact = ExactRiemann(left, right, eos)
        sampled = exact.sample(0.0)
        observed = product["flux"]
        if (not _valid_float_sequence(observed, 4)
                or not _valid_wave_sequence(product.get("waves"))):
            return {"status": INCONCLUSIVE, "reason": "malformed_a_flux_or_waves"}
        exact_flux = eos.flux(sampled)
        # ExactRiemann stores each wave as (outer/head, inner/tail).
        # The right rarefaction tuple is therefore descending numerically.
        exact_waves_ordered = (
            exact.waves[0][0] <= exact.waves[0][1]
            <= exact.ustar <= exact.waves[1][1] <= exact.waves[1][0])
        checks = {
            "states_admissible": _admissible(left, eos) and _admissible(right, eos),
            "exact_reference_valid": exact.residual <= 1e-13 and _admissible(sampled, eos),
            "product_flux_finite": all(math.isfinite(value) for value in observed),
            "product_reason_matches": product.get("reason") == audit_reason,
            "no_unexpected_fallback": product.get("reason") is None and audit_reason is None,
            "product_waves_ordered": (_finite_number(product["waves"][1])
                                      and product["waves"][0] < product["waves"][1]
                                      < product["waves"][2]),
            "audit_waves_ordered": (_finite_number(audit_waves[1])
                                    and audit_waves[0] < audit_waves[1] < audit_waves[2]),
            "exact_waves_ordered": exact_waves_ordered,
            "direction_matches": _sign(observed[0]) == _sign(audit_flux[0]) == _sign(exact.ustar),
        }
        return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                "left_state": list(left), "right_state": list(right),
                "hllc_exact_error_is_diagnostic": True,
                "hllc_flux": list(audit_flux), "exact_flux": list(exact_flux),
                "exact_star": {"p": exact.pstar, "u": exact.ustar}}
    except (KeyError, IndexError, TypeError, ValueError, OverflowError,
            ZeroDivisionError, struct.error) as exc:
        return {"status": INCONCLUSIVE, "reason": "a_evidence_error", "error": str(exc)}


def select_causal_return(history, expected_time):
    """Select the preregistered first positive return sample from one history."""
    if (not isinstance(expected_time, (int, float))
            or not math.isfinite(float(expected_time)) or expected_time <= 0.0):
        return None
    window = (0.5 * float(expected_time), 1.5 * float(expected_time))
    for index, info in enumerate(history):
        if not isinstance(info, dict):
            continue
        sample_time = info.get("sample_time_pre_step")
        mass_flux = info.get("mass_flux")
        if (isinstance(sample_time, (int, float))
                and isinstance(mass_flux, (int, float))
                and math.isfinite(float(sample_time))
                and math.isfinite(float(mass_flux))
                and window[0] <= float(sample_time) <= window[1]
                and float(mass_flux) > 0.0):
            return {"index": index, "time": float(sample_time),
                    "window": list(window), "record": info,
                    "rule": "first positive mass_flux in preregistered return window"}
    return None


def evaluate_c3_r5(acquisition, geometry, *, expected_runtime=None, eos=EOS):
    """Evaluate approved C3-R5 gates from one declared acquisition."""
    if (acquisition.get("contract") != CONTRACT
            or acquisition.get("acquisition_kind") != "focal_c3_r5"):
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "not_one_declared_c3_r5_acquisition"}

    actual_runtime = acquisition.get("runtime")
    if expected_runtime is None:
        expected_runtime = runtime_binding()
    if not actual_runtime or actual_runtime != expected_runtime:
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "runtime_binding_missing_or_different"}

    history = acquisition.get("history")
    if not isinstance(history, list) or not history:
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "missing_single_acquisition_history"}

    max_global_resid = acquisition.get("max_global_resid")
    solver_status = acquisition.get("solver_status")
    if (isinstance(solver_status, str)
            and solver_status in EXPLICIT_SOLVER_FAILURES):
        return {"classification": "P4_SCI_C3_FAIL",
                "reason": "solver_admissibility_failed",
                "solver_status": solver_status}
    if (not _finite_number(max_global_resid)
            or float(max_global_resid) < 0.0
            or solver_status is None):
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "existing_physical_evidence_missing"}
    if float(max_global_resid) > CONSERVATION_THRESHOLD:
        return {"classification": "P4_SCI_C3_FAIL",
                "reason": "global_conservation_failed",
                "max_global_resid": float(max_global_resid)}
    solver_time = acquisition.get("solver_time")
    target_final_time = acquisition.get("target_final_time")
    finite_completion_times = (
        _finite_number(solver_time) and _finite_number(target_final_time)
        and float(solver_time) >= 0.0 and float(target_final_time) > 0.0)
    if solver_status == "completed" and not finite_completion_times:
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "solver_completion_time_missing_or_invalid"}
    if solver_status == "completed" and float(solver_time) < float(target_final_time):
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "solver_completion_truncated",
                "solver_time": float(solver_time),
                "target_final_time": float(target_final_time)}
    if solver_status != "completed":
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "solver_completion_not_verified",
                "solver_status": solver_status}

    selection = select_causal_return(history, acquisition.get("expected_return_time"))
    if selection is None:
        return {"classification": "P4_SCI_C3_INCONCLUSIVE",
                "reason": "causal_return_not_selected_from_history"}
    a_report = audit_a(selection["record"], eos=eos)

    reports = []
    for item in history:
        if not isinstance(item, dict):
            reports.append({"status": INCONCLUSIVE,
                            "reason": "malformed_history_record"})
            continue
        stages = item.get("audit_stages", {})
        stage_a = stages.get("stage_a") if isinstance(stages, dict) else None
        stage_b = stages.get("stage_b") if isinstance(stages, dict) else None
        after = stages.get("after") if isinstance(stages, dict) else None
        if not all(isinstance(value, dict) for value in (stage_a, stage_b, after)):
            reports.append({"status": INCONCLUSIVE,
                            "reason": "missing_b2_stage_evidence"})
            continue
        b0 = audit_b0(stage_a, geometry, eos=eos)
        b1a = audit_b1(stage_a, geometry, eos=eos)
        b1b = audit_b1(stage_b, geometry, eos=eos)
        b2 = audit_b2(stage_a, stage_b, after, geometry, eos=eos)
        reports.append({"b0": b0, "b1_stage_a": b1a,
                        "b1_stage_b": b1b, "b2": b2})

    statuses = [r.get("b2", {}).get("status",
                                    r.get("status", INCONCLUSIVE))
                for r in reports]
    if a_report.get("status") == "FAIL" or "FAIL" in statuses:
        classification = "P4_SCI_C3_FAIL"
    elif (a_report.get("status") == "PASS" and statuses
          and all(status == "PASS" for status in statuses)):
        classification = "P4_SCI_C3_PASS"
    else:
        classification = "P4_SCI_C3_INCONCLUSIVE"

    selection_public = {key: value for key, value in selection.items()
                        if key != "record"}
    return {"classification": classification, "contract": CONTRACT,
            "runtime": actual_runtime, "return_selection": selection_public,
            "physical": {"max_global_resid": float(max_global_resid),
                          "conservation_threshold": CONSERVATION_THRESHOLD,
                          "solver_status": solver_status,
                          "solver_time": float(solver_time),
                          "target_final_time": float(target_final_time)},
            "a": a_report, "reports": reports,
            "gates": {"A": a_report.get("status", INCONCLUSIVE),
                      "B0": "evaluated", "B1": "evaluated",
                      "B2": "evaluated"}}
