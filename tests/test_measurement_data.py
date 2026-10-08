import math
import hashlib

import pytest

from motorsim.measurement_data import (
    MeasurementDataError,
    declarations,
    exploratory_overlay,
    load_import,
    parse_csv,
    prepare_import,
    save_import,
)


def test_pressure_trace_conversion_preserves_raw_and_declares_full_cycle():
    meta = declarations("pressure_trace", "bar", cycle_period_deg=360,
                        provenance="MEASURED", source="Test bench")
    raw = b"cycle,crank_angle_deg,value,uncertainty\n1,360,1.2,0.01\n1,0,1,0.02\n"
    prepared = prepare_import(raw, meta)
    assert prepared["raw"] == raw
    assert [(row["x"], row["value"], row["uncertainty"]) for row in prepared["rows"]] == [
        (0.0, 100_000.0, 2000.0), (360.0, 120_000.0, 1000.0)]


@pytest.mark.parametrize("kind,unit,raw,expected", [
    ("dyno_torque", "lb-ft", b"rpm,value,uncertainty\n3000,10,0.5\n", (13.558179483314004, 0.6779089741657002)),
    ("dyno_power", "hp", b"rpm,value,uncertainty\n3000,10,0.5\n", (7456.998715822702, 372.8499357911351)),
])
def test_dyno_unit_conversion(kind, unit, raw, expected):
    row = parse_csv(raw, declarations(kind, unit))[0]
    assert row["value"] == pytest.approx(expected[0])
    assert row["uncertainty"] == pytest.approx(expected[1])


def test_exploratory_overlay_matches_exact_coordinates_only_and_never_validates():
    external = prepare_import(b"rpm,value,uncertainty\n2000,10,1\n3000,20,2\n",
                              declarations("dyno_torque", "N*m", provenance="MEASURED"))
    saved_shape = {"manifest": {"dataset_id": "0123456789abcdef0123456789abcdef",
                                "csv_sha256": hashlib.sha256(external["raw"]).hexdigest()}}
    external.update(saved_shape)
    result = exploratory_overlay(external, [
        {"x": 2000, "value": 11}, {"x": 2500, "value": 15},
    ], simulated_unit="N*m")
    assert result["status"] == "EXPLORATORY_COMPARISON"
    assert result["validation_eligible"] is False
    assert result["p9_decision_eligible"] is False
    assert result["metrics"]["matched_count"] == 1
    assert result["metrics"]["bias"] == pytest.approx(1.0)
    assert result["rows"][1]["simulated"] is None
    assert result["rows"][0]["relative_error"] == pytest.approx(0.1)
    with pytest.raises(MeasurementDataError, match="units"):
        exploratory_overlay(external, [{"x": 2000, "value": 11}], simulated_unit="W")
    external["raw"] += b"\n"
    with pytest.raises(MeasurementDataError, match="hash-bound"):
        exploratory_overlay(external, [], simulated_unit="N*m")


def test_pressure_overlay_keys_by_cycle_and_normalizes_uncertainty():
    external = prepare_import(b"cycle,crank_angle_deg,value,uncertainty\n1,0,100,10\n1,360,120,10\n",
        declarations("pressure_trace", "Pa", cycle_period_deg=360))
    external["manifest"] = {"dataset_id": "f" * 32,
                             "csv_sha256": hashlib.sha256(external["raw"]).hexdigest()}
    result = exploratory_overlay(external, [
        {"cycle": 1, "x": 0, "value": 120},
        {"cycle": 1, "x": 360, "value": 120},
    ], simulated_unit="Pa")
    assert result["metrics"]["bias"] == pytest.approx(10)
    assert result["metrics"]["uncertainty_normalized_rmse"] == pytest.approx(math.sqrt(2))


def test_persistence_binds_original_file_and_metadata(tmp_path):
    prepared = prepare_import(b"rpm,value,uncertainty\n3000,10,1\n",
                             declarations("dyno_power", "kW", provenance="DOCUMENTED"))
    saved = save_import(tmp_path / "measurement", prepared)
    loaded = load_import(saved["path"])
    assert loaded["raw"] == prepared["raw"]
    assert loaded["rows"] == prepared["rows"]
    assert loaded["manifest"]["metadata"] == prepared["metadata"]
    loaded["path"].write_text("{}", encoding="utf-8")
    with pytest.raises(MeasurementDataError):
        load_import(loaded["path"])


def test_malformed_input_provenance_duplicates_and_units_rejected():
    valid = declarations("pressure_trace", "Pa", cycle_period_deg=720)
    bad_headers = b"angle,pressure\n0,100000\n720,100000\n"
    with pytest.raises(MeasurementDataError):
        parse_csv(bad_headers, valid)
    duplicate = b"cycle,crank_angle_deg,value,uncertainty\n1,0,100000,0\n1,0,100001,0\n1,720,100000,0\n"
    with pytest.raises(MeasurementDataError, match="duplicate"):
        parse_csv(duplicate, valid)
    with pytest.raises(MeasurementDataError):
        declarations("pressure_trace", "Pa", cycle_period_deg=360, provenance="VALIDATED")
    with pytest.raises(MeasurementDataError):
        declarations("dyno_power", "hp", uncertainty_unit="W")


@pytest.mark.parametrize("text", ["NaN", "inf", "1e9999", "1e-9999", "1,000", "1_000"])
def test_nonfinite_underflow_or_locale_numbers_rejected(text):
    raw = f"rpm,value,uncertainty\n3000,{text},0\n".encode()
    with pytest.raises(MeasurementDataError):
        parse_csv(raw, declarations("dyno_power", "W"))


def test_out_of_domain_pressure_and_negative_uncertainty_rejected():
    meta = declarations("pressure_trace", "Pa", cycle_period_deg=360)
    for raw in (b"cycle,crank_angle_deg,value,uncertainty\n1,0,0,1\n1,360,1,1\n",
                b"cycle,crank_angle_deg,value,uncertainty\n1,0,1,-1\n1,360,1,0\n"):
        with pytest.raises(MeasurementDataError):
            parse_csv(raw, meta)


def test_unknown_measurement_schema_rejected_on_reload():
    with pytest.raises(MeasurementDataError):
        load_import("missing.json")
