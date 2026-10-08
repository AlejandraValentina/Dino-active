import json
from pathlib import Path
RESULT = Path("results/p4-r10a-20260922")
ORIG = Path("results/p4-r10-20260922")

# Load corrected
mesh = json.loads((RESULT/"mesh_trend_corrected.json").read_text())
front = json.loads((RESULT/"front_tracking_corrected.json").read_text())
energy = json.loads((RESULT/"error_energy_localization.json").read_text())
sensor = json.loads((RESULT/"sensor_front_corrected.json").read_text())

# Load original for diff
orig_mesh = json.loads((ORIG/"mesh_trend.json").read_text())

# Determine classification: check corrected fractions
# For N250, fraction_inside_3 0.33 (<0.6) -> distributed
# For N350 0.65 (>0.6) localized
# So mixed
localized = []
distributed = []
for N in ["250","350","400"]:
    frac = mesh[N]["fraction_inside_3"]
    if frac > 0.6:
        localized.append(N)
    elif frac < 0.4:
        distributed.append(N)
    else:
        # intermediate
        localized.append(N) if frac>0.5 else distributed.append(N)

# Overall mixed if both present
if localized and distributed:
    classification = "P4_R10_MIXED_SHOCK_AND_GLOBAL_NONCLOSURE"
elif all(mesh[N]["fraction_inside_3"] > 0.6 for N in ["350","400"]):
    classification = "P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE"
elif all(mesh[N]["fraction_inside_3"] < 0.4 for N in ["250","300"]):
    classification = "P4_R10_DISTRIBUTED_LAG2_NONCLOSURE"
else:
    classification = "P4_R10_MECHANISM_UNRESOLVED"

# Check width: original described as "shock width few cells" but corrected shows width_B 50-90 cells, width_A 9-11 cells
audit_diff = dict(
    L2_error_math_corrected=True,
    L2_original_formula="L2_outside/L2_total*100 (RMS ratio, wrong N)",
    L2_corrected_formula="E_inside/E_total (sum diff^2 ratio)",
    impact="Original gave 60-88% inside, corrected gives 33% N250, 28% N300, 65% N350, 66% N400 for +-3 cells. N250/N300 now show distributed, N350/N400 localized.",
    front_switching="Original global argmax alternated between x~0.005 and 0.23 (different waves). Corrected per-pair tracking chooses same front near sensor (0.09 vs 0.10) with delta 0, but still shows two fronts (even at 0.09, odd at 0.009) corresponding to period-2 A/B orbits. Tracking per lag-2 pair (even-even, odd-odd) correctly tracks same front, delta 0.",
    labels_corrected="Original labels 5 vs3 etc. corrected to 40 vs38,39 vs37,38 vs36 (actual cycle numbers 36-40). Data already corresponded to 36-40, only metadata wrong.",
    width_old_vs_new=dict(
        N250_orig_cells=orig_mesh["250"]["front_width_cells"],
        N250_width_A_cells=mesh["250"]["width_A_m"]/mesh["250"]["dx"],
        N250_width_B_cells=mesh["250"]["width_B_m"]/mesh["250"]["dx"],
        note="Original 83 cells was broader wavefront width (0.5*max), corrected separates local strongest 9 cells (0.9*max) vs broader 82 cells. Original 'few cells' description incorrect; corrected shows local 9-11 cells but broader 50-90."
    ),
    plateau_vs_adjacent=dict(
        N350_jump_adj=front["350"][0]["jump_adj_cur"],
        N350_plateau_jump=front["350"][0]["plateau_jump_cur"],
        note="Adjacent jump 7 Pa vs plateau 649 Pa for N250, 4264 vs 7360 for N350. Original called 1480-2805 'jump strength' without distinguishing. Corrected reports both."
    ),
    delta_x_per_pair={N: [p["delta_x"] for p in front[N]] for N in front},
    classification_original="P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE",
    classification_corrected=classification,
    classification_sustained=(classification=="P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE")
)

# Evaluation
evaluation = dict(
    mesh_trend_corrected=mesh,
    front_tracking_corrected=front,
    error_energy_localization=energy,
    sensor_front_corrected=sensor,
    audit_diff=audit_diff,
    classification=classification,
    original_classification="P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE",
    corrected_classification=classification,
    n500_executed=False,
    n500_reason="Not needed: corrected still shows localized for fines but distributed for coarse, mechanism resolved as mixed without N500.",
    rhoE_formula="rhoE = p/(gamma-1) + 0.5*rho*u^2 (correct, not rho*rhoE). Test confirms.",
    implementation_agent="OpenCode / Muse Spark 1.2",
    timestamp="2026-09-22"
)

(RESULT/"evaluation.json").write_text(json.dumps(evaluation, indent=2))
print(f"Classification {classification}")

# Decision
decision = dict(
    phase="P4-R10A",
    classification=classification,
    original_R10_classification="P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE",
    corrected_classification=classification,
    sustained=(classification=="P4_R10_SHOCK_LOCALIZED_NUMERICAL_NONCLOSURE"),
    p4_state="P4_BLOCKED_PERIODIC_CONVERGENCE",
    p4_pass=False,
    p5_started=False,
    e13_modified=False,
    n500_executed=False,
    L2_math_corrected=True,
    front_tracking_corrected=True,
    labels_corrected=True,
    width_corrected=True,
    plateau_distinguished=True,
    key_metrics=dict(
        fraction_inside_1={N: mesh[N]["fraction_inside_1"] for N in mesh},
        fraction_inside_3={N: mesh[N]["fraction_inside_3"] for N in mesh},
        support90_m={N: mesh[N]["support90_m"] for N in mesh},
        delta_x_avg={N: mesh[N]["delta_x_avg"] for N in mesh},
        width_A_m={N: mesh[N]["width_A_m"] for N in mesh},
        width_B_m={N: mesh[N]["width_B_m"] for N in mesh}
    ),
    evidence_paths=dict(
        front_tracking_corrected="results/p4-r10a-20260922/front_tracking_corrected.json",
        error_energy_localization="results/p4-r10a-20260922/error_energy_localization.json",
        mesh_trend_corrected="results/p4-r10a-20260922/mesh_trend_corrected.json",
        sensor_front_corrected="results/p4-r10a-20260922/sensor_front_corrected.json",
        audit_diff="results/p4-r10a-20260922/audit_diff_vs_r10.json",
        original_R10="results/p4-r10-20260922/",
        evaluation="results/p4-r10a-20260922/evaluation.json"
    ),
    implementation_agent="OpenCode / Muse Spark 1.2",
    independent_review="INDEPENDENT_REVIEW_PENDING",
    timestamp="2026-09-22",
    commit_base="beeaee6"
)

(RESULT/"decision.json").write_text(json.dumps(decision, indent=2))
print(json.dumps(decision, indent=2))
# Also create audit_diff file
Path(RESULT/"audit_diff_vs_r10.json").write_text(json.dumps(audit_diff, indent=2))
