"""Strict, lossless comparison records for native Dino 4T results."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math

from .. import engine_platform

SCHEMA = "DINO4T_AB_COMPARISON_V2"
DESIGN_SECTIONS = ("geometry", "intake_valve", "exhaust_valve", "intake_duct",
                   "exhaust_duct", "intake_plenum")
METRICS = (
    ("Potencia de freno", "brake_power_kW", "kW"),
    ("Torque de freno", "brake_torque_Nm", "N·m"),
    ("BMEP", "bmep_bar", "bar"),
    ("IMEP neto", "imep_net_bar", "bar"),
)


class ComparisonIneligible(ValueError):
    """The two run endpoints do not meet the registered comparison conditions."""


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _run_context(config: dict) -> dict:
    """Keep every operating/model/numerical input; remove only declared design sections."""
    normalized = deepcopy(config)
    normalized.pop("identifier", None)
    normalized.pop("description", None)
    for section in DESIGN_SECTIONS:
        design = normalized.get(section)
        if isinstance(design, dict):
            normalized[section] = {"provenance": design.get("provenance")}
    return normalized


def _flatten_changes(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            yield from _flatten_changes(a.get(key), b.get(key), (*path, str(key)))
    elif isinstance(a, list) and isinstance(b, list):
        for index in range(max(len(a), len(b))):
            av = a[index] if index < len(a) else None
            bv = b[index] if index < len(b) else None
            yield from _flatten_changes(av, bv, (*path, str(index)))
    elif a != b:
        yield {"path": ".".join(path), "a": a, "b": b}


def _require(condition: bool, message: str):
    if not condition:
        raise ComparisonIneligible(message)


def build_comparison(endpoint_a: dict, endpoint_b: dict, *, policy="STRICT_SOURCE_V1") -> dict:
    """Validate two verified endpoint dictionaries and return a reproducible A/B record.

    Each endpoint contains ``summary``, resolved ``config``, ``meta``, ``reference``
    and optionally ``trace_sha256``. The Desktop history loader verifies source
    bytes/hashes before calling this function.
    """
    _require(policy in ("STRICT_SOURCE_V1", "LEGACY_RECEIPT_DESCRIPTIVE_V1"), "Política de comparación desconocida")
    from .four_stroke_artifacts import require_verified_run
    verified = []
    for supplied in (endpoint_a, endpoint_b):
        try:
            original = require_verified_run(supplied["reference"])
        except (ValueError, OSError, KeyError, TypeError) as exc:
            raise ComparisonIneligible("No hay vínculo original verificable: " + str(exc)) from exc
        _require(supplied.get("summary") == original.summary and supplied.get("config") == original.config,
                 "El endpoint contradice los datos originales verificados")
        verified.append(original.endpoint())
    a, b = verified
    sa, sb = a["summary"], b["summary"]
    ca, cb = a["config"], b["config"]
    ma, mb = a["meta"], b["meta"]
    ra, rb = a["reference"], b["reference"]

    for side, summary, config, meta, ref in (("A", sa, ca, ma, ra), ("B", sb, cb, mb, rb)):
        try:
            from ..dino4t import api
            problems = api.check_summary(summary, config=config)
            if problems: raise ValueError("; ".join(problems))
        except ValueError as exc:
            raise ComparisonIneligible(f"Resultado {side} no cumple el contrato 4T: {exc}") from exc
        _require(summary.get("status") == "completed", f"El resultado {side} no terminó correctamente")
        _require(summary.get("periodicity", {}).get("status") == "PERIODIC_CONVERGED",
                 f"El resultado {side} no alcanzó periodicidad con los criterios registrados")
        checked = engine_platform.validate_config("4T", config)
        _require(checked["valid"] and not checked["unknown_keys"],
                 f"Configuración {side} inválida o con claves desconocidas")
        _require(checked["config_sha256"] == summary.get("config_sha256") == ref.get("config_sha256"),
                 f"Hash de configuración {side} inconsistente")
        _require(meta.get("result_sha256") == ref.get("result_sha256"),
                 f"Hash de resultado {side} inconsistente")
        _require(summary.get("code_dirty") is False and isinstance(summary.get("code_commit"), str),
                 f"La identidad del código de {side} no es reproducible")
        _require(meta.get("api") == "DINO4T_API_V1", f"La corrida {side} no declara DINO4T_API_V1")
        if policy == "STRICT_SOURCE_V1":
            _require(meta.get("source_qualification") == "COMPLETE_CLEAN_SOURCE_SNAPSHOT",
                     f"La procedencia del código de {side} carece de inventario original completo; histórico no promocionado")
            _require(isinstance(summary.get("runtime_environment"), dict) and all(isinstance(summary["runtime_environment"].get(k), str) and summary["runtime_environment"][k] for k in ("python", "implementation", "platform", "numpy", "scipy")),
                     "Falta identidad del entorno numérico original")
        else:
            _require(meta.get("artifact_origin", {}).get("kind") == "EXPLICIT_LEGACY_RECEIPT_RECONSTRUCTION",
                     "La política descriptiva requiere recibos históricos originales explícitos")
        expected_provenance = {name: config[name].get("provenance") for name in
            ("geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct",
             "combustion", "heat_transfer", "friction", "ambient")}
        _require(summary.get("provenance") == expected_provenance,
                 f"La procedencia declarada por el resultado {side} no coincide con su configuración")
        _require(summary.get("claims", {}).get("experimental_validation") == "NOT_PERFORMED"
                 and summary.get("claims", {}).get("predictive_capability") == "NOT_CLAIMED",
                 f"El resultado {side} contiene claims científicos no admitidos por esta comparación")

    _require(ra.get("run_id") != rb.get("run_id"), "Se requieren dos corridas distintas")
    _require(sa.get("model_id") == sb.get("model_id") and sa.get("models") == sb.get("models"),
             "Los identificadores o selecciones de modelo 4T no coinciden")
    _require(sa.get("code_commit") == sb.get("code_commit"), "Los commits del solver no coinciden")
    if policy == "STRICT_SOURCE_V1":
        _require(sa["source_identity"]["canonical_code_inventory_sha256"] == sb["source_identity"]["canonical_code_inventory_sha256"],
                 "Los inventarios de código originales no coinciden")
        _require(sa["runtime_environment"] == sb["runtime_environment"], "Los entornos numéricos originales no coinciden")
    _require(sa.get("thermo_sources") == sb.get("thermo_sources"), "Las fuentes termodinámicas no coinciden")
    _require(sa.get("periodicity", {}).get("tolerances") == sb.get("periodicity", {}).get("tolerances"),
             "Los criterios de periodicidad no coinciden")
    _require(_canonical(sa.get("operating_point")) == _canonical(sb.get("operating_point")),
             "Las condiciones de operación, incluido RPM exacto, no coinciden")
    _require(_canonical(_run_context(ca)) == _canonical(_run_context(cb)),
             "Hay diferencias fuera de los grupos geométricos/de diseño permitidos")

    provenance_a = sa.get("provenance")
    provenance_b = sb.get("provenance")
    _require(provenance_a == provenance_b, "Las etiquetas de procedencia física no coinciden")
    changes = []
    for section in DESIGN_SECTIONS:
        changes.extend(_flatten_changes(ca.get(section), cb.get(section), (section,)))
    _require(bool(changes), "Las configuraciones no tienen diferencias de diseño")

    fa, fb = sa.get("final_cycle") or {}, sb.get("final_cycle") or {}
    rows = []
    for label, key, unit in METRICS:
        av, bv = fa.get(key), fb.get(key)
        _require(_finite(av) and _finite(bv), f"La métrica requerida {key} no es finita en ambos resultados")
        delta = float(bv) - float(av)
        relative = (delta / abs(float(av)) * 100.0) if float(av) != 0.0 else None
        rows.append({"label": label, "key": key, "unit": unit, "a": float(av), "b": float(bv),
                     "delta_b_minus_a": delta, "relative_percent_to_abs_a": relative})

    endpoints = []
    for side, summary, config, meta, ref, source in (
        ("A", sa, ca, ma, ra, a), ("B", sb, cb, mb, rb, b)):
        endpoints.append({
            "side": side, "run_id": ref["run_id"], "variant_id": ref.get("variant_id") or "",
            "result_sha256": ref["result_sha256"], "config_sha256": summary["config_sha256"],
            "trace_sha256": source.get("trace_sha256"),
            "run_manifest_sha256": ref["run_manifest_sha256"],
            "artifacts_manifest_sha256": meta["artifacts_manifest_sha256"],
            "artifact_origin": meta["artifact_origin"], "artifact_byte_policy": meta["artifact_byte_policy"],
            "source_qualification": meta["source_qualification"],
            "source_identity": summary.get("source_identity"),
            "runtime_environment": summary.get("runtime_environment"),
            "code_commit": summary["code_commit"], "code_dirty": summary["code_dirty"],
            "api": meta.get("api"), "model_id": summary["model_id"], "models": summary["models"],
            "thermo_sources": summary["thermo_sources"], "provenance": summary["provenance"],
            "run_status": summary["status"], "periodicity": summary["periodicity"],
            "cycles_run": summary["cycles_run"], "conservation": summary["conservation"],
            "final_cycle": summary["final_cycle"], "resolved_config": config,
            "summary_path": meta.get("summary_path"), "config_path": meta.get("config_path"),
            "trace_path": meta.get("trace_path"),
        })

    payload = {
        "schema": SCHEMA, "classification": "PERIODIC_MODEL_SENSITIVITY_ONLY" if policy == "STRICT_SOURCE_V1" else "LEGACY_SOURCE_UNVERIFIED_MODEL_SENSITIVITY",
        "comparison_policy": policy,
        "qualification": {
            "calibration": "NOT_PERFORMED", "experimental_validation": "NOT_PERFORMED",
            "predictive_capability": "NOT_CLAIMED",
            "periodicity_is_not_experimental_validation": True,
            "delta_is_not_evidence_of_real_engine_performance_improvement": True,
            "relative_delta_denominator": "absolute baseline A; null when A is zero",
            "source_provenance": "complete original source snapshots" if policy == "STRICT_SOURCE_V1" else "legacy source identity not independently verified by artifact reconstruction",
        },
        "operating_point": sa["operating_point"], "model_id": sa["model_id"], "models": sa["models"],
        "periodicity_tolerances": sa["periodicity"]["tolerances"],
        "design_changes": changes, "metrics": rows, "endpoints": endpoints,
    }
    digest_source = deepcopy(payload)
    for endpoint in digest_source["endpoints"]:
        endpoint.pop("summary_path", None)
        endpoint.pop("config_path", None)
        endpoint.pop("trace_path", None)
    payload["comparison_id"] = hashlib.sha256(_canonical(digest_source).encode("utf-8")).hexdigest()
    return payload
