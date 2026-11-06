"""Versioned application validation; no integration equations or tolerances changed."""
from __future__ import annotations

import json
import math
import re

CONFIG_VALIDATION = "DINO4T_CONFIG_VALIDATION_V2"
RESULT_VALIDATION = "DINO4T_RESULT_VALIDATION_V2"
PROVENANCE = ("MEASURED", "DOCUMENTED", "STANDARD_V1", "SYNTHETIC_ASSUMPTION", "CALIBRATED")
METRIC_KEYS = ("imep_rel", "trapped_mass_rel", "pressure_trace_rel", "mass_imbalance_rel")
DEFAULT_TOLERANCES = dict(zip(METRIC_KEYS, (.002, .002, .005, .005)), consecutive=2)
MIN_CYCLES = 3
ASSURANCE_PROFILE = "DINO4T_ROUNDOFF_ASSURANCE_PROFILE_V1"
MAX_RELATIVE_CLOSURE = 1e-12  # scoped native regression admission, not a universal accuracy guarantee


def finite(value):
    try:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    except OverflowError:
        return False


def number(*, positive=False, nonnegative=False, maximum=None, integer=False):
    return {"kind": "integer" if integer else "number", "positive": positive,
            "nonnegative": nonnegative, "maximum": maximum}


def obj(required=(), **fields):
    return {"kind": "object", "required": required, "fields": fields}


def array(item, minimum=1):
    return {"kind": "array", "item": item, "minimum": minimum}


def enum(*values):
    return {"kind": "enum", "values": values}


TEXT = {"kind": "text"}
BOOL = {"kind": "boolean"}
POS = number(positive=True)
NONNEG = number(nonnegative=True)
NUM = number()
META = dict(provenance=enum(*PROVENANCE), notes=TEXT)
TOLERANCE_SCHEMA = obj(**{k: POS for k in METRIC_KEYS}, consecutive=number(positive=True, integer=True))
SEGMENT = obj(("length_mm", "start_diameter_mm", "end_diameter_mm"),
              length_mm=POS, start_diameter_mm=POS, end_diameter_mm=POS)
DUCT_FIELDS = dict(**META, segments=array(SEGMENT), open_end_cd_inflow=NONNEG,
                   open_end_cd_outflow=NONNEG, friction=BOOL, heat_transfer=BOOL, wall_temperature_K=POS)
LIFT = {"kind": "tagged", "tag": "type", "variants": {
    "harmonic": obj(("type", "open_deg", "close_deg", "max_lift_mm"),
                    type=enum("harmonic"), open_deg=NUM, close_deg=NUM, max_lift_mm=POS),
    "tabulated": obj(("type", "angle_deg", "lift_mm"), type=enum("tabulated"),
                     angle_deg=array(NUM, 3), lift_mm=array(NONNEG, 3))}}
CD = obj(("l_over_d", "forward", "reverse"), l_over_d=array(NONNEG),
         forward=array(number(nonnegative=True, maximum=1.2)),
         reverse=array(number(nonnegative=True, maximum=1.2)),
         reference_area=enum("curtain", "inner_seat"), notes=TEXT)
VALVE = obj(("provenance", "count", "diameter_mm", "lift", "discharge_coefficient"),
            **META, count=number(positive=True, integer=True), diameter_mm=POS,
            lift=LIFT, discharge_coefficient=CD)
SCHEMA = obj(("schema", "geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct",
              "combustion", "heat_transfer", "friction", "ambient", "operating_point"),
    schema=enum("DINO4T_ENGINE_CONFIG_V1"), identifier=TEXT, description=TEXT,
    geometry=obj(("provenance", "bore_mm", "stroke_mm", "rod_mm", "compression_ratio"), **META,
                 bore_mm=POS, stroke_mm=POS, rod_mm=POS, compression_ratio=POS),
    intake_valve=VALVE, exhaust_valve=VALVE,
    intake_duct=obj(("provenance", "segments"), **DUCT_FIELDS),
    exhaust_duct=obj(("provenance", "segments"), **DUCT_FIELDS),
    intake_plenum=obj(("provenance", "volume_cm3", "feed_duct"), **META, volume_cm3=POS,
                      feed_duct=obj(("segments",), **DUCT_FIELDS)),
    ambient=obj(("provenance", "intake_pressure_pa", "intake_temperature_K", "exhaust_pressure_pa"),
                **META, intake_pressure_pa=POS, intake_temperature_K=POS,
                exhaust_pressure_pa=POS, exhaust_temperature_K=POS),
    combustion=obj(("provenance", "fuel"), **META, model=enum("WIEBE_SINGLE_ZONE_V1"), enabled=BOOL,
        fuel=TEXT, zone_model=enum("single_zone", "two_zone_equilibrium"), start_deg=NUM,
        duration_deg=POS, wiebe_a=POS, wiebe_m=NONNEG,
        efficiency=number(nonnegative=True, maximum=1), water_gas_k=POS),
    heat_transfer=obj(("provenance",), **META, model=enum("WOSCHNI_1967"), enabled=BOOL,
        **{k: POS for k in ("t_head_K", "t_piston_K", "t_liner_K", "head_area_factor", "piston_area_factor")},
        **{k: NONNEG for k in ("c0", "c1_gas_exchange", "c1_closed", "c2_combustion", "multiplier")}),
    friction=obj(("provenance", "a_pa", "b", "c_pa_s_m", "d_pa_s2_m2"), **META,
                 model=enum("CHEN_FLYNN"), a_pa=NUM, b=NUM, c_pa_s_m=NUM, d_pa_s2_m2=NUM),
    operating_point=obj(("rpm", "equivalence_ratio"), rpm=POS, equivalence_ratio=NONNEG),
    initial_conditions=obj(cylinder_pressure_pa=POS, cylinder_temperature_K=POS, exhaust_temperature_K=POS),
    numerics=obj(dx_mm=POS, cfl=number(positive=True, maximum=1), max_dtheta_deg=POS,
                 second_order=BOOL, limiter=enum("minmod", "van_leer", "mc", "unlimited_central"),
                 max_cycles=number(positive=True, integer=True), periodicity=TOLERANCE_SCHEMA,
                 restriction_model=enum("V1", "V2")))


def configuration_issues(config):
    issues = []

    def fail(path, message, code="CONFIG_INVALID"):
        issues.append({"code": code, "path": path or "$", "message": f"{path or '$'}: {message}"})

    def walk(value, spec, path):
        kind = spec["kind"]
        if kind == "tagged":
            if not isinstance(value, dict):
                fail(path, "expected an object"); return
            choice = value.get(spec["tag"])
            if not isinstance(choice, str) or choice not in spec["variants"]:
                fail(path + "." + spec["tag"], "unsupported selector"); return
            walk(value, spec["variants"][choice], path); return
        if kind == "object":
            if not isinstance(value, dict):
                fail(path, "expected an object"); return
            for key in spec["required"]:
                if key not in value: fail(f"{path}.{key}".lstrip("."), "required field is missing")
            for key, item in value.items():
                sub = f"{path}.{key}".lstrip(".")
                if key not in spec["fields"]: fail(sub, "unknown or misplaced field", "UNKNOWN_KEY")
                else: walk(item, spec["fields"][key], sub)
        elif kind == "array":
            if not isinstance(value, list) or len(value) < spec["minimum"]:
                fail(path, f"expected an array of at least {spec['minimum']} values"); return
            for i, item in enumerate(value): walk(item, spec["item"], f"{path}.{i}")
        elif kind in ("number", "integer"):
            if not finite(value) or (kind == "integer" and not isinstance(value, int)):
                fail(path, "expected a finite integer" if kind == "integer" else "expected a finite number"); return
            if spec["positive"] and value <= 0: fail(path, "must be positive")
            if spec["nonnegative"] and value < 0: fail(path, "must be nonnegative")
            if spec["maximum"] is not None and value > spec["maximum"]: fail(path, f"must be <= {spec['maximum']}")
        elif kind == "boolean" and not isinstance(value, bool): fail(path, "expected a boolean")
        elif kind == "text" and not isinstance(value, str): fail(path, "expected text")
        elif kind == "enum" and value not in spec["values"]: fail(path, f"expected one of {spec['values']}")

    walk(config, SCHEMA, "")
    if isinstance(config, dict) and isinstance(config.get("combustion"), dict):
        c = config["combustion"]
        if c.get("enabled", True):
            for key in ("start_deg", "duration_deg"):
                if key not in c: fail("combustion." + key, "required when combustion is enabled")
    return issues


def tolerance_issues(tolerances):
    if not isinstance(tolerances, dict): return ["periodicity tolerances must be an object"]
    issues = [f"unknown periodicity tolerance {k}" for k in tolerances if k not in DEFAULT_TOLERANCES]
    for key, value in tolerances.items():
        if key in DEFAULT_TOLERANCES and (not finite(value) or value <= 0 or
                (key == "consecutive" and not isinstance(value, int))):
            issues.append(f"periodicity.{key} must be a finite positive {'integer' if key == 'consecutive' else 'number'}")
    return issues


def summary_issues(summary, config=None):
    """Semantic validity, never a claim of model fidelity or experimental truth."""
    from .api import RESULT_REQUIRED_KEYS, RESULT_SCHEMA, RUN_STATUSES
    issues = []
    if not isinstance(summary, dict): return ["summary must be an object"]
    issues.extend(f"missing key {k}" for k in RESULT_REQUIRED_KEYS if k not in summary)
    if summary.get("schema") != RESULT_SCHEMA: issues.append("unsupported result schema")
    from . import MODEL_ID
    if summary.get("model_id") != MODEL_ID: issues.append("unsupported native model identity")
    def check_finite(node, path):
        if isinstance(node, dict):
            for key, value in node.items(): check_finite(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node): check_finite(value, f"{path}.{i}")
        elif isinstance(node, (int, float)) and not isinstance(node, bool) and not finite(node):
            issues.append(path + " is not finite")
    check_finite(summary, "summary")
    operating = summary.get("operating_point")
    if not isinstance(operating, dict) or not finite(operating.get("rpm")) or operating["rpm"] <= 0 or not finite(operating.get("equivalence_ratio")) or operating["equivalence_ratio"] < 0:
        issues.append("operating_point requires finite positive rpm and nonnegative equivalence_ratio")
    commit = summary.get("code_commit")
    if commit is not None and (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)):
        issues.append("code_commit is neither a complete Git identity nor explicitly unknown")
    status = summary.get("status"); termination = summary.get("termination")
    if status not in RUN_STATUSES: issues.append("invalid run status")
    if not isinstance(termination, str) or not termination: issues.append("invalid termination")
    n = summary.get("cycles_run")
    if not isinstance(n, int) or isinstance(n, bool) or n < 0: issues.append("cycles_run must be a nonnegative integer"); n = 0
    claims = summary.get("claims")
    if not isinstance(claims, dict): issues.append("claims must be an object")
    else:
        for key, expected in (("calibration", "NOT_PERFORMED"), ("experimental_validation", "NOT_PERFORMED"),
                              ("predictive_capability", "NOT_CLAIMED")):
            if claims.get(key) != expected: issues.append(f"{key}: no verified validation/calibration authority exists in this contract")
    period = summary.get("periodicity")
    if not isinstance(period, dict): issues.append("periodicity must be an object"); period = {}
    tol = period.get("tolerances"); problems = tolerance_issues(tol)
    if isinstance(tol, dict) and set(tol) != set(DEFAULT_TOLERANCES):
        problems.append("result must retain all actual detector settings")
    issues.extend(problems); effective = dict(DEFAULT_TOLERANCES)
    if isinstance(tol, dict): effective.update(tol)
    history = period.get("history"); streak = 0
    if not isinstance(history, list) or len(history) != n:
        issues.append("periodicity history must contain one entry per complete cycle"); history = []
    for index, metric in enumerate(history):
        if index == 0:
            if metric is not None: issues.append("first cycle has no previous comparison")
            continue
        if not isinstance(metric, dict) or not all(finite(metric.get(k)) and metric[k] >= 0 for k in METRIC_KEYS):
            issues.append(f"periodicity history[{index}] contains invalid metrics"); streak = 0; continue
        passed = not problems and all(metric[k] <= effective[k] for k in METRIC_KEYS)
        if metric.get("passed") is not passed: issues.append(f"periodicity history[{index}].passed contradicts metrics")
        streak = streak + 1 if passed else 0
    computed = not problems and n >= MIN_CYCLES and streak >= effective["consecutive"]
    expected_period = "PERIODIC_CONVERGED" if computed else "NOT_CONVERGED"
    if period.get("status") != expected_period: issues.append("periodicity status contradicts actual comparisons/minimum cycles")
    if status == "completed":
        if n == 0: issues.append("completed result has no complete cycles")
        if termination != ("periodic_converged" if computed else "requested_cycles"):
            issues.append("completed termination contradicts periodicity")
    elif status == "incomplete" and termination not in ("wall_limit", "cancelled_by_user"):
        issues.append("incomplete termination is inconsistent")
    if status != "completed" and computed: issues.append("noncompleted result cannot be a periodic success")
    if status == "failed_numerical" and termination in ("requested_cycles", "periodic_converged", "wall_limit", "cancelled_by_user"):
        issues.append("failed numerical termination contradicts status")
    detector = period.get("detector")
    if detector is not None and detector != {"schema": "DINO4T_PERIODICITY_DECISION_V2", "min_cycles": MIN_CYCLES}:
        issues.append("unsupported native detector identity/minimum cycles")
    if isinstance(summary.get("cycle_history"), list) and len(summary["cycle_history"]) != n:
        issues.append("cycle_history length contradicts cycles_run")
    final = summary.get("final_cycle")
    if n == 0:
        if final is not None: issues.append("zero-cycle result must not have final-cycle performance")
    elif not isinstance(final, dict): issues.append("complete cycles require final_cycle")
    else:
        for key in ("brake_power_kW", "brake_torque_Nm", "bmep_bar", "imep_net_bar", "fmep_bar"):
            if not finite(final.get(key)): issues.append(f"final_cycle.{key} must be finite")
        if finite(final.get("fmep_bar")) and final["fmep_bar"] < 0: issues.append("negative evaluated friction loss is outside the model's physical domain")
        if all(finite(final.get(k)) for k in ("imep_net_bar", "fmep_bar", "bmep_bar")) and not math.isclose(
                final["bmep_bar"], final["imep_net_bar"] - final["fmep_bar"], rel_tol=1e-12, abs_tol=1e-12):
            issues.append("BMEP contradicts net IMEP minus FMEP")
    conservation = summary.get("conservation")
    if not isinstance(conservation, dict): issues.append("conservation must be an object")
    else:
        maximum = conservation.get("max_relative_closure", {}); last = conservation.get("final_relative_closure", {})
        for key in ("mass", "energy", "elements"):
            if not isinstance(maximum, dict) or not finite(maximum.get(key)) or maximum[key] < 0:
                issues.append(f"conservation maximum {key} must be finite/nonnegative")
            elif maximum[key] >= MAX_RELATIVE_CLOSURE:
                issues.append(f"INELIGIBLE_INTEGRITY: {key} outside {ASSURANCE_PROFILE}")
            if not isinstance(last, dict) or not finite(last.get(key)) or last[key] < 0:
                issues.append(f"conservation final {key} must be finite/nonnegative")
            elif isinstance(maximum, dict) and finite(maximum.get(key)) and last[key] > maximum[key] + 1e-15:
                issues.append(f"conservation final {key} exceeds recorded maximum")
    if config is not None:
        from .config import canonical_hash
        from .runner import resolved_models
        from .api import validate
        config_problems = validate(config)["issues"]
        if config_problems: issues.append("resolved config is invalid")
        else:
            if summary.get("config_sha256") != canonical_hash(config): issues.append("config identity mismatch")
            if summary.get("operating_point") != config["operating_point"]: issues.append("operating point contradicts config")
            actual = summary.get("models", {}); expected = resolved_models(config)
            if not isinstance(actual, dict) or any(actual.get(k) != v for k, v in expected.items()):
                issues.append("selected models contradict resolved config")
            expected_tol = dict(DEFAULT_TOLERANCES, **config.get("numerics", {}).get("periodicity", {}))
            if tol != expected_tol: issues.append("detector tolerances contradict resolved config")
            expected_prov = {k: config[k]["provenance"] for k in ("geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct", "combustion", "heat_transfer", "friction", "ambient")}
            if summary.get("provenance") != expected_prov: issues.append("provenance contradicts config")
            if isinstance(final, dict):
                try:
                    g = config["geometry"]; rpm = config["operating_point"]["rpm"]
                    displacement = math.pi / 4 * (g["bore_mm"] * 1e-3) ** 2 * g["stroke_mm"] * 1e-3
                    speed = 2 * g["stroke_mm"] * 1e-3 * rpm / 60
                    fr = config["friction"]
                    def identity(key, expected):
                        if not finite(final.get(key)) or not finite(expected) or not math.isclose(final[key], expected, rel_tol=1e-12, abs_tol=1e-12):
                            issues.append(f"final_cycle.{key} contradicts native config/indicator identity")
                    if finite(final.get("p_max_bar")):
                        loss = (fr["a_pa"] + fr["b"] * final["p_max_bar"] * 1e5 + fr["c_pa_s_m"] * speed + fr["d_pa_s2_m2"] * speed ** 2) / 1e5
                        identity("fmep_bar", loss)
                    else: issues.append("final_cycle.p_max_bar must be finite")
                    if finite(final.get("bmep_bar")):
                        power = final["bmep_bar"] * 1e5 * displacement * rpm / 120 / 1000
                        identity("brake_power_kW", power)
                        identity("brake_torque_Nm", power * 1000 / (2 * math.pi * rpm / 60))
                    if finite(final.get("work_net_J")): identity("imep_net_bar", final["work_net_J"] / displacement / 1e5)
                except (OverflowError, ZeroDivisionError):
                    issues.append("derived config/indicator arithmetic is outside finite representable domain")
    if not isinstance(summary.get("models"), dict): issues.append("models must be an object")
    if summary.get("code_dirty") is not None and not isinstance(summary.get("code_dirty"), bool): issues.append("code_dirty must be bool or unknown")
    sources = summary.get("thermo_sources")
    if not isinstance(sources, dict): issues.append("thermo_sources must be an object")
    else:
        for key in ("gri30_sha256", "burcat_sha256"):
            value = sources.get(key)
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                issues.append("invalid thermochemistry source digest: " + key)
    if "source_identity" in summary:
        from ..source_provenance import validate_source_identity
        identity = summary["source_identity"]
        issues.extend(validate_source_identity(identity))
        if isinstance(identity, dict) and (identity.get("code_commit") != summary.get("code_commit") or identity.get("dirty") is not summary.get("code_dirty")):
            issues.append("source identity contradicts summary code origin")
    return issues
