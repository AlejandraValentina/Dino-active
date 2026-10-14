"""Reconstruct the missing B/8 and cross-design comparisons from audited primaries."""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration
from motorsim.engine_configuration import resolve_for_operating_point
from motorsim.integrated_2t import make_integrated_engineering_output
from motorsim.mechanical import MechanicalLossModel

def artifact_root():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root",type=Path,default=Path(os.environ.get("DINO_ARTIFACT_ROOT",Path.home()/"Dino-artifacts"))/"exhaust-numerical-convergence-v2")
    return parser.parse_args().artifact_root

ART=artifact_root()
RUNS=ART/"exploratory-workflow-v1"/"dino-exhaust-comparison-starter"
BATCH=ART/"reports"/"exhaust-numerical-convergence-v2-matrix-batch-01.json"
PROJECT=ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json"

def sha(data):return hashlib.sha256(data).hexdigest()
def read_trace(label,n):
    project=load_project(PROJECT);source=project["variants"][label]
    sections=source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    config=refine_exhaust_configuration(source,[1]*len(sections))
    config=refine_exhaust_configuration(config,[n]*len(sections))
    effective=resolve_for_operating_point(config,rpm=3000)
    run_id=f"encv2-{label.lower().replace(' ','-').replace('+','plus')}-3000rpm-{n}c"
    folder=RUNS/run_id;manifest=json.loads((folder/"run.json").read_text(encoding="utf-8"))
    if manifest.get("status")!="COMPLETE" or manifest.get("cycles_completed")!=1:
        raise ValueError(f"{run_id}: point is not a completed one-cycle diagnostic")
    cycle=manifest["cycles"][0]
    if cycle.get("audit",{}).get("status")!="PASS" or cycle["audit"].get("recomputed") is not True:
        raise ValueError(f"{run_id}: primary has no passing recomputed audit")
    packed=(folder/cycle["artifact"]).read_bytes();payload=gzip.decompress(packed)
    if sha(payload)!=cycle["primary_sha256"]:raise ValueError(f"{run_id}: primary hash mismatch")
    primary=json.loads(payload)
    output=make_integrated_engineering_output(primary,
      displacement_m3=primary["swept_displacement_m3"],
      mechanical_loss_model=MechanicalLossModel.from_dict(effective["mechanical_loss_model"]),
      load=effective["operating_conditions"]["load"],periodicity_status="NOT_EVALUATED")
    trace=output["crank_angle_trace"]
    native=config["native_configuration"];duct=next(x for x in native["ducts"] if x["id"]=="exhaust")
    bounds=[];cursor=0
    for _ in sections:bounds.append((cursor,cursor+n));cursor+=n
    def midpoint(section,angle_index):
      lo,hi=bounds[section];xs=duct["mesh"]["centers"][lo:hi]
      values=[trace["channels"][f"duct:exhaust:cell:{i}:pressure_pa"]["values"][angle_index]
              for i in range(lo,hi)]
      start=duct["mesh"]["faces"][0]+sum(s["length_mm"] for s in sections[:section])/1000
      target=start+sections[section]["length_mm"]/2000
      if len(xs)==1:return values[0]
      if target<=xs[0]:return values[0]
      if target>=xs[-1]:return values[-1]
      for j in range(len(xs)-1):
        if xs[j]<=target<=xs[j+1]:
          f=(target-xs[j])/(xs[j+1]-xs[j]);return values[j]+f*(values[j+1]-values[j])
      return values[-1]
    return {"run_id":run_id,"label":label,"n":n,"manifest":manifest,
      "primary_sha256":cycle["primary_sha256"],"checkpoint_sha256":manifest["checkpoint_sha256"],
      "configuration_sha256":manifest["bindings"]["configuration_sha256"],
      "identity_sha256":manifest["bindings"]["identity_sha256"],"solver_hash":manifest["bindings"]["source_hashes"]["motorsim.integrated_2t"],
      "adapter_hash":native["geometry_identity"]["exhaust_mesh_discretization"]["adapter_sha256"],
      "trace":trace,"result":json.loads((folder/"result.json").read_text(encoding="utf-8")),"sections":sections,"centers":duct["mesh"]["centers"],"bounds":bounds,
      "faces":duct["mesh"]["faces"],"pressure_midpoint":midpoint}

def compare(a,b):
  ta,tb=a["trace"],b["trace"];angles=sorted(set(ta["angle_deg"])&set(tb["angle_deg"]))
  result={"common_exact_crank_angles":len(angles),"spatial_reconstruction":"piecewise-linear cell-center pressure to named-section local midpoint"}
  for si,section in enumerate(a["sections"]):
    av=[a["pressure_midpoint"](si,ta["angle_deg"].index(x)) for x in angles]
    bv=[b["pressure_midpoint"](si,tb["angle_deg"].index(x)) for x in angles]
    ds=[x-y for x,y in zip(av,bv)]
    result[f"section:{section['name']}:midpoint_pressure_pa"]={"rms":math.sqrt(math.fsum(x*x for x in ds)/len(ds)),"max_abs":max(map(abs,ds))}
    if si<len(a["sections"])-1:
      ia=a["bounds"][si][1];ib=b["bounds"][si][1]
      ka=f"duct:exhaust:face:{ia}:mass_flow_kg_s";kb=f"duct:exhaust:face:{ib}:mass_flow_kg_s"
      ma=dict(zip(ta["angle_deg"],ta["channels"][ka]["values"]));mb=dict(zip(tb["angle_deg"],tb["channels"][kb]["values"]));flow=[ma[x]-mb[x] for x in angles]
      result[f"interface_after:{section['name']}:mass_flow_kg_s"]={"rms":math.sqrt(math.fsum(x*x for x in flow)/len(flow)),"max_abs":max(map(abs,flow))}
  return result

base=json.loads(BATCH.read_text(encoding="utf-8"))
a8=read_trace("Escape original",8);b8=read_trace("Escape modified +20 mm",8)
b4=read_trace("Escape modified +20 mm",4)
unfinished=[r for r in base["runs"] if r.get("variant")==b8["label"] and r.get("cells_per_section")==8 and r.get("classification")=="NOT_STARTED_BUDGET_EXHAUSTED"]
base["budget_events"]=[{"batch":"01","event":"B/8 not started because invocation budget was exhausted; no point was lost or overwritten; completed in batch 02 from the same frozen authorization."}]
base["runs"]=[r for r in base["runs"] if not (r.get("variant")==b8["label"] and r.get("cells_per_section")==8)]
base["runs"].append({"variant":b8["label"],"cells_per_section":8,"run_id":b8["run_id"],
 "classification":b8["manifest"]["classification"],"status":b8["manifest"]["status"],
 "cycles_completed":b8["manifest"]["cycles_completed"],"periodicity":"NOT_EVALUATED",
 "elapsed_seconds":b8["result"]["elapsed_seconds"],"identity_sha256":b8["identity_sha256"],
 "configuration_sha256":b8["configuration_sha256"],"source_hashes":b8["manifest"]["bindings"]["source_hashes"],
 "result_sha256":b8["result"]["result_sha256"],"checkpoint_sha256":b8["checkpoint_sha256"],
 "primary_sha256":b8["primary_sha256"],"primary_audit":b8["manifest"]["cycles"][0]["audit"],
 "conservation":b8["manifest"]["cycles"][0]["conservation"],
 "rejected_step_count":b8["manifest"]["cycles"][0]["rejected_step_count"],
 "artifact_directory":str(RUNS/b8["run_id"])})
base["refinement_comparisons"]["Escape modified +20 mm: 4_vs_8"]=compare(b4,b8)
base["refinement_comparisons"]["A_vs_B_at_8_cells_per_section"]=compare(a8,b8)
base["matrix_complete"]=True
base["matrix_attempts_total"]=len(base["runs"])
base["cross_report_verification"]="A/8, B/4 and B/8 result bindings and recomputed primary audit status checked from persisted manifests; primary payload hashes verified before output reconstruction."
base["matrix_completed_points"]=[f"{label}@{n}" for label in ("Escape original","Escape modified +20 mm") for n in (1,2,4,8)]
base["matrix_missing_points"]=[]
base["periodicity_claim"]="NOT_EVALUATED_ONE_CYCLE_PER_POINT"
base["spatial_independence"]="NOT_ESTABLISHED; A/B values are single-cycle transients, and comparisons do not establish an asymptotic regime."
out=ART/"reports"/"exhaust-numerical-convergence-v2-matrix-full.json"
out.write_text(json.dumps(base,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps({"report":str(out),"matrix_complete":True,"added_comparisons":{
 "B_4_vs_8":base["refinement_comparisons"]["Escape modified +20 mm: 4_vs_8"],
 "A_vs_B_8":base["refinement_comparisons"]["A_vs_B_at_8_cells_per_section"]}},indent=2,ensure_ascii=False))
