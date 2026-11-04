"""Dino 4T: coupled engine cycle, ledgers, configuration and CLI (L0/L1)."""
import json

import numpy as np
import pytest

from motorsim.dino4t import config
from motorsim.dino4t.runner import run_operating_point


@pytest.fixture(scope="module")
def example():
    return config.load(config.EXAMPLE_PATH)


@pytest.fixture(scope="module")
def coarse_run(example, tmp_path_factory):
    out = tmp_path_factory.mktemp("d4t")
    return run_operating_point(example, out_dir=out, max_cycles=2,
                               overrides={"numerics": {"dx_mm": 25.0}}), out


def test_config_requires_provenance(example):
    broken = json.loads(json.dumps(example))
    broken["geometry"]["provenance"] = "GUESS"
    with pytest.raises(config.ConfigError):
        config.validate(broken)


def test_valve_area_cannot_exceed_port(example):
    with pytest.raises(ValueError, match="exceeds"):
        config.build(example, overrides={"intake_valve": {"count": 4}})


def test_valve_open_during_burn_rejected(example):
    with pytest.raises(ValueError, match="open during combustion"):
        config.build(example, overrides={"exhaust_valve": {"lift": {"type": "harmonic", "open_deg": 10.0,
                                                                     "close_deg": -350.0, "max_lift_mm": 9.0}}})


def test_cycle_conservation_closes_to_roundoff(coarse_run):
    summary = coarse_run[0]["summary"]
    assert summary["status"] == "completed"
    assert max(summary["conservation"]["max_relative_closure"].values()) < 1e-12
    assert summary["conservation"]["final_relative_closure"]["tracer"] < 1e-12


def test_indicators_are_internally_consistent(coarse_run):
    f = coarse_run[0]["summary"]["final_cycle"]
    assert f["imep_net_bar"] == pytest.approx(f["imep_gross_bar"] - f["pmep_bar"], rel=1e-12)
    assert f["bmep_bar"] == pytest.approx(f["imep_net_bar"] - f["fmep_bar"], rel=1e-12)
    assert f["fuel_burned_per_cycle_mg"] <= f["fuel_per_cycle_mg"] * 1.05
    assert 0.0 < f["residual_gas_fraction_ivc"] < 0.5
    assert f["p_max_bar"] > 20 and -10 < f["theta_p_max_deg"] < 40
    for key in ("CA10_deg", "CA50_deg", "CA90_deg"):
        assert key in f
    # CA50 from the integrated burn trace equals the analytic Wiebe value (trace resolution)
    from motorsim.dino4t.combustion import Wiebe
    w = Wiebe(-20.0, 55.0)
    assert f["CA50_deg"] == pytest.approx(-20.0 + w.angle_at_fraction(0.5), abs=0.3)


def test_outputs_written_with_claims(coarse_run):
    result, out = coarse_run
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert summary["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert summary["claims"]["predictive_capability"] == "NOT_CLAIMED"
    assert summary["provenance"]["geometry"] == "SYNTHETIC_ASSUMPTION"
    header = (out / "trace_last_cycle.csv").read_text(encoding="utf-8").splitlines()[0].split(",")
    assert {"theta", "p", "T", "V", "mdot_intake_valve", "mdot_exhaust_valve"} <= set(header)


def test_trace_angles_cover_720(coarse_run):
    trace = coarse_run[0]["records"][-1].trace
    theta = np.asarray(trace["theta"])
    assert theta[0] == pytest.approx(-360.0) and theta[-1] == pytest.approx(360.0)
    assert np.all(np.diff(theta) > 0)


def test_platform_contract(coarse_run):
    from motorsim import engine_platform
    assert engine_platform.families() == ("4T",)
    engine_platform.check_summary(coarse_run[0]["summary"])
    with pytest.raises(KeyError):
        engine_platform.run_operating_point("2T", {})


def test_dino4t_does_not_import_two_stroke_solver():
    import subprocess
    import sys
    code = ("import sys, motorsim.dino4t.runner, motorsim.dino4t.verification;"
            "bad=[m for m in sys.modules if m.split('.')[-1] in ('integrated_2t','crankcase','two_stroke_ports',"
            "'scavenging','reed','four_stroke')]; print(bad); sys.exit(1 if bad else 0)")
    assert subprocess.run([sys.executable, "-c", code], capture_output=True).returncode == 0
