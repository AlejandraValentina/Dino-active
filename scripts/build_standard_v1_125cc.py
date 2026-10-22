"""Build and validate the STANDARD_V1 125 cc Blair/Cartwright configuration.

This script only constructs and serializes the integrated 2T configuration. It
does not advance the solver, run a cycle, or claim predictive validity.

The geometry follows Blair, *Design and Simulation of Two-Stroke Engines*
(SAE, 1996), Sec. 5.5.2, using the documented 56 x 50.6 mm engine, exhaust
timing, transfer timing, port widths, pipe A2, crankcase ratio, combustion
parameters, and the exhaust-control-valve trapped-compression-ratio table.

Usage:
    python scripts/build_standard_v1_125cc.py
    python scripts/build_standard_v1_125cc.py --output <path>
    python scripts/build_standard_v1_125cc.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from motorsim.combustion import WiebeComponent
from motorsim.crankcase import CrankcaseGeometry
from motorsim.fuel_combustion import FuelCoupledCombustionV1
from motorsim.gas1d.mesh import segments_mesh, uniform_mesh
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from motorsim.integrated_2t import (DuctPath2T, EngineGeometry2T,
                                    IntegratedEngine2T,
                                    IntegratedPortBinding2T,
                                    SliderCrankChambers2T)
from motorsim.kinematics import piston_position
from motorsim.powervalve import PowerValve
from motorsim.reed import ReedPetal
from motorsim.thermal import ThermalSurface, ThermalSystem
from motorsim.two_stroke_ports import (DuctBinding, PortDefinition,
                                       TwoStrokePortSet)

DEFAULT_OUTPUT = (
    ROOT / "configs" / "reference_cases"
    / "standard_v1_125cc_blair_cartwright.json"
)

# Documented Blair/Cartwright 125 cc racing engine.
BORE_MM = 56.0
STROKE_MM = 50.6
ROD_MM = 110.0
VD_CC = math.pi * BORE_MM**2 / 4.0 * STROKE_MM / 1000.0
CR_TRAPPED_BASELINE = 9.0
CR_CRANKCASE = 1.35
V_BDC_CC = VD_CC / (CR_CRANKCASE - 1.0)

# Port geometry derived from documented timing and widths.
X_81 = piston_position(STROKE_MM, ROD_MM, 81.0)
X_95 = piston_position(STROKE_MM, ROD_MM, 95.0)
# Blair's baseline trapped CR is 9.0 with the valve open, i.e. at the natural
# exhaust closing event 81 deg BTDC (279 deg ATDC), not at the 81 deg ATDC
# opening event. The slider-crank position is symmetric about BDC, so
# x(81 BTDC) = x(279 ATDC) = x(81 ATDC); the numerical formula uses x(81) but
# the physical event is the closing. At 95 deg BTDC the same geometry gives the
# documented ~11.1 trapped CR, a useful consistency check.
CR_GEOM = 1.0 + (CR_TRAPPED_BASELINE - 1.0) * STROKE_MM / X_81
EXHAUST_TOP_MM = X_81
EXHAUST_HEIGHT_MM = STROKE_MM - X_81
EXHAUST_ROOF_TRAVEL_MM = X_95 - X_81
TRANSFER_TOP_MM = piston_position(STROKE_MM, ROD_MM, 115.0)
TRANSFER_HEIGHT_MM = STROKE_MM - TRANSFER_TOP_MM

# Pipe A2 from Blair Sec. 5.5.2, mm (length, start diameter, end diameter).
PIPE = (
    (83.0, 37.5, 37.5),
    (189.0, 37.5, 48.5),
    (209.0, 48.5, 100.0),
    (65.0, 100.0, 116.0),
    (78.0, 116.0, 116.0),
    (205.0, 116.0, 21.0),
    (250.0, 21.0, 21.0),
)

# Species order: fresh_air, fuel, residual, burned.
FRESH = (0.92, 0.08, 0.0, 0.0)
RESIDUAL = (0.0, 0.0, 1.0, 0.0)
RHO_300 = 101325.0 / (287.0 * 300.0)
RHO_600 = 101325.0 / (287.0 * 600.0)


def build_configuration() -> tuple[dict, dict]:
    """Construct the engine and return (configuration, diagnostic summary)."""
    ports = TwoStrokePortSet(
        STROKE_MM, ROD_MM,
        (DuctBinding("inlet", "intake"),
         DuctBinding("primary", "transfer"),
         DuctBinding("secondary", "transfer"),
         DuctBinding("boost", "transfer"),
         DuctBinding("exhaust", "exhaust")),
        (
            # The solver has no reed-specific intake port family, so the reed
            # is bound to a synthetic piston window standing in for the reed
            # block. Width 38 mm is the documented carburettor/reed throat;
            # height 36 mm is a modelling choice, not a measured port. It makes
            # the window effective area 1162.8 mm2, slightly above the 1134.1
            # mm2 inlet duct, at maximum opening; the window still restricts at partial lift, not simply
            # an always-transparent reed-block proxy. The window is fully open only from
            # 302.01 to 57.99 deg ATDC and tapers to zero at 165.77/194.23 deg.
            PortDefinition(
                "inlet-window", "Inlet", "intake", "piston_port", "inlet",
                "piston_port", 0.85, "SYNTHETIC_ASSUMPTION",
                top_mm=56.0, height_mm=36.0, width_mm=38.0, skirt_mm=42.0),
            PortDefinition(
                "primary-window", "Primary transfer", "transfer", "primary",
                "primary", "rectangular_window", 0.70,
                "DERIVED_FROM_DOCUMENTED", top_mm=TRANSFER_TOP_MM,
                height_mm=TRANSFER_HEIGHT_MM, width_mm=30.0),
            PortDefinition(
                "secondary-window", "Secondary transfer", "transfer",
                "secondary", "secondary", "rectangular_window", 0.70,
                "DERIVED_FROM_DOCUMENTED", top_mm=TRANSFER_TOP_MM,
                height_mm=TRANSFER_HEIGHT_MM, width_mm=30.0),
            PortDefinition(
                "boost-window", "Boost transfer", "transfer", "boost",
                "boost", "rectangular_window", 0.70,
                "DERIVED_FROM_DOCUMENTED", top_mm=TRANSFER_TOP_MM,
                height_mm=TRANSFER_HEIGHT_MM, width_mm=20.4),
            PortDefinition(
                "main-exhaust", "Main exhaust", "exhaust", "main", "exhaust",
                "rectangular_window", 0.80, "DOCUMENTED",
                top_mm=EXHAUST_TOP_MM, height_mm=EXHAUST_HEIGHT_MM,
                width_mm=43.0, roof_travel_mm=EXHAUST_ROOF_TRAVEL_MM),
        ))

    # Synthetic interpolation. Blair documents the fully lowered extreme
    # (closing at 95 deg BTDC) and that the valve is fully lifted by 9500 rpm,
    # but not the start or shape of the map. The 8500 rpm start is chosen so
    # that 9000 rpm is the midpoint. This is an assumption, not a measured map.
    valve = PowerValve(
        "exhaust-valve", "main-exhaust", (1000.0, 8500.0, 9500.0),
        (1.0, 1.0, 0.0), "SYNTHETIC_ASSUMPTION")
    binding = IntegratedPortBinding2T(
        ports,
        {"inlet": "intake", "primary": "primary", "secondary": "secondary",
         "boost": "boost", "exhaust": "exhaust"},
        valve)
    crankcase = CrankcaseGeometry(
        BORE_MM, STROKE_MM, ROD_MM, V_BDC_CC, "DERIVED_FROM_DOCUMENTED")
    slider = SliderCrankChambers2T(crankcase, CR_GEOM)

    intake_mesh = uniform_mesh(4, 0.080, math.pi * 0.038**2 / 4.0)
    primary_area = 30.0 * TRANSFER_HEIGHT_MM * 1e-6
    secondary_area = 30.0 * TRANSFER_HEIGHT_MM * 1e-6
    boost_area = 20.4 * TRANSFER_HEIGHT_MM * 1e-6
    transfer_meshes = {
        "primary": uniform_mesh(3, 0.050, primary_area),
        "secondary": uniform_mesh(3, 0.050, secondary_area),
        "boost": uniform_mesh(3, 0.050, boost_area),
    }
    exhaust_mesh = segments_mesh(
        [{"length": length, "start_diameter": d0, "end_diameter": d1}
         for length, d0, d1 in PIPE],
        0.040,
    )
    paths = (
        DuctPath2T("intake", intake_mesh, "intake"),
        *[DuctPath2T(name, mesh, "transfer")
          for name, mesh in transfer_meshes.items()],
        DuctPath2T("exhaust", exhaust_mesh, "exhaust"),
    )

    def duct_rows(path: DuctPath2T, rho: float,
                  fractions: tuple[float, ...]):
        rows_states = []
        rows_species = []
        for volume in path.mesh.volumes:
            mass = rho * volume
            rows_states.append([rho, 0.0, 101325.0, 1.0])
            rows_species.append([fractions[i] * mass for i in range(4)])
        return rows_states, rows_species

    initial_duct_states: dict[str, list[list[float]]] = {}
    duct_species: dict[str, list[list[float]]] = {}
    for path in paths:
        if path.role == "exhaust":
            state_rows, species_rows = duct_rows(path, RHO_600, RESIDUAL)
        else:
            state_rows, species_rows = duct_rows(path, RHO_300, FRESH)
        initial_duct_states[path.id] = state_rows
        duct_species[path.id] = species_rows

    cc_vol_tdc = crankcase.volume_m3(0.0)
    cy_vol_tdc = VD_CC * 1e-6 / (CR_GEOM - 1.0)
    cc_mass = RHO_300 * cc_vol_tdc
    cy_mass = RHO_300 * cy_vol_tdc
    initial_chambers = {
        "crankcase": [RHO_300, 0.0, 101325.0, 1.0],
        "cylinder": [RHO_300, 0.0, 101325.0, 1.0],
        "species": {
            "crankcase": [0.92 * cc_mass, 0.08 * cc_mass, 0.0, 0.0],
            "cylinder": [0.46 * cy_mass, 0.04 * cy_mass, 0.50 * cy_mass, 0.0],
        },
    }

    # Six glass-fibre petals. The effective static stiffness is a synthetic
    # assumption; the current reed model does not use mass or damping.
    petals = tuple(
        ReedPetal(f"reed-{i + 1}", 6.9e-4, 8.626e-4, 0.0227, 1000.0, 0.5,
                  0.013, 0.80, "SYNTHETIC_ASSUMPTION")
        for i in range(6)
    )

    # Documented wall temperatures; representative heat-transfer coefficients.
    surfaces = [
        ThermalSurface("cylinder-wall", "cylinder_wall",
                       math.pi * 0.056 * 0.0506, 500.0,
                       "SYNTHETIC_ASSUMPTION", wall_temperature_K=473.0),
        ThermalSurface("cylinder-head", "cylinder_head",
                       math.pi * 0.056**2 / 4.0, 500.0,
                       "SYNTHETIC_ASSUMPTION", wall_temperature_K=473.0),
        ThermalSurface("piston-crown", "piston_crown",
                       math.pi * 0.056**2 / 4.0, 500.0,
                       "SYNTHETIC_ASSUMPTION", wall_temperature_K=473.0),
        ThermalSurface("crankcase-wall", "crankcase", 0.020, 50.0,
                       "SYNTHETIC_ASSUMPTION", wall_temperature_K=353.0),
    ]
    locations = {
        "cylinder-wall": "cylinder",
        "cylinder-head": "cylinder",
        "piston-crown": "cylinder",
        "crankcase-wall": "crankcase",
    }
    for index, (face_left, face_right, area_left, area_right) in enumerate(zip(
            exhaust_mesh.faces, exhaust_mesh.faces[1:], exhaust_mesh.areas,
            exhaust_mesh.areas[1:])):
        diameter_left = math.sqrt(4.0 * area_left / math.pi)
        diameter_right = math.sqrt(4.0 * area_right / math.pi)
        area = math.pi * 0.5 * (diameter_left + diameter_right) * (
            face_right - face_left)
        sid = f"exhaust-wall-{index:02d}"
        surfaces.append(ThermalSurface(
            sid, "exhaust_walls", area, 50.0, "SYNTHETIC_ASSUMPTION",
            wall_temperature_K=623.0))
        locations[sid] = f"exhaust:{index}"

    combustion = FuelCoupledCombustionV1(
        components=(WiebeComponent(weight=1.0, duration_deg=41.0,
                                    shape_a=5.25, shape_m=1.25,
                                    delay_deg=12.0),),
        ignition_timing_deg=340.0,
        combustion_efficiency=0.85,
    )

    def angle_for_piston_position(target_mm: float, lower_deg: float,
                                  upper_deg: float) -> float:
        f_lower = piston_position(STROKE_MM, ROD_MM, lower_deg) - target_mm
        lo, hi = lower_deg, upper_deg
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            f_mid = piston_position(STROKE_MM, ROD_MM, mid) - target_mm
            if f_lower * f_mid <= 0.0:
                hi = mid
            else:
                lo = mid
                f_lower = f_mid
        return 0.5 * (lo + hi)

    valve_position_9000 = valve.at(9000.0)
    exhaust_top_9000 = (
        EXHAUST_TOP_MM + valve_position_9000 * EXHAUST_ROOF_TRAVEL_MM)
    exhaust_open_9000 = angle_for_piston_position(
        exhaust_top_9000, 0.0, 180.0)
    trapped_cr_9000 = (
        1.0 + exhaust_top_9000 * (CR_GEOM - 1.0) / STROKE_MM)

    inlet_window = next(port for port in ports.ports
                        if port.id == "inlet-window")
    exhaust_port = next(port for port in ports.ports
                        if port.id == "main-exhaust")
    inlet_window_max = max(
        ports.area_at(inlet_window, angle) for angle in range(361))
    inlet_duct_area = math.pi * 0.038**2 / 4.0 * 1e6
    exhaust_max_open = max(
        ports.area_at(exhaust_port, angle) for angle in range(361))
    exhaust_max_9000 = max(
        valve.area_at(ports, 9000.0, angle) for angle in range(361))

    geometry_identity = {
        "standard": "STANDARD_V1_125CC_BLAIR_CARTWRIGHT",
        "source": (
            "Blair, Design and Simulation of Two-Stroke Engines, "
            "Sec. 5.5.2"),
        "bore_mm": BORE_MM,
        "stroke_mm": STROKE_MM,
        "rod_length_mm": ROD_MM,
        "displacement_cc": VD_CC,
        "trapped_compression_ratio_baseline": CR_TRAPPED_BASELINE,
        "trapped_compression_ratio_at_81_btdc": CR_TRAPPED_BASELINE,
        "trapped_compression_ratio_at_95_btdc": (
            1.0 + X_95 * (CR_GEOM - 1.0) / STROKE_MM),
        "geometric_compression_ratio": CR_GEOM,
        "crankcase_compression_ratio": CR_CRANKCASE,
        "crankcase_volume_bdc_cc": V_BDC_CC,
        "exhaust_opens_atdc_deg_valve_open": 81.0,
        "exhaust_closes_atdc_deg_valve_open": 279.0,
        "exhaust_closes_btdc_deg_valve_open": 81.0,
        "exhaust_closes_btdc_deg_fully_lowered": 95.0,
        "powervalve_position_at_9000": valve_position_9000,
        "exhaust_opens_atdc_deg_at_9000": exhaust_open_9000,
        "exhaust_closes_atdc_deg_at_9000": 360.0 - exhaust_open_9000,
        "trapped_compression_ratio_at_9000": trapped_cr_9000,
        "exhaust_max_effective_area_mm2_valve_open": exhaust_max_open,
        "exhaust_max_effective_area_mm2_at_9000": exhaust_max_9000,
        "inlet_window_full_area_atdc_deg": [302.0137840171832,
                                           57.9862159828168],
        "inlet_window_effective_area_mm2": inlet_window_max,
        "inlet_duct_area_mm2": inlet_duct_area,
        "transfer_opens_atdc_deg": 115.0,
        "exhaust_width_mm": 43.0,
        "transfer_effective_width_mm": 80.4,
        "pipe_sections_mm": [
            [length, d0, d1] for length, d0, d1 in PIPE],
        "assumptions": [
            "single main exhaust window; no auxiliary exhaust ports",
            "synthetic inlet window stands in for a reed block; width 38 mm "
            "is documented, height 36 mm is modelled",
            "maximum inlet window area exceeds duct area, but the synthetic "
            "piston window can restrict flow at partial opening",
            "transfer port area gates both crankcase and cylinder endpoints",
            "powervalve map is a linear synthetic interpolation between the "
            "documented fully-lowered and fully-lifted states",
            "static reed model; effective stiffness is not measured",
            "thermal h and some wall areas are representative, not measured",
        ],
    }

    boundary = OpenEndPlenumV2Boundary(101325.0, 300.0, 1.0)

    def geometry(angle: float) -> EngineGeometry2T:
        cc_vol, cy_vol, cc_rate, cy_rate = slider.resolve(angle, 9000.0)
        intake_area, transfer_areas, exhaust_area = binding.resolve(
            paths, angle, 9000.0)
        return EngineGeometry2T(
            cc_vol, cy_vol, cc_rate, cy_rate,
            intake_area, transfer_areas, exhaust_area)

    engine = IntegratedEngine2T(
        tuple(initial_chambers["crankcase"]),
        tuple(initial_chambers["cylinder"]),
        paths,
        initial_duct_states,
        geometry,
        species={
            "crankcase": tuple(initial_chambers["species"]["crankcase"]),
            "cylinder": tuple(initial_chambers["species"]["cylinder"]),
            **{key: tuple(tuple(row) for row in rows)
               for key, rows in duct_species.items()},
        },
        atmosphere=(101325.0, 300.0),
        atmosphere_species=FRESH,
        outlet_species=(1.0, 0.0, 0.0, 0.0),
        inlet_boundary=boundary,
        outlet_boundary=boundary,
        max_cfl=0.4,
        geometry_identity=geometry_identity,
        reed_petals=petals,
        port_binding=binding,
        slider_crank=slider,
        reference_rpm=9000.0,
        thermal_system=ThermalSystem(tuple(surfaces)),
        thermal_locations=locations,
        thermal_load=0.0,
        combustion_start_angle_deg=None,
        fuel_coupled_combustion=combustion,
    )
    config = engine.configuration_dict()
    diagnostics = {
        "vd_cc": VD_CC,
        "v_bdc_cc": V_BDC_CC,
        "cr_geom": CR_GEOM,
        "x_81": X_81,
        "x_95": X_95,
        "cr_81": 1.0 + X_81 * (CR_GEOM - 1.0) / STROKE_MM,
        "cr_95": 1.0 + X_95 * (CR_GEOM - 1.0) / STROKE_MM,
        "valve_9000": valve_position_9000,
        "exhaust_open_9000": exhaust_open_9000,
        "exhaust_close_9000": 360.0 - exhaust_open_9000,
        "cr_9000": trapped_cr_9000,
        "exhaust_max_open": exhaust_max_open,
        "exhaust_max_9000": exhaust_max_9000,
        "inlet_window_max": inlet_window_max,
        "inlet_duct_area": inlet_duct_area,
        "mesh_cells": {path.id: len(path.mesh.volumes) for path in paths},
        "exhaust_first_area": exhaust_mesh.areas[0],
        "exhaust_last_area": exhaust_mesh.areas[-1],
        "max_effective_areas_valve_open": {
            port.id: max(ports.area_at(port, angle)
                         for angle in range(361))
            for port in ports.ports
        },
        "max_effective_areas_at_9000": {
            port.id: max(
                valve.area_at(ports, 9000.0, angle)
                if port.id == "main-exhaust"
                else ports.area_at(port, angle)
                for angle in range(361))
            for port in ports.ports
        },
    }
    return config, diagnostics


def validate(config: dict, diagnostics: dict) -> None:
    """Fail closed if the constructed configuration is internally inconsistent."""
    if config.get("schema") != "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V5":
        raise SystemExit("unexpected schema")
    restored = IntegratedEngine2T.from_configuration_dict(config)
    if restored.configuration_dict() != config:
        raise SystemExit("configuration roundtrip is not stable")
    if abs(diagnostics["cr_geom"] - 17.714769879063663) > 1e-9:
        raise SystemExit("geometric CR does not match the documented table")
    if abs(diagnostics["cr_81"] - 9.0) > 1e-9:
        raise SystemExit("baseline trapped CR at closing 81 deg BTDC is not 9.0")
    if abs(diagnostics["cr_95"] - 11.052435624726295) > 1e-9:
        raise SystemExit("trapped CR at closing 95 deg BTDC does not match the table")
    if abs(diagnostics["valve_9000"] - 0.5) > 1e-12:
        raise SystemExit("powervalve position at 9000 rpm is not 0.5")
    if abs(diagnostics["exhaust_open_9000"] - 87.91528292196685) > 1e-6:
        raise SystemExit("exhaust opening at 9000 rpm is inconsistent")
    if abs(diagnostics["exhaust_close_9000"] - 272.0847170780331) > 1e-6:
        raise SystemExit("exhaust closing at 9000 rpm is inconsistent")
    if abs(diagnostics["cr_9000"] - 10.026217812363148) > 1e-6:
        raise SystemExit("trapped CR at 9000 rpm is inconsistent")
    if abs(diagnostics["exhaust_max_open"] - 907.5372949820794) > 1e-6:
        raise SystemExit("exhaust area with the valve open is inconsistent")
    if abs(diagnostics["exhaust_max_9000"] - 800.6691905549155) > 1e-6:
        raise SystemExit("exhaust area at 9000 rpm is inconsistent")
    if abs(diagnostics["inlet_window_max"] - 1162.8) > 1e-9:
        raise SystemExit("inlet window area is inconsistent")
    if abs(diagnostics["inlet_duct_area"] - 1134.1149479459152) > 1e-6:
        raise SystemExit("inlet duct area is inconsistent")
    if diagnostics["inlet_window_max"] <= diagnostics["inlet_duct_area"]:
        raise SystemExit("inlet window would be the primary flow restriction")
    if diagnostics["mesh_cells"] != {
            "intake": 4, "primary": 3, "secondary": 3, "boost": 3,
            "exhaust": 31}:
        raise SystemExit("unexpected mesh cell counts")
    if config["initial_chambers"]["cylinder"][0] <= 0.0:
        raise SystemExit("non-positive cylinder density")
    if min(sum(row) for row in
           config["initial_chambers"]["species"].values()) <= 0.0:
        raise SystemExit("non-positive initial species mass")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the STANDARD_V1 125 cc configuration without "
                    "running the solver.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true",
                        help="validate only; do not write the output file")
    args = parser.parse_args()

    config, diagnostics = build_configuration()
    validate(config, diagnostics)

    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
        print(f"sha256 {digest}")

    print(f"schema {config['schema']}")
    print(
        "geometry "
        f"Vd={diagnostics['vd_cc']:.6f} cc, "
        f"VbdC={diagnostics['v_bdc_cc']:.6f} cc, "
        f"CRgeom={diagnostics['cr_geom']:.9f}")
    print(
        "compression "
        f"CR81BTDC={diagnostics['cr_81']:.9f}, "
        f"CR95BTDC={diagnostics['cr_95']:.9f}, "
        f"CR9000={diagnostics['cr_9000']:.9f}")
    print(
        "mesh "
        + ", ".join(f"{key}={value}"
                    for key, value in diagnostics["mesh_cells"].items()))
    print(
        "powervalve "
        f"9000={diagnostics['valve_9000']:.3f}, "
        f"exhaust_open={diagnostics['exhaust_open_9000']:.6f} deg ATDC, "
        f"exhaust_close={diagnostics['exhaust_close_9000']:.6f} deg ATDC")
    print(
        "exhaust area "
        f"valve_open={diagnostics['exhaust_max_open']:.6f} mm2, "
        f"at_9000={diagnostics['exhaust_max_9000']:.6f} mm2")
    print(
        "inlet area "
        f"window={diagnostics['inlet_window_max']:.6f} mm2, "
        f"duct={diagnostics['inlet_duct_area']:.6f} mm2")
    print("max effective areas at valve-open geometry (mm2)")
    for port_id, area in diagnostics["max_effective_areas_valve_open"].items():
        print(f"  {port_id}: {area:.6f}")
    print("max effective areas at 9000 rpm (mm2)")
    for port_id, area in diagnostics["max_effective_areas_at_9000"].items():
        print(f"  {port_id}: {area:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
