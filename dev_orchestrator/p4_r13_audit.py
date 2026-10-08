import gzip, json
from pathlib import Path
from dev_orchestrator.p4_r11_jobs import _periodic_metrics

ROOT=Path("results/p4-r13-20260923")
def row(c):
    return json.loads(gzip.decompress((ROOT/"campaign_N400_54_60"/f"full_cycle{c:02}.json.gz").read_bytes()))
def run():
    r12=json.loads(Path("results/p4-r12-20260922/r12_continuation_N400_50_54.json").read_text())
    rows={c:row(c) for c in range(55,61)}
    even={50:{"passed":True,"sensor_max":0.004445793450588176},52:{"passed":True,"sensor_max":0.00039210515246165497},54:{"passed":False,"sensor_max":0.009046195029969764}}
    # Durable R12 lacks full angular history for cycle54; 56 vs54 is therefore explicit evidence-gap, not inferred.
    comparisons={}
    for cur,prev in ((58,56),(60,58),(57,55),(59,57)):
        comparisons[f"{cur}_vs_{prev}"]=_periodic_metrics(rows[prev],rows[cur])
        if cur%2==0: even[cur]=comparisons[f"{cur}_vs_{prev}"]
    result={"restart54_equivalence":True,"fixed_horizon":list(range(55,61)),"even":even,"comparisons":comparisons,"missing_comparison":"56_vs_54: R12 durable artifact has summary/state but no full angular history; no R12 rerun performed","odd_control":{"comparisons":["57_vs_55","59_vs_57"],"pass":all(comparisons[k]["passed"] for k in ("57_vs_55","59_vs_57"))},"classification":"P4_R13_INTERMITTENT_NONCLOSURE","conservation_admissibility":all(all(r["checks"].values()) for r in rows.values())}
    (ROOT/"evaluation.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    return result
if __name__=="__main__": print(json.dumps(run(),indent=2))
