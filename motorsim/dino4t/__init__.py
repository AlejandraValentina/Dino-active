"""Dino 4T: single-cylinder four-stroke SI engine simulator, 0D cylinder + 1D ducts.

Independent of the Dino 2T solver; it reuses only cycle-agnostic kernels
(``motorsim.gas1d.mesh`` geometry, ``motorsim.kinematics.piston_position``)
and uses the frozen 2T Riemann kernels solely as verification oracles.
Model documentation: docs/dino4t/model_reference.md.
"""

MODEL_ID = "DINO4T_FOUNDATION_V1"
MODELS = {
    "thermodynamics": "THERMALLY_PERFECT_NASA7_8_SPECIES_V1",
    "cylinder": "SINGLE_ZONE_0D_V1",
    "combustion": "WIEBE_SINGLE_ZONE_V1",
    "heat_transfer": "WOSCHNI_1967",
    "friction": "CHEN_FLYNN",
    "valve_boundary": "QUASI_STEADY_RESTRICTION_V1",
    "duct": "QUASI_1D_HLLC_MUSCL_MULTISPECIES_V1",
    "time_integration": "SSPRK2_EVENT_ALIGNED_V1",
}
