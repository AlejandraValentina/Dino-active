"""Efficient engineering mode inside the existing project/run workflow.

Uses the shared point engine, project identities, run directories, history and
result widgets. No independent audit is claimed for this explicit run schema.
"""
from pathlib import Path
import hashlib
import json
import shutil

from . import engineering_point as point
from .engine_configuration import resolve_for_operating_point
from .mechanical import MechanicalLossModel

SCHEMA="DINO_ENGINEERING_RUN_V1"


def run(document, *, project_id,run_id,artifact_root,rpm,max_cycles,budget_seconds,
        memory_limit_mib,resume=False,cancel_event=None,progress=None,variant_label="base",
        initial_state_provenance=None,**unused):
    from .exploratory_workflow import _run_directory,preflight
    check=preflight(document,rpm=rpm,max_cycles=max_cycles,budget_seconds=budget_seconds,memory_limit_mib=memory_limit_mib)
    effective=resolve_for_operating_point(document,rpm=rpm)
    if initial_state_provenance is not None:
        provenance=document.get("provenance",{}).get("periodic_state_initialization")
        if (not isinstance(provenance,dict) or provenance.get("schema")!=
                "DINO_PERIODIC_STATE_INITIALIZATION_V1" or
                provenance != initial_state_provenance):
            raise ValueError("periodic warm-start provenance does not match the target document")
    root=_run_directory(Path(artifact_root),project_id,run_id)
    if root.is_relative_to(point.ROOT):
        raise ValueError("artifact root must be external")
    previous=None
    if resume:
        previous=json.loads((root/"run.json").read_text())
        if previous.get("schema")!=SCHEMA or previous["bindings"]["identity_sha256"]!=effective["identity_sha256"]:
            raise ValueError("engineering resume identity mismatch")
        parent=root/previous["attempt"]/"manifest.json"
        number=previous["invocations"]+1
    else:
        if root.exists():raise ValueError("run already exists; use explicit resume")
        root.mkdir(parents=True)
        number=1
    native=root/"native-configuration.json"
    if not resume:point.atomic(native,effective["native_configuration"])
    elif json.loads(native.read_text())!=effective["native_configuration"]:
        raise ValueError("stored native configuration mismatch")
    attempt=f"invocation-{number:03d}"
    args=point.parser().parse_args(["--config",str(native),"--output",str(root/attempt),
        "--rpm",str(rpm),"--max-cycles",str(max_cycles),"--wall-seconds",str(budget_seconds),
        "--memory-mib",str(memory_limit_mib),"--mechanical-loss","undefined"])
    if resume:
        args.resume_manifest=parent;args.parent_runner=parent.parent/"producer.py"
    args._cancel_event=cancel_event;args._progress=progress
    args._loss_model=MechanicalLossModel.from_dict(document["mechanical_loss_model"])
    args._load=document["operating_conditions"]["load"]
    point.run(args)
    shutil.copyfile(Path(point.__file__),root/attempt/"producer.py")
    raw=(root/attempt/"manifest.json").read_bytes();diagnostic=json.loads(raw)
    status=("INTERRUPTED_CHECKPOINTED" if diagnostic["status"] in ("TIME_LIMIT_NONCONVERGED","CANCELLED_CHECKPOINTED")
        else "FAILED_CLOSED" if diagnostic["status"]=="STOPPED_ERROR" else "COMPLETE")
    result=dict(schema=SCHEMA,status=status,classification=diagnostic["status"],mode="ENGINEERING_EXPLORATORY",
        scientific_validation="NOT_CLAIMED",audit="NOT_PERFORMED",failure=diagnostic["failure"],
        bindings=dict(identity_sha256=effective["identity_sha256"],variant_label=variant_label,
            configuration_sha256=effective["native_configuration_sha256"],project_id=project_id,run_id=run_id),
        initial_state_provenance=initial_state_provenance,
        preflight=check,attempt=attempt,invocations=number,
        diagnostic_manifest_sha256=hashlib.sha256(raw).hexdigest(),
        cycles_completed=diagnostic["cycles_completed"],periodicity=(diagnostic["periodicity"] if diagnostic["periodicity"].startswith("PERIOD_") else "NOT_CONVERGED" if diagnostic["cycles_completed"]>=2 else "INSUFFICIENT_CYCLES"),
        elapsed_seconds=diagnostic["wall_s"]+(previous.get("elapsed_seconds",0) if previous else 0),
        artifact_directory=str(root),checkpoint_artifact=None,
        cycles=diagnostic["cycles"],source_hashes=effective["source_hashes"])
    if initial_state_provenance is not None:
        result["initial_state_provenance"] = initial_state_provenance
    if diagnostic.get("checkpoint_artifact"):
        cp=root/attempt/diagnostic["checkpoint_artifact"]
        shutil.copyfile(cp,root/"checkpoint.json")
        result.update(checkpoint_artifact=f"{attempt}/{cp.name}",checkpoint_sha256=diagnostic["checkpoint_sha256"])
    result_hash=point.atomic(root/"result.json",result)
    point.atomic(root/"run.json",dict(result,result_sha256=result_hash))
    return dict(result,result_sha256=result_hash)


def import_desktop_runs(paths):
    """Dispatch explicitly by schema; legacy runs retain their full importer."""
    from .exploratory_workflow import import_exploratory_runs
    schemas=[]
    for path in paths:
        root=Path(path);root=root if root.is_dir() else root.parent
        schemas.append(json.loads((root/"result.json").read_text()).get("schema"))
    if all(schema!=SCHEMA for schema in schemas):
        return import_exploratory_runs(paths)
    datasets=[]
    for path in paths:
        root=Path(path);root=root if root.is_dir() else root.parent
        raw=(root/"result.json").read_bytes();result=json.loads(raw)
        if result.get("schema")!=SCHEMA:
            datasets.append(import_exploratory_runs([path]));continue
        manifest=json.loads((root/"run.json").read_text())
        if hashlib.sha256(raw).hexdigest()!=manifest["result_sha256"]:
            raise ValueError("engineering result hash mismatch")
        diag_raw=(root/result["attempt"]/"manifest.json").read_bytes()
        if hashlib.sha256(diag_raw).hexdigest()!=result["diagnostic_manifest_sha256"]:
            raise ValueError("engineering diagnostics hash mismatch")
        diag=json.loads(diag_raw)
        if not diag["cycles"]:raise ValueError("no complete engineering cycle to display")
        c=diag["cycles"][-1];periodic=diag["periodicity"].startswith("PERIOD_1")
        loss=c["mechanical_estimate"]
        estimates=dict(brake_power=None if loss is None else loss["brake_power_w"]/1000,
            brake_torque=None if loss is None else loss["brake_torque_nm"],
            IMEP=c["imep_Pa"]/1000,BMEP=None if loss is None else loss["brake_mep_pa"]/1000,
            FMEP=None if loss is None else loss["friction_mep_pa"]/1000,
            indicated_power=c["indicated_power_W"]/1000,indicated_torque=c["indicated_torque_Nm"])
        row=dict(point_id=result["bindings"]["run_id"],variant_id=result["bindings"]["variant_label"],
            run_id=result["bindings"]["run_id"],rpm=diag["bindings"]["rpm"],cycle=c["cycle"],
            cycles_completed=result["cycles_completed"],classification=result["classification"],
            periodicity=(diag["periodicity"] if periodic else "NOT_CONVERGED" if c["cycle"]>=2 else "INSUFFICIENT_CYCLES"),mode="ENGINEERING_EXPLORATORY",audit_status="NOT_PERFORMED",
            audit_recomputed=False,conservation=c["conservation"],transient_estimates=estimates,
            result_sha256=manifest["result_sha256"],checkpoint_sha256=result.get("checkpoint_sha256"),
            point_configuration_sha256=diag["bindings"]["configuration_canonical_sha256"],
            artifact_directory=str(root),experimental_validation="NOT_PERFORMED")
        from .engine_configuration import sha256
        row.update(solver_identity_sha256=result.get('source_hashes',{}).get('motorsim.integrated_2t'),
            implementation_identity_sha256=sha256(result['source_hashes']) if result.get('source_hashes') else None,
            fuel_id=result.get('preflight',{}).get('fuel_id'),
            afr_kg_air_per_kg_fuel=c.get('afr_supplied'),
            total_finite_volume_cells=result.get('preflight',{}).get('total_finite_volume_cells'),
            cycles_requested=diag['bindings'].get('max_cycles',result['cycles_completed']))
        row["engineering_diagnostics"]={
            "Trabajo indicado (J/ciclo)":c["cylinder_work_J"],
            "Potencia indicada transitoria (kW)":c["indicated_power_W"]/1000,
            "Trabajo del cárter (J/ciclo)":c["crankcase_work_J"],
            "Calor de combustión (J/ciclo)":c["chemical_heat_J"],
            "Combustible quemado (mg/ciclo)":c["fuel_burned_kg"]*1e6,
            "Aire atrapado al cierre (mg)":c["closure_snapshots"]["exhaust"]["cylinder_species_kg"][0]*1e6,
            "AFR atrapado":c["afr_trapped"],
            "Fricción": "Modelo explícito del proyecto; no es una medición de banco"}
        for name,value in estimates.items():
            row[name]=value if periodic else None
            row[name+"_status"]="DEFINED" if periodic and value is not None else "UNDEFINED"
            row[name+"_reason"]="NO_PERIODICITY_TRANSIENT_ONLY" if not periodic else "ENGINEERING_ONLY_NOT_VALIDATED"
        sample_path=root/result["attempt"]/f"cycle-{c['cycle']:03d}-diagnostics.json"
        sample_raw=sample_path.read_bytes()
        expected=c.get("diagnostic_artifact_sha256")
        if expected is None:
            # Earlier development runs can be viewed only with an explicit
            # post-run integrity inventory, never by silently trusting samples.
            seal=json.loads((root/"artifact-integrity.json").read_text())
            if seal["result_sha256"]!=manifest["result_sha256"]:
                raise ValueError("engineering sample inventory identity mismatch")
            expected=seal["files_sha256"].get(str(sample_path.relative_to(root)).replace('\\','/'))
        if not expected or hashlib.sha256(sample_raw).hexdigest()!=expected:
            raise ValueError("engineering sample hash mismatch")
        sample=json.loads(sample_raw)["samples"]
        channels={"cylinder_pressure_pa":dict(unit="Pa",values=[s["pressures_Pa"]["cylinder"] for s in sample]),
            "duct:exhaust:cell:0:pressure_pa":dict(unit="Pa",values=[s["pressures_Pa"]["exhaust_entry"] for s in sample]),
            "duct:exhaust:face:0:mass_flow_kg_s":dict(unit="kg/s",values=[s["mass_flow_kg_s"]["exhaust"] for s in sample])}
        datasets.append(dict(points=[row],traces=[dict(point_id=row["point_id"],variant_id=row["variant_id"],rpm=row["rpm"],
            cycle=c["cycle"],angles_deg=[s["angle_deg"]%360 for s in sample],channels=channels)]))
    return dict(schema="DINO_DESKTOP_ENGINEERING_DATA_V1",points=[p for d in datasets for p in d["points"]],
        traces=[t for d in datasets for t in d.get("traces",[])],provenance="ENGINEERING · internal conservation · independent audit NOT_PERFORMED",
        experimental_validation="NOT_CLAIMED",audit_method="INTERNAL_CONSERVATION_NO_REPLAY" if all(s==SCHEMA for s in schemas) else "MIXED_SCHEMAS")
