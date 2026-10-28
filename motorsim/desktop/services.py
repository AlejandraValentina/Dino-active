"""Desktop-facing adapters and cancellable background task primitive."""
from __future__ import annotations

import json
import math
import sys
import concurrent.futures
import multiprocessing
import os
import tempfile
import time
import uuid
from copy import deepcopy
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..engine_configuration import create, identity, validate
from ..engine_project import create_project, load_project, save_project, validate_project
from ..engine_results import import_report
from ..crankcase import CrankcaseGeometry
from ..integrated_2t import SliderCrankChambers2T
from ..two_stroke_ports import TwoStrokePortSet, DuctBinding, PortDefinition
from .preferences import impl2_historical_report_candidate

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
FIXTURE = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"
STARTER_TEMPLATE = Path(__file__).resolve().parent / "templates/single_cylinder_2t_starter_v1.json"


def fixture_engine():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return create(native_configuration=data["engine_configuration"],
        mechanical_loss_model=data["mechanical_loss_model"],
        operating_conditions={"reference_rpm": 3000, "load": 1.0,
                              "fuel_id": data["fuel_surrogate_snapshot"]["sha256"], "afr": 49.0},
        provenance={"configuration_source": {"path": str(FIXTURE.relative_to(ROOT)),
            "classification": data["classification"]}, "fuel": data["fuel_surrogate_snapshot"]},
        display_name="Fixture A — sintético")


def new_project(project_id="dino-project"):
    return create_project(project_id, fixture_engine(), scientific_validation_status="SYNTHETIC_UNVALIDATED")


def new_design_project(project_id="dino-2t-nuevo", inputs=None, input_sources=None):
    """Create a clean design project from an assumption-labeled solver template.

    The project contains no run references. Defaults are editable and are never
    represented as measured or experimentally validated values.
    """
    from ..engine_configuration import sha256, validate
    if not STARTER_TEMPLATE.is_file():
        raise FileNotFoundError(f"No está disponible la plantilla inicial: {STARTER_TEMPLATE}")
    engine=json.loads(STARTER_TEMPLATE.read_text(encoding="utf-8"))
    native=engine["native_configuration"]
    crankcase=native["slider_crank"]["crankcase"]
    values={"bore_mm":crankcase["bore_mm"],"stroke_mm":crankcase["stroke_mm"],
            "rod_length_mm":crankcase["rod_length_mm"],"volume_bdc_cm3":crankcase["volume_bdc_cm3"],
            "cylinder_compression_ratio":native["slider_crank"]["cylinder_compression_ratio"],
            "reference_rpm":native["reference_rpm"],
            "intake_control":native["geometry_identity"]["gas_exchange_model"]["intake_control"]}
    values.update(inputs or {})
    allowed_sources={"MEASURED","ESTIMATED","SYNTHETIC_ASSUMPTION"}
    sources=input_sources or {}
    if any(value not in allowed_sources for value in sources.values()):
        raise ValueError("La provenance debe ser Medido, Estimado o Supuesto")
    cc=native["slider_crank"]["crankcase"]
    old_bore=float(cc["bore_mm"]);old_stroke=float(cc["stroke_mm"])
    cc.update({key:float(values[key]) for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3")})
    geometric_sources={sources.get(key,"SYNTHETIC_ASSUMPTION") for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3")}
    cc["provenance"]=("DOCUMENTED" if geometric_sources=={"MEASURED"} else
        "SYNTHETIC_ASSUMPTION" if geometric_sources=={"SYNTHETIC_ASSUMPTION"} else "UNKNOWN")
    native["slider_crank"]["cylinder_compression_ratio"]=float(values["cylinder_compression_ratio"])
    native["reference_rpm"]=float(values["reference_rpm"])
    engine["operating_conditions"]["reference_rpm"]=float(values["reference_rpm"])
    exchange=native["geometry_identity"]["gas_exchange_model"]
    if values["intake_control"] not in ("piston_port","reed"):
        raise ValueError("La admisión debe ser por pistón o láminas")
    exchange["intake_control"]=values["intake_control"]
    if values["intake_control"]=="piston_port":
        native["reed_petals"]=[]
        native["dynamic_reed_binding"]=None
    port_set=native["port_binding"]["port_set"]
    port_rows=deepcopy(port_set["ports"])
    stroke_scale=float(values["stroke_mm"])/old_stroke
    bore_scale=float(values["bore_mm"])/old_bore
    for port in port_rows:
        for key in ("top_mm","height_mm","roof_travel_mm","skirt_mm"):
            if port.get(key) is not None:port[key]=float(port[key])*stroke_scale
        if port.get("width_mm") is not None:port["width_mm"]=float(port["width_mm"])*bore_scale
    resolved=TwoStrokePortSet(float(values["stroke_mm"]),float(values["rod_length_mm"]),
        tuple(DuctBinding.from_dict(item) for item in port_set["ducts"]),
        tuple(PortDefinition.from_dict(item) for item in port_rows)).to_dict()
    native["port_binding"]["port_set"]=resolved
    native["geometry_identity"]["ports"]=deepcopy(resolved)
    crank=CrankcaseGeometry.from_dict(cc)
    volumes=SliderCrankChambers2T(crank,float(values["cylinder_compression_ratio"])).resolve(0.0,float(values["reference_rpm"]))
    for name,volume in (("crankcase",volumes[0]),("cylinder",volumes[1])):
        previous=native["initial_chambers"]["species"][name]
        total=math.fsum(previous)
        if total<=0:
            raise ValueError(f"Inventario inicial de {name} no positivo en la plantilla")
        target=native["initial_chambers"][name][0]*volume
        native["initial_chambers"]["species"][name]=[mass*target/total for mass in previous]
    engine["native_configuration_sha256"]=sha256(native)
    engine["provenance"]["design_inputs"]={key:{
        "classification":sources.get(key,"SYNTHETIC_ASSUMPTION"),
        "rationale":"Declarado al crear el diseño; valor inicial de plantilla si no fue medido o estimado por el usuario."
    } for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3","cylinder_compression_ratio","reference_rpm")}
    engine["provenance"]["design_inputs"].update({
        key:{"classification":"SYNTHETIC_ASSUMPTION","rationale":"Valor inicial supuesto de plantilla; se puede editar en las pantallas Motor y Escape."}
        for key in ("port_dimensions","intake_control","exhaust_sections","fuel_model")
    })
    engine["display_name"]="Motor nuevo · diseño editable"
    validate(engine)
    return create_project(project_id,engine,scientific_validation_status="SYNTHETIC_UNVALIDATED")


def starter_reed_petals():
    """Return the declared starter reed geometry when switching controls in UI."""
    template=json.loads(STARTER_TEMPLATE.read_text(encoding="utf-8"))
    return deepcopy(template["native_configuration"].get("reed_petals",[]))


def load_results(path: str | Path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return import_report(path, metadata_path=path.with_suffix(".json"))
    return import_report(path)


class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    completed = Signal(object)


class _TaskRegistry(QObject):
    """Keep QRunnable wrappers alive until their queued completion is delivered."""
    def __init__(self):
        super().__init__(); self.tasks=set()

    @Slot(object)
    def release(self, task):
        self.tasks.discard(task)


_TASKS = _TaskRegistry()


class BackgroundTask(QRunnable):
    """Run I/O/service work off the UI thread; cooperative cancellation is explicit."""
    def __init__(self, function, *args, **kwargs):
        super().__init__(); self.function=function; self.args=args; self.kwargs=kwargs
        self.signals=_Signals(); self.cancel_requested=False

    def cancel(self): self.cancel_requested=True

    @Slot()
    def run(self):
        try:
            if self.cancel_requested:
                self.signals.cancelled.emit(); return
            value=self.function(*self.args,**self.kwargs)
            if self.cancel_requested: self.signals.cancelled.emit()
            else: self.signals.finished.emit(value)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.signals.completed.emit(self)


def run_background(function, *args, on_done=None, on_error=None, **kwargs):
    task=BackgroundTask(function,*args,**kwargs)
    _TASKS.tasks.add(task)
    task.signals.completed.connect(_TASKS.release)
    if on_done: task.signals.finished.connect(on_done)
    if on_error: task.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(task)
    return task


def _parallel_curve_point(spec, stop_event):
    from ..exploratory_workflow import run_exploratory
    from ..power_curve_sweep import _operating_document
    result=run_exploratory(_operating_document(spec["document"],spec["rpm"],spec.get("control_policy")),
        project_id=spec["project_id"],run_id=spec["run_id"],artifact_root=spec["artifact_root"],
        rpm=spec["rpm"],max_cycles=spec["max_cycles"],budget_seconds=spec["point_budget_seconds"],
        memory_limit_mib=spec["memory_limit_mib"],cancel_event=stop_event,variant_label=spec["variant_label"])
    result_path=Path(result["artifact_directory"])/"result.json"
    import hashlib
    run_status=result.get("status")
    execution_status=("COMPLETE" if run_status in {"COMPLETE","MAX_CYCLES_NONCONVERGED"}
                      else "FAILED_CLOSED" if run_status in {"FAIL_CLOSED","FAILED_CLOSED"} else run_status)
    return {"variant_id":spec["variant_label"],"rpm":spec["rpm"],"status":execution_status,"solver_status":run_status,
        "classification":result.get("classification"),"cycles_completed":result.get("cycles_completed"),
        "periodicity":result.get("periodicity"),"run_directory":result.get("artifact_directory"),
        "identity_sha256":result.get("bindings",{}).get("identity_sha256"),
        "result_sha256":result.get("result_sha256"),"result_artifact_sha256":hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "checkpoint_sha256":result.get("checkpoint_sha256"),"failure":result.get("failure")}


def _atomic_json(path, data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as stream:
            json.dump(data,stream,ensure_ascii=False,sort_keys=True,allow_nan=False);stream.write("\n");stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        try:os.unlink(name)
        except FileNotFoundError:pass


def run_parallel_curve_points(specs, *, max_workers=3, total_budget_seconds=1800,
                              cancel_event=None, progress=None):
    """Bounded A/B curve coordinator; every worker owns one RPM run/checkpoint."""
    if not isinstance(specs,(list,tuple)) or len(specs)<2 or type(max_workers) is not int or max_workers<2:
        raise ValueError("parallel curve dispatch requires at least two points and two workers")
    project_ids={spec["project_id"] for spec in specs};roots={str(Path(spec["artifact_root"]).resolve()) for spec in specs}
    if len(project_ids)!=1 or len(roots)!=1:raise ValueError("parallel curve points must share one project and artifact root")
    if len({spec["run_id"] for spec in specs})!=len(specs):raise ValueError("parallel curve point run IDs must be unique")
    group_id=uuid.uuid4().hex;root=Path(specs[0]["artifact_root"])/"dino-parallel-point-sweep-v1"/specs[0]["project_id"]/group_id
    manifest={"schema":"DINO_PARALLEL_POINT_SWEEP_V1","group_id":group_id,"project_id":specs[0]["project_id"],
        "worker_count":max_workers,"status":"RUNNING","elapsed_seconds":0.0,
        "points":[{"variant_id":spec["variant_label"],"rpm":spec["rpm"],"run_id":spec["run_id"],"status":"NOT_STARTED",
                    "identity_sha256":spec.get("identity_sha256")} for spec in specs]}
    manifest_path=root/"dispatch.json";_atomic_json(manifest_path,manifest)
    started=time.monotonic();ctx=multiprocessing.get_context("spawn");rows={};last_progress={}
    with ctx.Manager() as manager:
        stops=[manager.Event() for _ in specs]
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers,mp_context=ctx) as executor:
            futures={executor.submit(_parallel_curve_point,spec,stop):i for i,(spec,stop) in enumerate(zip(specs,stops))}
            try:
                while not all(future.done() for future in futures):
                    elapsed=time.monotonic()-started
                    if elapsed>=total_budget_seconds or (cancel_event is not None and cancel_event.is_set()):
                        for stop in stops:stop.set()
                    if progress:
                        for index,spec in enumerate(specs):
                            run_dir=Path(spec["artifact_root"])/"exploratory-workflow-v1"/spec["project_id"]/spec["run_id"]
                            try:run_doc=json.loads((run_dir/"run.json").read_text(encoding="utf-8"))
                            except (OSError,ValueError):continue
                            cycle_count=run_doc.get("cycles_completed",0)
                            key=(index,cycle_count,run_doc.get("status"))
                            if key!=last_progress.get(index):
                                last_progress[index]=key
                                progress({"point_index":index+1,"point_count":len(specs),"rpm":spec["rpm"],
                                    "variant_label":spec["variant_label"],"point":{"classification":run_doc.get("classification"),
                                    "cycles_completed":cycle_count,"status":run_doc.get("status")}})
                    for future,index in futures.items():
                        if future.done() and index not in rows:rows[index]=future.result()
                    manifest["elapsed_seconds"]=elapsed
                    manifest["points"]=[{**manifest["points"][i],**rows[i]} if i in rows else manifest["points"][i] for i in range(len(specs))]
                    _atomic_json(manifest_path,manifest);time.sleep(.2)
                for future,index in futures.items():
                    if index not in rows:rows[index]=future.result()
            except Exception as exc:
                for stop in stops:stop.set()
                manifest["status"]="FAILED"
                manifest["failure"]={"type":type(exc).__name__,"message":str(exc)}
                manifest["elapsed_seconds"]=time.monotonic()-started
                manifest["points"]=[
                    {**manifest["points"][i],**rows[i]} if i in rows else manifest["points"][i]
                    for i in range(len(specs))
                ]
                _atomic_json(manifest_path,manifest)
                raise
    manifest["elapsed_seconds"]=time.monotonic()-started
    manifest["points"]=[{**manifest["points"][i],**rows[i]} for i in range(len(specs))]
    manifest["status"]="COMPLETE" if all(row.get("status")=="COMPLETE" for row in manifest["points"]) else "PARTIAL"
    _atomic_json(manifest_path,manifest)
    return {"schema":"DINO_PARALLEL_POINT_SWEEP_RESULT_V1","status":manifest["status"],
        "classification":"EXPLORATORY_PARALLEL_POINT_SWEEP","mode":"EXPLORATORY",
        "scientific_validation":"NOT_CLAIMED","periodicity":"NOT_EVALUATED",
        "elapsed_seconds":manifest["elapsed_seconds"],"points":manifest["points"],
        "parallel_manifest":str(manifest_path),"parallel_workers":max_workers,
        "bindings":{"project_id":manifest["project_id"]},"curve_availability":"EXPLORATORY_CURVE_PARTIAL"}
