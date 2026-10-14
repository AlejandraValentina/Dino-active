"""Independently verify persisted EXHAUST_MESH_V1 diagnostic artifacts."""
from __future__ import annotations
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.exploratory_workflow import import_exploratory_runs
from motorsim.integrated_2t import audit_integrated_cycle_primary

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--artifact-root",type=Path,required=True);a=p.parse_args()
 root=a.artifact_root/"exploratory-workflow-v1"/"dino-exhaust-comparison-starter"
 run_dirs=sorted(root.glob("exm-*-3000rpm-*c"));paths=[x/"result.json" for x in run_dirs]
 if len(paths)!=6:raise SystemExit(f"expected six isolated diagnostic points, found {len(paths)}")
 imported=import_exploratory_runs(paths)
 report_path=a.artifact_root/"reports"/"exhaust-mesh-v1-1-2-4-report.json"
 report=json.loads(report_path.read_text(encoding="utf-8"));metrics=[]
 for d in run_dirs:
  result=json.loads((d/"result.json").read_text(encoding="utf-8"));config=json.loads((d/"configuration.json").read_text(encoding="utf-8"))
  cycle=result["cycles"][0];payload=gzip.decompress((d/cycle["artifact"]).read_bytes())
  if sha(payload)!=cycle["primary_sha256"]:raise ValueError(f"primary digest mismatch: {d.name}")
  primary=json.loads(payload);audit=audit_integrated_cycle_primary(primary,preserve_precycle_p7_baseline=True)
  if audit.get("status")!="PASS" or audit.get("recomputed") is not True:raise ValueError(f"independent replay audit failed: {d.name}")
  engine_mesh=next(x for x in config["native_configuration"]["ducts"] if x["id"]=="exhaust")["mesh"]
  meta=config["native_configuration"]["geometry_identity"]["exhaust_mesh_discretization"]
  trajectory=primary["trajectory"]
  row=next(x for x in report["runs"] if x["run_id"]==d.name)
  detail={"run_id":d.name,"cells_per_section":meta["cells_per_section"],"total_cells":len(engine_mesh["volumes"]),
    "identity_sha256":config["identity_sha256"],"adapter_sha256":meta["adapter_sha256"],
    "discrete_geometry_sha256":meta["discrete_geometry_sha256"],
    "configuration_artifact_sha256":sha((d/"configuration.json").read_bytes()),
    "checkpoint_sha256":result["checkpoint_sha256"],"result_sha256":result["result_sha256"],
    "primary_sha256":cycle["primary_sha256"],"independent_reaudit":"PASS","recomputed":True,
    "completed_cycles":result["cycles_completed"],"classification":result["classification"],
    "solver_elapsed_seconds":result["elapsed_seconds"],"accepted_steps":len(trajectory),
    "rejected_trials":len(primary["rejected_trials"]),"max_stage_cfl":primary["CFL"]["max"],
    "min_stage_cfl":primary["CFL"]["min"],
    "memory_rss_at_finish_mib":result["memory_rss_at_finish_bytes"]/1048576,
    "conservation":primary["conservation"],"boundary_faces":len(engine_mesh["areas"]),
    "mesh_length_m":engine_mesh["faces"][-1]-engine_mesh["faces"][0]}
  row.update({k:detail[k] for k in ("accepted_steps","rejected_trials","max_stage_cfl","min_stage_cfl","memory_rss_at_finish_mib","adapter_sha256","discrete_geometry_sha256","independent_reaudit")})
  metrics.append(detail)
 report["post_run_verification"]={"classification":"ALL_SIX_ARTIFACTS_HASHED_AND_REAUDITED",
  "offline_workflow_import":"PASS","points":metrics,
  "cpu_utilization":"NOT_INSTRUMENTED","peak_memory":"NOT_MEASURED; RSS at result completion recorded per process"}
 report["independent_import_summary"]={"point_count":len(imported["points"]),"trace_count":len(imported["traces"]),
  "all_audit_statuses":[p["audit_status"] for p in imported["points"]],
  "all_periodicity":[p["periodicity"] for p in imported["points"]]}
 report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 receipt={"schema":"EXHAUST_MESH_V1_DIAGNOSTIC_RECEIPT_V1","objective":"EXHAUST_MESH_V1",
  "classification":"SIX_POINTS_COMPLETE_ALL_HASHES_AND_INDEPENDENT_AUDITS_PASS",
  "source_report":"${DINO_ARTIFACT_ROOT}/exhaust-mesh-v1/reports/exhaust-mesh-v1-1-2-4-report.json",
  "source_report_sha256":sha(report_path.read_bytes()),"run_logged_summary":"${DINO_ARTIFACT_ROOT}/exhaust-mesh-v1/logs/exhaust-mesh-v1-1-2-4.summary.json",
  "run_logged_wall_seconds":360.797,"aggregate_budget_seconds":600,"owner_maximum_seconds":1800,
  "artifact_root":"${DINO_ARTIFACT_ROOT}/exhaust-mesh-v1","execution":"six one-cycle runs, sequential, each isolated and conventionally audited",
  "workflow_import":"PASS; six points, six traces; independent primary replay recomputed PASS for all points",
  "points":metrics,"cpu_utilization":"NOT_INSTRUMENTED","periodicity":"NOT_EVALUATED; one cycle each",
  "steady_performance":"NOT_CLAIMED","experimental_validation":"NOT_PERFORMED","spatial_independence":"NOT_ESTABLISHED"}
 (ROOT/"results/exhaust-mesh-v1/diagnostic-receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps({"classification":receipt["classification"],"wall_seconds":360.797,"report_sha256":receipt["source_report_sha256"],"audits":6},indent=2))
if __name__=="__main__":main()
