"""Exploratory pressure/dyno import; deliberately separate from P9 intake."""
from __future__ import annotations

import csv
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
from pathlib import Path
import re
import uuid
from typing import Any

SCHEMA = "motorsim-measurement-dataset-v1"
FORMAT = "motorsim-measurement-import"
LIMIT_BYTES = 16 * 1024 * 1024
LIMIT_ROWS = 100_000
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
META_TEXT = ("engine", "configuration", "conditions", "source", "notes")
PROVENANCE = {"MEASURED", "DOCUMENTED", "SYNTHETIC", "UNKNOWN"}
KINDS = {
    "pressure_trace": {"headers": ("cycle", "crank_angle_deg", "value", "uncertainty"),
                       "x": "crank_angle_deg", "x_unit": "degCA",
                       "value_units": {"Pa": 1.0, "kPa": 1000.0, "bar": 100_000.0}},
    "dyno_torque": {"headers": ("rpm", "value", "uncertainty"),
                    "x": "rpm", "x_unit": "rpm",
                    "value_units": {"N*m": 1.0, "lb-ft": 1.3558179483314004}},
    "dyno_power": {"headers": ("rpm", "value", "uncertainty"),
                   "x": "rpm", "x_unit": "rpm",
                   "value_units": {"W": 1.0, "kW": 1000.0, "hp": 745.6998715822702}},
}
CANONICAL_UNITS = {"pressure_trace": "Pa", "dyno_torque": "N*m", "dyno_power": "W"}


class MeasurementDataError(ValueError):
    pass


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise MeasurementDataError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise MeasurementDataError(f"{label} outside supported range")
    return result


def _parse_number(text: str, row: int, column: str) -> float:
    if not isinstance(text, str) or len(text.strip()) > 80 or not NUMBER.fullmatch(text.strip()):
        raise MeasurementDataError(f"row {row}, {column}: finite decimal with dot and no thousands separators required")
    try:
        exact = Decimal(text.strip())
        value = float(exact)
    except (ValueError, OverflowError, InvalidOperation):
        raise MeasurementDataError(f"row {row}, {column}: number outside finite range") from None
    if not math.isfinite(value) or (exact != 0 and value == 0):
        raise MeasurementDataError(f"row {row}, {column}: number outside finite range")
    return value


def declarations(kind: str, value_unit: str, *, uncertainty_unit: str | None = None,
                 cycle_period_deg: int | None = None, provenance: str = "UNKNOWN", **texts):
    if kind not in KINDS:
        raise MeasurementDataError("Unsupported measurement kind")
    definition = KINDS[kind]
    if value_unit not in definition["value_units"]:
        raise MeasurementDataError("Unsupported measurement value unit")
    uncertainty_unit = value_unit if uncertainty_unit is None else uncertainty_unit
    if uncertainty_unit != value_unit:
        raise MeasurementDataError("Uncertainty must use the declared value unit")
    if kind == "pressure_trace":
        if type(cycle_period_deg) is not int or cycle_period_deg not in (360, 720):
            raise MeasurementDataError("Pressure trace must declare 360 or 720 degrees per cycle")
    elif cycle_period_deg is not None:
        raise MeasurementDataError("Cycle period applies only to pressure traces")
    if provenance not in PROVENANCE:
        raise MeasurementDataError("Measurement provenance is invalid")
    if set(texts) - set(META_TEXT):
        raise MeasurementDataError("Unknown measurement metadata field")
    result = {"schema": SCHEMA, "kind": kind, "x_unit": definition["x_unit"],
              "angle_convention": "forward_from_tdc_zero_tdc" if kind == "pressure_trace" else None,
              "value_unit": value_unit, "canonical_value_unit": CANONICAL_UNITS[kind],
              "uncertainty_unit": uncertainty_unit, "cycle_period_deg": cycle_period_deg,
              "provenance": provenance}
    for key in META_TEXT:
        value = texts.get(key, "")
        if not isinstance(value, str) or len(value) > 4096:
            raise MeasurementDataError(f"{key} must be text up to 4096 characters")
        result[key] = value.strip() or "Not provided"
    return result


def validate_declarations(value: Any):
    expected_fields = {"schema", "kind", "x_unit", "value_unit", "canonical_value_unit",
                       "uncertainty_unit", "cycle_period_deg", "angle_convention",
                       "provenance", *META_TEXT}
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise MeasurementDataError("Measurement metadata fields are incomplete or unknown")
    expected = declarations(value["kind"], value["value_unit"],
        uncertainty_unit=value["uncertainty_unit"], cycle_period_deg=value["cycle_period_deg"],
        provenance=value["provenance"], **{key: value[key] for key in META_TEXT})
    if value != expected:
        raise MeasurementDataError("Measurement metadata units or definitions are inconsistent")
    return expected


def parse_csv(raw: bytes, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    meta = validate_declarations(metadata)
    if not isinstance(raw, bytes) or len(raw) > LIMIT_BYTES:
        raise MeasurementDataError("CSV must be bytes up to 16 MiB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeError as error:
        raise MeasurementDataError("CSV must be UTF-8") from error
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    definition = KINDS[meta["kind"]]
    try:
        header = next(reader, None)
        if tuple(header or ()) != definition["headers"]:
            raise MeasurementDataError("CSV header does not match the declared measurement kind")
        parsed = []
        seen = set()
        factor = definition["value_units"][meta["value_unit"]]
        for cells in reader:
            row_number = reader.line_num
            if len(cells) != len(definition["headers"]):
                raise MeasurementDataError(f"row {row_number}: incorrect column count")
            record = dict(zip(definition["headers"], cells))
            if meta["kind"] == "pressure_trace":
                cycle_text = record["cycle"].strip()
                if not re.fullmatch(r"[1-9][0-9]*", cycle_text) or len(cycle_text) > 12:
                    raise MeasurementDataError(f"row {row_number}, cycle: positive integer required")
                cycle = int(cycle_text)
                angle = _parse_number(record["crank_angle_deg"], row_number, "crank_angle_deg")
                if not 0.0 <= angle <= meta["cycle_period_deg"]:
                    raise MeasurementDataError(f"row {row_number}, crank_angle_deg: outside declared cycle")
                key = (cycle, angle)
                canonical = {"cycle": cycle, "x": angle}
                canonical["x_unit"] = "degCA"
            else:
                rpm = _parse_number(record["rpm"], row_number, "rpm")
                if rpm <= 0:
                    raise MeasurementDataError(f"row {row_number}, rpm: must be positive")
                key = rpm
                canonical = {"x": rpm, "x_unit": "rpm"}
            value = _parse_number(record["value"], row_number, "value")
            uncertainty = _parse_number(record["uncertainty"], row_number, "uncertainty")
            if uncertainty < 0:
                raise MeasurementDataError(f"row {row_number}, uncertainty: must be nonnegative")
            if meta["kind"] == "pressure_trace" and value <= 0:
                raise MeasurementDataError(f"row {row_number}, pressure: absolute pressure must be positive")
            canonical.update(value=value * factor, uncertainty=uncertainty * factor,
                             value_unit=meta["canonical_value_unit"], source_row=row_number)
            if (not math.isfinite(canonical["value"]) or not math.isfinite(canonical["uncertainty"])
                    or (value != 0 and canonical["value"] == 0)
                    or (uncertainty != 0 and canonical["uncertainty"] == 0)):
                raise MeasurementDataError(f"row {row_number}: unit conversion outside finite range")
            if key in seen:
                raise MeasurementDataError(f"row {row_number}: duplicate independent coordinate")
            seen.add(key)
            parsed.append(canonical)
            if len(parsed) > LIMIT_ROWS:
                raise MeasurementDataError("CSV exceeds 100000 data rows")
    except csv.Error as error:
        raise MeasurementDataError(f"CSV syntax error on row {reader.line_num}: {error}") from error
    if not parsed:
        raise MeasurementDataError("CSV contains no data rows")
    if meta["kind"] == "pressure_trace":
        parsed.sort(key=lambda row: (row["cycle"], row["x"]))
        for cycle in sorted({row["cycle"] for row in parsed}):
            angles = [row["x"] for row in parsed if row["cycle"] == cycle]
            if len(angles) < 2 or angles[0] != 0.0 or angles[-1] != meta["cycle_period_deg"]:
                raise MeasurementDataError(f"cycle {cycle}: trace must include both declared endpoints")
    else:
        parsed.sort(key=lambda row: row["x"])
    return parsed


def prepare_import(raw: bytes, metadata: dict[str, Any]):
    metadata = validate_declarations(metadata)
    return {"raw": raw, "metadata": metadata, "rows": parse_csv(raw, metadata)}


def save_import(folder: str | Path, prepared: dict[str, Any]):
    prepared = prepare_import(prepared["raw"], prepared["metadata"])
    destination = Path(folder)
    created = False
    files = []
    manifest = {"format": FORMAT, "version": 1, "dataset_id": uuid.uuid4().hex,
                "metadata": prepared["metadata"], "csv_file": "original.csv",
                "csv_sha256": hashlib.sha256(prepared["raw"]).hexdigest()}
    try:
        destination.mkdir(exist_ok=False)
        created = True
        csv_path = destination / "original.csv"
        with csv_path.open("xb") as stream:
            files.append(csv_path)
            stream.write(prepared["raw"])
        manifest_path = destination / "metadata.json"
        with manifest_path.open("x", encoding="utf-8", newline="\n") as stream:
            files.append(manifest_path)
            json.dump(manifest, stream, ensure_ascii=False, sort_keys=True, allow_nan=False)
            stream.write("\n")
        return load_import(manifest_path)
    except (OSError, ValueError) as error:
        for path in reversed(files):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        if created:
            try:
                destination.rmdir()
            except OSError:
                pass
        raise MeasurementDataError(f"Measurement import not saved: {error}") from error


def load_import(path: str | Path):
    path = Path(path)
    try:
        if path.name != "metadata.json" or path.stat().st_size > 128 * 1024:
            raise MeasurementDataError("Select a bounded metadata.json")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict) or set(manifest) !=
                {"format", "version", "dataset_id", "metadata", "csv_file", "csv_sha256"}
                or manifest["format"] != FORMAT or type(manifest["version"]) is not int
                or manifest["version"] != 1 or not isinstance(manifest["dataset_id"], str)
                or re.fullmatch(r"[0-9a-f]{32}", manifest["dataset_id"]) is None
                or manifest["csv_file"] != "original.csv"
                or re.fullmatch(r"[0-9a-f]{64}", manifest["csv_sha256"]) is None):
            raise MeasurementDataError("Measurement manifest identity/schema invalid")
        source = (path.parent / manifest["csv_file"]).resolve()
        source.relative_to(path.parent.resolve())
        raw = source.read_bytes()
        if len(raw) > LIMIT_BYTES or hashlib.sha256(raw).hexdigest() != manifest["csv_sha256"]:
            raise MeasurementDataError("Measurement CSV hash/size mismatch")
        return {**prepare_import(raw, manifest["metadata"]),
                "manifest": manifest, "path": path.resolve()}
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        if isinstance(error, MeasurementDataError):
            raise
        raise MeasurementDataError(f"Measurement import unreadable: {error}") from error


def exploratory_overlay(external: dict[str, Any], simulated: list[dict[str, Any]], *,
                        simulated_unit: str):
    """Exact-coordinate descriptive comparison; never interpolates or grants P9."""
    metadata = validate_declarations(external["metadata"])
    manifest = external.get("manifest")
    raw = external.get("raw")
    if (not isinstance(manifest, dict) or not isinstance(manifest.get("dataset_id"), str)
            or re.fullmatch(r"[0-9a-f]{32}", manifest["dataset_id"]) is None
            or not isinstance(raw, bytes)
            or manifest.get("csv_sha256") != hashlib.sha256(raw).hexdigest()):
        raise MeasurementDataError("Overlay requires a hash-bound imported dataset")
    if simulated_unit != metadata["canonical_value_unit"]:
        raise MeasurementDataError("Simulated and imported value units must match exactly")
    measured_rows = parse_csv(raw, metadata)
    if not isinstance(simulated, list):
        raise MeasurementDataError("Simulated overlay must be a list")
    sim_by_key = {}
    for row in simulated:
        if not isinstance(row, dict):
            raise MeasurementDataError("Malformed simulated measurement row")
        if metadata["kind"] == "pressure_trace":
            cycle = row.get("cycle")
            if type(cycle) is not int or cycle <= 0:
                raise MeasurementDataError("Simulated pressure row needs a positive integer cycle")
            key = (cycle, _finite(row.get("x"), "simulated.x"))
        else:
            key = _finite(row.get("x"), "simulated.x")
        value = _finite(row.get("value"), "simulated.value")
        if key in sim_by_key:
            raise MeasurementDataError("Duplicate simulated coordinate")
        sim_by_key[key] = value
    pairs = []
    residuals = []
    normalized = []
    for row in measured_rows:
        key = (row["cycle"], row["x"]) if metadata["kind"] == "pressure_trace" else row["x"]
        simulated_value = sim_by_key.get(key)
        difference = None if simulated_value is None else simulated_value - row["value"]
        if difference is not None:
            if not math.isfinite(difference):
                raise MeasurementDataError("Comparison difference outside finite range")
            residuals.append(difference)
            if row["uncertainty"] > 0:
                normalized.append(difference / row["uncertainty"])
        pairs.append({"key": key, "measured": row["value"], "uncertainty": row["uncertainty"],
                      "simulated": simulated_value, "difference": difference,
                      "relative_error": (difference / abs(row["value"])
                          if difference is not None and row["value"] != 0 else None)})
    count = len(residuals)
    metrics = {"matched_count": count,
               "bias": math.fsum(residuals) / count if count else None,
               "mae": math.fsum(abs(value) for value in residuals) / count if count else None,
               "rmse": math.sqrt(math.fsum(value * value for value in residuals) / count) if count else None,
               "uncertainty_normalized_rmse": math.sqrt(
                   math.fsum(value * value for value in normalized) / len(normalized)) if normalized else None}
    if any(value is not None and not math.isfinite(value)
           for value in metrics.values() if isinstance(value, (int, float))):
        raise MeasurementDataError("Comparison metric outside finite range")
    return {"status": "EXPLORATORY_COMPARISON", "validation_eligible": False,
            "p9_decision_eligible": False, "interpolation": "NONE_EXACT_COORDINATES_ONLY",
            "dataset_id": external["manifest"]["dataset_id"],
            "kind": metadata["kind"], "canonical_unit": metadata["canonical_value_unit"],
            "metrics": metrics, "rows": pairs,
            "notice": "Exploratory comparison only; not preregistered validation."}
