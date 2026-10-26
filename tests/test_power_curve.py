import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import csv
import pytest
from PySide6.QtWidgets import QApplication

from motorsim.power_curve import (build_curve_series, exact_rpm_differences,
    peak_points, plan_rpm_range)
from motorsim.desktop.performance_curves import PowerCurvePanel
from motorsim.desktop.results_page import _referenced_curve_rpms


APP = QApplication.instance() or QApplication([])


def _row(variant, rpm, power, torque, **changes):
    row = {
        "variant_id": variant, "rpm": rpm, "classification": "PERIOD_1",
        "periodicity": "PERIOD_1", "brake_power": power,
        "brake_power_status": "DEFINED" if power is not None else "UNDEFINED",
        "brake_power_reason": None if power is not None else "not periodic",
        "brake_torque": torque,
        "brake_torque_status": "DEFINED" if torque is not None else "UNDEFINED",
        "brake_torque_reason": None if torque is not None else "not periodic",
        "fuel_id": "fuel-a", "mechanical_loss_model_sha256": "a" * 64,
        "periodicity_contract": "REFERENCE_PERIODIC_CONVERGENCE_V2",
        "total_finite_volume_cells": 48,
    }
    row.update(changes)
    return row


def _dataset(rows):
    return {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1",
        "provenance": "SYNTHETIC", "experimental_validation": "NOT_PERFORMED",
        "identity": {"implementation_identity_sha256": "b" * 64,
                     "preregistration_sha256": "c" * 64,
                     "producer_sha256": "d" * 64},
        "units": {"brake_power": "kW", "brake_torque": "N*m"},
        "points": rows,
    }


def test_plan_rpm_range_requires_exact_integer_endpoint():
    assert plan_rpm_range(3000, 4000, 500) == [3000, 3500, 4000]
    with pytest.raises(ValueError, match="exactamente"):
        plan_rpm_range(3000, 4100, 500)
    with pytest.raises(ValueError, match="enteros"):
        plan_rpm_range(3000.0, 4000, 500)


def test_curve_unit_conversion_and_failed_points_remain_gaps():
    data = _dataset([
        _row("A", 3000, 7.456998715822702, 20.0),
        _row("A", 3500, 9.0, 22.0, classification="NUMERICAL_INVALID"),
        _row("A", 4000, None, None),
    ])
    curve = build_curve_series(data, {"A"}, power_unit="HP")[0]
    assert curve["points"][0]["power"] == pytest.approx(10.0)
    assert curve["points"][1]["power"] is None
    assert curve["points"][2]["power"] is None
    assert curve["points"][0]["torque"] == 20.0


def test_maxima_and_exact_comparison_require_shared_compatible_identity():
    data = _dataset([
        _row("A", 3000, 10.0, 25.0), _row("A", 4000, 12.0, 20.0),
        _row("B", 3000, 11.0, 26.0), _row("B", 4500, 14.0, 28.0),
    ])
    curves = build_curve_series(data, {"A", "B"}, power_unit="kW")
    assert peak_points(curves, "power")[0]["rpm"] == 4000
    diffs = exact_rpm_differences(curves)
    assert len(diffs) == 1 and diffs[0]["rpm"] == 3000
    assert diffs[0]["compatible"]
    assert diffs[0]["power_delta"] == pytest.approx(1.0)
    assert diffs[0]["torque_delta"] == pytest.approx(1.0)

    data["points"][2]["mechanical_loss_model_sha256"] = "f" * 64
    incompatible = exact_rpm_differences(build_curve_series(data, {"A", "B"}, power_unit="kW"))
    assert not incompatible[0]["compatible"]
    assert incompatible[0]["power_delta"] is None


def test_curve_panel_table_peaks_units_and_csv_export(tmp_path):
    panel = PowerCurvePanel()
    data = _dataset([_row("A", 3000, 5.0, 12.0), _row("A", 4000, 7.5, 15.0)])
    panel.set_dataset(data, {"A"})
    assert panel.points.rowCount() == 2
    assert "10.06 HP" in panel.peaks.text()
    panel.unit_selector.setCurrentText("CV")
    assert "CV" in panel.peaks.text()
    target = tmp_path / "curve.csv"
    panel.export_csv(target)
    with target.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 2
    assert float(rows[0]["brake_power_CV"]) == pytest.approx(5.0 * 1000 / 735.49875)


def test_unreferenced_same_rpm_exploratory_pair_is_not_filled_from_project_recipe():
    project={"simulation_recipes":{"rpm_curve_v1":{"rpms":[8000,9000,10000]}},
        "result_references":[{"artifact_sha256":"a"*64}]}
    local={"points":[{"result_sha256":"b"*64},{"result_sha256":"c"*64}]}
    assert _referenced_curve_rpms(project,local) is None
    referenced={"points":[{"result_sha256":"a"*64}]}
    assert _referenced_curve_rpms(project,referenced)==[8000,9000,10000]


def test_same_rpm_transient_pair_is_compatible_but_remains_exploratory():
    def transient(variant, power, torque, result_hash):
        return _row(variant,3000,None,None,classification="MAX_CYCLES_NONCONVERGED",
            periodicity="INSUFFICIENT_CYCLES",brake_power_status="UNDEFINED",
            brake_torque_status="UNDEFINED",brake_power_reason="NO_PERIODICITY_TRANSIENT_ONLY",
            brake_torque_reason="NO_PERIODICITY_TRANSIENT_ONLY",mode="ENGINEERING_EXPLORATORY",
            result_sha256=result_hash,solver_identity_sha256="e"*64,
            implementation_identity_sha256="b"*64,
            transient_estimates={"brake_power":power,"brake_torque":torque})
    data=_dataset([transient("base",-3.8028,-9.0265,"a"*64),
                   transient("V2 exhaust test",-3.7992,-9.0178,"b"*64)])
    panel=PowerCurvePanel();panel.exploratory_toggle.setChecked(True)
    panel.set_dataset(data,{"base","V2 exhaust test"})
    assert panel.comparison.rowCount()==1
    assert panel.comparison.item(0,3).text()=="EXPLORATORIO"
    assert "TRANSITORIO" in panel.comparison.item(0,4).text()
    assert panel.comparison.item(0,1).text()!="—"
