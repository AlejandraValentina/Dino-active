"""Provenance-bound Yamaha KT100SP documentary case and synthetic runner fixture.

This module contains geometry/configuration utilities only.  It does not modify
the production solver and it makes no experimental or predictive claim.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from math import cos, isfinite, pi, sin, sqrt
from typing import Any

from .project import DuctSegment, Ducts, Intake, Port, Project
from .simulation_case import SyntheticCase

REFERENCE_ID = "KT100_REFERENCE_CASE_V1"
FIXTURE_ID = "KT100_MODEL_FIXTURE_V1"
SIMULATION_ID = "KT100_REFERENCE_SIMULATION"
YAMAHA_SOURCE = "https://global.yamaha-motor.com/jp/news/1998/1216/kart.html"
ACADEMIC_SOURCE = "https://repository.lib.ncsu.edu/bitstreams/24433484-a6eb-4ad8-80f1-a18fa75c4ef6/download"
REFERENCE_CASE_STATUS = "REAL_ENGINE_REFERENCE_CASE"
CLAIMS_PROHIBITED = ("P9_PASS", "EXPERIMENTALLY_VALIDATED", "PREDICTIVELY_VALIDATED")


def _entry(value: Any, units: str, status: str, source: str | None,
           location: str | None, notes: str, **assumption: Any) -> dict:
    result = {"value": value, "units": units, "status": status,
              "source": source, "source_location": location, "notes": notes}
    if status == "SYNTHETIC_ASSUMPTION":
        result.update(assumption)
    return result


DOCUMENTED = "DOCUMENTED"
DERIVED = "DERIVED_FROM_DOCUMENTED"
SYNTHETIC = "SYNTHETIC_ASSUMPTION"
UNKNOWN = "UNKNOWN"


def _synthetic(value, units, reason, sensitivity, strong, origin):
    return _entry(value, units, SYNTHETIC, None, None, reason,
                  reason=reason, expected_sensitivity=sensitivity,
                  strongly_affects_results=strong, conceptual_origin=origin)


def build_provenance_manifest() -> dict:
    """Build canonical source and parameter inventory; no current-directory I/O."""
    parameters = {
        "manufacturer": _entry("Yamaha Motor Co., Ltd.", "text", DOCUMENTED,
            YAMAHA_SOURCE, "heading and release text; 16 December 1998", "Manufacturer's official release."),
        "variant": _entry("KT100SP", "model designation", DOCUMENTED,
            YAMAHA_SOURCE, "heading; product description; specifications", "Selected explicitly; no KT100S/SD/SEC data are merged."),
        "variant_context": _entry("Japan domestic FP2 karting class; announced 1998-12-16", "text", DOCUMENTED,
            YAMAHA_SOURCE, "release date and FP2 background", "Release does not identify an exact production year or serial range."),
        "architecture": _entry("single-cylinder piston-valve two-stroke", "text", DOCUMENTED,
            YAMAHA_SOURCE, "product description and specifications", "Yamaha wording: air-cooled two-cycle piston-valve single-cylinder."),
        "cycle": _entry("2T", "cycle", DOCUMENTED, YAMAHA_SOURCE, "specifications", "Two-stroke cycle."),
        "cylinder_count": _entry(1, "cylinders", DOCUMENTED, YAMAHA_SOURCE, "specifications: cylinder count", "Single cylinder."),
        "cooling": _entry("air-cooled", "text", DOCUMENTED, YAMAHA_SOURCE, "product description; specifications", "Variant-specific release."),
        "displacement_cm3": _entry(97.6, "cm3", DOCUMENTED, YAMAHA_SOURCE, "specifications: displacement", "Rounded manufacturer-declared displacement."),
        "bore_mm": _entry(52.0, "mm", DOCUMENTED, YAMAHA_SOURCE, "specifications: bore x stroke", "Variant-specific KT100SP."),
        "stroke_mm": _entry(46.0, "mm", DOCUMENTED, YAMAHA_SOURCE, "specifications: bore x stroke", "Variant-specific KT100SP."),
        "compression_ratio": _entry(9.0, "dimensionless", DOCUMENTED, YAMAHA_SOURCE, "specifications: compression ratio", "Yamaha gives 9.0:1; measurement convention is not described in the release."),
        "induction": _entry("piston-valve", "text", DOCUMENTED, YAMAHA_SOURCE, "product description; specifications", "Piston-controlled inlet; port dimensions and timing remain unknown."),
        "ignition": _entry("TCI", "text", DOCUMENTED, YAMAHA_SOURCE, "specifications: ignition", "The release does not provide timing curve or advance."),
        "lubrication": _entry("premix", "text", DOCUMENTED, YAMAHA_SOURCE, "specifications: lubrication", "No premix ratio stated in this release."),
        "carburetor": _entry("WALBRO WB40", "text", DOCUMENTED, YAMAHA_SOURCE, "specifications: carburetor", "No jetting, throat flow map or fuel schedule stated."),
        "exhaust_description": _entry("oval exhaust pipe; dedicated stepped chamber/muffler optional", "text", DOCUMENTED,
            YAMAHA_SOURCE, "exhaust-system description", "No dimensions or tuned operating range stated."),
        "operating_rpm_range": _entry(None, "rpm", UNKNOWN, None, None,
            "The selected-variant primary source gives no operating or rated RPM range."),
        "connecting_rod_length_mm": _entry(None, "mm", UNKNOWN, None, None,
            "No variant-specific connecting-rod center distance was found in the selected source."),
        "port_timing_deg": _entry(None, "deg crank", UNKNOWN, None, None,
            "No port opening/closing angles were found for KT100SP in the selected source."),
        "port_geometry": _entry(None, "mm / mm2", UNKNOWN, None, None,
            "No variant-specific port maps or dimensions found in the selected primary source."),
        "crankcase_volume_cm3": _entry(None, "cm3", UNKNOWN, None, None,
            "No KT100SP crankcase compression volume found."),
        "fuel_specification": _entry(None, "text", UNKNOWN, None, None,
            "The release identifies premix lubrication but not fuel grade, composition, or mixture ratio."),
    }
    derived = {
        "displacement_from_bore_stroke_cm3": _entry(displacement_cm3(52.0, 46.0), "cm3", DERIVED,
            "documented bore_mm and stroke_mm", "pi*D^2*S/4000", "Independent calculation; compared with rounded 97.6 cm3 declaration."),
        "piston_area_mm2": _entry(pi * 52.0**2 / 4.0, "mm2", DERIVED,
            "documented bore_mm", "pi*D^2/4", "Geometric circular-bore area."),
        "swept_volume_per_cylinder_cm3": _entry(displacement_cm3(52.0, 46.0), "cm3", DERIVED,
            "documented bore_mm and stroke_mm", "pi*D^2*S/4000", "One cylinder; equals geometric displacement."),
        "clearance_volume_cm3_if_geometric_ratio": _entry(displacement_cm3(52.0, 46.0)/(9.0-1.0), "cm3", DERIVED,
            "documented bore_mm, stroke_mm, compression_ratio", "Vs/(CR-1)", "Conditional derivation assuming Yamaha's ratio means VBDC/VTDC; the source does not state its method."),
        "crank_radius_mm": _entry(23.0, "mm", DERIVED,
            "documented stroke_mm", "S/2", "Slider-crank throw radius."),
    }
    fixture = {
        "connecting_rod_length_mm": _synthetic(100.0, "mm", "A rod length is required for slider-crank kinematics; KT100SP-specific value was unavailable.", "high for near-TDC volume and timing; moderate for swept volume", True, "conventional long-rod slider-crank numerical fixture; not a measured KT100 dimension"),
        "crank_offset_mm": _synthetic(0.0, "mm", "The selected project kinematics use a centered slider-crank.", "low for the chosen geometry; can affect piston motion if nonzero", True, "existing MotorSim zero-offset kinematic convention"),
        "crankcase_volume_bdc_cm3": _synthetic(250.0, "cm3", "A finite crankcase volume is required by the existing coupled chamber model; the baseline is a coarse synthetic screening value, not a Yamaha measurement.", "high for pumping and transfer pressure", True, "borrowed as a numerical scale from the existing S2T-0D-01 synthetic fixture only; no KT100 specification is implied"),
        "exhaust_port_top_mm": _synthetic(30.0, "mm below TDC", "A port height/location is needed to calculate exhaust opening.", "high for blowdown and scavenging", True, "small rectangular port surrogate in the existing project geometry model"),
        "exhaust_port_height_mm": _synthetic(10.0, "mm", "A port height is needed to define area versus crank angle.", "high for discharge and trapped charge", True, "small rectangular port surrogate"),
        "exhaust_port_width_mm": _synthetic(16.0, "mm developed", "A port width is needed to define geometric area.", "high for mass flow", True, "small rectangular port surrogate"),
        "transfer_port_top_mm": _synthetic(36.0, "mm below TDC", "Two transfer windows are required by the existing topology.", "high for scavenging timing", True, "two symmetric small rectangular transfer surrogates"),
        "transfer_port_height_mm": _synthetic(8.0, "mm", "A port height is needed to define area versus crank angle.", "high for scavenging", True, "small rectangular port surrogate"),
        "transfer_port_width_mm": _synthetic(12.0, "mm developed per port", "A port width is needed to define geometric area.", "high for delivered and short-circuit mass", True, "two symmetric small rectangular port surrogates"),
        "intake_port_top_mm": _synthetic(62.0, "mm from project datum", "The piston-port inlet requires geometry in the project convention.", "high for intake timing", True, "piston-skirt-controlled rectangular port surrogate"),
        "intake_model_mode": _synthetic("piston_port", "mode", "The executable project schema supports the piston-port inlet model.", "high for intake timing", True, "existing MotorSim project model; not a complete carburetor representation"),
        "intake_port_height_mm": _synthetic(10.0, "mm", "The inlet area model requires height.", "high for intake flow", True, "rectangular port surrogate"),
        "intake_port_width_mm": _synthetic(16.0, "mm developed", "The inlet area model requires width.", "high for intake flow", True, "small rectangular port surrogate"),
        "intake_piston_skirt_mm": _synthetic(42.0, "mm", "The piston-port opening calculation requires skirt reference.", "high for intake timing", True, "straight-skirt geometry convention"),
        "intake_duct_length_mm": _synthetic(65.0, "mm", "A completed fixture needs an inlet tract length.", "moderate for stored gas and pressure response", True, "minimal straight tract; not copied from KT100S rules"),
        "intake_duct_diameter_mm": _synthetic(14.0, "mm", "A completed fixture needs an inlet duct section.", "moderate to high for flow", True, "constant-area circular tract surrogate; carburetor venturi flow map is not modeled"),
        "exhaust_header_length_mm": _synthetic(120.0, "mm", "A completed fixture needs an exhaust path.", "high for wave travel and backpressure", True, "straight-header surrogate; not an OEM dimension"),
        "exhaust_header_diameter_mm": _synthetic(35.0, "mm", "A completed fixture needs an exhaust section area.", "high for flow and wave impedance", True, "constant-area circular duct surrogate"),
        "exhaust_tail_length_mm": _synthetic(180.0, "mm", "The project geometry requires a connected outlet route.", "high for pressure response", True, "short straight outlet surrogate"),
        "exhaust_tail_diameter_mm": _synthetic(35.0, "mm", "The project geometry requires a connected outlet section.", "high for flow", True, "constant-area circular duct surrogate"),
        "thermo_R_J_kgK": _synthetic(287.0, "J/(kg K)", "The frozen ideal-gas solver requires a specific gas constant; composition is not modeled.", "moderate for mass flow and pressure", True, "existing MotorSim P5-C/P8 synthetic gas fixture"),
        "thermodynamic_model": _synthetic("calorically perfect ideal gas", "model", "The existing application model requires fixed caloric properties.", "high for pressure and energy", True, "existing MotorSim 0D gas model; not a composition model"),
        "thermo_gamma": _synthetic(1.35, "dimensionless", "The frozen calorically-perfect solver requires gamma.", "high for acoustic speed and energy", True, "existing MotorSim P5-C/P8 synthetic gas fixture"),
        "initial_pressure_Pa": _synthetic(101325.0, "Pa absolute", "A finite initial state is required to execute the fixture.", "high for mass and flow", True, "standard atmosphere as a numerical boundary value"),
        "initial_crankcase_pressure_Pa": _synthetic(120000.0, "Pa absolute", "The existing 0D case needs an explicit initial crankcase state; no KT100SP value is available.", "high for initial pumping and transfer", True, "declared synthetic initial condition used unchanged in the completed study"),
        "initial_cylinder_pressure_Pa": _synthetic(140000.0, "Pa absolute", "The existing 0D case needs an explicit initial cylinder state; no KT100SP value is available.", "high for initial trapped mass and pressure", True, "declared synthetic residual-state initialization used unchanged in the completed study"),
        "initial_intake_temperature_K": _synthetic(300.0, "K", "Initial intake state is not variant-specific documented data.", "moderate", True, "existing MotorSim P8 synthetic initialization"),
        "initial_crankcase_temperature_K": _synthetic(330.0, "K", "Initial crankcase state is not variant-specific documented data.", "moderate", True, "existing MotorSim P8 synthetic initialization"),
        "initial_cylinder_temperature_K": _synthetic(700.0, "K", "Initial cylinder residual state is not variant-specific documented data.", "high for pressure and heat transfer", True, "existing MotorSim P8 synthetic initialization"),
        "initial_exhaust_temperature_K": _synthetic(500.0, "K", "Initial exhaust state is not variant-specific documented data.", "moderate for pressure waves", True, "existing MotorSim P8 synthetic initialization"),
        "initial_fresh_fraction_by_cv": _synthetic([1.0, 1.0, 0.0, 0.0], "fraction [I,K,C,E]", "The legacy 0D model tracks a passive fresh fraction and requires explicit initial marker states.", "high for marker accounting", True, "declared synthetic initial states; not four-species mass fractions"),
        "atmospheric_fresh_marker_fraction": _synthetic(1.0, "fraction", "The 0D intake reservoir carries only its passive fresh marker; this scalar is not the P6 four-species composition vector.", "high for fresh-marker boundary accounting", True, "pure fresh-air reservoir convention for this synthetic 0D fixture"),
        "exhaust_reservoir_fresh_marker_fraction": _synthetic(0.0, "fraction", "The 0D exhaust reservoir starts without the passive fresh marker.", "moderate for initial marker state", True, "declared synthetic reservoir initial condition"),
        "atmosphere_species_mass_fractions": _synthetic([1.0, 0.0, 0.0, 0.0], "mass fraction [fresh_air,fuel,residual,burned]", "The 0D application tracks only a passive fresh marker; these four values document the requested ideal fresh-air boundary convention, not a four-species solver state.", "high for fresh-marker bookkeeping", True, "explicit fixture boundary convention"),
        "prescribed_heat_model": _synthetic("P7 prescribed source; no chemistry", "model label", "The existing P7 law is a fixed bookkeeping heat source, not Yamaha combustion data.", "dominant for indicated work", True, "existing MotorSim P7 source contract; Q_F=800000 J/kg and 40 deg duration"),
        "p7_start_angle_deg": _synthetic(350.0, "deg CA", "The existing P7 verification source uses a fixed event start.", "dominant for pressure phasing", True, "existing P7 prescribed-source contract"),
        "p7_duration_deg": _synthetic(40.0, "deg CA", "The existing P7 verification source uses a fixed duration.", "dominant for pressure phasing", True, "existing P7 prescribed-source contract"),
        "p7_heat_value_J_kg": _synthetic(800000.0, "J/kg", "This is the code's prescribed heat per bookkeeping burned mass, not a fuel LHV.", "dominant for indicated work", True, "existing MotorSim P7 constant Q_F"),
        "solver_profile": _synthetic("B", "profile", "Use existing adaptive profile B unchanged.", "high for integration cost and accuracy", True, "motorsim.adaptive.PROFILES[1]"),
        "sensitivity_rod_scale": _synthetic([0.95, 1.05], "fraction of baseline", "A preregistered +/-5% perturbation tests an uncertain kinematic input.", "high for volume/port phasing", True, "symmetric local sensitivity; not calibration"),
        "sensitivity_exhaust_length_scale": _synthetic([0.95, 1.05], "fraction of baseline", "A preregistered +/-5% perturbation tests an uncertain exhaust length.", "high for pressure response", True, "symmetric local sensitivity; not calibration"),
    }
    return {
        "schema": "motorsim-reference-provenance-v1",
        "reference_case_id": REFERENCE_ID,
        "reference_kind": REFERENCE_CASE_STATUS,
        "selected_variant": "Yamaha KT100SP (Japan FP2 context; 1998 announcement)",
        "variant_identification_limit": "Production year/serial range not stated by the release.",
        "fixture_id": FIXTURE_ID,
        "simulation_claim_status": "SYNTHETIC_NON_CONFIRMATORY",
        "experimental_validation": "NOT_PERFORMED",
        "predictive_validation": "NOT_CLAIMED",
        "prohibited_claims": list(CLAIMS_PROHIBITED),
        "sources": {
            "yamaha_1998_kt100sp": {"url": YAMAHA_SOURCE, "title": "Yamaha KT100SP product release", "publisher": "Yamaha Motor Co., Ltd.", "published": "1998-12-16", "authority": "manufacturer primary source", "used_for": ["variant", "context", "architecture", "2T", "single cylinder", "air cooling", "97.6 cm3", "52x46 mm", "compression ratio 9.0:1", "TCI", "premix", "Walbro WB40", "oval/optional exhaust description"]},
            "gore_2024_thesis": {"url": ACADEMIC_SOURCE, "title": "Experimental Development of a High Power Density Generator Utilizing Renewable Fuel", "publisher": "North Carolina State University repository", "published": "2024", "authority": "academic secondary source; variant identity differs/unclear", "used_for": ["context only; not used to populate KT100SP parameters"]},
            "aka_kt100s_series_2013": {"url": "https://www.karting.net.au/wp-content/uploads/2010/09/YAMAHA-KT100S-V-5.pdf", "title": "Yamaha KT100S Series Engines Technical Specifications, Version 5", "publisher": "Australian Karting Association", "published": "2013-08-20 update", "authority": "competition technical document for S/SE/SD/SEC series", "used_for": ["variant-difference cross-check only; not mixed into KT100SP"]},
        },
        "parameters": parameters,
        "derived_parameters": derived,
        "fixture_assumptions": fixture,
        "source_reconciliation": {
            "selected_source": "Yamaha official KT100SP 1998 release",
            "not_merged": ["KT100S/SE/SD/SEC Australian 2013 technical rules", "generic KT-100 thesis table"],
            "rpm_range": "UNKNOWN for this variant; the numerical sweep is an exploratory MotorSim grid only.",
            "compression_method": "Yamaha publishes 9.0:1 without a stated measurement convention; clearance volume derivation is conditional on a geometric VBDC/VTDC interpretation.",
        },
    }


def displacement_cm3(bore_mm: float, stroke_mm: float) -> float:
    if not all(isfinite(float(v)) and float(v) > 0 for v in (bore_mm, stroke_mm)):
        raise ValueError("bore and stroke must be finite and positive")
    return pi * float(bore_mm)**2 * float(stroke_mm) / 4000.0


def piston_area_mm2(bore_mm: float) -> float:
    if not isfinite(float(bore_mm)) or float(bore_mm) <= 0:
        raise ValueError("bore must be finite and positive")
    return pi * float(bore_mm)**2 / 4.0


def slider_crank_volume_cm3(angle_deg: float, *, bore_mm: float, stroke_mm: float,
                            rod_length_mm: float, compression_ratio: float) -> float:
    """Geometric volume; rod length is fixture-synthetic in this case."""
    values = (angle_deg, bore_mm, stroke_mm, rod_length_mm, compression_ratio)
    if not all(isfinite(float(v)) for v in values):
        raise ValueError("slider-crank inputs must be finite")
    if min(bore_mm, stroke_mm) <= 0 or rod_length_mm <= stroke_mm/2 or compression_ratio <= 1:
        raise ValueError("invalid slider-crank geometry")
    radius = stroke_mm/2.0
    theta = float(angle_deg)*pi/180.0
    # Written without depending on project/UI helpers, for independent checking.
    travel = radius * (1.0 - cos(theta)) + rod_length_mm - sqrt(
        rod_length_mm**2 - radius**2 * sin(theta)**2)
    swept = displacement_cm3(bore_mm, stroke_mm)
    clearance = swept/(compression_ratio-1.0)
    area_mm2 = piston_area_mm2(bore_mm)
    return clearance + area_mm2*travel/1000.0


def mean_piston_speed_m_s(stroke_mm: float, rpm: float) -> float:
    if not all(isfinite(float(v)) and float(v) > 0 for v in (stroke_mm, rpm)):
        raise ValueError("stroke and rpm must be finite and positive")
    return 2.0*(stroke_mm/1000.0)*rpm/60.0


def cycle_frequency_hz(rpm: float, cycle: str = "2T") -> float:
    if not isfinite(float(rpm)) or rpm <= 0 or cycle not in ("2T", "4T"):
        raise ValueError("invalid rpm or cycle")
    return rpm/60.0 if cycle == "2T" else rpm/120.0


def indicated_power_2t_w(work_per_cycle_j: float, rpm: float) -> float:
    if not all(isfinite(float(v)) for v in (work_per_cycle_j, rpm)) or rpm <= 0:
        raise ValueError("work must be finite and rpm finite positive")
    return work_per_cycle_j*rpm/60.0


def indicated_torque_equivalent_nm(work_per_cycle_j: float) -> float:
    if not isfinite(float(work_per_cycle_j)):
        raise ValueError("work must be finite")
    return work_per_cycle_j/(2.0*pi)


def fixture_project(*, rod_scale: float = 1.0, exhaust_scale: float = 1.0) -> Project:
    """Complete editable project geometry; non-documented fields are synthetic."""
    if not all(isfinite(float(v)) and float(v) > 0 for v in (rod_scale, exhaust_scale)):
        raise ValueError("fixture sensitivity scales must be finite and positive")
    return Project(
        name="KT100_MODEL_FIXTURE_V1 — SINTÉTICO, NO MEDIDO",
        cycle="2T", manufacturer="Yamaha (referencia documental KT100SP)",
        model=FIXTURE_ID, cylinder_count=1, bore_mm=52.0, stroke_mm=46.0,
        rod_length_mm=100.0*rod_scale, compression_ratio=9.0,
        notes=("Fixture numérico sintético basado solo en geometría Yamaha KT100SP "
               "documentada; biela, cárter, puertos, conductos, condiciones y fuente "
               "P7 son supuestos. No medido, no calibrado, no validado."),
        ports=(Port("Escape sintético", "escape", 30.0, 10.0, 16.0),
               Port("Transferencia 1 sintética", "transfer", 36.0, 8.0, 12.0),
               Port("Transferencia 2 sintética", "transfer", 36.0, 8.0, 12.0)),
        crankcase_volume_bdc_cm3=250.0,
        intake=Intake("piston_port", 62.0, 10.0, 16.0, 42.0),
        ducts=Ducts((DuctSegment("Admisión sintética", 65.0, 14.0, 14.0),),
                    (DuctSegment("Header sintético", 120.0*exhaust_scale, 35.0, 35.0),
                     DuctSegment("Salida sintética", 180.0*exhaust_scale, 35.0, 35.0))),
    )


def fixture_case(rpm: int, *, rod_scale: float = 1.0,
                 exhaust_scale: float = 1.0) -> SyntheticCase:
    if type(rpm) is not int or not 2500 <= rpm <= 15000:
        raise ValueError("exploratory RPM must be an integer in MotorSim's 2T execution domain [2500,15000]")
    return replace(SyntheticCase(), identifier=FIXTURE_ID, model="KT100 existing 0D synthetic fixture",
        project_geometry=fixture_project(rod_scale=rod_scale,
                                         exhaust_scale=exhaust_scale),
        rpm=rpm, gas_r=287.0, gamma=1.35,
        initial_pty=((101325.0, 300.0, 1.0), (120000.0, 330.0, 1.0),
                     (140000.0, 700.0, 0.0), (101325.0, 500.0, 0.0)),
        reservoirs_pty=((101325.0, 300.0, 1.0), (101325.0, 500.0, 0.0)),
        initial_angle_deg=180.0, heat_start_deg=350.0, heat_duration_deg=40.0,
        fresh_energy_j_kg=800000.0)


def build_fixture_config() -> dict:
    manifest = build_provenance_manifest()
    project = fixture_project()
    project.validate()
    config = {
        "schema": "motorsim-kt100-fixture-v1",
        "fixture_id": FIXTURE_ID,
        "reference_case_id": REFERENCE_ID,
        "kind": "synthetic_model_fixture",
        "claims": {"experimental_validation": "NOT_PERFORMED", "predictive_validation": "NOT_CLAIMED",
                   "p9_status_effect": "NONE", "prohibited": list(CLAIMS_PROHIBITED)},
        "reference_geometry": {"cylinders": 1, "bore_mm": 52.0, "stroke_mm": 46.0,
            "displacement_cm3": displacement_cm3(52.0, 46.0), "compression_ratio": 9.0,
            "rod_length_mm": 100.0, "rod_length_provenance": "SYNTHETIC_ASSUMPTION"},
        "engine_geometry_and_project": project.to_dict(),
        "cylinder": {"cylinders": 1, "swept_volume_cm3": displacement_cm3(52.0, 46.0),
                     "clearance_volume_cm3_conditional": displacement_cm3(52.0,46.0)/8.0,
                     "port_geometry_origin": "SYNTHETIC_ASSUMPTION"},
        "crank_slider": {"crank_radius_mm": 23.0, "rod_length_mm": 100.0,
                         "offset_mm": 0.0, "offset_provenance": "SYNTHETIC_ASSUMPTION"},
        "crankcase": {"volume_at_bdc_cm3": 250.0, "provenance": "SYNTHETIC_ASSUMPTION"},
        "intake": {"mode": "piston_port", "carburetor_reference": "Walbro WB40 (documented model identity only)",
                   "tract_geometry_provenance": "SYNTHETIC_ASSUMPTION",
                   "fuel_metering": "NOT_MODELED"},
        "transfer": {"two_rectangular_transfer_ports": True,
                     "flow_representation": "four-control-volume 0D lumped restrictions; no finite transfer-duct storage or wave dynamics",
                     "port_geometry_provenance": "SYNTHETIC_ASSUMPTION"},
        "exhaust": {"documented_description": "oval pipe; optional stepped chamber/muffler",
                    "modeled_path": "synthetic straight circular sections",
                    "geometry_provenance": "SYNTHETIC_ASSUMPTION",
                    "total_lumped_duct_length_mm": 300.0, "duct_area_m2": pi*(0.035**2)/4.0},
        "combustion": {"model": "legacy 0D analytic prescribed heat/burn bookkeeping; no chemistry",
            "event_start_deg": 350.0, "duration_deg": 40.0, "heat_per_bookkeeping_burned_kg_J": 800000.0,
            "provenance": "SYNTHETIC_ASSUMPTION", "fuel_chemistry": "NOT_MODELED"},
        "thermodynamics": {"eos": "calorically perfect ideal gas", "R_J_kgK": 287.0,
                           "gamma": 1.35, "provenance": "SYNTHETIC_ASSUMPTION"},
        "boundaries": {"ambient_pressure_Pa": 101325.0, "ambient_temperature_K": 300.0,
                       "atmosphere_species": [1.0,0.0,0.0,0.0],
                       "inlet_and_initial_states_provenance": "SYNTHETIC_ASSUMPTION",
                       "initial_states_pty": [[101325.0,300.0,1.0],
                         [120000.0,330.0,1.0],[140000.0,700.0,0.0],
                         [101325.0,500.0,0.0]],
                       "reservoir_states_pty": [[101325.0,300.0,1.0],
                         [101325.0,500.0,0.0]],
                       "states_are_0d_control_volume_values": True},
        "solver": {"topology": "existing four-control-volume 0D: intake, crankcase, cylinder, exhaust",
                   "integrator": "existing adaptive RK4 (two-half-step error estimate)",
                   "profile": "B", "profile_limits_from_existing_code": True,
                   "maximum_cycles": 30, "CFL": "NOT_APPLICABLE_ZERO_D",
                   "periodicity_contract": "existing application 0D period-1 cycle convergence; not E13-R1 and no period-2 detector",
                   "finite_duct_wave_dynamics": "NOT_MODELED",
                   "four_species_P6": "NOT_MODELED; one passive fresh-fraction marker is tracked",
                   "restart_api": "NOT_SUPPORTED_BY_EXISTING_0D_APPLICATION_RUNNER",
                   "P8_bounded_transient_substitution": False},
        "sensitivity_plan": {"pre_registered": True,
            "parameters": ["connecting_rod_length_mm", "exhaust_header_length_mm"],
            "relative_variants": [0.95,1.0,1.05], "calibration": False},
    }
    config["provenance_parameter_map"] = {
        "reference_geometry.cylinders": "parameters.cylinder_count",
        "reference_geometry.bore_mm": "parameters.bore_mm",
        "reference_geometry.stroke_mm": "parameters.stroke_mm",
        "reference_geometry.displacement_cm3": "derived_parameters.displacement_from_bore_stroke_cm3",
        "reference_geometry.compression_ratio": "parameters.compression_ratio",
        "reference_geometry.rod_length_mm": "fixture_assumptions.connecting_rod_length_mm",
        "engine_geometry_and_project.cylinder_count": "parameters.cylinder_count",
        "engine_geometry_and_project.bore_mm": "parameters.bore_mm",
        "engine_geometry_and_project.stroke_mm": "parameters.stroke_mm",
        "engine_geometry_and_project.rod_length_mm": "fixture_assumptions.connecting_rod_length_mm",
        "engine_geometry_and_project.compression_ratio": "parameters.compression_ratio",
        "engine_geometry_and_project.crankcase_volume_bdc_cm3": "fixture_assumptions.crankcase_volume_bdc_cm3",
        "engine_geometry_and_project.ports[0]": "fixture_assumptions.exhaust_port_top_mm|exhaust_port_height_mm|exhaust_port_width_mm",
        "engine_geometry_and_project.ports[1:3]": "fixture_assumptions.transfer_port_top_mm|transfer_port_height_mm|transfer_port_width_mm",
        "engine_geometry_and_project.intake": "fixture_assumptions.intake_port_top_mm|intake_port_height_mm|intake_port_width_mm|intake_piston_skirt_mm",
        "engine_geometry_and_project.ducts.intake[0]": "fixture_assumptions.intake_duct_length_mm|intake_duct_diameter_mm",
        "engine_geometry_and_project.ducts.exhaust[0]": "fixture_assumptions.exhaust_header_length_mm|exhaust_header_diameter_mm",
        "engine_geometry_and_project.ducts.exhaust[1]": "fixture_assumptions.exhaust_tail_length_mm|exhaust_tail_diameter_mm",
        "cylinder.cylinders": "parameters.cylinder_count",
        "cylinder.swept_volume_cm3": "derived_parameters.swept_volume_per_cylinder_cm3",
        "cylinder.clearance_volume_cm3_conditional": "derived_parameters.clearance_volume_cm3_if_geometric_ratio",
        "crank_slider.crank_radius_mm": "derived_parameters.crank_radius_mm",
        "crank_slider.rod_length_mm": "fixture_assumptions.connecting_rod_length_mm",
        "crank_slider.offset_mm": "fixture_assumptions.crank_offset_mm",
        "crankcase.volume_at_bdc_cm3": "fixture_assumptions.crankcase_volume_bdc_cm3",
        "intake.carburetor_reference": "parameters.carburetor",
        "intake.mode": "fixture_assumptions.intake_model_mode",
        "transfer.two_rectangular_paths": "fixture_assumptions.transfer_port_top_mm|transfer_port_height_mm|transfer_port_width_mm",
        "exhaust.documented_description": "parameters.exhaust_description",
        "exhaust.modeled_path": "fixture_assumptions.exhaust_header_length_mm|exhaust_header_diameter_mm|exhaust_tail_length_mm|exhaust_tail_diameter_mm",
        "exhaust.total_lumped_duct_length_mm": "fixture_assumptions.exhaust_header_length_mm|exhaust_tail_length_mm",
        "exhaust.duct_area_m2": "fixture_assumptions.exhaust_header_diameter_mm|exhaust_tail_diameter_mm",
        "combustion.event_start_deg": "fixture_assumptions.p7_start_angle_deg",
        "combustion.duration_deg": "fixture_assumptions.p7_duration_deg",
        "combustion.heat_per_bookkeeping_burned_kg_J": "fixture_assumptions.p7_heat_value_J_kg",
        "thermodynamics.R_J_kgK": "fixture_assumptions.thermo_R_J_kgK",
        "thermodynamics.gamma": "fixture_assumptions.thermo_gamma",
        "thermodynamics.eos": "fixture_assumptions.thermodynamic_model",
        "boundaries.ambient_pressure_Pa": "fixture_assumptions.initial_pressure_Pa",
        "boundaries.ambient_temperature_K": "fixture_assumptions.initial_intake_temperature_K",
        "boundaries.atmosphere_species": "fixture_assumptions.atmosphere_species_mass_fractions",
        "boundaries.initial_states_pty[0].pressure_Pa": "fixture_assumptions.initial_pressure_Pa",
        "boundaries.initial_states_pty[0].temperature_K": "fixture_assumptions.initial_intake_temperature_K",
        "boundaries.initial_states_pty[0].fresh_fraction": "fixture_assumptions.initial_fresh_fraction_by_cv[0]",
        "boundaries.initial_states_pty[1].pressure_Pa": "fixture_assumptions.initial_crankcase_pressure_Pa",
        "boundaries.initial_states_pty[1].temperature_K": "fixture_assumptions.initial_crankcase_temperature_K",
        "boundaries.initial_states_pty[1].fresh_fraction": "fixture_assumptions.initial_fresh_fraction_by_cv[1]",
        "boundaries.initial_states_pty[2].pressure_Pa": "fixture_assumptions.initial_cylinder_pressure_Pa",
        "boundaries.initial_states_pty[2].temperature_K": "fixture_assumptions.initial_cylinder_temperature_K",
        "boundaries.initial_states_pty[2].fresh_fraction": "fixture_assumptions.initial_fresh_fraction_by_cv[2]",
        "boundaries.initial_states_pty[3].pressure_Pa": "fixture_assumptions.initial_pressure_Pa",
        "boundaries.initial_states_pty[3].temperature_K": "fixture_assumptions.initial_exhaust_temperature_K",
        "boundaries.initial_states_pty[3].fresh_fraction": "fixture_assumptions.initial_fresh_fraction_by_cv[3]",
        "boundaries.reservoir_states_pty[0].pressure_Pa": "fixture_assumptions.initial_pressure_Pa",
        "boundaries.reservoir_states_pty[0].temperature_K": "fixture_assumptions.initial_intake_temperature_K",
        "boundaries.reservoir_states_pty[0].fresh_fraction": "fixture_assumptions.atmospheric_fresh_marker_fraction",
        "boundaries.reservoir_states_pty[1].pressure_Pa": "fixture_assumptions.initial_pressure_Pa",
        "boundaries.reservoir_states_pty[1].temperature_K": "fixture_assumptions.initial_exhaust_temperature_K",
        "boundaries.reservoir_states_pty[1].fresh_fraction": "fixture_assumptions.exhaust_reservoir_fresh_marker_fraction",
        "solver.integrator": "existing motorsim.adaptive.Stepper RK4 implementation",
        "solver.profile": "existing motorsim.adaptive.PROFILES['B']",
        "solver.maximum_cycles": "existing motorsim.adaptive.run_adaptive fixed 30-cycle limit",
        "solver.CFL": "NOT_APPLICABLE_ZERO_D",
        "solver.restart_api": "NOT_SUPPORTED_BY_EXISTING_0D_APPLICATION_RUNNER",
        "sensitivity_plan.parameters": "fixture_assumptions.sensitivity_rod_scale|sensitivity_exhaust_length_scale",
    }
    config["provenance_sha256"] = sha256(canonical_json(manifest).encode()).hexdigest()
    validate_fixture_config(config, manifest)
    return config


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)


def validate_provenance(manifest: dict) -> None:
    if manifest.get("reference_case_id") != REFERENCE_ID or manifest.get("fixture_id") != FIXTURE_ID:
        raise ValueError("reference/fixture identity mismatch")
    for section in ("parameters", "derived_parameters", "fixture_assumptions"):
        entries = manifest.get(section)
        if not isinstance(entries, dict) or not entries:
            raise ValueError(f"provenance section missing: {section}")
        for name, row in entries.items():
            required = {"value", "units", "status", "source", "source_location", "notes"}
            if not isinstance(row, dict) or not required <= row.keys():
                raise ValueError(f"incomplete provenance: {section}.{name}")
            if row["status"] not in {DOCUMENTED, DERIVED, SYNTHETIC, UNKNOWN}:
                raise ValueError(f"invalid provenance status: {section}.{name}")
            if row["status"] == UNKNOWN and row["value"] is not None:
                raise ValueError(f"unknown parameter has a value: {name}")
            if row["status"] == DOCUMENTED and (not row["source"] or not row["source_location"]):
                raise ValueError(f"documented value lacks source: {name}")
            if row["status"] == SYNTHETIC:
                extra = {"reason", "expected_sensitivity", "strongly_affects_results", "conceptual_origin"}
                if not extra <= row.keys():
                    raise ValueError(f"synthetic assumption incomplete: {name}")
    if manifest.get("experimental_validation") != "NOT_PERFORMED" or manifest.get("predictive_validation") != "NOT_CLAIMED":
        raise ValueError("reference case cannot claim validation")
    if any(claim in canonical_json(manifest) for claim in ("P9_PASS", "EXPERIMENTALLY_VALIDATED", "PREDICTIVELY_VALIDATED")):
        # Prohibited labels appear in the explicit guard list by design.  They
        # are not status claims; reject only if accidentally used as a value.
        for section in ("parameters", "derived_parameters", "fixture_assumptions"):
            if any(row.get("value") in CLAIMS_PROHIBITED for row in manifest[section].values()):
                raise ValueError("prohibited validation claim found as parameter value")


def validate_fixture_config(config: dict, manifest: dict | None = None) -> None:
    required = {"engine_geometry_and_project", "cylinder", "crank_slider", "crankcase",
                "intake", "transfer", "exhaust", "combustion", "thermodynamics",
                "boundaries", "solver", "sensitivity_plan", "provenance_parameter_map"}
    if not required <= config.keys():
        raise ValueError(f"fixture sections missing: {sorted(required-config.keys())}")
    if config.get("fixture_id") != FIXTURE_ID or config.get("kind") != "synthetic_model_fixture":
        raise ValueError("fixture identity or kind is invalid")
    config["engine_geometry_and_project"]
    Project.from_dict(config["engine_geometry_and_project"]).validate()
    if manifest is not None:
        validate_provenance(manifest)
        for path, expression in config["provenance_parameter_map"].items():
            previous_section = None
            for reference in str(expression).split("|"):
                if reference in {"existing motorsim.adaptive.Stepper RK4 implementation",
                                 "existing motorsim.adaptive.PROFILES['B']",
                                 "existing motorsim.adaptive.run_adaptive fixed 30-cycle limit",
                                 "NOT_APPLICABLE_ZERO_D",
                                 "NOT_SUPPORTED_BY_EXISTING_0D_APPLICATION_RUNNER"}:
                    continue
                if "." not in reference:
                    if previous_section is None:
                        raise ValueError(f"fixture parameter lacks provenance: {path}")
                    section, key = previous_section, reference
                else:
                    section, key = reference.split(".", 1)
                if section not in {"parameters", "derived_parameters", "fixture_assumptions"}:
                    raise ValueError(f"unknown provenance section for {path}: {section}")
                indexed = key.endswith("]") and "[" in key
                base_key = key[:key.rfind("[")] if indexed else key
                if base_key not in manifest[section]:
                    raise ValueError(f"unknown provenance key for {path}: {reference}")
                if indexed:
                    try:
                        index = int(key[key.rfind("[")+1:-1])
                    except ValueError as exc:
                        raise ValueError(f"invalid provenance index for {path}: {reference}") from exc
                    value = manifest[section][base_key].get("value")
                    if not isinstance(value, list) or not 0 <= index < len(value):
                        raise ValueError(f"provenance index out of range for {path}: {reference}")
                previous_section = section
    if (config["solver"].get("integrator") != "existing adaptive RK4 (two-half-step error estimate)"
            or config["solver"].get("profile") != "B"
            or config["solver"].get("CFL") != "NOT_APPLICABLE_ZERO_D"):
        raise ValueError("fixture solver no longer describes the existing 0D application path")
    if config["claims"].get("p9_status_effect") != "NONE":
        raise ValueError("KT100 fixture cannot modify P9")
