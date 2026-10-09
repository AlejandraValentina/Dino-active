"""Fail-closed, hash-bound mechanical-loss resolution for RPM sweeps.

Historical engineering APIs retain their existing optional default. New sweep
code must resolve a model through this module before it can evaluate brake
outputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from .mechanical import MechanicalLossModel


class MechanicalLossBindingError(ValueError):
    """A sweep configuration has no usable explicit mechanical-loss model."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ResolvedMechanicalLossV1:
    variant_id: str
    fixture_id: str
    fixture_sha256: str
    engine_configuration_sha256: str
    model_sha256: str
    model: MechanicalLossModel
    provenance: dict[str, Any]


def canonical_sha256(value: Any) -> str:
    try:
        payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MechanicalLossBindingError(
            "INVALID_MECHANICAL_LOSS_PROVENANCE", str(exc)) from exc
    return hashlib.sha256(payload).hexdigest()


def _load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MechanicalLossBindingError(code, f"{path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MechanicalLossBindingError(code, f"{path} must contain a JSON object")
    return value


def resolve_mechanical_loss_v1(
    *,
    preregistration_path: str | Path,
    variant_id: str,
    repository_root: str | Path | None = None,
    rpm_points: tuple[float, ...] | list[float] | None = None,
    load: float = 1.0,
) -> ResolvedMechanicalLossV1:
    """Resolve only the explicit model bound to the registered source fixture.

    The resolver verifies both the registered fixture identity and all nested
    canonical identities before constructing ``MechanicalLossModel``. There
    is deliberately no fallback path.
    """
    prereg_path = Path(preregistration_path).resolve()
    prereg = _load_json(prereg_path, "INVALID_SWEEP_PREREGISTRATION")
    variants = prereg.get("variants")
    if not isinstance(variants, list):
        raise MechanicalLossBindingError(
            "INVALID_SWEEP_PREREGISTRATION", "variants must be a list")
    rows = [row for row in variants
            if isinstance(row, dict) and row.get("variant_id") == variant_id]
    if len(rows) != 1:
        raise MechanicalLossBindingError(
            "SWEEP_VARIANT_NOT_REGISTERED", f"variant_id={variant_id!r}")
    row = rows[0]

    model_data = row.get("mechanical_loss_model")
    if not isinstance(model_data, dict):
        raise MechanicalLossBindingError(
            "MISSING_EXPLICIT_MECHANICAL_LOSS_MODEL",
            f"variant {variant_id} has no mechanical_loss_model")

    root = (Path(repository_root).resolve() if repository_root is not None
            else prereg_path.parents[2])
    source_relative = row.get("source_fixture_path")
    if not isinstance(source_relative, str) or not source_relative:
        raise MechanicalLossBindingError(
            "INVALID_MECHANICAL_LOSS_PROVENANCE", "source_fixture_path is absent")
    fixture_path = (root / Path(source_relative)).resolve()
    if not fixture_path.is_relative_to(root):
        raise MechanicalLossBindingError(
            "INVALID_MECHANICAL_LOSS_PROVENANCE", "fixture path escapes repository root")
    try:
        fixture_bytes = fixture_path.read_bytes()
    except OSError as exc:
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_FIXTURE_UNAVAILABLE", str(exc)) from exc
    fixture_sha = hashlib.sha256(fixture_bytes).hexdigest()
    if fixture_sha != row.get("fixture_sha256"):
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_FIXTURE_HASH_MISMATCH",
            f"expected={row.get('fixture_sha256')} actual={fixture_sha}")
    fixture = _load_json(fixture_path, "INVALID_MECHANICAL_LOSS_FIXTURE")
    if fixture.get("fixture_id") != row.get("fixture_id"):
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_FIXTURE_ID_MISMATCH", variant_id)

    engine_configuration = fixture.get("engine_configuration")
    if not isinstance(engine_configuration, dict):
        raise MechanicalLossBindingError(
            "INVALID_MECHANICAL_LOSS_PROVENANCE", "fixture has no engine_configuration")
    config_sha = canonical_sha256(engine_configuration)
    if (config_sha != row.get("engine_configuration_sha256") or
            config_sha != row.get("declared_configuration_sha256") or
            fixture.get("engine_configuration_sha256") != config_sha):
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_CONFIGURATION_HASH_MISMATCH",
            f"registered={row.get('engine_configuration_sha256')} actual={config_sha}")

    fixture_model = fixture.get("mechanical_loss_model")
    if not isinstance(fixture_model, dict):
        raise MechanicalLossBindingError(
            "MISSING_EXPLICIT_MECHANICAL_LOSS_MODEL",
            "source fixture does not declare mechanical_loss_model")
    if canonical_sha256(fixture_model) != row.get("mechanical_loss_model_sha256"):
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_MODEL_HASH_MISMATCH",
            "source fixture model differs from preregistered model hash")
    if canonical_sha256(model_data) != canonical_sha256(fixture_model):
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_MODEL_BINDING_MISMATCH",
            "preregistered model does not equal the fixture-declared model")
    try:
        model = MechanicalLossModel.from_dict(model_data)
    except (TypeError, ValueError, KeyError) as exc:
        raise MechanicalLossBindingError(
            "INVALID_EXPLICIT_MECHANICAL_LOSS_MODEL", str(exc)) from exc

    for term in model.terms:
        if term.provenance == "UNKNOWN":
            raise MechanicalLossBindingError(
                "INCOMPATIBLE_MECHANICAL_LOSS_PROVENANCE",
                f"term {term.id} provenance is UNKNOWN")

    contract_points = prereg.get("rpm_grid", {}).get("points_rpm")
    points = tuple(rpm_points if rpm_points is not None else contract_points or ())
    if not points:
        raise MechanicalLossBindingError(
            "INVALID_SWEEP_RPM_DOMAIN", "no registered RPM points")
    try:
        # Evaluating every map at every point fails closed on map-domain gaps.
        values = {
            f"{term.id}@{float(rpm):g}": term.value(float(rpm), float(load))
            for term in model.terms for rpm in points
        }
    except (TypeError, ValueError, OverflowError) as exc:
        raise MechanicalLossBindingError(
            "MECHANICAL_LOSS_MODEL_INCOMPATIBLE_WITH_SWEEP", str(exc)) from exc
    model_sha = canonical_sha256(model_data)
    provenance = {
        "schema": "FULL_RPM_SWEEP_MECHANICAL_LOSS_PROVENANCE_V1",
        "fixture_id": fixture["fixture_id"],
        "fixture_path": source_relative,
        "fixture_sha256": fixture_sha,
        "engine_configuration_sha256": config_sha,
        "model_schema": model_data["schema"],
        "model_sha256": model_sha,
        "fields_used": ["terms[].id", "terms[].source", "terms[].provenance",
                        "terms[].mep_pa", "terms[].operating_map"],
        "terms": [term.to_dict() for term in model.terms],
        "evaluated_mep_pa_by_term_and_rpm": values,
        "fallback_used": False,
    }
    return ResolvedMechanicalLossV1(
        variant_id=variant_id,
        fixture_id=fixture["fixture_id"],
        fixture_sha256=fixture_sha,
        engine_configuration_sha256=config_sha,
        model_sha256=model_sha,
        model=model,
        provenance=provenance,
    )
