"""JSON configuration -> engine model.  Schema ``DINO4T_ENGINE_CONFIG_V1``.

Geometry is given in mm (like the rest of Dino), everything else in SI.
Every parameter group carries a ``provenance`` label so that synthetic
assumptions can never be mistaken for measurements:

  MEASURED | DOCUMENTED | STANDARD_V1 | SYNTHETIC_ASSUMPTION | CALIBRATED
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .closures import ChenFlynnFriction, WoschniHeatTransfer
from .combustion import Wiebe, burned_composition, premixed_charge
from .duct import Duct, DuctWall
from .engine import CombustionSpec, Connection, Cylinder, FourStrokeEngine, Plenum, Reservoir
from .kinematics import SliderCrank
from .thermo import Mixture
from .valves import FlowCoefficients, HarmonicLift, TabulatedLift, Valve

SCHEMA = "DINO4T_ENGINE_CONFIG_V1"
PROVENANCE = {"MEASURED", "DOCUMENTED", "STANDARD_V1", "SYNTHETIC_ASSUMPTION", "CALIBRATED"}
GROUPS_WITH_PROVENANCE = ("geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct",
                          "combustion", "heat_transfer", "friction", "ambient")


class ConfigError(ValueError):
    pass


def canonical_hash(config: dict) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path) -> dict:
    with open(path, encoding="utf-8") as fh:
        config = json.load(fh)
    validate(config)
    return config


def validate(config: dict) -> None:
    if config.get("schema") != SCHEMA:
        raise ConfigError(f"schema must be {SCHEMA}")
    for group in GROUPS_WITH_PROVENANCE:
        if group not in config:
            raise ConfigError(f"missing section {group}")
        if config[group].get("provenance") not in PROVENANCE:
            raise ConfigError(f"{group}.provenance must be one of {sorted(PROVENANCE)}")


def _lift_law(spec):
    if spec["type"] == "harmonic":
        return HarmonicLift(spec["open_deg"], spec["close_deg"], spec["max_lift_mm"] * 1e-3)
    if spec["type"] == "tabulated":
        return TabulatedLift(spec["angle_deg"], [x * 1e-3 for x in spec["lift_mm"]])
    raise ConfigError("lift law type must be harmonic or tabulated")


def _valve(spec):
    cd = spec["discharge_coefficient"]
    return Valve(_lift_law(spec["lift"]), spec["diameter_mm"] * 1e-3, int(spec["count"]),
                 FlowCoefficients(tuple(cd["l_over_d"]), tuple(cd["forward"]), tuple(cd["reverse"])),
                 cd.get("reference_area", "curtain"))


def _segments(spec):
    return [{"length": s["length_mm"], "start_diameter": s["start_diameter_mm"],
             "end_diameter": s["end_diameter_mm"]} for s in spec["segments"]]


def build(config: dict, *, overrides: dict | None = None):
    """Return (engine, initial_state, context)."""
    config = copy.deepcopy(config)
    if overrides:
        _deep_update(config, overrides)
    validate(config)
    mix = Mixture.standard()
    fuel = config["combustion"]["fuel"]
    phi = config["operating_point"]["equivalence_ratio"]
    charge = premixed_charge(mix, fuel, phi)
    burned = burned_composition(mix, fuel, charge, config["combustion"].get("water_gas_k", 3.5))
    g = config["geometry"]
    geometry = SliderCrank(g["bore_mm"] * 1e-3, g["stroke_mm"] * 1e-3, g["rod_mm"] * 1e-3,
                           g["compression_ratio"])
    ht = config["heat_transfer"]
    heat = None if not ht.get("enabled", True) else WoschniHeatTransfer(
        **{k: v for k, v in ht.items() if k not in ("enabled", "provenance", "model", "notes")})
    c = config["combustion"]
    combustion = None if not c.get("enabled", True) else CombustionSpec(
        fuel, Wiebe(c["start_deg"], c["duration_deg"], c.get("wiebe_a", 5.0), c.get("wiebe_m", 2.0)),
        c.get("efficiency", 0.98), c.get("water_gas_k", 3.5))
    intake_valve, exhaust_valve = _valve(config["intake_valve"]), _valve(config["exhaust_valve"])
    cylinder = Cylinder("cylinder", mix, geometry, heat_transfer=heat, combustion=combustion,
                        intake_valves=intake_valve, exhaust_valves=exhaust_valve)
    num = config.get("numerics", {})
    dx = num.get("dx_mm", 10.0) * 1e-3
    second = num.get("second_order", True)

    def duct(name, spec):
        wall = DuctWall(spec.get("friction", True), spec.get("heat_transfer", True),
                        spec.get("wall_temperature_K", 300.0))
        return Duct(name, mix, _segments(spec), dx, wall=wall, second_order=second,
                    limiter=num.get("limiter", "minmod"))

    intake, exhaust = duct("intake", config["intake_duct"]), duct("exhaust", config["exhaust_duct"])
    amb = config["ambient"]
    inlet = Reservoir("intake_ambient", mix, amb["intake_pressure_pa"], amb["intake_temperature_K"], charge, 0.0)
    outlet = Reservoir("exhaust_ambient", mix, amb["exhaust_pressure_pa"], amb.get("exhaust_temperature_K", 300.0),
                       burned, 1.0)
    ducts = {"intake": intake, "exhaust": exhaust}
    plenums = {}
    plenum_cfg = config.get("intake_plenum")
    if plenum_cfg is not None:
        if plenum_cfg.get("provenance") not in PROVENANCE:
            raise ConfigError("intake_plenum.provenance must be one of " + str(sorted(PROVENANCE)))
        airbox = Plenum("airbox", mix, plenum_cfg["volume_cm3"] * 1e-6)
        plenums["airbox"] = airbox
        feed = duct("intake_feed", plenum_cfg["feed_duct"])
        ducts["intake_feed"] = feed
        connections = [
            Connection.open_end("intake_open_end", feed, "left", inlet,
                                plenum_cfg["feed_duct"].get("open_end_cd_inflow", 1.0),
                                plenum_cfg["feed_duct"].get("open_end_cd_outflow", 1.0)),
            Connection.open_end("airbox_feed", feed, "right", airbox),
            Connection.open_end("airbox_runner", intake, "left", airbox),
        ]
    else:
        connections = [
            Connection.open_end("intake_open_end", intake, "left", inlet,
                                config["intake_duct"].get("open_end_cd_inflow", 1.0),
                                config["intake_duct"].get("open_end_cd_outflow", 1.0)),
        ]
    connections += [
        Connection.valve("intake_valve", intake, "right", cylinder, intake_valve, "intake"),
        Connection.valve("exhaust_valve", exhaust, "left", cylinder, exhaust_valve, "exhaust"),
        Connection.open_end("exhaust_open_end", exhaust, "right", outlet,
                            config["exhaust_duct"].get("open_end_cd_inflow", 1.0),
                            config["exhaust_duct"].get("open_end_cd_outflow", 1.0)),
    ]
    sensors = {"intake_port": ("intake", -1), "exhaust_port": ("exhaust", 0)}
    engine = FourStrokeEngine(mix, cylinder, ducts, connections,
                              config["operating_point"]["rpm"], cfl=num.get("cfl", 0.8),
                              max_dtheta=num.get("max_dtheta_deg", 0.5), sensors=sensors,
                              plenums=plenums, restriction_model=num.get("restriction_model", "V2"))
    init = config.get("initial_conditions", {})
    state = engine.initial_state(
        cylinder=dict(p=init.get("cylinder_pressure_pa", amb["exhaust_pressure_pa"]),
                      T=init.get("cylinder_temperature_K", 900.0), Y=burned, xb=1.0),
        ducts={**{name: dict(p=amb["intake_pressure_pa"], T=amb["intake_temperature_K"], Y=charge, xb=0.0)
                  for name in ducts if name.startswith("intake")},
               "exhaust": dict(p=amb["exhaust_pressure_pa"], T=init.get("exhaust_temperature_K", 700.0),
                               Y=burned, xb=1.0)},
        plenums={name: dict(p=amb["intake_pressure_pa"], T=amb["intake_temperature_K"], Y=charge, xb=0.0)
                 for name in plenums})
    fr = config["friction"]
    friction = ChenFlynnFriction(fr["a_pa"], fr["b"], fr["c_pa_s_m"], fr["d_pa_s2_m2"])
    context = dict(mixture=mix, fuel=fuel, charge=charge, burned=burned, geometry=geometry,
                   friction=friction, config=config, config_hash=canonical_hash(config))
    return engine, state, context


def _deep_update(base, extra):
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value


EXAMPLE_PATH = Path(__file__).resolve().parents[2] / "configs" / "dino4t" / "example_single_cylinder_500cc.json"
