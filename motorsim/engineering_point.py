"""Shared bounded point engine, factored from the committed exploratory runner.

No primary construction, replay, independent audit or predictive claim. Stage
traces supply exact SSPRK flux quadrature; only compact diagnostics and native
cycle checkpoints survive. Historical campaign code is not used or changed.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.engine_physics_v1 import standard_fmep_model_v1
from motorsim.reed import static_area
from motorsim.reference_harness.convergence import CONTRACT, compare_cycles_v2


def _producer_head():
    """Frozen distributions bind their build commit without requiring Git."""
    if getattr(sys, "frozen", False):
        commit = json.loads((ROOT / "motorsim/build.json").read_text(encoding="utf-8"))["source_commit"]
        if not isinstance(commit, str) or re.fullmatch(r"[0-9a-f]{40}", commit) is None:
            raise ValueError("invalid packaged source commit")
        return commit
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")).encode()


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def atomic(path, value):
    data = encode(value)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return hashlib.sha256(data).hexdigest()


def terminal_observables(engine, initial, delta):
    chambers = {}
    for name, (mass, energy, volume) in engine.state["chambers"].items():
        chambers[name] = dict(mass_kg=mass, total_energy_J=energy,
            pressure_Pa=(engine.eos.gamma-1)*energy/volume,
            temperature_K=energy/(mass*engine.eos.cv))
    ducts = {}
    for path in engine.ducts:
        cells = []
        for q, species, volume in zip(engine.state["ducts"][path.id],
                engine.state["species"]["ducts"][path.id], path.mesh.volumes):
            rho, velocity, pressure, _ = engine._primitive(q)
            cells.append(dict(mass_kg=rho*volume, total_energy_J=q[2]*volume,
                pressure_Pa=pressure, temperature_K=pressure/(rho*engine.eos.R),
                species_mass_fractions=[x/sum(species) for x in species],
                velocity_over_sound_speed=velocity/engine.eos.sound_speed((rho,velocity,pressure,1.0))))
        ducts[path.id] = cells
    return dict(chambers=chambers, ducts=ducts,
        global_species_kg=list(engine.inventory()["species_kg"]),
        cycle_start_total_mass_kg=initial["mass_kg"],
        cycle_start_total_energy_J=initial["energy_J"], work_J=-delta["cylinder_work_J"],
        fresh_delivery_kg=delta["fresh_delivered_kg"],
        fresh_short_circuit_kg=delta["fresh_short_circuit_kg"],
        p7_burned_produced_kg=delta["p7_source_species_kg"][3],
        p7_heat_J=delta["p7_heat_added_J"])


def conservation(engine):
    report = engine.conservation_report()
    mass_scale = max(report["mass"]["initial"], report["mass"]["final"])
    energy_scale = max(report["energy"]["initial"], report["energy"]["final"],
        abs(report["energy"]["external"]), abs(report["energy"].get("fuel_combustion_heat_added", 0)))
    relative = dict(mass=abs(report["mass"]["residual"])/mass_scale,
        energy=abs(report["energy"]["residual"])/energy_scale,
        species=max(abs(v["residual"])/mass_scale for v in report["species"].values()))
    if max(relative.values()) > 1e-8:
        raise ValueError("CONSERVATION_LIMIT: " + str(relative))
    return dict(cumulative=report, relative=relative, independent_audit="NOT_PERFORMED")


def ledger_delta(after, before):
    return {k: ([a-b for a,b in zip(v,before[k])] if isinstance(v,(tuple,list)) else v-before[k])
            for k,v in after.items()}


class Diagnostics:
    def __init__(self):
        self.flows = Counter()
        self.limits = Counter()
        self.pressures = {k: [float("inf"), 0.0] for k in ("cylinder","crankcase","exhaust_entry","exhaust_middle")}
        self.peak_angle = 0.0
        self.dt = [float("inf"), 0.0]
        self.cfl = 0.0
        self.samples = []
        self.closures = {}
        self.areas_max = Counter()
        self.heat_wall_by_location = Counter()
        self.positive_cylinder_work = self.negative_cylinder_work = 0.0
        self.outlet_samples = []
        self.combustion = Counter()

    def consume(self, engine, row):
        dt = row["dt_s"]
        self.dt = [min(self.dt[0], dt), max(self.dt[1], dt)]
        self.cfl = max(self.cfl, *row["stage_cfl"])
        for stage in range(2):
            weight = .5*dt
            source = row.get("stage_fuel_combustion_source_rates", ({},{}))[stage]
            for key in ("requested_fuel_rate_kg_s", "burned_fuel_rate_kg_s"):
                self.combustion[key.replace("_rate_kg_s", "_kg")] += weight*source.get(key,0.0)
            requested = source.get("requested_fuel_rate_kg_s",0.0)
            burned = source.get("burned_fuel_rate_kg_s",0.0)
            if requested > 0:
                self.combustion["active_stage_time_s"] += weight
                if burned < requested*(1-1e-10):
                    self.combustion["stage_availability_limited_time_s"] += weight
                    if math.isclose(burned, source.get("oxygen_limited_fuel_rate_kg_s", -1),rel_tol=1e-9,abs_tol=1e-20):
                        self.combustion["oxygen_stage_limited_time_s"] += weight
            state = row["stage_states"][stage]
            faces = row["stage_face_fluxes"][stage]
            g = row["stage_geometry"][stage]
            for path in engine.ducts:
                f = faces[path.id]
                for side in ("left","right"):
                    self.flows[f"{path.id}.{side}.net_kg"] += weight*f[side][0]
                    self.flows[f"{path.id}.{side}.positive_kg"] += weight*max(0,f[side][0])
                    self.flows[f"{path.id}.{side}.negative_kg"] += weight*max(0,-f[side][0])
                    for j,name in enumerate(("air","fuel","residual","burned")):
                        value = f[side+"_species"][j]
                        self.flows[f"{path.id}.{side}.{name}.out_positive_kg"] += weight*max(0,value)
                        self.flows[f"{path.id}.{side}.{name}.out_negative_kg"] += weight*max(0,-value)
            pressures = {}
            for name in ("cylinder","crankcase"):
                m,u,v = state["chambers"][name]
                pressures[name] = (engine.eos.gamma-1)*u/v
            ex = state["ducts"][engine.exhaust.id]
            pressures["exhaust_entry"] = engine._primitive(ex[0])[2]
            pressures["exhaust_middle"] = engine._primitive(ex[len(ex)//2])[2]
            for name, value in pressures.items():
                if name == "cylinder" and value > self.pressures[name][1]:
                    self.peak_angle = row["angle_start_deg"] if stage == 0 else row["angle_end_deg"]
                self.pressures[name] = [min(self.pressures[name][0],value), max(self.pressures[name][1],value)]
            pin = engine._primitive(state["ducts"][engine.intake.id][-1])[2]
            reed = static_area(engine.reed_petals,pin-pressures["crankcase"]) if engine.reed_petals else g["intake_area_m2"]
            options = dict(window=g["intake_area_m2"], reed=reed, duct=engine.intake.mesh.areas[-1])
            limiting = min(options, key=options.get)
            self.limits[f"intake.{limiting}.time_s"] += weight
            if pin > pressures["crankcase"]:
                self.limits[f"intake.suction.{limiting}.time_s"] += weight
                self.limits[f"intake.suction.{limiting}.forward_kg"] += weight*max(0,faces[engine.intake.id]["right"][0])
            areas = dict(intake_window=g["intake_area_m2"], intake_actual=faces[engine.intake.id]["effective_reed_area_m2"], reed=reed,
                exhaust=g["exhaust_area_m2"])
            for path,area in zip(engine.transfers,g["transfer_areas_m2"]):
                areas[path.id] = area
                if area < min(path.mesh.areas[0],path.mesh.areas[-1]):
                    label=".cylinder_end_port_limited.time_s" if engine.gas_exchange_model is not None else ".both_end_port_limited.time_s"
                    self.limits[path.id+label] += weight
            for name,value in areas.items():
                self.areas_max[name] = max(self.areas_max[name],value)
            for name,value in row["stage_thermal_rates"][stage].items():
                self.heat_wall_by_location[name] += weight*value
            work = -weight*row["stage_work_rates"][stage]["cylinder"]
            self.positive_cylinder_work += max(0,work)
            self.negative_cylinder_work += min(0,work)
            if stage == 0 and (not self.samples or row["angle_start_deg"]-self.samples[-1]["angle_deg"] >= .499999):
                self.samples.append(dict(angle_deg=row["angle_start_deg"], pressures_Pa=pressures,
                    areas_m2=areas, intake_limiting=limiting,
                    cylinder_species_kg=list(state["species"]["chambers"]["cylinder"]),
                    exhaust_outlet_species_rate_kg_s=list(faces[engine.exhaust.id]["left_species"]),
                    mass_flow_kg_s={path.id: faces[path.id]["right" if path.role != "exhaust" else "left"][0] for path in engine.ducts}))


def closure_events(engine, rpm):
    ports = engine.port_binding.port_set
    valve = engine.port_binding.powervalve
    if valve:
        ports = replace(ports, ports=tuple(valve.apply(p,rpm) if p.id==valve.exhaust_port_id else p for p in ports.ports))
    return {duct.role: max(ports.duct_closing_angles(duct.id)) for duct in ports.ducts if duct.role in ("transfer","exhaust")}


def restore_parent(engine, config, args):
    """Explicit append-only continuation; never rewrite/relabel the producer."""
    path = args.resume_manifest.resolve()
    raw = path.read_bytes()
    parent = json.loads(raw)
    if parent.get("schema") != "DINO_MINIMAL_EXPLORATORY_POINT_V1" or parent.get("status") not in ("MAX_CYCLES_NONCONVERGED","TIME_LIMIT_NONCONVERGED","CANCELLED_CHECKPOINTED"):
        raise ValueError("resume requires a complete-cycle nonconverged parent")
    bindings = parent["bindings"]
    if (bindings["configuration_canonical_sha256"] != digest(config) or
            bindings["configuration_file_sha256"] != hashlib.sha256(args.config.read_bytes()).hexdigest() or
            bindings["native_configuration_identity"] != engine.configuration_identity or
            bindings["rpm"] != args.rpm or
            bindings["solver_sha256"] != hashlib.sha256((ROOT/"motorsim/integrated_2t.py").read_bytes()).hexdigest()):
        raise ValueError("parent configuration/solver/RPM identity mismatch")
    frozen = args.parent_runner.read_bytes()
    if hashlib.sha256(frozen).hexdigest() != bindings["runner_sha256"]:
        raise ValueError("parent producer hash mismatch")
    cp_name = parent["checkpoint_artifact"]
    if Path(cp_name).name != cp_name:
        raise ValueError("unsafe parent checkpoint path")
    cp_raw = (path.parent/cp_name).read_bytes()
    if hashlib.sha256(cp_raw).hexdigest() != parent["checkpoint_sha256"]:
        raise ValueError("parent checkpoint integrity mismatch")
    cp = json.loads(cp_raw)
    if cp["bindings"] != bindings or cp["next_cycle"] != len(parent["cycles"])+1:
        raise ValueError("parent checkpoint binding/sequence mismatch")
    if [c["cycle"] for c in parent["cycles"]] != list(range(1,cp["next_cycle"])):
        raise ValueError("noncontiguous parent cycles")
    history = cp["periodicity_history"]
    if len(history) != len(parent["cycles"]) or any(
            h["cycle_index"] != i+1 or h["configuration_hash"] != digest(config)
            or h["contract"] != CONTRACT or h["observables"] != parent["cycles"][i]["observables"]
            for i,h in enumerate(history)):
        raise ValueError("parent detector history mismatch")
    engine.restore(cp["engine_snapshot"])
    if engine.snapshot() != cp["engine_snapshot"] or engine.crank_angle_unwrapped_deg != len(history)*360:
        raise ValueError("parent state did not restore exactly")
    streak = 0
    for a,b in zip(history,history[1:]):
        comparison = compare_cycles_v2(a,b)
        if comparison["status"] == "INVALID":
            raise ValueError("invalid parent periodicity history")
        streak = streak+1 if comparison["status"] == "PASS" else 0
    return parent,history,streak,dict(manifest_sha256=hashlib.sha256(raw).hexdigest(),
        checkpoint_sha256=hashlib.sha256(cp_raw).hexdigest(),producer_sha256=bindings["runner_sha256"],
        source_directory=str(path.parent),cycles_preserved=len(history),exact_state_restore=True,
        physical_steps_during_restore=0)


def run(args):
    start = time.perf_counter()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError("artifacts must be outside repository")
    output.mkdir(parents=True, exist_ok=False)
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    if args.rpm != config["reference_rpm"]:
        raise ValueError("RPM must match explicit configuration reference_rpm; rebuild explicitly")
    if args.max_cycles < 1 or not 0 < args.wall_seconds <= 3600 or not 0 < args.memory_mib <= 3072:
        raise ValueError("invalid execution limits")
    if psutil.virtual_memory().available < args.memory_mib*1024**2:
        raise MemoryError("insufficient available RAM for declared worker budget")
    engine = IntegratedEngine2T.from_configuration_dict(config)
    if engine.configuration_dict() != config:
        raise ValueError("configuration roundtrip mismatch")
    loss = getattr(args,"_loss_model",None)
    if loss is None:
        loss = standard_fmep_model_v1() if args.mechanical_loss == "standard-v1" else None
    parent = None
    history, streak, continuation = [], 0, None
    if args.resume_manifest:
        if not args.parent_runner or args.smoke_degrees:
            raise ValueError("resume needs frozen parent runner and no smoke")
        parent,history,streak,continuation = restore_parent(engine,config,args)
        if parent["bindings"]["mechanical_loss"] != (None if loss is None else loss.to_dict()):
            raise ValueError("parent mechanical postprocessing model mismatch")
    bindings = dict(configuration_file_sha256=hashlib.sha256(config_bytes).hexdigest(),
        configuration_canonical_sha256=digest(config), runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        native_configuration_identity=engine.configuration_identity,
        solver_sha256=hashlib.sha256((ROOT/"motorsim/integrated_2t.py").read_bytes()).hexdigest(),
        mechanical_loss=None if loss is None else loss.to_dict(), rpm=args.rpm,
        head=_producer_head(),
        python=sys.version, platform=platform.platform())
    atomic(output/"configuration.json", config)
    manifest = dict(schema="DINO_MINIMAL_EXPLORATORY_POINT_V1", bindings=bindings,
        limits={k:v for k,v in vars(args).items() if not k.startswith("_")}|{"config":str(args.config),"output":str(output),
            "resume_manifest":None if args.resume_manifest is None else str(args.resume_manifest),
            "parent_runner":None if args.parent_runner is None else str(args.parent_runner)},
        audit="NOT_PERFORMED_NO_REPLAY", predictive_validity="NOT_CLAIMED",
        cycles=[] if parent is None else deepcopy(parent["cycles"]),
        continuation=continuation, status="RUNNING", periodicity="NOT_EVALUATED")
    atomic(output/"manifest.json",manifest)
    deadline = start+args.wall_seconds-3.0
    process = psutil.Process()
    peak = process.memory_info().rss
    compute_seconds = processing_seconds = 0.0
    rejects = Counter()
    first_cycle = len(history)+1
    if first_cycle > args.max_cycles:
        raise ValueError("resume has no authorized cycles left")
    closures = closure_events(engine,args.rpm)
    terminal = "MAX_CYCLES_NONCONVERGED"
    failure = None
    current = None
    try:
        for cycle in range(first_cycle,args.max_cycles+1):
            cycle_start = time.perf_counter()
            baseline = deepcopy(engine.ledger)
            initial = engine.inventory()
            diag = Diagnostics()
            current = diag
            cycle_rejects = Counter()
            steps = 0
            target_cycle = min(cycle*360.0,args.smoke_degrees or cycle*360.0)
            while engine.crank_angle_unwrapped_deg < target_cycle-1e-9:
                if getattr(args,"_cancel_event",None) is not None and args._cancel_event.is_set():
                    raise InterruptedError("cancel requested at accepted-step boundary")
                if time.perf_counter() >= deadline:
                    raise TimeoutError("wall budget reached at accepted-step boundary")
                if steps % 50 == 0:
                    peak = max(peak,process.memory_info().rss)
                    if getattr(args,"_progress",None):
                        args._progress(dict(cycle=cycle,cycles_completed=cycle-1,angle_deg=engine.crank_angle_unwrapped_deg,rss_bytes=peak))
                    if peak > args.memory_mib*1024**2:
                        raise MemoryError("worker RSS cap")
                    if steps % 500 == 0:
                        atomic(output/"progress.json",dict(cycle=cycle,angle_deg=engine.crank_angle_unwrapped_deg,
                            wall_s=time.perf_counter()-start, peak_rss_mib=peak/1024**2))
                angle = engine.crank_angle_unwrapped_deg
                target = min(target_cycle,(math.floor((angle+1e-9)/.5)+1)*.5)
                base = (cycle-1)*360
                special = [base+x for x in (33,340,352,*closures.values())]
                target = min([target]+[x for x in special if angle+1e-9<x<target])
                delta = target-angle
                for attempt in range(25):
                    tick = time.perf_counter()
                    try:
                        row = engine.step(delta/(6*args.rpm),delta,profile_capture=True)
                    except ValueError as exc:
                        compute_seconds += time.perf_counter()-tick
                        if not any(s in str(exc) for s in ("CFL limit exceeded","inadmissible species mass","rho/p/Y inadmissible")):
                            raise
                        cycle_rejects[str(exc).split(":")[0]] += 1
                        rejects[str(exc).split(":")[0]] += 1
                        delta *= .5
                    else:
                        compute_seconds += time.perf_counter()-tick
                        break
                else:
                    raise RuntimeError("25 rejected trials without an admissible step")
                tick = time.perf_counter()
                diag.consume(engine,row)
                for role,phase in closures.items():
                    if abs(engine.crank_angle_unwrapped_deg-(base+phase)) < 1e-8:
                        diag.closures[role] = dict(angle_deg=base+phase,
                            cylinder_species_kg=list(engine.state["species"]["chambers"]["cylinder"]))
                if steps % 100 == 0:
                    conservation(engine)
                processing_seconds += time.perf_counter()-tick
                steps += 1
            if args.smoke_degrees:
                terminal = "SMOKE_COMPLETE"
                break
            tick = time.perf_counter()
            check = conservation(engine)
            delta_ledger = ledger_delta(engine.ledger,baseline)
            observables = terminal_observables(engine,initial,delta_ledger)
            record = dict(cycle_index=cycle,configuration_hash=bindings["configuration_canonical_sha256"],
                contract=CONTRACT,observables=observables)
            comparison = compare_cycles_v2(history[-1],record) if history else None
            if comparison and comparison["status"] == "INVALID":
                raise ValueError("invalid periodicity observables: "+str(comparison))
            streak = streak+1 if comparison and comparison["status"] == "PASS" else 0
            history.append(record)
            trapped = diag.closures["exhaust"]["cylinder_species_kg"]
            vd = config["geometry_identity"]["displacement_cc"]*1e-6
            work = -delta_ledger["cylinder_work_J"]
            crankcase_work = -delta_ledger["crankcase_work_J"]
            performance = None if loss is None else loss.evaluate_2t_net_piston_work(
                net_piston_gas_work_j=work+crankcase_work, displacement_m3=vd,rpm=args.rpm,load=getattr(args,"_load",1.0))
            summary = dict(cycle=cycle,accepted_steps=steps,rejected_trials=dict(cycle_rejects),
                conservation=check,ledger_delta=delta_ledger, flow_integrals=dict(diag.flows),
                restriction_integrals=dict(diag.limits),area_max_m2=dict(diag.areas_max),
                pressure_min_max_Pa=diag.pressures, peak_pressure_angle_deg=diag.peak_angle%360,
                closure_snapshots=diag.closures, afr_supplied=engine.atmosphere_species[0]/engine.atmosphere_species[1],
                afr_trapped=None if trapped[1] <= 0 else trapped[0]/trapped[1],
                fuel_burned_kg=-delta_ledger["fuel_combustion_source_species_kg"][1],
                chemical_heat_J=delta_ledger["fuel_combustion_heat_added_J"],
                cylinder_work_J=work, crankcase_work_J=crankcase_work,
                cylinder_positive_work_J=diag.positive_cylinder_work,
                cylinder_negative_work_J=diag.negative_cylinder_work,
                imep_Pa=work/vd, indicated_power_W=work*args.rpm/60,
                indicated_torque_Nm=work/(2*math.pi), mechanical_estimate=performance,
                thermal_heat_by_surface_J=dict(diag.heat_wall_by_location),
                combustion_stage_diagnostics=dict(diag.combustion),
                ignition_event=None if engine.fuel_combustion_event is None else engine.fuel_combustion_event.to_dict(),
                dt_min_max_s=diag.dt, max_accepted_cfl=diag.cfl,
                comparison= comparison, periodicity_streak=streak,
                wall_s=time.perf_counter()-cycle_start,peak_rss_mib=peak/1024**2,
                observables=observables)
            peak = max(peak,process.memory_info().rss, getattr(process.memory_info(),"peak_wset",0))
            summary["peak_rss_mib"] = peak/1024**2
            summary["diagnostic_artifact_sha256"] = atomic(output/f"cycle-{cycle:03d}-diagnostics.json",dict(summary=summary,samples=diag.samples))
            engine.compact_cycle_trace()
            checkpoint = dict(schema="DINO_MINIMAL_EXPLORATORY_CHECKPOINT_V1",bindings=bindings,
                next_cycle=cycle+1,engine_snapshot=engine.snapshot(),periodicity_history=history)
            cp_name = f"checkpoint-next-{cycle+1:03d}.json"
            cp_sha = atomic(output/cp_name,checkpoint)
            manifest["cycles"].append(summary)
            manifest.update(checkpoint_artifact=cp_name,checkpoint_sha256=cp_sha)
            processing_seconds += time.perf_counter()-tick
            atomic(output/"manifest.json",manifest)
            print(json.dumps(dict(cycle=cycle,work_J=work,heat_J=summary["chemical_heat_J"],
                pmax_Pa=diag.pressures["cylinder"][1],wall_s=summary["wall_s"],streak=streak)),flush=True)
            if cycle >= 10 and streak >= 3:
                manifest["periodicity"] = "PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED"
                terminal = "PERIODIC_EXPLORATORY"
                break
    except (Exception,KeyboardInterrupt) as exc:
        terminal = ("TIME_LIMIT_NONCONVERGED" if isinstance(exc,TimeoutError) else "CANCELLED_CHECKPOINTED" if isinstance(exc,InterruptedError) else "STOPPED_ERROR")
        failure = type(exc).__name__+": "+str(exc)
    # Preserve the current partial trajectory without pretending it is complete.
    if engine.trace:
        tick = time.perf_counter()
        engine.compact_cycle_trace()
        partial = dict(bindings=bindings,partial_cycle=True,engine_snapshot=engine.snapshot())
        manifest["partial_checkpoint_sha256"] = atomic(output/"partial-checkpoint.json",partial)
        if current:
            atomic(output/"partial-diagnostics.json",dict(samples=current.samples,flows=dict(current.flows)))
        processing_seconds += time.perf_counter()-tick
    manifest.update(status=terminal,failure=failure,cycles_completed=len(manifest["cycles"]),
        terminal_angle_deg=engine.crank_angle_unwrapped_deg,
        wall_s=time.perf_counter()-start,solver_step_wall_s=compute_seconds,
        cycles_computed_this_invocation=len(manifest["cycles"])-(first_cycle-1),
        trace_dictionary_capture_wall_s=engine.trace_capture_seconds,
        solver_step_excluding_trace_dictionary_wall_s=compute_seconds-engine.trace_capture_seconds,
        processing_wall_s=processing_seconds,other_wall_s=time.perf_counter()-start-compute_seconds-processing_seconds,
        cpu_s=sum(process.cpu_times()[:2]),peak_rss_mib=max(peak,process.memory_info().rss)/1024**2,
        rejected_trials=dict(rejects))
    try:
        manifest["final_conservation"] = conservation(engine)
    except ValueError as exc:
        manifest.update(status="STOPPED_ERROR",failure=str(exc),
            final_conservation=dict(cumulative=engine.conservation_report(),check="FAIL"))
    atomic(output/"manifest.json",manifest)
    print(json.dumps({k:manifest[k] for k in ("status","cycles_completed","wall_s","solver_step_wall_s","processing_wall_s","peak_rss_mib","failure")}),flush=True)
    return 1 if failure and terminal == "STOPPED_ERROR" else 0


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--rpm",type=float,required=True)
    p.add_argument("--max-cycles",type=int,default=30)
    p.add_argument("--wall-seconds",type=float,default=1800)
    p.add_argument("--memory-mib",type=int,default=3072)
    p.add_argument("--mechanical-loss",choices=("undefined","standard-v1"),required=True)
    p.add_argument("--smoke-degrees",type=float,default=0)
    p.add_argument("--resume-manifest",type=Path)
    p.add_argument("--parent-runner",type=Path)
    return p
