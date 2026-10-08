import math

import pytest

from motorsim.engineering_outputs import (
    build_engineering_output,
    build_integrated_engineering_output_v2,
    build_integrated_engineering_output_v3,
    build_integrated_engineering_output_v5,
    validate_engineering_output,
    validate_integrated_engineering_output_v2,
    validate_integrated_engineering_output_v3,
    validate_integrated_engineering_output_v5,
)
from motorsim.scavenging import (ScavengingInput, calculate_scavenging_metrics,
                                 scavenging_engineering_records)


def output(**changes):
    values = dict(
        rpm=6000.0, cycle_number=3,
        angles_deg=(180.0, 270.0, 360.0, 450.0, 540.0),
        channels={
            "cylinder_pressure_pa": {"values": [100_000, 150_000, 200_000, 150_000, 100_000],
                                     "source": "P5C primary trajectory"},
            "exhaust_mach": {"values": [0, .2, .4, .2, 0], "source": "P4 duct trace"},
        },
        cycle_metrics={
            "indicated_work_j": {"value": 42.0, "status": "DEFINED",
                                 "reason": None, "source": "P8 cycle integrator"},
            "bsfc_g_kwh": {"value": None, "status": "UNDEFINED",
                           "reason": "NONPOSITIVE_BRAKE_POWER", "source": "fuel ledger"},
        },
        dependency_status="CONDITIONAL_ON_P4",
    )
    values.update(changes)
    return build_engineering_output(**values)


def test_schema_carries_units_provenance_and_explicit_nonclaims():
    record = output()
    assert record["schema"] == "MOTORSIM_ENGINEERING_OUTPUTS_V1"
    assert record["operating_point"]["cycle_convention"] == "2T_360_DEG_ONE_CYCLE_PER_REV"
    assert record["operating_point"]["dependency_status"] == "CONDITIONAL_ON_P4"
    assert record["crank_angle_trace"]["channels"]["cylinder_pressure_pa"]["unit"] == "Pa"
    assert record["crank_angle_trace"]["channels"]["cylinder_pressure_pa"]["source"] == "P5C primary trajectory"
    assert record["cycle_metrics"]["bsfc_g_kwh"]["status"] == "UNDEFINED"
    assert record["claims"] == {"periodicity": "NOT_EVALUATED",
        "experimental_validation": "NOT_PERFORMED", "predictive_validation": "NOT_CLAIMED"}
    assert validate_engineering_output(record) == record


@pytest.mark.parametrize("change", [
    {"angles_deg": (0, 90, 180)},
    {"rpm": True}, {"cycle_number": 0},
    {"channels": {"fabricated_curve": {"values": [1, 2, 3, 4, 5], "source": "x"}}},
    {"channels": {"cylinder_pressure_pa": {"values": [1, 2], "source": "x"}}},
    {"channels": {"cylinder_pressure_pa": {"values": [1, 2, math.nan, 4, 5], "source": "x"}}},
    {"dependency_status": "P4_PASS"},
])
def test_bad_trace_or_operating_point_is_rejected(change):
    with pytest.raises(ValueError):
        output(**change)


def test_malformed_undefined_metric_and_modified_units_are_rejected():
    bad = output()
    bad["cycle_metrics"]["bsfc_g_kwh"]["reason"] = None
    with pytest.raises(ValueError):
        validate_engineering_output(bad)
    bad = output()
    bad["crank_angle_trace"]["channels"]["cylinder_pressure_pa"]["unit"] = "bar"
    with pytest.raises(ValueError):
        validate_engineering_output(bad)


def test_schema_never_claims_four_stroke_or_nonperiodic_trace_as_2t():
    with pytest.raises(ValueError):
        output(cycle_period_deg=720.0)


def test_schema_accepts_geometry_bound_scavenging_diagnostics():
    metrics = calculate_scavenging_metrics(ScavengingInput(
        0.01, 0.012, 0.002, (0.003, 0.001, 0.006, 0.0),
        (0.004, 0.001, 0.004, 0.001)))
    record = output(cycle_metrics=scavenging_engineering_records(metrics))
    validated = validate_engineering_output(record)
    assert validated["cycle_metrics"]["purity_at_transfer_close"]["value"] == pytest.approx(0.4)
    assert validated["cycle_metrics"]["fresh_retained_kg"]["value"] == pytest.approx(0.005)
    assert metrics["flow_semantics"]["net_unique_fresh_mass"] == "NOT_AVAILABLE"
    assert "recrossings counted" in metrics["flow_semantics"]["fresh_delivered"]
    assert "reverse flow excluded" in metrics["flow_semantics"]["fresh_short_circuit"]


def test_integrated_v2_binds_configuration_and_path_addressed_duct_channels():
    base = output()
    channels = {
        **{name: {"values": row["values"], "source": row["source"]}
           for name, row in base["crank_angle_trace"]["channels"].items()},
        "crankcase_mass_kg": {"values": [1, 1, 1, 1, 1], "source": "integrated state"},
        "duct:primary:cell:0:pressure_pa": {
            "values": [100_000, 110_000, 120_000, 110_000, 100_000],
            "source": "integrated duct state"},
        "duct:primary:face:1:mass_flow_kg_s": {
            "values": [0, .01, .02, .01, 0], "source": "accepted HLLC face flux"},
        "network:intake%20plenum:pressure_pa": {
            "values": [100_000, 101_000, 102_000, 101_000, 100_000],
            "source": "accepted finite-volume plenum state"},
    }
    values = dict(rpm=base["operating_point"]["rpm"], cycle_number=3,
                  angles_deg=tuple(base["crank_angle_trace"]["angle_deg"]),
                  channels=channels,
                  cycle_metrics={name: {key: row[key] for key in
                                        ("value", "status", "reason", "source")}
                                 for name, row in base["cycle_metrics"].items()},
                  dependency_status="CONDITIONAL_ON_P4",
                  configuration_sha256="a" * 64)
    record = build_integrated_engineering_output_v2(**values)
    assert record["schema"] == "MOTORSIM_ENGINEERING_OUTPUTS_V2"
    assert record["configuration_sha256"] == "a" * 64
    assert record["crank_angle_trace"]["channels"][
        "duct:primary:cell:0:pressure_pa"]["unit"] == "Pa"
    assert record["crank_angle_trace"]["channels"][
        "network:intake%20plenum:pressure_pa"]["unit"] == "Pa"
    assert validate_integrated_engineering_output_v2(record) == record
    with pytest.raises(ValueError, match="Unsupported or malformed crank-angle channel"):
        build_integrated_engineering_output_v2(
            **{**values, "channels": {"duct:primary:cell:0:fake": {
                "values": [1, 2, 3, 4, 5], "source": "bad"}}})
    with pytest.raises(ValueError, match="configuration SHA-256"):
        build_integrated_engineering_output_v2(**{**values, "configuration_sha256": "bad"})
    v1_only = {**values, "cycle_metrics": {**values["cycle_metrics"],
        "brake_work_j": {"value": 1.0, "status": "DEFINED", "reason": None,
                         "source": "must require schema V2"}},
        "channels": {name: {"values": row["values"], "source": row["source"]}
                     for name, row in base["crank_angle_trace"]["channels"].items()}}
    with pytest.raises(ValueError, match="Unsupported or malformed cycle metric"):
        build_engineering_output(**{key: value for key, value in v1_only.items()
                                    if key != "configuration_sha256"})

    v3_values = {**values, "cycle_metrics": {
        **values["cycle_metrics"],
        "gross_fresh_charge_delivery_kg": {
            "value": .001, "status": "DEFINED", "reason": None,
            "source": "gross crossing ledger"},
        "gross_intake_air_fuel_ratio": {
            "value": 49.0, "status": "DEFINED", "reason": None,
            "source": "gross intake species"},
        "afr": {"value": None, "status": "UNDEFINED",
                "reason": "No trapped/burned AFR", "source": "not available"},
        "isfc_g_kwh": {"value": None, "status": "UNDEFINED",
                        "reason": "No P7 consumed fuel", "source": "not available"},
    }}
    record_v3 = build_integrated_engineering_output_v3(**v3_values)
    assert record_v3["schema"] == "MOTORSIM_ENGINEERING_OUTPUTS_V3"
    assert validate_integrated_engineering_output_v3(record_v3) == record_v3
    with pytest.raises(ValueError, match="Unsupported or malformed cycle metric"):
        build_integrated_engineering_output_v2(**v3_values)


def test_integrated_v5_requires_metric_provenance_and_periodicity_contract():
    base = output()
    metric = {"value": 42.0, "status": "DEFINED", "reason": None,
              "source": "accepted primary", "provenance": "SYNTHETIC_ASSUMPTION",
              "periodicity_dependency": "NOT_REQUIRED",
              "definition_version": "TEST_METRIC_V1"}
    values = dict(
        rpm=base["operating_point"]["rpm"], cycle_number=3,
        angles_deg=tuple(base["crank_angle_trace"]["angle_deg"]),
        channels={name: {"values": row["values"], "source": row["source"]}
                  for name, row in base["crank_angle_trace"]["channels"].items()},
        cycle_metrics={"indicated_work_j": metric},
        dependency_status="CONDITIONAL_ON_P4", configuration_sha256="b" * 64)
    record = build_integrated_engineering_output_v5(**values)
    assert record["cycle_metrics"]["indicated_work_j"]["provenance"] == \
        "SYNTHETIC_ASSUMPTION"
    assert validate_integrated_engineering_output_v5(record) == record
    periodic_metric = {**metric, "periodicity_dependency": "REQUIRED"}
    with pytest.raises(ValueError, match="accepted period-1 cycle"):
        build_integrated_engineering_output_v5(**{
            **values,
            "cycle_metrics": {"indicated_power_w": periodic_metric}})
    with pytest.raises(ValueError, match="accepted period-1 cycle"):
        build_integrated_engineering_output_v5(**{
            **values,
            "cycle_metrics": {"brake_work_j": periodic_metric},
            "periodicity_status": "PERIOD_2"})
    with pytest.raises(ValueError, match="must be positive"):
        build_integrated_engineering_output_v5(**{
            **values,
            "cycle_metrics": {"afr": {**metric, "value": 0.0}}})
    brake = {**metric, "value": None, "status": "UNDEFINED",
             "reason": "periodicity pending", "periodicity_dependency": "REQUIRED"}
    brake_values = {**values, "cycle_metrics": {"brake_work_j": brake}}
    record = build_integrated_engineering_output_v5(**brake_values)
    record["cycle_metrics"]["brake_work_j"]["periodicity_dependency"] = "NOT_REQUIRED"
    with pytest.raises(ValueError, match="invalid periodicity dependency"):
        validate_integrated_engineering_output_v5(record)
