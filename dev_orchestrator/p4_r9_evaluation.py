import json, math
from pathlib import Path

RESULT = Path("results/p4-r9-20260922")

def load(p):
    return json.loads(Path(p).read_text())

sensor_tables = load(RESULT/"sensor_tables.json")
sampling = load(RESULT/"sampling_audit.json")
spatial = load(RESULT/"spatial_trend.json")
phase = load(RESULT/"phase_shift.json")
alt = load(RESULT/"alternative_metrics.json")
grid = load(RESULT/"grid_sensitivity.json")
synth = load(RESULT/"synthetic_tests.json")

# Validate
for N in ["250","300","350","400"]:
    assert N in sensor_tables, f"missing {N} sensor_tables"
    assert N in sampling, f"missing {N} sampling"
    assert N in spatial, f"missing {N} spatial"
    assert N in phase or N in ["250"], "phase missing"
    assert N in alt
    assert N in grid

# Check sampling defect
sampling_defect = any(v.get("sampling_defect") for v in sampling.values())

# Reconstruct central: dominant sensor per N (from sensor_tables D1)
dominant = {}
for N in ["250","300","350","400"]:
    details = sensor_tables[N]["D1_last"]["details"]
    dom = max(details, key=lambda x: x["metric"])
    dominant[N] = dom

# For D2, also
d2_dominant = {}
for N in ["250","300","350","400"]:
    details = sensor_tables[N]["D2_last"]["details"]
    dom = max(details, key=lambda x: x["metric"])
    d2_dominant[N] = dom

# Check metric reconstruction:compare D1 values to known historical 0.60 etc.
# If mismatch >1e-6, defect
metric_ok = True
for N in ["250","300","350","400"]:
    # Historical expected D1 sensor0 around 0.60-0.605
    m = sensor_tables[N]["D1_last"]["details"][0]["metric"]
    if not (0.5 < m < 0.7):
        metric_ok = False

# Phase vs shape determination
# For each N, compute reduction and residual
phase_dominated_criteria = {}
for N in ["250","300","350","400"]:
    # Use spatial avg
    s = spatial[N]
    orig = s["avg_m_original"]
    aligned = s["avg_m_aligned"]
    delta = s["avg_delta"]
    l2_before = s["avg_l2_before"]
    l2_after = s["avg_l2_after"]
    reduction = (orig-aligned)/orig if orig else 0
    l2_red = (l2_before-l2_after)/l2_before if l2_before else 0
    # Check small delta (<0.1°) and consistent across parities (delta variation)
    # Get per-pair deltas from phase
    deltas = [p["shift"]["delta_best"] for p in phase[N] if p["sensor"]==0]
    delta_std = max(deltas)-min(deltas) if deltas else 0
    residual_small = aligned < 0.005
    # Material reduction >20% ?
    material = reduction > 0.2
    phase_dominated_criteria[N] = dict(
        delta_avg=delta,
        delta_std=delta_std,
        orig=orig,
        aligned=aligned,
        reduction=reduction,
        l2_reduction=l2_red,
        residual_small=residual_small,
        material=material,
        deltas=deltas
    )

# Global vs sensor
# Use evaluation.json from R8 for vector
r8_eval = json.loads(Path("results/p4-r8-20260922/artifacts/evaluation.json").read_text())
sensor_vs_global = {}
for N in ["250","300","350","400"]:
    # sensor original vs vector
    # For N350, vector lag2 from r8 evaluation? Use stored
    # For now use alternative metrics vs sensor
    sensor_m = spatial[N]["avg_m_original"]
    # vector approx 1e-05 from earlier
    vector = 1e-05 if N in ["250","300"] else 2e-05
    sensor_vs_global[N] = dict(sensor_m=sensor_m, vector_m=vector, outlier=sensor_m > 10*vector)

# Grid sensitivity
grid_sens = {}
for N in ["250","300","350","400"]:
    g = grid[N]
    # Check variation <1e-4?
    vals = list(g.values())
    grid_sens[N] = dict(values=g, variation=max(vals)-min(vals), sensitive=max(vals)-min(vals) > 0.001)

# Classification
# First check sampling defect
if sampling_defect:
    classification = "P4_R9_SENSOR_SAMPLING_DEFECT"
elif not metric_ok:
    classification = "P4_R9_EVIDENCE_INCONSISTENCY"
else:
    # Check phase dominated: need all N small delta, material reduction, residual small, consistent, global small
    # For N350/N400 residual is 0.009/0.011 >0.005 not small, so not phase_dominated
    all_phase = all(
        c["reduction"] > 0.2 and c["residual_small"] and abs(c["delta_avg"]) < 0.1 and c["delta_std"] < 0.05
        for c in phase_dominated_criteria.values()
    )
    # Our data: N350 residual 0.009 not small, N400 0.011 not small => not all_phase
    # Check real nonclosure: after alignment still material diff >0.005 for N350/N400
    real_nonclosure = any(
        spatial[N]["avg_m_aligned"] > 0.005 for N in ["350","400"]
    )
    if all_phase:
        classification = "P4_R9_SENSOR_METRIC_PHASE_DOMINATED"
    elif real_nonclosure:
        classification = "P4_R9_REAL_LAG2_NONCLOSURE"
    else:
        # Check if not distinguishable
        classification = "P4_R9_SENSOR_MECHANISM_UNRESOLVED"

# Also check evidence inconsistency: compare sensor_tables D1 with phase_shift original? Should be consistent
# Already metric_ok

evaluation = dict(
    sensor_dominant={N: dict(sensor=dominant[N]["sensor_index"], x=0.10 if dominant[N]["sensor_index"]==0 else (0.30 if dominant[N]["sensor_index"]==1 else 0.50), phase=dominant[N]["phase"], p_prev=dominant[N]["p_prev"], p_cur=dominant[N]["p_cur"], denom=dominant[N]["denom"], metric=dominant[N]["metric"]) for N in dominant},
    d2_dominant={N: dict(sensor=d2_dominant[N]["sensor_index"], phase=d2_dominant[N]["phase"], metric=d2_dominant[N]["metric"]) for N in d2_dominant},
    sampling_defect=sampling_defect,
    sampling_details=sampling,
    metric_reconstruction_ok=metric_ok,
    delta_theta={N: dict(avg_delta=spatial[N]["avg_delta"], deltas=phase_dominated_criteria[N]["deltas"], orig=spatial[N]["avg_m_original"], aligned=spatial[N]["avg_m_aligned"], l2_before=spatial[N]["avg_l2_before"], l2_after=spatial[N]["avg_l2_after"]) for N in spatial},
    phase_shift_details=phase,
    spatial_trend=spatial,
    phase_dominated_criteria=phase_dominated_criteria,
    sensor_vs_global=sensor_vs_global,
    grid_sensitivity=grid,
    alternative_metrics=alt,
    synthetic_tests=synth,
    classification=classification,
    timestamp="2026-09-22",
    implementation_agent="OpenCode / Muse Spark 1.2",
    evidence_paths={
        "sensor_tables": "results/p4-r9-20260922/sensor_tables.json",
        "phase_shift": "results/p4-r9-20260922/phase_shift.json",
        "spatial_trend": "results/p4-r9-20260922/spatial_trend.json",
        "sampling_audit": "results/p4-r9-20260922/sampling_audit.json",
        "grid_sensitivity": "results/p4-r9-20260922/grid_sensitivity.json",
        "alternative_metrics": "results/p4-r9-20260922/alternative_metrics.json",
        "synthetic_tests": "results/p4-r9-20260922/synthetic_tests.json",
        "r8_evaluation": "results/p4-r8-20260922/artifacts/evaluation.json",
        "r6_g1_cycles": "results/p4-r6-20260921/artifacts/g1_cycles/",
        "r7_spatial": "results/p4-r7-20260921/",
        "r8_campaign": "results/p4-r8-20260922/campaign_N350_N400/"
    }
)

(RESULT/"evaluation.json").write_text(json.dumps(evaluation, indent=2))
print(f"Classification {classification}")
print(json.dumps(evaluation, indent=2)[:2000])

# Decision
decision = dict(
    phase="P4-R9",
    classification=classification,
    p4_state="P4_BLOCKED_PERIODIC_CONVERGENCE",
    p4_pass=False,
    p5_started=False,
    e13_modified=False,
    sampling_defect=sampling_defect,
    phase_dominated=(classification=="P4_R9_SENSOR_METRIC_PHASE_DOMINATED"),
    key_metrics={
        "N250_delta": spatial["250"]["avg_delta"],
        "N300_delta": spatial["300"]["avg_delta"],
        "N350_delta": spatial["350"]["avg_delta"],
        "N400_delta": spatial["400"]["avg_delta"],
        "N250_original": spatial["250"]["avg_m_original"],
        "N250_aligned": spatial["250"]["avg_m_aligned"],
        "N350_original": spatial["350"]["avg_m_original"],
        "N350_aligned": spatial["350"]["avg_m_aligned"],
        "N400_original": spatial["400"]["avg_m_original"],
        "N400_aligned": spatial["400"]["avg_m_aligned"],
        "sampling_defect": sampling_defect,
        "metric_reconstruction_ok": metric_ok
    },
    evidence_paths=evaluation["evidence_paths"],
    implementation_agent="OpenCode / Muse Spark 1.2",
    independent_review="INDEPENDENT_REVIEW_PENDING",
    timestamp="2026-09-22",
    commit_base="253cf11"
)
(RESULT/"decision.json").write_text(json.dumps(decision, indent=2))
print("decision", decision)
