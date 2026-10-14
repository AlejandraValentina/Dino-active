"""Isolated eight-point, one-cycle 1/2/4/8 exhaust mesh sensitivity diagnostics."""
from __future__ import annotations
import argparse,gzip,hashlib,json,math,os,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
PROJECT=ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json"
from motorsim.engine_configuration import resolve_for_operating_point,identity
from motorsim.engine_project import load_project
from motorsim.engine_variants import replace_escape_sections
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration, _adapter_hash
from motorsim.exploratory_workflow import preflight,run_exploratory
from motorsim.integrated_2t import audit_integrated_cycle_primary,make_integrated_engineering_output
from motorsim.mechanical import MechanicalLossModel

def sha(b):return hashlib.sha256(b).hexdigest()
def _trace(primary,effective):
    audit=audit_integrated_cycle_primary(primary,preserve_precycle_p7_baseline=True)
    if audit.get("status")!="PASS" or audit.get("recomputed") is not True:raise ValueError("independent primary audit failed")
    outputs=make_integrated_engineering_output(primary,displacement_m3=primary["swept_displacement_m3"],
      mechanical_loss_model=MechanicalLossModel.from_dict(effective["mechanical_loss_model"]),
      load=effective["operating_conditions"]["load"],periodicity_status="NOT_EVALUATED")
    trace=outputs["crank_angle_trace"]
    return audit,dict(zip(trace["angle_deg"],zip(*[row["values"] for row in trace["channels"].values()]))) if False else trace

def _pressure_at(trace,centers,bounds,sections,starts,section,angle_index):
    indices=bounds[section]
    xs=centers[indices[0]:indices[1]]
    # Find the pressure channel by semantic cell id, then linearly reconstruct
    # to the named section's local half-length at the identical recorded angle.
    ch=trace["channels"];values=[]
    for i in range(indices[0],indices[1]):
        key=f"duct:exhaust:cell:{i}:pressure_pa"
        if key not in ch:raise ValueError(f"missing cell pressure primary channel {key}")
        values.append(ch[key]["values"][angle_index])
    target=starts[section]+sections[section]["length_mm"]/2000.0
    if len(xs)==1:return values[0]
    if target<=xs[0]:return values[0]
    if target>=xs[-1]:return values[-1]
    for i in range(len(xs)-1):
        if xs[i]<=target<=xs[i+1]:
            f=(target-xs[i])/(xs[i+1]-xs[i]);return values[i]+f*(values[i+1]-values[i])
    return values[-1]

def run(artifact_root:Path,budget_seconds:float,memory_limit_mib:int):
    project=load_project(PROJECT);deadline=time.monotonic()+budget_seconds
    runs=[];traces={};variants=("Escape original","Escape modified +20 mm")
    for label in variants:
      for n in (1,2,4,8):
        remaining=deadline-time.monotonic()
        if remaining<5:
          runs.append({"variant":label,"cells_per_section":n,"classification":"NOT_STARTED_BUDGET_EXHAUSTED"});continue
        source=project["variants"][label];sections=source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
        refined=refine_exhaust_configuration(source,[1]*len(sections))
        refined=refine_exhaust_configuration(refined,[n]*len(sections))
        run_id=f"encv2-{label.lower().replace(' ','-').replace('+','plus')}-3000rpm-{n}c"
        check=preflight(refined,rpm=3000,max_cycles=1,budget_seconds=min(600,remaining),memory_limit_mib=memory_limit_mib)
        effective=resolve_for_operating_point(refined,rpm=3000);start=time.monotonic()
        try:
          result=run_exploratory(refined,project_id=project["project_id"],run_id=run_id,
            artifact_root=artifact_root,rpm=3000,max_cycles=1,budget_seconds=min(600,max(1,remaining)),
            memory_limit_mib=memory_limit_mib,variant_label=f"{label} / {n} cells per section")
          row={"variant":label,"cells_per_section":n,"run_id":run_id,"preflight":check,
            "classification":result["classification"],"status":result["status"],
            "cycles_completed":result["cycles_completed"],"periodicity":result["periodicity"],
            "elapsed_seconds":result["elapsed_seconds"],"wall_seconds_including_audit":time.monotonic()-start,
            "identity_sha256":result["bindings"]["identity_sha256"],
            "configuration_sha256":result["bindings"]["configuration_sha256"],
            "source_hashes":result["bindings"]["source_hashes"],"result_sha256":result["result_sha256"],
            "checkpoint_sha256":result["checkpoint_sha256"],"artifact_directory":result["artifact_directory"],
            "cycle_records":result["cycles"]}
          if result["cycles_completed"]==1:
            cyc=result["cycles"][0];primary_path=Path(result["artifact_directory"])/cyc["artifact"]
            payload=gzip.decompress(primary_path.read_bytes())
            if sha(payload)!=cyc["primary_sha256"]:raise ValueError("primary digest mismatch")
            primary=json.loads(payload);audit,trace=_trace(primary,effective)
            row["primary_sha256"]=cyc["primary_sha256"];row["primary_audit"]=audit
            row["conservation"]=primary["conservation"]
            row["rejected_step_count"]=result.get("rejected_step_count",cyc.get("rejected_step_count"))
            duct=next(d for d in refined["native_configuration"]["ducts"] if d["id"]=="exhaust")
            counts=[n]*len(sections);cell_bounds=[];acc=0
            for count in counts:cell_bounds.append((acc,acc+count));acc+=count
            starts=[];x=duct["mesh"]["faces"][0]
            for sec in sections:starts.append(x);x+=sec["length_mm"]/1000
            traces[(label,n)]={"trace":trace,"centers":duct["mesh"]["centers"],"bounds":cell_bounds,
              "sections":sections,"starts":starts,"artifact_sha256":cyc["primary_sha256"]}
          runs.append(row)
        except Exception as exc:runs.append({"variant":label,"cells_per_section":n,"run_id":run_id,
          "classification":"DIAGNOSTIC_EXECUTION_ERROR","error":f"{type(exc).__name__}: {exc}","wall_seconds":time.monotonic()-start})
    comparisons={};section_names=project["variants"][variants[0]]["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    for label in variants:
      for lo,hi in ((1,2),(2,4),(4,8),(1,4),(1,8)):
        a=traces.get((label,lo));b=traces.get((label,hi));key=f"{label}: {lo}_vs_{hi}"
        if not a or not b:comparisons[key]={"status":"MISSING_OR_INCOMPLETE"};continue
        ta,tb=a["trace"],b["trace"];common=sorted(set(ta["angle_deg"])&set(tb["angle_deg"]))
        deltas={};sa,sb=a["sections"],b["sections"]
        for si in range(min(len(sa),len(sb))):
          for labelkey in ("pressure_pa",):
            av=[];bv=[]
            for angle in common:
              ia=ta["angle_deg"].index(angle);ib=tb["angle_deg"].index(angle)
              va=_pressure_at(ta,a["centers"],a["bounds"],sa,a["starts"],si,ia)
              vb=_pressure_at(tb,b["centers"],b["bounds"],sb,b["starts"],si,ib);av.append(va);bv.append(vb)
            ds=[x-y for x,y in zip(av,bv)];deltas[f"section:{sa[si]['name']}:midpoint_pressure_pa"]={"max_abs":max(map(abs,ds),default=None),"rms":math.sqrt(math.fsum(x*x for x in ds)/len(ds)) if ds else None,"spatial_method":"piecewise_linear_from_cell_centers_to_named_section_local_midpoint","common_exact_crank_angles":len(common)}
        for si in range(len(sa)-1):
          ia_face=a["bounds"][si][1];ib_face=b["bounds"][si][1]
          ka=f"duct:exhaust:face:{ia_face}:mass_flow_kg_s";kb=f"duct:exhaust:face:{ib_face}:mass_flow_kg_s"
          if ka in ta["channels"] and kb in tb["channels"]:
            ma=dict(zip(ta["angle_deg"],ta["channels"][ka]["values"]));mb=dict(zip(tb["angle_deg"],tb["channels"][kb]["values"]));angles=sorted(ma.keys()&mb.keys());flow=[ma[x]-mb[x] for x in angles]
            deltas[f"interface_after:{sa[si]['name']}:mass_flow_kg_s"]={"max_abs":max(map(abs,flow),default=None),"rms":math.sqrt(math.fsum(x*x for x in flow)/len(flow)) if flow else None,"comparison":"EXACT_NAMED_INTERFACE_AND_EXACT_COMMON_ANGLES"}
        comparisons[key]=deltas
    for n in (1,2,4,8):
      a=traces.get((variants[0],n));b=traces.get((variants[1],n));key=f"A_vs_B_at_{n}_cells_per_section"
      if not a or not b:comparisons[key]={"status":"MISSING_OR_INCOMPLETE"};continue
      ta,tb=a["trace"],b["trace"];common=sorted(set(ta["angle_deg"])&set(tb["angle_deg"]));deltas={}
      for si in range(len(a["sections"])):
        av=[];bv=[]
        for angle in common:
          ia=ta["angle_deg"].index(angle);ib=tb["angle_deg"].index(angle)
          av.append(_pressure_at(ta,a["centers"],a["bounds"],a["sections"],a["starts"],si,ia))
          bv.append(_pressure_at(tb,b["centers"],b["bounds"],b["sections"],b["starts"],si,ib))
        ds=[x-y for x,y in zip(av,bv)]
        deltas[f"section:{a['sections'][si]['name']}:midpoint_pressure_pa"]={"max_abs":max(map(abs,ds),default=None),"rms":math.sqrt(math.fsum(x*x for x in ds)/len(ds)) if ds else None,"spatial_method":"piecewise_linear_to_named_section_local_midpoint","common_exact_crank_angles":len(common)}
        if si<len(a["sections"])-1:
          ia_face=a["bounds"][si][1];ib_face=b["bounds"][si][1];ka=f"duct:exhaust:face:{ia_face}:mass_flow_kg_s";kb=f"duct:exhaust:face:{ib_face}:mass_flow_kg_s"
          if ka in ta["channels"] and kb in tb["channels"]:
            fa=ta["channels"][ka]["values"];fb=tb["channels"][kb]["values"];ma=dict(zip(ta["angle_deg"],fa));mb=dict(zip(tb["angle_deg"],fb));angles=sorted(ma.keys()&mb.keys());flow=[ma[x]-mb[x] for x in angles]
            deltas[f"interface_after:{a['sections'][si]['name']}:mass_flow_kg_s"]={"max_abs":max(map(abs,flow),default=None),"rms":math.sqrt(math.fsum(x*x for x in flow)/len(flow)) if flow else None,"comparison":"EXACT_NAMED_INTERFACE_AND_EXACT_COMMON_ANGLES"}
      comparisons[key]=deltas
    wall=budget_seconds-(deadline-time.monotonic())
    report={"schema":"EXHAUST_NUMERICAL_CONVERGENCE_V2_DIAGNOSTIC_REPORT_V1","objective":"EXHAUST_NUMERICAL_CONVERGENCE_V2",
      "classification":"EXHAUST_NUMERICAL_CONVERGENCE_V2_PARTIAL","project":"examples/projects/dino-2t-exhaust-comparison.dino2t.json",
      "rpm":3000,"cycles_per_point":1,"matrix":["Escape original x 1/2/4/8","Escape modified +20 mm x 1/2/4/8"],
      "budget_seconds":budget_seconds,"wall_seconds":wall,"memory_limit_mib":memory_limit_mib,
      "runs":runs,"refinement_comparisons":comparisons,
      "claims":{"periodicity":"NOT_EVALUATED_BY_ONE_CYCLE","steady_performance":"NOT_CLAIMED",
        "experimental_validation":"NOT_PERFORMED","spatial_independence":"NOT_ESTABLISHED_BY_SHORT_TRANSIENT_1_2_4_8"},
      "limitations":["Pressure comparisons use a stated spatial linear reconstruction to named local section midpoints; this reconstruction is diagnostic, not a higher-order validated observable.","Mass flow is compared at named section interfaces using their exact shared face and exact common crank angles.","One cycle is diagnostic and does not establish periodicity."],
      "script_sha256":sha(Path(__file__).read_bytes()),
      "solver_sha256":sha(Path(ROOT/"motorsim"/"integrated_2t.py").read_bytes().replace(b"\r\n",b"\n")),
      "adapter_sha256":_adapter_hash(),"adapter_identity":"EXHAUST_MESH_V2"}
    path=artifact_root/"reports"/"exhaust-numerical-convergence-v2-1-2-4-8-report.json";path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return {"report_path":str(path),"wall_seconds":wall,"runs":[{"variant":r.get("variant"),"cells_per_section":r.get("cells_per_section"),"classification":r.get("classification"),"elapsed_seconds":r.get("elapsed_seconds")} for r in runs]}

def main():
 p=argparse.ArgumentParser();p.add_argument("--artifact-root",type=Path,default=Path(os.environ.get("DINO_ARTIFACT_ROOT",r"E:\Dino-artifacts"))/"exhaust-numerical-convergence-v2");p.add_argument("--budget-seconds",type=float,default=600);p.add_argument("--memory-limit-mib",type=int,default=4096);a=p.parse_args()
 if not 30<=a.budget_seconds<=600:p.error("bounded diagnostic budget must be 30..600 seconds (AGENTS operational limit)")
 print(json.dumps(run(a.artifact_root,a.budget_seconds,a.memory_limit_mib),indent=2,ensure_ascii=False))
if __name__=="__main__":main()
