"""Single-run C3 audit with independent offline momentum reconstruction."""
import json
import math
import statistics
import time
from math import fsum
from pathlib import Path

from dev_orchestrator.p4_sci_04b import EOS, C2_AREA, C2_VOLUME, C2_L_DUCT, solve_c2_one
from dev_orchestrator.reference.exact_riemann import ExactRiemann
from dev_orchestrator.reference.hllc_audit import hllc as audit_hllc

OUT = Path("results/p4-c3-r3-20260928")
CONSERVATION_THRESHOLD = 1e-10  # existing P4/C2 ledger criterion
RESIDUAL_EPSILON = 1e-30


class _AuditEvidenceError(ValueError):
    """Persisted metadata is insufficient to perform the independent audit."""


class _AuditReasonMismatch(ValueError):
    """Product fallback reason disagrees with the independent recomputation."""


def _minmod(a, b):
    if a == 0.0 or b == 0.0 or (a > 0.0) != (b > 0.0):
        return 0.0
    return a if abs(a) <= abs(b) else b


def reconstruct_external_faces(states, geometry, eos=EOS):
    """Minimal independent B0 reconstruction for the two exterior faces.

    This intentionally duplicates only the MUSCL/minmod stencil needed by the
    C3 fixture.  It does not import or call the production reconstruct().
    The left exterior ghost is outflow (the first cell), and the right one is
    the reflective wall ghost.
    """
    if not states:
        raise ValueError("B0 requires at least one primitive cell")
    if "faces" in geometry and "centers" in geometry:
        faces = geometry["faces"]
        centers = geometry["centers"]
    else:
        # Small synthetic unit-cell fixtures may provide only areas.  Their
        # geometry is intentionally normalized here, without consulting a
        # production mesh or flux field.
        n = len(states)
        faces = [float(i) for i in range(n + 1)]
        centers = [i + 0.5 for i in range(n)]
    first = tuple(states[0])
    last = tuple(states[-1])
    left_ghost = first
    right_ghost = (last[0], -last[1], last[2], last[3])

    def face_pair(i, left, xl, right, xr):
        x = centers[i]
        slopes = [_minmod((v - l) / (x - xl), (r - v) / (xr - x))
                  for l, v, r in zip(left, states[i], right)]
        cell = tuple(states[i])
        left = tuple(v + s * (faces[i] - x) for v, s in zip(cell, slopes))
        right = tuple(v + s * (faces[i + 1] - x) for v, s in zip(cell, slopes))
        downgraded = False
        try:
            # Production reconstruct() validates both reconstructed faces and
            # downgrades the complete cell if either face is inadmissible.
            eos.validate(left)
            eos.validate(right)
        except (ValueError, OverflowError, ZeroDivisionError):
            left = right = cell
            downgraded = True
        return left, right, downgraded

    left_ghost_x = 2.0 * faces[0] - centers[0]
    right_ghost_x = 2.0 * faces[-1] - centers[-1]
    if len(states) == 1:
        left_face, right_face, downgraded = face_pair(
            0, left_ghost, left_ghost_x, right_ghost, right_ghost_x)
        left_downgraded = right_downgraded = downgraded
    else:
        left_face, _, left_downgraded = face_pair(
            0, left_ghost, left_ghost_x, states[1], centers[1])
        _, right_face, right_downgraded = face_pair(
            len(states) - 1, states[-2], centers[-2], right_ghost, right_ghost_x)
    wall_right = (right_face[0], -right_face[1], right_face[2], right_face[3])
    downgraded_cells = []
    if left_downgraded:
        downgraded_cells.append(0)
    if right_downgraded and len(states) - 1 not in downgraded_cells:
        downgraded_cells.append(len(states) - 1)
    return {"interface": {"right": list(left_face)},
            "wall": {"left": list(right_face), "right": list(wall_right)},
            "downgraded": {
                "cells": downgraded_cells,
                "sides": {
                    "interface": {"right": left_downgraded},
                    "wall": {"left": right_downgraded,
                             "right": right_downgraded},
                },
            }}


def _b0_audit_stage(stage, geometry):
    expected = reconstruct_external_faces(stage["primitive"], geometry)
    expected["interface"]["left"] = list(_state_from_chamber(stage["chamber_state"]))
    captured = stage.get("external_faces")
    if captured is None:
        return {"status": "FAIL", "reason": "missing_persisted_external_faces",
                "expected": expected}
    reconstruction = captured.get("reconstruction")
    checks = {
        # Both values are derived from the same persisted chamber state with
        # the same algebra; this is metadata identity, not a scientific gate.
        "interface_left": captured["interface"]["left"] == expected["interface"]["left"],
        "interface_right": captured["interface"]["right"] == expected["interface"]["right"],
        "wall_left": captured["wall"]["left"] == expected["wall"]["left"],
        "wall_right": captured["wall"]["right"] == expected["wall"]["right"],
        # Product persists only the cell list.  Expected sides remain an
        # independent B0 diagnostic and are deliberately not compared here.
        "downgrade_metadata_present": (isinstance(reconstruction, dict)
                                        and isinstance(reconstruction.get("downgraded_cells"), list)),
        "downgrade_metadata_matches": (
            isinstance(reconstruction, dict)
            and reconstruction.get("downgraded_cells") == expected["downgraded"]["cells"]),
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks, "expected": expected,
            "captured": captured,
            "product_fluxes_used": False}


def _write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _physical_flux(state):
    rho, velocity, pressure, species = state
    rho_e = EOS.conservative(state)[2]
    return [rho * velocity, rho * velocity * velocity + pressure,
            velocity * (rho_e + pressure), rho * velocity * species]


def _relative_error(observed, expected):
    errors = [abs(a - b) / max(abs(a), abs(b), 1.0)
              for a, b in zip(observed, expected)]
    return {"components": errors, "max": max(errors)}


def _rounding_parity(observed, expected):
    """Report exact/ULP parity as a diagnostic metric, never as a gate."""
    exact = tuple(observed) == tuple(expected)
    ulps = []
    for actual, reference in zip(observed, expected):
        scale = max(abs(actual), abs(reference), 1.0)
        ulps.append(abs(actual - reference) / math.ulp(scale))
    limit = 4.0
    return {
        "exact": exact,
        "within_4_ulp_metric": exact or all(value <= limit for value in ulps),
        "components_ulps": ulps,
        "max_ulps": max(ulps, default=0.0),
        "classification": "METRIC_ONLY",
        "policy": "exact/parity report; 4 ULP is not a preregistered scientific gate",
        "physical_threshold": None,
    }


def _sign(value):
    return 1 if value > 0.0 else -1 if value < 0.0 else 0


def _admissible(state):
    return all(math.isfinite(value) for value in state) and state[0] > 0.0 and state[2] > 0.0


def _state_from_chamber(chamber):
    mass, energy, fresh = chamber
    return (mass / C2_VOLUME, 0.0, (EOS.gamma - 1.0) * energy / C2_VOLUME,
            fresh / mass)


def _select_return(history, expected_time):
    window = (0.5 * expected_time, 1.5 * expected_time)
    candidates = []
    for external_time, info in history:
        sample_time = info.get("sample_time_pre_step", external_time)
        if (window[0] <= sample_time <= window[1]
                and info["mass_flux"] > 0.0):
            candidates.append((sample_time, info))
    return (candidates[0], window) if candidates else (None, window)


def _riemann_audit(info):
    # interface_flux_observed is captured from op0, i.e. stage_a.  Both
    # references must consume the exact same persisted reconstructed face pair.
    stage = info["audit_stages"]["stage_a"]
    observed = list(info["interface_flux_observed"])
    faces = stage.get("external_faces", {}).get("interface")
    if not faces or "left" not in faces or "right" not in faces:
        # Keep the legacy diagnostic shape for old synthetic fixtures, but do
        # not accredit it: the productive reconstructed right face is absent.
        left = _state_from_chamber(stage["chamber_state"])
        right = tuple(stage["primitive"][0])
        reference = ExactRiemann(left, right, EOS)
        expected = [C2_AREA * x for x in _physical_flux(reference.sample(0.0))]
        return {"status": "INCONCLUSIVE",
                "status_reason": "missing_persisted_interface_face_states",
                "criterion_authority": "P4-SCI-03/P4-SCI-04A",
                "left_state": list(left), "right_state": list(right),
                "exact_star": {"p": reference.pstar, "u": reference.ustar,
                                "sample": list(reference.sample(0.0)),
                                "residual": reference.residual},
                "flux_expected_area_integrated": expected,
                "flux_observed_area_integrated": observed,
                "relative_error": _relative_error(observed, expected)}
    left = tuple(faces["left"])
    right = tuple(faces["right"])
    try:
        admissible = {"left": _admissible(left), "right": _admissible(right)}
        if not all(admissible.values()):
            return {"status": "FAIL", "status_reason": "inadmissible_interface_face_state",
                    "left_state": list(left), "right_state": list(right),
                    "admissibility": admissible,
                    "criterion_authority": "P4-SCI-03/P4-SCI-04A"}
        audit_flux, audit_waves, audit_reason = audit_hllc(left, right, EOS)
        reference = ExactRiemann(left, right, EOS)
        sampled = reference.sample(0.0)
        expected_per_area = _physical_flux(sampled)
        expected = [C2_AREA * x for x in expected_per_area]
        audit_expected = [C2_AREA * x for x in audit_flux]
        parity = _rounding_parity(observed, audit_expected)
        hllc_ordered = audit_reason is not None or not (audit_waves[0] < audit_waves[1] < audit_waves[2])
        product_waves = info.get("speeds_iface")
        product_reason = info.get("reason_iface")
        if product_waves is None or "reason_iface" not in info:
            return {"status": "INCONCLUSIVE",
                    "status_reason": "missing_persisted_product_wave_diagnostics",
                    "criterion_authority": "P4-SCI-03/P4-SCI-04A",
                    "left_state": list(left), "right_state": list(right),
                    "hllc_exact_error_is_diagnostic": True}
        product_evidence = product_waves is not None and len(product_waves) == 3
        product_ordered = product_evidence and product_reason is None and all(
            math.isfinite(value) for value in product_waves
        ) and product_waves[0] < product_waves[1] < product_waves[2]
        exact_ordered = not (reference.waves[0][0] <= reference.waves[0][1]
                             <= reference.waves[1][0] <= reference.waves[1][1])
        exact_sample_admissible = _admissible(sampled)
        exact_finite = all(math.isfinite(value) for value in sampled)
        direction = {
            "mass_flux_sign": _sign(audit_flux[0]),
            "hllc_sm_sign": _sign(audit_waves[1]),
            "exact_ustar_sign": _sign(reference.ustar),
        }
        direction_ok = (direction["mass_flux_sign"] == direction["exact_ustar_sign"]
                        and direction["hllc_sm_sign"] == direction["exact_ustar_sign"])
        checks = {
            "states_admissible": all(admissible.values()),
            "product_flux_finite": len(observed) == 4 and all(math.isfinite(value) for value in observed),
            "observed_flux_signs_match": all(_sign(a) == _sign(b)
                                             for a, b in zip(observed, audit_expected)),
            "hllc_no_fallback": audit_reason is None,
            "hllc_ordered": not hllc_ordered,
            "product_no_fallback": product_evidence and product_reason is None,
            "product_ordered": product_ordered,
            "direction_matches_exact_ustar": direction_ok,
            "exact_residual_contract": reference.residual <= 1e-13,
            "exact_sample_admissible": exact_finite and exact_sample_admissible,
            "exact_waves_ordered": not exact_ordered,
        }
        return {
            "status": "QUALITATIVE_PASS" if all(checks.values()) else "FAIL",
            "status_reason": "SCI-03/04A qualitative falsification checks",
            "criterion_authority": "P4-SCI-03/P4-SCI-04A",
            "reference_module": "dev_orchestrator.reference.exact_riemann.ExactRiemann",
            "reference_independent_of_productive_hllc": True,
            "productive_fixture_executed": True,
            "left_state": list(left), "right_state": list(right),
            "normal": info["interface_normal"], "area_m2": info["interface_area"],
            "sample_xi": 0.0,
            "exact_star": {"p": reference.pstar, "u": reference.ustar,
                            "sample": list(sampled), "residual": reference.residual,
                            "waves": [list(pair) for pair in reference.waves]},
            "hllc_audit": {"flux_per_area": list(audit_flux),
                           "waves": list(audit_waves), "fallback_reason": audit_reason},
            "flux_expected_area_integrated": expected,
            "flux_observed_area_integrated": observed,
            "flux_hllc_audit_area_integrated": audit_expected,
            "relative_error": _relative_error(audit_expected, expected),
            "hllc_exact_error_is_diagnostic": True,
            "parity": parity,
            "direction": direction,
            "checks": checks,
            "capture_contract": "stage_a external_faces.interface.left/right and observed op0/stage_a flux",
        }
    except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
        return {"status": "INCONCLUSIVE", "status_reason": "audit_evidence_error",
                "error": str(exc), "criterion_authority": "P4-SCI-03/P4-SCI-04A",
                "left_state": list(left), "right_state": list(right)}


def _recompute_stage(stage, geometry):
    primitive = [tuple(w) for w in stage["primitive"]]
    areas = geometry["areas"]
    left_state = _state_from_chamber(stage["chamber_state"])
    left_flux = C2_AREA * _physical_flux(
        ExactRiemann(left_state, primitive[0], EOS).sample(0.0))[1]
    # The production C2 fixture uses an exact reflective wall state, not a
    # static-pressure face.  Rebuild the physical ghost from the last cell and
    # solve that wall Riemann problem independently of productive HLLC.
    last = primitive[-1]
    ghost = (last[0], -last[1], last[2], last[3])
    wall_reference = ExactRiemann(last, ghost, EOS)
    wall_sample = wall_reference.sample(0.0)
    right_flux = areas[-1] * _physical_flux(wall_sample)[1]
    source = fsum(w[2] * (areas[i + 1] - areas[i])
                   for i, w in enumerate(primitive))
    return {"left": left_flux, "right": right_flux, "source": source,
            "momentum_before": fsum(row[1] for row in stage["conservative"]),
            "units": {"face_flux": "N", "source": "N", "momentum": "kg*m/s"}}


def _recompute_stage_b(stage, geometry):
    """Recompute one B2 stage from B0 states and independent B1 HLLC only."""
    b0 = _b0_audit_stage(stage, geometry)
    if b0["status"] != "PASS":
        raise ValueError("B0 audit failed; B1/B2 are not evaluated")
    faces = b0["captured"]
    # B1 consumes the four literal B0 states.  In particular, do not rebuild
    # the interface-left state from chamber_state here.
    interface_left = tuple(faces["interface"]["left"])
    interface_right = tuple(faces["interface"]["right"])
    wall_left = tuple(faces["wall"]["left"])
    wall_right = tuple(faces["wall"]["right"])
    interface_flux, interface_waves, interface_reason = audit_hllc(
        interface_left, interface_right, EOS)
    wall_flux, wall_waves, wall_reason = audit_hllc(wall_left, wall_right, EOS)
    product_riemann = faces.get("riemann")
    if product_riemann is None:
        raise _AuditEvidenceError("missing_persisted_product_riemann_diagnostics")
    product_interface = product_riemann.get("interface", {})
    product_wall = product_riemann.get("wall", {})
    reason_checks = {
        "interface_reason_matches": product_interface.get("reason") == interface_reason,
        "wall_reason_matches": product_wall.get("reason") == wall_reason,
    }
    wave_checks = {
        "interface_waves_match": list(product_interface.get("speeds", ())) == list(interface_waves),
        "wall_waves_match": list(product_wall.get("speeds", ())) == list(wall_waves),
    }
    if not all(reason_checks.values()):
        raise _AuditReasonMismatch("productive_audit_fallback_reason_mismatch")
    area_left = geometry["areas"][0]
    area_right = geometry["areas"][-1]
    source = fsum(w[2] * (geometry["areas"][i + 1] - geometry["areas"][i])
                  for i, w in enumerate(stage["primitive"]))
    before = fsum(row[1] for row in stage["conservative"])
    return {
        "b0": b0,
        "left": area_left * interface_flux[1],
        "right": area_right * wall_flux[1],
        "source": source,
        "momentum_before": before,
        "b1": {"interface_waves": interface_waves, "wall_waves": wall_waves,
                "interface_reason": interface_reason, "wall_reason": wall_reason,
                "interface_flux": list(interface_flux), "wall_flux": list(wall_flux),
                "product_reasons": {"interface": product_interface.get("reason"),
                                    "wall": product_wall.get("reason")},
                "reason_checks": reason_checks,
                "wave_checks": wave_checks,
                "product_audit_semantics_match": all(reason_checks.values()),
                "wave_parity": wave_checks,
                "fallback": {"interface": interface_reason is not None,
                              "wall": wall_reason is not None}},
        "units": {"face_flux": "N", "source": "N", "momentum": "kg*m/s"},
    }


def _b1_audit_stage(stage, geometry):
    """B1 result for both exterior faces; never reads a product flux field."""
    try:
        result = _recompute_stage_b(stage, geometry)
    except _AuditReasonMismatch as exc:
        return {"status": "FAIL", "status_reason": str(exc),
                "reason": "productive fallback reason gate over persisted B0 states",
                "product_flux_fields_used": []}
    except _AuditEvidenceError as exc:
        return {"status": "INCONCLUSIVE", "status_reason": str(exc),
                "reason": "independent HLLC/HLLE over persisted B0 states",
                "product_flux_fields_used": []}
    except ValueError as exc:
        return {"status": "FAIL", "status_reason": str(exc),
                "reason": "independent HLLC/HLLE over persisted B0 states",
                "product_flux_fields_used": []}
    reason_checks = result["b1"]["reason_checks"]
    return {"status": "PASS" if result["b0"]["status"] == "PASS" else "FAIL",
            "reason": "independent HLLC/HLLE over persisted B0 states",
            "product_flux_fields_used": [], "result": result["b1"]}


def _validate_b2_inputs(stage_a, stage_b, after):
    """Validate the stage contract before doing any balance arithmetic."""
    dt_a = stage_a.get("dt")
    dt_b = stage_b.get("dt")
    if not isinstance(dt_a, (int, float)) or not isinstance(dt_b, (int, float)):
        return "INCONCLUSIVE", "missing_or_non_numeric_stage_dt"
    if not math.isfinite(dt_a) or not math.isfinite(dt_b) or dt_a <= 0.0 or dt_b <= 0.0:
        return "FAIL", "stage_dt_must_be_finite_and_positive"
    if dt_a != dt_b:
        return "FAIL", "stage_dt_mismatch"
    for name, rows in (("stage_a", stage_a.get("conservative")),
                       ("stage_b", stage_b.get("conservative")),
                       ("after", after.get("conservative"))):
        if rows is None:
            return "INCONCLUSIVE", f"missing_{name}_conservative_state"
        if not all(math.isfinite(value) for row in rows for value in row):
            return "FAIL", f"non_finite_{name}_conservative_state"
    for name, states in (("stage_a", stage_a.get("primitive")),
                         ("stage_b", stage_b.get("primitive"))):
        if states is None:
            return "INCONCLUSIVE", f"missing_{name}_primitive_state"
        if not all(_admissible(tuple(state)) for state in states):
            return "FAIL", f"inadmissible_{name}_primitive_state"
    return None, None


def _momentum_audit(history, geometry):
    rows = []
    for time_value, info in history:
        stages = info["audit_stages"]
        input_status, input_reason = _validate_b2_inputs(
            stages["stage_a"], stages["stage_b"], stages["after"])
        if input_status is not None:
            rows.append({"time": time_value, "status": input_status,
                         "status_reason": input_reason})
            continue
        try:
            a = _recompute_stage_b(stages["stage_a"], geometry)
            b = _recompute_stage_b(stages["stage_b"], geometry)
        except _AuditReasonMismatch as exc:
            rows.append({"time": time_value, "status": "FAIL",
                         "status_reason": str(exc)})
            continue
        except _AuditEvidenceError as exc:
            rows.append({"time": time_value, "status": "INCONCLUSIVE",
                         "status_reason": str(exc)})
            continue
        except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError) as exc:
            rows.append({"time": time_value, "status": "INCONCLUSIVE",
                         "status_reason": str(exc)})
            continue
        after = fsum(row[1] for row in stages["after"]["conservative"])
        predicted = 0.5 * stages["stage_a"]["dt"] * (
            a["left"] - a["right"] + a["source"] +
            b["left"] - b["right"] + b["source"])
        observed = after - a["momentum_before"]
        residual = observed - predicted
        relative_residual = abs(residual) / max(abs(predicted), abs(observed),
                                               RESIDUAL_EPSILON)
        rows.append({"time": time_value, "status": "METRIC_ONLY",
                     "dt": stages["stage_a"]["dt"],
                     "recomputed_stage_a": a, "recomputed_stage_b": b,
                     "momentum_after": after, "predicted_delta": predicted,
                     "observed_delta": observed, "residual": residual,
                     "relative_residual": relative_residual})
    row_statuses = [row["status"] for row in rows]
    metric_rows = [row for row in rows if "residual" in row]
    status_counts = {status: row_statuses.count(status)
                     for status in sorted(set(row_statuses))}
    overall_status = ("FAIL" if "FAIL" in row_statuses else
                      "INCONCLUSIVE" if "INCONCLUSIVE" in row_statuses else
                      "METRIC_ONLY")
    invalid_reasons = [row["status_reason"] for row in rows
                       if "residual" not in row]
    if overall_status == "FAIL":
        status_reason = ("Invalid audit evidence or semantic divergence blocked "
                         "B2: " + "; ".join(invalid_reasons))
    elif overall_status == "INCONCLUSIVE":
        status_reason = ("Incomplete or semantically divergent audit evidence "
                         "blocked B2: " + "; ".join(invalid_reasons))
    else:
        status_reason = ("Metric-only balance; no rigorous IEEE-754 backward-error "
                         "bound has been derived for the full primitive "
                         "reconstruction, EOS and HLLC operation graph; no "
                         "physical tolerance is introduced.")
    return {
        "status": overall_status,
        "status_reason": status_reason,
        "control_volume": "all duct cells, chamber excluded",
        "sign_convention": "+x duct direction; left enters, right exits; source=sum[p_i*(A_right-A_left)]",
        "interior_faces": "telescoped by control-volume definition; no productive interior flux array is read",
        "independent_inputs": ["stored conservative states", "stored primitive states",
                               "persisted B0 external face states", "stored areas/faces/volumes", "stage dt"],
        "product_field_names_used": [], "steps": len(rows), "rows": rows,
        "status_counts": status_counts,
        "max_abs_residual": max((abs(r["residual"]) for r in metric_rows), default=0.0),
        "relative_residual_scale": "max(abs(predicted_delta), abs(observed_delta), epsilon)",
        "relative_residual_epsilon": RESIDUAL_EPSILON,
        "max_relative_residual": max((r["relative_residual"] for r in metric_rows),
                                      default=0.0),
        "median_relative_residual": statistics.median(
            [r["relative_residual"] for r in metric_rows]) if metric_rows else 0.0,
        "rounding_policy": {
            "classification": "metric-only",
            "residual_is": "observed SSPRK2 momentum delta minus independently recomputed B1 face/source prediction",
            "physical_threshold": None,
            "missing_justification": "operation-count and conditioning analysis covering EOS primitive conversion, MUSCL minmod branches, HLLC waves, area scaling and fsum order",
        },
    }


def classify(return_ok, conservation_ok, admissibility_ok, riemann, momentum):
    if not return_ok or not conservation_ok or not admissibility_ok:
        return "P4_SCI_C3_FAIL"
    if riemann.get("status") == "FAIL" or momentum.get("status") == "FAIL":
        return "P4_SCI_C3_FAIL"
    # No scientific authorization/gate exists in this revision.  The function
    # deliberately has no implicit PASS path, even when two reports say PASS.
    return "P4_SCI_C3_INCONCLUSIVE"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    expected_time = 2.0 * C2_L_DUCT / math.sqrt(
        EOS.gamma * 100000.0 / (100000.0 / (EOS.R * 300.0)))
    started = time.perf_counter()
    result = solve_c2_one(100, 0.2, 200000.0, 400.0, 0.5,
                          100000.0, 300.0, 0.2, t_final=0.004)
    selected, window = _select_return(result["interface_history"], expected_time)
    return_ok = selected is not None
    if selected is None:
        selected_time, selected_info = None, None
        riemann = {"status": "INCONCLUSIVE", "status_reason": "No admissible return sample in preregistered window."}
    else:
        selected_time, selected_info = selected
        riemann = _riemann_audit(selected_info)
    momentum = _momentum_audit(result["interface_history"], result["audit_geometry"])
    conservation_ok = result["max_global_resid"] <= CONSERVATION_THRESHOLD
    admissibility_ok = result["status"] == "completed"
    classification = classify(return_ok, conservation_ok, admissibility_ok, riemann, momentum)
    capture_contract = {
        "stage_a": "pre-step cells/z/t copied before commit; primitive and observed flux from op0",
        "stage_b": "cells1/z1/op1 primitive",
        "after": "cells_new/z_new/ws_new",
        "invalidated_revision": "174b261",
        "invalidated_reason": "stage_a conservative/chamber captured post-step while primitive/flux were pre-step",
    }
    _write(OUT / "configuration.json", {"N": 100, "CFL": 0.2, "t_final": 0.004,
        "area": C2_AREA, "duct_length": C2_L_DUCT, "backend": "existing C2 fixture",
        "acquisition": "single focal run", "expected_return": expected_time,
        "return_window": window, "conservation_threshold": CONSERVATION_THRESHOLD,
        "capture_contract": capture_contract})
    _write(OUT / "return_snapshot.json", {"status": "PASS" if return_ok else "FAIL",
        "time": selected_time, "interface": selected_info,
        "selection": "first admissible sample in window with positive mass flux"})
    _write(OUT / "exact_riemann_comparison.json", riemann)
    _write(OUT / "momentum_control_volume.json", momentum)
    _write(OUT / "conservation.json", {"max_global_resid": result["max_global_resid"],
        "admissibility": admissibility_ok, "status": "PASS" if conservation_ok else "FAIL",
        "threshold": CONSERVATION_THRESHOLD})
    _write(OUT / "decision.json", {"classification": classification,
        "return_snapshot": "PASS" if return_ok else "FAIL",
        "conservation": "PASS" if conservation_ok else "FAIL",
        "admissibility": "PASS" if admissibility_ok else "FAIL",
        "exact_riemann": riemann["status"], "momentum_balance": momentum["status"],
        "single_run": True, "wall_seconds": time.perf_counter() - started,
        "capture_contract": capture_contract,
        "e13": "NOT_EXECUTED",
        "p9": "STOPPED"})


if __name__ == "__main__":
    main()
