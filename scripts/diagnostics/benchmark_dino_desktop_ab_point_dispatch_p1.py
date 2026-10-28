"""Bounded feasibility of independent one-RPM workers; one cycle, no periodicity claim."""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _run_point(spec):
    from motorsim.exploratory_workflow import run_exploratory
    from motorsim.power_curve_sweep import _operating_document
    result=run_exploratory(_operating_document(spec["document"],spec["rpm"],None),
        project_id=spec["project_id"],run_id=spec["run_id"],artifact_root=spec["artifact_root"],
        rpm=spec["rpm"],max_cycles=1,budget_seconds=120,memory_limit_mib=1024,
        variant_label=spec["variant_label"])
    result_path=Path(result["artifact_directory"])/"result.json"
    return {"variant":spec["variant_label"],"rpm":spec["rpm"],"status":result["status"],
        "classification":result["classification"],"cycles_completed":result["cycles_completed"],
        "checkpoint_sha256":result.get("checkpoint_sha256"),"result_sha256":result.get("result_sha256"),
        "result_artifact_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "identity_sha256":result["bindings"]["identity_sha256"],"run_directory":result["artifact_directory"]}


def main():
    from motorsim.engine_project import load_project
    from motorsim.desktop.preferences import artifact_root
    import psutil
    if psutil.virtual_memory().available<3*1024**3+512*1024**2:
        raise RuntimeError("Three 1-GiB workers plus 512-MiB supervisor reserve do not fit")
    project=load_project(ROOT/"configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json")
    variants=[("A_original",project["variants"]["A_original"]),
              ("B_header_plus20",project["variants"]["B_header_plus20"])]
    root=str(Path(artifact_root()).expanduser().resolve());cases=[]
    for case_id,rpms in (("low",(4500,5000,5500)),("high",(7000,7500,8000))):
        specs=[]
        for variant,engine in variants:
            for rpm in rpms:
                specs.append({"document":engine,"project_id":project["project_id"],
                    "variant_label":variant,"rpm":rpm,"artifact_root":root,
                    "run_id":f"ab-p1-point-{case_id}-serial-{variant}-{rpm}-{uuid.uuid4().hex[:8]}"})
        started=time.perf_counter();serial=[_run_point(spec) for spec in specs];serial_wall=time.perf_counter()-started
        parallel_specs=[{**spec,"run_id":spec["run_id"].replace("serial","parallel")} for spec in specs]
        started=time.perf_counter()
        with concurrent.futures.ProcessPoolExecutor(max_workers=3,mp_context=multiprocessing.get_context("spawn")) as pool:
            parallel=list(pool.map(_run_point,parallel_specs))
        parallel_wall=time.perf_counter()-started
        serial_by_key={(row["variant"],row["rpm"]):row for row in serial}
        pairs=[]
        for row in parallel:
            previous=serial_by_key[(row["variant"],row["rpm"])]
            pairs.append({"variant":row["variant"],"rpm":row["rpm"],
                "serial_status":previous["status"],"parallel_status":row["status"],
                "serial_classification":previous["classification"],"parallel_classification":row["classification"],
                "cycles_equal":previous["cycles_completed"]==row["cycles_completed"]==1,
                "checkpoint_equal":previous["checkpoint_sha256"]==row["checkpoint_sha256"],
                "serial_checkpoint_sha256":previous["checkpoint_sha256"],
                "parallel_checkpoint_sha256":row["checkpoint_sha256"]})
        cases.append({"case_id":case_id,"rpms":list(rpms),"serial_wall_seconds":serial_wall,
            "parallel_wall_seconds":parallel_wall,"speedup":serial_wall/parallel_wall,
            "all_checkpoints_equal":all(row["checkpoint_equal"] for row in pairs),
            "all_one_cycle":all(row["cycles_equal"] for row in pairs),"points":pairs})
    out={"schema":"DINO_DESKTOP_AB_POINT_DISPATCH_FEASIBILITY_V1","project":project["project_id"],
        "workers":3,"memory_limit_mib_per_worker":1024,"max_cycles_per_point":1,
        "periodicity_evaluated":False,"artifact_root":"${DINO_ARTIFACT_ROOT}","cases":cases,
        "acceptance_2x_both_cases":all(case["speedup"]>=2 for case in cases),
        "state_equivalence":all(case["all_checkpoints_equal"] and case["all_one_cycle"] for case in cases),
        "interpretation":"Bounded dispatch feasibility only; one-cycle checkpoints are not periodic performance results."}
    print(json.dumps(out,sort_keys=True,separators=(",",":")))


if __name__=="__main__":
    multiprocessing.freeze_support();main()
