from __future__ import annotations
import csv,json,io
import hashlib
import html
import math
from pathlib import Path
import uuid
from PySide6.QtCore import Qt,Signal,QRect,QBuffer,QIODevice
from PySide6.QtGui import QPixmap,QColor,QPainter,QPen,QImage,QFontMetrics,QImageWriter
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QGroupBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,
    QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QTabWidget,QScrollArea,QFrame,QAbstractItemView,QPlainTextEdit,QGridLayout)
from .plot import CurvePlot
from .performance_curves import PowerCurvePanel
from .services import load_results,run_background
from .preferences import artifact_root,impl2_historical_report_candidate,settings
from .technical_report import (write_technical_report,write_technical_report_pdf,
    write_study_comparison_report_pdf)
from .parametric_study_snapshot import SNAPSHOT_SCHEMA as PARAMETRIC_STUDY_SNAPSHOT_SCHEMA
from .parametric_factorial_snapshot import SNAPSHOT_SCHEMA as PARAMETRIC_FACTORIAL_SNAPSHOT_SCHEMA
from .comparison_snapshot import SNAPSHOT_SCHEMA as CROSS_STUDY_CSV_SNAPSHOT_SCHEMA
from ..exploratory_workflow import import_exploratory_runs
from .. import measurement_data
from ..engine_project import validate_project
from .presentation import display_value,field_label,format_number,state_label as _state_label

METRICS={"Potencia de freno (kW)":"brake_power","Torque (N·m)":"brake_torque","IMEP (kPa)":"IMEP","FMEP (kPa)":"FMEP","BMEP (kPa)":"BMEP","BSFC (g/kWh)":"BSFC"}
_CROSS_STUDY_NO_ENDPOINT="__DINO_CROSS_STUDY_NO_ENDPOINT__"

def _nonconverged(point):
    """Treat both explicit non-convergence and too-short horizons as transient."""
    return (point.get("classification") in {
        "MAX_CYCLES_NONCONVERGED", "NOT_CONVERGED",
        "EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
    } or point.get("periodicity") in {"NOT_CONVERGED", "INSUFFICIENT_CYCLES"})


def _referenced_curve_rpms(project,data):
    """Return a saved RPM grid only for results referenced by this project.

    A recipe must not add NOT_STARTED points to unrelated local history runs;
    that made a valid same-RPM exploratory pair look incompatible at empty RPMs.
    """
    recipe=project.get("simulation_recipes",{}).get("rpm_curve_v1",{})
    rpms=recipe.get("rpms")
    if not isinstance(rpms,list) or not rpms:return None
    referenced={ref.get("artifact_sha256") for ref in project.get("result_references",[])
                if isinstance(ref,dict) and isinstance(ref.get("artifact_sha256"),str)}
    imported={row.get("result_sha256") for row in data.get("points",[])
              if isinstance(row,dict)}
    if not imported or None in imported or not imported.issubset(referenced):return None
    return list(rpms)


_STUDY_COMPARE_CONTEXT=("fuel_id","afr_kg_air_per_kg_fuel","total_finite_volume_cells",
    "cycles_requested","solver_identity_sha256","implementation_identity_sha256")
_STUDY_COMPARE_METRICS={"brake_power":("Potencia de freno","kW"),
    "brake_torque":("Torque de freno","N·m"),"BMEP":("BMEP","kPa")}
_STUDY_EXPORT_FIELDS=("study_schema","study_id","project_id","design_method","manifest_path",
    "manifest_sha256","baseline_engine_identity_sha256","parameter_id","parameter_label",
    "parameter_unit","point_index","design_value","design_unit","factor_values_json","rpm",
    "run_id","source_run_id","execution_status","classification","periodicity","cycles_completed",
    "engine_identity_sha256","identity_sha256","result_sha256","result_artifact_sha256",
    "run_directory","reused_verified","source_verified","source_verification","brake_power_kw","brake_torque_nm","BMEP_kpa",
    "scientific_validation")
_FACTORIAL_EFFECTS_CSV_FIELDS=("csv_schema","record_type","study_schema","study_id","project_id",
    "design_method","manifest_path","manifest_sha256","baseline_engine_identity_sha256",
    "scientific_validation","rpm","point_index","design_label","parameter_id","parameter_label",
    "parameter_unit","factor_values_json","factor_a_id","factor_a_label","factor_a_value","factor_a_unit",
    "factor_b_id","factor_b_label","factor_b_value","factor_b_unit","run_id","source_run_id",
    "source_project_id","execution_status","classification","periodicity","cycles_completed","source_path",
    "engine_identity_sha256","identity_sha256","result_sha256","result_artifact_sha256","source_verified",
    "brake_power_kw","brake_power_status","brake_power_qualification","brake_torque_nm",
    "brake_torque_status","brake_torque_qualification","BMEP_kpa","BMEP_status","BMEP_qualification",
    "metric_id","metric_label","metric_unit","contrast_term","contrast_value","contrast_unit",
    "contrast_status","contrast_formula","contrast_reason","contrast_source_run_ids_json",
    "contrast_source_result_sha256s_json")
_STUDY_FILTER_MISSING="__DINO_MISSING_RECORDED_VALUE__"
_CROSS_STUDY_CSV_FIELDS=("comparison_schema","baseline_engine_identity_sha256","row_type",
    "study_a_id","study_a_manifest_path","study_a_manifest_sha256","point_a_index","point_a_run_id",
    "point_a_source_run_id","point_a_design_value","point_a_design_unit","point_a_factor_values_json",
    "point_a_classification","point_a_periodicity","point_a_cycles_completed","point_a_engine_identity_sha256",
    "point_a_identity_sha256","point_a_result_sha256","point_a_result_artifact_sha256","point_a_run_directory","point_a_source_verified",
    "study_b_id","study_b_manifest_path","study_b_manifest_sha256","point_b_index","point_b_run_id",
    "point_b_source_run_id","point_b_design_value","point_b_design_unit","point_b_factor_values_json",
    "point_b_classification","point_b_periodicity","point_b_cycles_completed","point_b_engine_identity_sha256",
    "point_b_identity_sha256","point_b_result_sha256","point_b_result_artifact_sha256","point_b_run_directory","point_b_source_verified",
    "rpm","pairing_status","pairing_reason","brake_power_a_kw","brake_power_b_kw","brake_power_delta_kw",
    "brake_torque_a_nm","brake_torque_b_nm","brake_torque_delta_nm","BMEP_a_kpa","BMEP_b_kpa",
    "BMEP_delta_kpa","scientific_validation")


def _build_cross_study_comparison_csv(comparison):
    """Flatten a verified comparison without rounding or synthesizing pair data."""
    if not isinstance(comparison,dict) or comparison.get("schema")!="DINO_PARAMETRIC_CROSS_STUDY_COMPARISON_V1":
        raise ValueError("comparación paramétrica no compatible")
    studies=comparison.get("studies")
    if not isinstance(studies,list) or not 2<=len(studies)<=4:
        raise ValueError("la comparación debe conservar entre dos y cuatro estudios")
    by_id={study.get("study_id"):study for study in studies}
    if len(by_id)!=len(studies) or None in by_id:
        raise ValueError("identidad de estudio ambigua en la comparación")
    base=comparison.get("baseline_engine_identity_sha256")
    for study in studies:
        try:
            manifest_raw=Path(study["manifest_path"]).read_bytes()
            if hashlib.sha256(manifest_raw).hexdigest()!=study.get("manifest_sha256"):
                raise ValueError(f"cambió el manifiesto de {study.get('study_id')}")
            live_manifest=json.loads(manifest_raw.decode("utf-8"))
            if (live_manifest.get("schema")!="DINO_PARAMETRIC_DESIGN_STUDY_V1" or
                    live_manifest.get("study_id")!=study.get("study_id") or
                    live_manifest.get("baseline_engine_identity_sha256")!=base):
                raise ValueError(f"identidad o baseline del manifiesto cambió para {study.get('study_id')}")
            saved_manifest=study.get("manifest")
            if saved_manifest is not None and live_manifest!=saved_manifest:
                raise ValueError(f"el contenido del manifiesto ya no coincide con la comparación de {study.get('study_id')}")
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as exc:
            raise ValueError(f"no se puede verificar el manifiesto de {study.get('study_id')}: {exc}") from exc
        for point in study.get("points",[]):
            if not point.get("source_verified"):
                continue
            try:
                source_dir=Path(point["run_directory"])
                result_raw=(source_dir/"result.json").read_bytes()
                run_meta=json.loads((source_dir/"run.json").read_text(encoding="utf-8"))
                result=json.loads(result_raw)
                result_hash=hashlib.sha256(result_raw).hexdigest()
                expected_run=point.get("source_run_id") or point.get("run_id")
                expected_identity=point.get("identity_sha256") or point.get("engine_identity_sha256")
                if (result_hash!=point.get("result_artifact_sha256") or
                        result_hash!=run_meta.get("result_sha256") or
                        (point.get("result_sha256") is not None and result_hash!=point.get("result_sha256")) or
                        result.get("bindings",{}).get("run_id")!=expected_run or
                        result.get("bindings",{}).get("identity_sha256")!=expected_identity):
                    raise ValueError("hash de artifact o identidad de corrida cambió")
            except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError) as exc:
                raise ValueError(f"fuente verificada modificada para {study.get('study_id')} · {point.get('run_id')}: {exc}") from exc

    def point_fields(prefix,study_id,point):
        fields={f"study_{prefix}_id":"",f"study_{prefix}_manifest_path":"",
            f"study_{prefix}_manifest_sha256":""}
        point_columns=("index","run_id","source_run_id","design_value","design_unit","factor_values_json",
            "classification","periodicity","cycles_completed","engine_identity_sha256","identity_sha256",
            "result_sha256","result_artifact_sha256","run_directory","source_verified")
        for key in point_columns:fields[f"point_{prefix}_{key}"]=""
        if point is None:return fields
        study=by_id[study_id];source=point.get("source_manifest_point") or point
        fields.update({f"study_{prefix}_id":study_id,
            f"study_{prefix}_manifest_path":study.get("manifest_path"),
            f"study_{prefix}_manifest_sha256":study.get("manifest_sha256"),
            f"point_{prefix}_index":point.get("index"),
            f"point_{prefix}_run_id":point.get("run_id"),
            f"point_{prefix}_source_run_id":point.get("source_run_id") or point.get("run_id"),
            f"point_{prefix}_design_value":source.get("value",point.get("value")),
            f"point_{prefix}_design_unit":source.get("unit",point.get("unit")),
            f"point_{prefix}_factor_values_json":json.dumps(source.get("factor_values") or [],
                ensure_ascii=False,allow_nan=False,separators=(",",":")),
            f"point_{prefix}_classification":point.get("classification") or point.get("status"),
            f"point_{prefix}_periodicity":point.get("periodicity"),
            f"point_{prefix}_cycles_completed":point.get("cycles_completed"),
            f"point_{prefix}_engine_identity_sha256":point.get("engine_identity_sha256"),
            f"point_{prefix}_identity_sha256":point.get("identity_sha256"),
            f"point_{prefix}_result_sha256":point.get("result_sha256"),
            f"point_{prefix}_result_artifact_sha256":point.get("result_artifact_sha256"),
            f"point_{prefix}_run_directory":point.get("run_directory"),
            f"point_{prefix}_source_verified":bool(point.get("source_verified"))})
        return fields

    def record(row_type,study_a,point_a,study_b,point_b,rpm,pairing_status,pairing_reason,metrics=None):
        row={key:"" for key in _CROSS_STUDY_CSV_FIELDS}
        row.update({"comparison_schema":comparison["schema"],
            "baseline_engine_identity_sha256":base,"row_type":row_type,"rpm":rpm,
            "pairing_status":pairing_status,"pairing_reason":pairing_reason,
            "scientific_validation":comparison.get("scientific_validation","NOT_CLAIMED")})
        row.update(point_fields("a",study_a,point_a));row.update(point_fields("b",study_b,point_b))
        for metric,stem in (("brake_power","brake_power"),("brake_torque","brake_torque"),("BMEP","BMEP")):
            item=(metrics or {}).get(metric,{})
            pa=str((point_a or {}).get("periodicity") or "").startswith("PERIOD_1")
            pb=str((point_b or {}).get("periodicity") or "").startswith("PERIOD_1")
            a=item.get("a") if pa else None;b=item.get("b") if pb else None
            delta=item.get("delta") if pa and pb else None
            for side,value in (("a",a),("b",b),("delta",delta)):
                column=f"{stem}_{side}_{'kw' if metric=='brake_power' else 'nm' if metric=='brake_torque' else 'kpa'}"
                row[column]=value if isinstance(value,(int,float)) and math.isfinite(float(value)) else ""
        return row

    rows=[]
    for pair in comparison.get("pairs",[]):
        rows.append(record("EXACT_PAIR",pair["study_a"],pair["point_a"],pair["study_b"],pair["point_b"],
            pair.get("rpm"),pair.get("pairing"),"",pair.get("metrics")))
    first_id=studies[0]["study_id"]
    for item in comparison.get("unpaired",[]):
        if item.get("study_id")==first_id:
            rows.append(record("UNPAIRED",first_id,item.get("point"),"",None,
                (item.get("point") or {}).get("rpm"),"NO_EXACT_COMPATIBLE_PAIR",item.get("reason")))
        else:
            rows.append(record("UNPAIRED",first_id,None,item["study_id"],item.get("point"),
                (item.get("point") or {}).get("rpm"),"NO_EXACT_COMPATIBLE_PAIR",item.get("reason")))
    return rows


def _factorial_effects_from_study(manifest,imported_points):
    """Return descriptive 2×2 contrasts only from four exact, verified PERIOD_1 points."""
    if not isinstance(manifest,dict) or manifest.get("design_method")!="FACTORIAL_2X2_V1":
        return None
    factors=manifest.get("factors")
    axes=[]
    if isinstance(factors,list) and len(factors)==2:
        for factor in factors:
            parameter=factor.get("parameter") or {}
            values=factor.get("values")
            if (not isinstance(values,list) or len(values)!=2 or
                    any(type(value) not in (int,float) or not math.isfinite(float(value)) for value in values) or
                    values[0]==values[1] or not parameter.get("id")):
                axes=[];break
            axes.append({"id":parameter["id"],"label":parameter.get("label") or parameter["id"],
                "unit":parameter.get("unit") or "","values":list(values)})
    if len(axes)!=2:
        return {"status":"UNAVAILABLE","reason":"El manifiesto no contiene dos factores con dos niveles exactos.",
            "factors":axes,"metrics":[]}
    combos=[(axes[0]["values"][i],axes[1]["values"][j]) for i in range(2) for j in range(2)]
    imported_by_run={}
    for row in imported_points or []:
        if row.get("run_id") is not None:imported_by_run.setdefault(str(row["run_id"]),[]).append(row)
    outcomes={};failure=None
    for point in manifest.get("points",[]):
        values=point.get("factor_values") or []
        by_id={item.get("parameter_id"):item.get("value") for item in values if isinstance(item,dict)}
        if any(axis["id"] not in by_id for axis in axes):
            failure="Uno o más diseños no identifican ambos factores.";break
        if any(type(by_id[axis["id"]]) not in (int,float) or not math.isfinite(float(by_id[axis["id"]]))
                for axis in axes):
            failure="Uno o más diseños contienen niveles factoriales no numéricos o no finitos.";break
        combo=(by_id[axes[0]["id"]],by_id[axes[1]["id"]])
        if combo not in combos or combo in outcomes:
            failure="La matriz factorial tiene una combinación duplicada o fuera de sus niveles declarados.";break
        if point.get("status") not in {"COMPLETE","CACHED"}:
            failure=f"Punto factorial {point.get('index')} no terminal: {point.get('status') or 'estado ausente'}.";break
        if point.get("status")=="CACHED" and not point.get("reused_verified"):
            failure=f"Punto factorial {point.get('index')} usa un resultado histórico no verificado.";break
        run_id=point.get("source_run_id") or point.get("historical_source_run_id") or point.get("run_id")
        candidates=imported_by_run.get(str(run_id),[]);imported=None
        expected_dir=point.get("run_directory")
        expected_hash=point.get("result_sha256") or point.get("result_artifact_sha256")
        for candidate in candidates:
            if expected_dir and candidate.get("artifact_directory"):
                if Path(expected_dir).resolve()!=Path(candidate["artifact_directory"]).resolve():continue
            if expected_hash and candidate.get("result_sha256")!=expected_hash:continue
            if candidate.get("rpm")!=manifest.get("rpm"):continue
            imported=candidate;break
        if imported is None:
            failure=f"Falta el artifact importado exacto del punto factorial {point.get('index')} ({run_id or 'run no informado'}).";break
        if not expected_dir or not expected_hash:
            failure=f"Falta ruta/hash fuente en el punto factorial {point.get('index')}.";break
        try:
            source=Path(expected_dir).resolve();raw=(source/"result.json").read_bytes()
            result=json.loads(raw);run_meta=json.loads((source/"run.json").read_text(encoding="utf-8"))
            digest=hashlib.sha256(raw).hexdigest()
            identity=point.get("identity_sha256") or point.get("engine_identity_sha256")
            if (digest!=expected_hash or digest!=run_meta.get("result_sha256") or
                    digest!=imported.get("result_sha256") or result.get("schema")!="DINO_ENGINEERING_RUN_V1" or
                    result.get("status")!="COMPLETE" or result.get("bindings",{}).get("run_id")!=run_id or
                    result.get("bindings",{}).get("identity_sha256")!=identity or
                    imported.get("identity_sha256")!=identity):
                failure=f"Hash o identidad de fuente no verificado en el punto factorial {point.get('index')}.";break
        except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
            failure=f"No se pudo verificar la fuente del punto factorial {point.get('index')}.";break
        if imported.get("periodicity")!="PERIOD_1":
            failure=failure or (f"Punto factorial {point.get('index')} no periódico PERIOD_1: "
                f"{imported.get('periodicity') or 'periodicidad no informada'}. No se calculan efectos.")
        outcomes[combo]={"manifest":point,"imported":imported}
    if len(outcomes)!=4 or set(outcomes)!=set(combos):
        failure=failure or "Falta al menos uno de los cuatro diseños factoriales exactos."
    ordered=[outcomes.get(combo) for combo in combos]
    if failure is None:
        contexts=[row["imported"] for row in ordered]
        for key in _STUDY_COMPARE_CONTEXT:
            values=[row.get(key) for row in contexts]
            if any(value is None for value in values) or len(set(map(str,values)))!=1:
                failure=f"Condiciones incompatibles o ausentes entre los cuatro puntos: {key}.";break
        rpms=[row.get("rpm") for row in contexts]
        if failure is None and (any(value is None for value in rpms) or len(set(rpms))!=1):
            failure="Los cuatro puntos no comparten una RPM exacta."
    metric_rows=[]
    definitions=(
        ("brake_power","Potencia de freno","kW"),
        ("brake_torque","Torque de freno","N·m"),
        ("BMEP","BMEP","kPa"),
    )
    for metric,label,unit in definitions:
        formula_a=f"((y(A₂,B₁)+y(A₂,B₂))−(y(A₁,B₁)+y(A₁,B₂)))/2 · niveles A: {axes[0]['values']}"
        formula_b=f"((y(A₁,B₂)+y(A₂,B₂))−(y(A₁,B₁)+y(A₂,B₁)))/2 · niveles B: {axes[1]['values']}"
        formula_interaction="(y(A₂,B₂)−y(A₂,B₁))−(y(A₁,B₂)−y(A₁,B₁))"
        row={"metric":metric,"label":label,"unit":unit,"status":"UNAVAILABLE",
            "reason":failure,"effects":[]}
        if failure is None:
            values=[];reason=None
            for outcome in ordered:
                sample=outcome["imported"];value=sample.get(metric);status=sample.get(metric+"_status")
                if (status!="DEFINED" or type(value) not in (int,float) or not math.isfinite(float(value))):
                    reason=f"La métrica {label} no está definida en los cuatro resultados periódicos.";break
                values.append(float(value))
            if reason is None:
                y11,y12,y21,y22=values
                row.update(status="DEFINED",reason=None,effects=[
                    {"term":f"Efecto principal · {axes[0]['label']}","value":((y21+y22)-(y11+y12))/2,
                     "unit":unit,"formula":formula_a},
                    {"term":f"Efecto principal · {axes[1]['label']}","value":((y12+y22)-(y11+y21))/2,
                     "unit":unit,"formula":formula_b},
                    {"term":"Interacción A×B","value":(y22-y21)-(y12-y11),
                     "unit":unit,"formula":formula_interaction},
                ])
            else:row["reason"]=reason
        if row["status"]!="DEFINED":
            row["effects"]=[{"term":f"Efecto principal · {axes[0]['label']}","value":None,"unit":unit,"formula":formula_a},
                {"term":f"Efecto principal · {axes[1]['label']}","value":None,"unit":unit,"formula":formula_b},
                {"term":"Interacción A×B","value":None,"unit":unit,"formula":formula_interaction}]
        metric_rows.append(row)
    has_defined=any(row["status"]=="DEFINED" for row in metric_rows)
    overall_reason=failure or (None if has_defined else "Ninguna de las tres métricas está definida en los cuatro resultados.")
    return {"schema":"DINO_PARAMETRIC_FACTORIAL_EFFECTS_V1","study_id":manifest.get("study_id"),
        "status":"AVAILABLE" if failure is None and has_defined else "UNAVAILABLE","reason":overall_reason,
        "rpm":manifest.get("rpm"),"factors":axes,"metrics":metric_rows,
        "point_sources_verified":len(outcomes)==4 and set(outcomes)==set(combos),
        "verified_points":[outcomes[combo] for combo in combos if combo in outcomes],
        "point_ids":[(row or {}).get("manifest",{}).get("source_run_id") or
            (row or {}).get("manifest",{}).get("run_id") for row in ordered]}


def _build_factorial_effects_csv(manifest_path,manifest_sha256,manifest,imported_points=()):
    """Build four exact source rows and qualified descriptive contrast rows."""
    if not isinstance(manifest,dict) or manifest.get("design_method")!="FACTORIAL_2X2_V1":
        raise ValueError("el manifiesto no es un estudio factorial 2×2")
    try:
        source=Path(manifest_path).resolve();raw=source.read_bytes()
        digest=hashlib.sha256(raw).hexdigest();live=json.loads(raw.decode("utf-8"))
    except (OSError,TypeError,ValueError,json.JSONDecodeError) as exc:
        raise ValueError(f"no se pudo verificar el manifiesto factorial: {exc}") from exc
    if digest!=manifest_sha256 or live!=manifest:
        raise ValueError("el manifiesto factorial cambió desde que se abrió el estudio")
    effects=_factorial_effects_from_study(live,imported_points)
    if not effects or not effects.get("point_sources_verified") or len(effects.get("verified_points",[]))!=4:
        raise ValueError((effects or {}).get("reason") or "no se verificaron los cuatro artifacts factoriales exactos")
    axes=effects["factors"];parameter=live.get("parameter") or {}
    base={"csv_schema":"DINO_PARAMETRIC_FACTORIAL_EXPORT_V1","study_schema":live.get("schema"),
        "study_id":live.get("study_id"),"project_id":live.get("project_id"),
        "design_method":live.get("design_method"),"manifest_path":str(source),
        "manifest_sha256":digest,"baseline_engine_identity_sha256":live.get("baseline_engine_identity_sha256"),
        "scientific_validation":live.get("scientific_validation","NOT_CLAIMED"),"rpm":live.get("rpm"),
        "parameter_id":parameter.get("id"),"parameter_label":parameter.get("label"),
        "parameter_unit":parameter.get("unit"),"source_verified":True}
    rows=[];verified=effects["verified_points"]
    metric_fields={"brake_power":("brake_power_kw","brake_power_status","brake_power_qualification"),
        "brake_torque":("brake_torque_nm","brake_torque_status","brake_torque_qualification"),
        "BMEP":("BMEP_kpa","BMEP_status","BMEP_qualification")}
    for outcome in verified:
        point=outcome["manifest"];sample=outcome["imported"]
        factor_values={item.get("parameter_id"):item for item in point.get("factor_values",[]) if isinstance(item,dict)}
        a=factor_values[axes[0]["id"]];b=factor_values[axes[1]["id"]]
        is_periodic=sample.get("periodicity")=="PERIOD_1"
        row={**base,"record_type":"POINT","point_index":point.get("index"),
            "design_label":f"Diseño {int(point.get('index',0))+1}",
            "factor_values_json":json.dumps(point.get("factor_values") or [],ensure_ascii=False,
                allow_nan=False,separators=(",",":")),
            "factor_a_id":axes[0]["id"],"factor_a_label":axes[0]["label"],"factor_a_value":a.get("value"),
            "factor_a_unit":a.get("unit") or axes[0]["unit"],"factor_b_id":axes[1]["id"],
            "factor_b_label":axes[1]["label"],"factor_b_value":b.get("value"),
            "factor_b_unit":b.get("unit") or axes[1]["unit"],"run_id":point.get("run_id"),
            "source_run_id":point.get("source_run_id") or point.get("historical_source_run_id") or point.get("run_id"),
            "source_project_id":point.get("historical_source_project_id") or live.get("project_id"),
            "execution_status":point.get("status"),"classification":sample.get("classification"),
            "periodicity":sample.get("periodicity"),"cycles_completed":sample.get("cycles_completed"),
            "source_path":point.get("run_directory"),"engine_identity_sha256":point.get("engine_identity_sha256"),
            "identity_sha256":point.get("identity_sha256") or point.get("engine_identity_sha256"),
            "result_sha256":point.get("result_sha256"),
            "result_artifact_sha256":point.get("result_artifact_sha256") or point.get("result_sha256")}
        for metric,(value_field,status_field,qualification_field) in metric_fields.items():
            value=sample.get(metric);metric_status=sample.get(metric+"_status") or "UNDEFINED"
            defined=is_periodic and metric_status=="DEFINED" and type(value) in (int,float) and math.isfinite(float(value))
            row[value_field]=value if defined else ""
            row[status_field]=metric_status
            row[qualification_field]="PERIOD_1_DEFINED" if defined else (
                "WITHHELD_NONPERIODIC" if not is_periodic else "UNDEFINED_OR_INVALID")
        rows.append(row)
    # Bind each descriptive contrast to the exact four POINT rows written above.
    # ``verified`` contains nested {manifest, imported} outcomes, not flat CSV rows.
    all_source_ids=json.dumps([row.get("source_run_id") for row in rows],ensure_ascii=False,
        separators=(",",":"))
    all_source_hashes=json.dumps([row.get("result_sha256") for row in rows],ensure_ascii=False,
        separators=(",",":"))
    metric_by_id={metric["metric"]:metric for metric in effects["metrics"]}
    for metric_id,metric in metric_by_id.items():
        for effect in metric["effects"]:
            value=effect.get("value")
            rows.append({**base,"record_type":"CONTRAST","metric_id":metric_id,
                "metric_label":metric.get("label"),"metric_unit":metric.get("unit"),
                "contrast_term":effect.get("term"),
                "contrast_value":value if metric.get("status")=="DEFINED" and type(value) in (int,float) and math.isfinite(float(value)) else "",
                "contrast_unit":effect.get("unit"),
                "contrast_status":"DESCRIPTIVE_DEFINED" if metric.get("status")=="DEFINED" else "UNAVAILABLE",
                "contrast_formula":effect.get("formula"),
                "contrast_reason":metric.get("reason") or effects.get("reason") or "",
                "contrast_source_run_ids_json":all_source_ids,
                "contrast_source_result_sha256s_json":all_source_hashes})
    return rows


def _write_factorial_effects_csv(path,rows):
    """Write a new factorial export without replacing an existing evidence file."""
    if len(rows)!=13 or sum(row.get("record_type")=="POINT" for row in rows)!=4 or \
            sum(row.get("record_type")=="CONTRAST" for row in rows)!=9:
        raise ValueError("la exportación factorial requiere exactamente cuatro puntos y nueve contrastes")
    with Path(path).open("x",encoding="utf-8-sig",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=_FACTORIAL_EFFECTS_CSV_FIELDS,extrasaction="raise")
        writer.writeheader();writer.writerows(rows)
    return Path(path)


def _build_parametric_study_export(manifest,manifest_path,manifest_sha256,selected_indexes,imported_points=()):
    """Build exact, provenance-bound CSV rows from a verified study snapshot."""
    if not isinstance(manifest,dict) or manifest.get("schema")!="DINO_PARAMETRIC_DESIGN_STUDY_V1":
        raise ValueError("manifiesto paramétrico no compatible")
    points=manifest.get("points")
    if not isinstance(points,list) or len(points)>30:
        raise ValueError("la exportación admite como máximo 30 puntos por estudio")
    indexes=sorted(set(selected_indexes))
    if not indexes or any(type(index) is not int or index<0 or index>=len(points) for index in indexes):
        raise ValueError("seleccioná al menos un punto válido de la matriz")
    parameter=manifest.get("parameter") or {}
    imported_by_run={}
    for row in imported_points:
        run_id=row.get("run_id")
        if run_id is not None:imported_by_run.setdefault(str(run_id),[]).append(row)
    exported=[]
    for index in indexes:
        point=points[index]
        run_id=point.get("source_run_id") or point.get("historical_source_run_id") or point.get("run_id")
        imported=None
        source_verification="NOT_LOADED"
        expected_directory=point.get("run_directory")
        candidates=imported_by_run.get(str(run_id),[])
        for candidate in candidates:
            candidate_directory=candidate.get("artifact_directory")
            if expected_directory and candidate_directory:
                if Path(expected_directory).resolve()!=Path(candidate_directory).resolve():continue
            expected_hash=point.get("result_sha256") or point.get("result_artifact_sha256")
            if expected_hash and candidate.get("result_sha256")!=expected_hash:continue
            expected_rpm=point.get("rpm",manifest.get("rpm"))
            if expected_rpm is not None and candidate.get("rpm")!=expected_rpm:continue
            imported=candidate;break
        if candidates and imported is None:source_verification="NO_EXACT_ARTIFACT_MATCH"
        if imported is not None:
            try:
                source_dir=Path(imported["artifact_directory"]).resolve()
                result_raw=(source_dir/"result.json").read_bytes();result=json.loads(result_raw)
                run_meta=json.loads((source_dir/"run.json").read_text(encoding="utf-8"))
                result_hash=hashlib.sha256(result_raw).hexdigest()
                expected_identity=point.get("identity_sha256") or point.get("engine_identity_sha256")
                expected_artifact=point.get("result_artifact_sha256")
                expected_result=point.get("result_sha256") or expected_artifact
                if (result_hash!=run_meta.get("result_sha256") or
                        (expected_artifact is not None and result_hash!=expected_artifact) or
                        (expected_result is not None and result_hash!=expected_result) or
                        result.get("bindings",{}).get("run_id")!=run_id or
                        result.get("bindings",{}).get("identity_sha256")!=expected_identity):
                    raise ValueError("source hash or identity changed")
                source_verification="VERIFIED_HASH_AND_IDENTITY"
            except (OSError,ValueError,TypeError,KeyError,json.JSONDecodeError):
                imported=None;source_verification="SOURCE_ARTIFACT_CHANGED"
        metrics={}
        periodic=str((imported or {}).get("periodicity") or point.get("periodicity") or "").startswith("PERIOD_1")
        for metric in _STUDY_COMPARE_METRICS:
            value=(imported or {}).get(metric);status=(imported or {}).get(metric+"_status")
            metrics[metric]=value if periodic and status=="DEFINED" and isinstance(value,(int,float)) and math.isfinite(float(value)) else ""
        exported.append({
            "study_schema":manifest["schema"],"study_id":manifest.get("study_id"),"project_id":manifest.get("project_id"),
            "design_method":manifest.get("design_method","GEOMETRY_V1"),"manifest_path":str(manifest_path),
            "manifest_sha256":manifest_sha256,"baseline_engine_identity_sha256":manifest.get("baseline_engine_identity_sha256"),
            "parameter_id":parameter.get("id"),"parameter_label":parameter.get("label"),"parameter_unit":parameter.get("unit"),
            "point_index":point.get("index",index),"design_value":point.get("value"),"design_unit":point.get("unit"),
            "factor_values_json":json.dumps(point.get("factor_values") or [],ensure_ascii=False,allow_nan=False,separators=(",",":")),
            "rpm":point.get("rpm",manifest.get("rpm")),"run_id":point.get("run_id"),"source_run_id":run_id,
            "execution_status":point.get("status"),"classification":(imported or {}).get("classification") or point.get("classification"),
            "periodicity":(imported or {}).get("periodicity") or point.get("periodicity"),
            "cycles_completed":(imported or {}).get("cycles_completed",point.get("cycles_completed")),
            "engine_identity_sha256":point.get("engine_identity_sha256"),
            "identity_sha256":point.get("identity_sha256") or point.get("engine_identity_sha256"),
            "result_sha256":point.get("result_sha256") or (imported or {}).get("result_sha256"),
            "result_artifact_sha256":point.get("result_artifact_sha256"),
            "run_directory":point.get("run_directory"),"reused_verified":bool(point.get("reused_verified")),
            "source_verified":source_verification=="VERIFIED_HASH_AND_IDENTITY",
            "source_verification":source_verification,"brake_power_kw":metrics["brake_power"],
            "brake_torque_nm":metrics["brake_torque"],"BMEP_kpa":metrics["BMEP"],
            "scientific_validation":manifest.get("scientific_validation","NOT_CLAIMED")})
    return exported


def _load_verified_study_comparison(references):
    """Verify project-bound manifests and sources, then compare exact operating pairs."""
    if not isinstance(references,list) or not 2<=len(references)<=4:
        raise ValueError("seleccioná entre dos y cuatro estudios guardados")
    studies=[];source_dirs=[]
    for reference in references:
        path=Path(reference["path"]).resolve();raw=path.read_bytes()
        digest=hashlib.sha256(raw).hexdigest()
        if digest!=reference.get("manifest_sha256"):
            raise ValueError(f"el SHA-256 del manifiesto {reference.get('study_id')} no coincide")
        manifest=json.loads(raw.decode("utf-8"))
        if (manifest.get("schema")!="DINO_PARAMETRIC_DESIGN_STUDY_V1" or
                manifest.get("study_id")!=reference.get("study_id") or
                manifest.get("project_id")!=reference.get("source_project_id")):
            raise ValueError("identidad o schema de un estudio no coincide con su referencia del proyecto")
        baseline=manifest.get("baseline_engine_identity_sha256")
        if not isinstance(baseline,str) or len(baseline)!=64 or any(c not in "0123456789abcdef" for c in baseline.lower()):
            raise ValueError(f"el estudio {manifest.get('study_id')} no conserva una identidad de baseline verificable")
        study_points=manifest.get("points")
        if not isinstance(study_points,list) or len(study_points)>30:
            raise ValueError("cada comparación admite como máximo 30 puntos por estudio")
        rows=[]
        for point_index,point in enumerate(study_points):
            rpm=point.get("rpm",manifest.get("rpm"))
            if type(rpm) not in (int,float) or not math.isfinite(float(rpm)) or rpm<=0:
                raise ValueError(f"RPM no verificable en {manifest.get('study_id')} punto {point.get('index')}")
            engine_id=point.get("engine_identity_sha256")
            if not isinstance(engine_id,str) or len(engine_id)!=64 or any(c not in "0123456789abcdef" for c in engine_id.lower()):
                raise ValueError(f"identidad de motor no verificable en {manifest.get('study_id')} punto {point.get('index')}")
            row={"index":point.get("index",point_index),"value":point.get("value"),"unit":point.get("unit"),
                "source_manifest_point":dict(point),
                "label":point.get("label"),"factor_values":point.get("factor_values"),"rpm":float(rpm),
                "status":point.get("status","NOT_STARTED"),"classification":point.get("classification"),
                "periodicity":point.get("periodicity","NOT_EVALUATED"),"cycles_completed":point.get("cycles_completed"),
                "run_id":point.get("run_id"),"source_run_id":point.get("source_run_id") or point.get("historical_source_run_id") or point.get("run_id"),
                "engine_identity_sha256":engine_id,"identity_sha256":point.get("identity_sha256") or engine_id,
                "result_sha256":point.get("result_sha256"),"result_artifact_sha256":point.get("result_artifact_sha256"),
                "run_directory":point.get("run_directory"),"metrics":{},"context":{},"source_verified":False}
            if point.get("status") in {"COMPLETE","CACHED"}:
                if not row["run_directory"]:raise ValueError("punto terminal sin ruta de artifact")
                run_dir=Path(row["run_directory"]).resolve();result_path=run_dir/"result.json";run_path=run_dir/"run.json"
                result_raw=result_path.read_bytes();run_meta=json.loads(run_path.read_text(encoding="utf-8"));result=json.loads(result_raw)
                artifact_hash=hashlib.sha256(result_raw).hexdigest()
                expected_result_sha=point.get("result_sha256") or run_meta.get("result_sha256")
                if (artifact_hash!=point.get("result_artifact_sha256") or
                        (point.get("result_sha256") is not None and run_meta.get("result_sha256")!=point.get("result_sha256")) or
                        artifact_hash!=run_meta.get("result_sha256") or
                        result.get("schema")!="DINO_ENGINEERING_RUN_V1" or result.get("status")!="COMPLETE" or
                        result.get("bindings",{}).get("identity_sha256")!=row["identity_sha256"] or
                        result.get("bindings",{}).get("run_id")!=row["source_run_id"]):
                    raise ValueError(f"source/hash/identidad no coincide en {manifest.get('study_id')} · {row['run_id']}")
                row["source_verified"]=True;row["run_directory"]=str(run_dir)
                row["result_sha256"]=expected_result_sha
                source_dirs.append(run_dir)
            rows.append(row)
        studies.append({"study_id":manifest["study_id"],"manifest_path":str(path),
            "manifest_sha256":digest,"source_project_id":manifest["project_id"],
            "baseline_engine_identity_sha256":baseline,"parameter":manifest.get("parameter",{}),
            "design_method":manifest.get("design_method","GEOMETRY_V1"),"manifest":manifest,"points":rows})
    baseline_ids={study["baseline_engine_identity_sha256"] for study in studies}
    if len(baseline_ids)!=1:
        raise ValueError("los estudios parten de baselines distintos; no se comparan como un mismo experimento")
    imported_by_path={}
    if source_dirs:
        from ..power_curve import import_curve_runs
        imported=import_curve_runs([str(path) for path in dict.fromkeys(source_dirs)])
        imported_by_path={str(Path(row.get("artifact_directory","")).resolve()).casefold():row
            for row in imported.get("points",[]) if row.get("artifact_directory")}
    for study in studies:
        for point in study["points"]:
            if not point["source_verified"]:continue
            imported=imported_by_path.get(str(Path(point["run_directory"]).resolve()).casefold())
            if imported is None or imported.get("run_id")!=point["source_run_id"]:
                raise ValueError(f"el importador no pudo re-verificar la fuente de {study['study_id']} · {point['run_id']}")
            if float(imported.get("rpm"))!=point["rpm"]:
                raise ValueError("RPM importada no coincide con la del manifiesto")
            point["classification"]=imported.get("classification") or point["classification"]
            point["periodicity"]=imported.get("periodicity") or point["periodicity"]
            point["cycles_completed"]=imported.get("cycles_completed",point["cycles_completed"])
            point["context"]={key:imported.get(key) for key in _STUDY_COMPARE_CONTEXT}
            point["result_sha256"]=imported.get("result_sha256") or point["result_sha256"]
            for metric in _STUDY_COMPARE_METRICS:
                value=imported.get(metric);status=imported.get(metric+"_status")
                periodic=str(point.get("periodicity","")).startswith("PERIOD_1")
                point["metrics"][metric]=value if periodic and status=="DEFINED" and isinstance(value,(int,float)) and math.isfinite(float(value)) else None
    pairs=[];matched=set();unpaired=[]
    for left_index,left_study in enumerate(studies):
        for right_study in studies[left_index+1:]:
            for left in left_study["points"]:
                for right in right_study["points"]:
                    if left["rpm"]!=right["rpm"]:continue
                    mismatches=[key for key in _STUDY_COMPARE_CONTEXT
                        if left["context"].get(key) is None or right["context"].get(key) is None or
                           left["context"].get(key)!=right["context"].get(key)]
                    if mismatches:continue
                    pair_metrics={}
                    for metric in _STUDY_COMPARE_METRICS:
                        a=left["metrics"].get(metric);b=right["metrics"].get(metric)
                        periodic_a=str(left.get("periodicity","")).startswith("PERIOD_1")
                        periodic_b=str(right.get("periodicity","")).startswith("PERIOD_1")
                        pair_metrics[metric]={"a":a,"b":b,"delta":(b-a if periodic_a and periodic_b and isinstance(a,(int,float)) and isinstance(b,(int,float)) else None)}
                    pairs.append({"study_a":left_study["study_id"],"point_a":left,
                        "study_b":right_study["study_id"],"point_b":right,"rpm":left["rpm"],
                        "metrics":pair_metrics,"pairing":"EXACT_RPM_AND_OPERATING_CONTEXT"})
                    matched.add((left_study["study_id"],left["index"]));matched.add((right_study["study_id"],right["index"]))
    for study in studies:
        for point in study["points"]:
            if (study["study_id"],point["index"]) not in matched:
                point["comparison_status"]="NO_EXACT_COMPATIBLE_PAIR"
                others=[other for other in studies if other is not study]
                same_rpm=[candidate for other in others for candidate in other["points"]
                    if candidate["rpm"]==point["rpm"]]
                if not same_rpm:
                    reason="No existe un punto de otro estudio en la misma RPM exacta."
                elif not point["source_verified"]:
                    reason=f"Punto {point.get('status')}: no hay artifact terminal verificado."
                else:
                    differences=set()
                    for candidate in same_rpm:
                        differences.update(key for key in _STUDY_COMPARE_CONTEXT
                            if point["context"].get(key) is None or candidate["context"].get(key) is None or
                               point["context"].get(key)!=candidate["context"].get(key))
                    reason=("Condiciones informadas incompatibles: "+", ".join(sorted(differences))+"."
                        if differences else "No existe fuente de resultados compatible.")
                unpaired.append({"study_id":study["study_id"],"point":point,"reason":reason})
    return {"schema":"DINO_PARAMETRIC_CROSS_STUDY_COMPARISON_V1",
        "baseline_engine_identity_sha256":next(iter(baseline_ids)),"studies":studies,
        "pairs":pairs,"unpaired":unpaired,
        "scientific_validation":"NOT_CLAIMED",
        "notice":"Emparejamiento exacto por RPM y condiciones de cálculo informadas. No hay interpolación ni efectos agregados; diferencias sólo para métricas definidas en puntos periódicos."}


class DiscreteAngleCellMap(QWidget):
    """QImage view of exact cell/angle observations; each pixel band holds one sample."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName("traceAngleCellMap");self.setMinimumHeight(240)
        self.angles=[];self.rows=[];self.image=QImage();self.value_range=None;self.raw_samples=[]
    def set_grid(self,angles,rows):
        self.angles=list(angles);self.rows=list(rows);self.raw_samples=[]
        finite=[float(v) for row in self.rows for v in row.get("values",[]) if v is not None and math.isfinite(float(v))]
        if not finite:
            self.value_range=None;self.image=QImage();self.update();return
        low=min(finite);high=max(finite);self.value_range=(low,high)
        width=max(2,min(1200,len(self.angles)*2));height=max(2,min(600,len(self.rows)*8));self.image=QImage(width,height,QImage.Format.Format_RGB32);self.image.fill(QColor("#182536"))
        raster=QPainter(self.image);xmin=self.angles[0] if self.angles else 0.;span=max(1e-9,(self.angles[-1]-xmin) if len(self.angles)>1 else 1.)
        groups={}
        for row in self.rows:groups.setdefault(row.get("group","run"),[]).append(row)
        group_height=height/max(1,len(groups));group_index=0
        for group,group_rows in groups.items():
            total=sum(max(1e-9,float(row.get("length_mm",1.))) for row in group_rows);cursor=group_index*group_height
            for row in group_rows:
                band=group_height*max(1e-9,float(row.get("length_mm",1.)))/total;y0=round(cursor);y1=max(y0+1,round(cursor+band));cursor+=band
                vals=row.get("values",[]);self.raw_samples.append({'label':row.get('label'),'values':list(vals),'angles_deg':list(self.angles),'position_m':row.get('position_m')})
                for j,value in enumerate(vals):
                    if value is None or not math.isfinite(float(value)):continue
                    x0=0 if j==0 else round((((self.angles[j-1]+self.angles[j])/2-xmin)/span)*width)
                    x1=width if j==len(vals)-1 else round((((self.angles[j]+self.angles[j+1])/2-xmin)/span)*width)
                    f=.5 if high==low else (float(value)-low)/(high-low);color=self._color(f)
                    raster.fillRect(QRect(max(0,x0),y0,max(1,min(width,x1)-max(0,x0)),min(height,y1)-y0),color)
            group_index+=1
        raster.end()
        self.update()
    @staticmethod
    def _color(value):
        stops=((0.,(35,55,110)),(.45,(29,155,174)),(.72,(150,205,87)),(1.,(252,210,73)))
        for i in range(len(stops)-1):
            if stops[i][0]<=value<=stops[i+1][0]:
                a,ca=stops[i];b,cb=stops[i+1];f=(value-a)/(b-a)
                return QColor(*(round(ca[j]+(cb[j]-ca[j])*f) for j in range(3)))
        return QColor(*stops[-1][1])
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor("#101a28"));r=self.rect().adjusted(100,14,-72,-46)
        p.setPen(QPen(QColor("#536b82"),1));p.drawRect(r)
        if self.image.isNull():p.setPen(QColor("#cad8e7"));p.drawText(r,Qt.AlignmentFlag.AlignCenter,"No hay muestras de celda y ángulo disponibles.");p.end();return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False);p.drawImage(r,self.image)
        p.setPen(QColor("#cad8e7"));p.drawText(6,r.center().y(),90,18,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,"Celdas reales")
        low_angle=self.angles[0] if self.angles else 0.;high_angle=self.angles[-1] if self.angles else 0.
        for i in range(5):
            angle=low_angle+(high_angle-low_angle)*i/4;x=r.left()+i/4*r.width();p.drawText(round(x)-28,r.bottom()+18,56,16,Qt.AlignmentFlag.AlignCenter,f"{format_number(angle)}°")
        p.drawText(r.left(),self.height()-5,"Ángulo muestreado · bandas discretas, sin interpolación")
        low,high=self.value_range or (0,1);bar=r.adjusted(r.width()+22,0,r.width()+52,0)
        for y in range(max(0,bar.top()),min(self.height(),bar.bottom()+1)):
            f=1-(y-bar.top())/max(bar.height(),1);p.setPen(self._color(f));p.drawLine(bar.left(),y,bar.right(),y)
        p.setPen(QColor("#cad8e7"));p.drawText(bar.left()-70,bar.top(),64,15,Qt.AlignmentFlag.AlignRight,format_number(high,5));p.drawText(bar.left()-70,bar.bottom(),64,15,Qt.AlignmentFlag.AlignRight,format_number(low,5));p.end()


class FactorialEffectsPlot(QWidget):
    """Descriptive signed contrasts, grouped by metric with independent scales."""
    def __init__(self,parent=None):
        super().__init__(parent);self.metrics=[];self.setObjectName("factorialEffectsPlot")
        self.setMinimumHeight(276);self.setMaximumHeight(315)
        self.setToolTip("Contrastes descriptivos. Escala independiente por métrica; sin barras de incertidumbre ni inferencia causal.")

    def set_effects(self,effects):
        self.metrics=list((effects or {}).get("metrics",[]))
        self.update()

    def paintEvent(self,event):
        painter=QPainter(self);painter.fillRect(self.rect(),QColor("#101a28"))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing,True)
        painter.setPen(QColor("#aabbd0"))
        painter.drawText(12,17,"Efectos firmados · escalas separadas por métrica · no son predicción validada")
        if not self.metrics:
            painter.drawText(12,48,"Gráfico disponible al abrir un estudio factorial 2×2 compatible.")
            painter.end();return
        width=self.width();height=self.height();left=220;right=116;plot_left=left;plot_right=max(left+80,width-right)
        plot_width=plot_right-plot_left;zero_x=plot_left+plot_width/2
        top=26;group_height=max(76,(height-top-4)/max(1,len(self.metrics)))
        row_labels=QFontMetrics(painter.font())
        for metric_index,metric in enumerate(self.metrics):
            y0=top+metric_index*group_height
            effects=metric.get("effects",[])
            defined=metric.get("status")=="DEFINED"
            values=[effect.get("value") for effect in effects
                    if defined and isinstance(effect.get("value"),(int,float)) and math.isfinite(float(effect["value"]))]
            scale=max((abs(float(value)) for value in values),default=0.0) or 1.0
            painter.setPen(QColor("#dce8f5"))
            painter.drawText(12,round(y0+14),f"{metric.get('label','Métrica')} ({metric.get('unit','')})")
            painter.setPen(QColor("#7589a2"))
            painter.drawText(plot_left,round(y0+14),f"−{format_number(scale)}")
            painter.drawText(plot_right-46,round(y0+14),f"+{format_number(scale)}")
            painter.setPen(QPen(QColor("#52647a"),1,Qt.PenStyle.DashLine))
            painter.drawLine(round(zero_x),round(y0+20),round(zero_x),round(y0+group_height-2))
            for effect_index,effect in enumerate(effects[:3]):
                y=round(y0+31+effect_index*20)
                painter.setPen(QColor("#c3d0df"))
                label=row_labels.elidedText(str(effect.get("term","Efecto")),Qt.TextElideMode.ElideRight,left-24)
                painter.drawText(12,y+4,label)
                value=effect.get("value")
                if not defined or not isinstance(value,(int,float)) or not math.isfinite(float(value)):
                    painter.setPen(QColor("#9caec2"));painter.drawText(plot_left,y+4,"No disponible")
                    continue
                extent=(plot_width/2)*(float(value)/scale)
                bar=QRect(round(zero_x if value>=0 else zero_x+extent),y-6,
                    max(1,round(abs(extent))),12)
                painter.fillRect(bar,QColor("#38a7e8" if value>=0 else "#ef9b62"))
                painter.setPen(QColor("#e5edf7"))
                painter.drawText(plot_right+6,y+4,f"{format_number(value,signed=True)} {effect.get('unit') or ''}".rstrip())
            if not defined and not effects:
                painter.setPen(QColor("#9caec2"));painter.drawText(plot_left,round(y0+42),"Efectos no disponibles")
        painter.end()

class ResultsPage(QWidget):
    evidence_updated=Signal()
    resume_project_study_requested=Signal(object)
    def __init__(self,context):
        super().__init__();self.context=context;self.dataset=None;self.source=None;self.loading=False;self._selected_point_id=None
        self._project_reference_signature=None
        self._study_reference_signature=None
        root=QVBoxLayout(self);root.setContentsMargins(12,10,12,10);root.setSpacing(6)
        title=QLabel("Resultados");title.setObjectName('title');root.addWidget(title)
        self.source_notice=QLabel("No hay una corrida seleccionada. Elegila desde el historial o abrí datos importados; todavía no se cargó evidencia histórica.")
        self.source_notice.setWordWrap(True);self.source_notice.setObjectName("notice");root.addWidget(self.source_notice)
        self.run_summary=QLabel("Sin una corrida seleccionada · las métricas de desempeño no están definidas.");self.run_summary.setWordWrap(True);self.run_summary.setObjectName("notice");root.addWidget(self.run_summary)
        self.metric_cards=[];cards=QHBoxLayout();root.addLayout(cards)
        for name in ("Potencia","Torque","BMEP","Auditoría"):
            card=QLabel(f"{name}\n—");card.setObjectName("metricCard");card.setWordWrap(True);card.setMinimumHeight(50);cards.addWidget(card);self.metric_cards.append(card)
        explanation=QLabel("Los estados científicos se conservan. Métricas no definidas se explican; no se interpolan.");explanation.setWordWrap(True);root.addWidget(explanation)
        bar=QHBoxLayout();root.addLayout(bar);self.metric_selector=QComboBox();self.metric_selector.addItems(METRICS);bar.addWidget(self.metric_selector)
        self.path_label=QLabel("Sin fuente seleccionada");self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);self.path_label.setWordWrap(True);bar.addWidget(self.path_label,1)
        actions=QHBoxLayout();root.addLayout(actions)
        browse=QPushButton("Importar resultados…");browse.setToolTip('Histórico/tabla: CSV + JSON compañero en la misma carpeta; también admite reporte JSON. Corridas: result.json y sus artefactos originales.');browse.clicked.connect(self.choose);actions.addWidget(browse)
        historical=QPushButton("Evidencia IMPL2 histórica…");historical.clicked.connect(self.choose_historical);actions.addWidget(historical)
        browse_runs=QPushButton("Abrir corridas EXPLORATORY…");browse_runs.clicked.connect(self.choose_exploratory);actions.addWidget(browse_runs);actions.addStretch()
        self.variants=QListWidget();self.variants.setMaximumHeight(80);self.variants.setFlow(QListWidget.Flow.LeftToRight);self.variants.setWrapping(True);root.addWidget(self.variants)
        baseline_row=QHBoxLayout();root.addLayout(baseline_row);self.baseline_label=QLabel("Baseline del proyecto");baseline_row.addWidget(self.baseline_label);self.baseline_selector=QComboBox();baseline_row.addWidget(self.baseline_selector)
        self.baseline_notice=QLabel("La baseline identifica la referencia de comparación; las curvas usan sólo puntos realmente disponibles.");self.baseline_notice.setWordWrap(True);baseline_row.addWidget(self.baseline_notice,1)
        measured=QGroupBox("Mediciones externas · contraste descriptivo");measured_layout=QVBoxLayout(measured)
        measured_row=QHBoxLayout();measured_layout.addLayout(measured_row)
        self.measurement_import_button=QPushButton("Importar CSV de banco…");self.measurement_import_button.clicked.connect(self.import_measurement);measured_row.addWidget(self.measurement_import_button)
        self.measurement_selector=QComboBox();self.measurement_selector.currentIndexChanged.connect(self.compare_measurement);measured_row.addWidget(self.measurement_selector)
        self.measurement_compare_button=QPushButton("Comparar RPM exactas");self.measurement_compare_button.clicked.connect(self.compare_measurement);measured_row.addWidget(self.measurement_compare_button)
        self.measurement_export_button=QPushButton("Exportar contraste CSV");self.measurement_export_button.clicked.connect(self.export_measurement_comparison);measured_row.addWidget(self.measurement_export_button)
        self.measurement_notice=QLabel("Las mediciones conservan unidades, origen e incertidumbre. Sin interpolación; no es validación experimental preregistrada.")
        self.measurement_notice.setWordWrap(True);measured_layout.addWidget(self.measurement_notice)
        self.measurement_plot=CurvePlot();self.measurement_plot.setObjectName("measuredRunOverlay");self.measurement_plot.setMinimumHeight(160);measured_layout.addWidget(self.measurement_plot)
        self.measurement_table=QTableWidget(0,5);self.measurement_table.setObjectName("measuredRunComparison")
        self.measurement_table.setHorizontalHeaderLabels(["RPM","Medido","Incertidumbre","Simulado","Simulado − medido"])
        self.measurement_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.measurement_table.setMaximumHeight(170);measured_layout.addWidget(self.measurement_table)
        root.addWidget(measured)
        self.condition_notice=QLabel();self.condition_notice.setWordWrap(True);self.condition_notice.setObjectName("notice");root.addWidget(self.condition_notice)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        self.power_curves=PowerCurvePanel();root.addWidget(self.power_curves)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        self.export_report_button=QPushButton("Exportar informe técnico HTML…");self.export_report_button.setObjectName("exportTechnicalReport")
        self.export_report_button.setToolTip("Informe local autosuficiente con origen, estados, pares exactos, gráficos y registros originales seleccionados.")
        self.export_report_button.clicked.connect(self.export_technical_report);controls.addWidget(self.export_report_button)
        self.export_report_pdf_button=QPushButton("Exportar informe técnico PDF.");self.export_report_pdf_button.setObjectName("exportTechnicalReportPdf")
        self.export_report_pdf_button.setToolTip("PDF paginado del mismo informe técnico, con la misma procedencia y límites científicos.")
        self.export_report_pdf_button.clicked.connect(self.export_technical_report_pdf);controls.addWidget(self.export_report_pdf_button)
        self.export_table_button=QPushButton("Exportar tabla CSV");self.export_table_button.setToolTip("Reportes históricos: CSV + JSON compañero para reabrir. Corridas exploratorias: tabla de consulta; conservar los artifacts originales.");self.export_table_button.clicked.connect(self.export_csv);controls.addWidget(self.export_table_button)
        self.export_plot_button=QPushButton("Exportar gráfico PNG");self.export_plot_button.clicked.connect(self.export_png);controls.addWidget(self.export_plot_button)
        self.point_table=QTableWidget(0,8);self.point_table.setHorizontalHeaderLabels(["Variante","RPM","Estado","Período","Auditoría","Ciclos","Balance","BMEP"]);self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.point_table.horizontalHeader().setMinimumSectionSize(48);self.point_table.setMinimumHeight(125);self.point_table.setMaximumHeight(190);self.point_table.currentCellChanged.connect(self._point_row_selected);root.addWidget(self.point_table)
        self.trace_group=QGroupBox("Señales de presión, ondas y flujo EXPLORATORY")
        trace_layout=QVBoxLayout(self.trace_group)
        trace_bar=QHBoxLayout();trace_layout.addLayout(trace_bar)
        self.trace_metric=QComboBox();self.trace_metric.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_metric)
        self.trace_rpm=QComboBox();self.trace_rpm.addItem('Todas las RPM',None);self.trace_rpm.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_rpm)
        self.trace_status=QLabel("Las trazas sólo se muestran después de re-auditar cada primario.");trace_bar.addWidget(self.trace_status,1)
        self.trace_legend=QLabel();self.trace_legend.setWordWrap(True);trace_layout.addWidget(self.trace_legend)
        self.trace_plot=CurvePlot();self.trace_plot.setMinimumHeight(220);trace_layout.addWidget(self.trace_plot)
        self.trace_map_legend=QLabel("Mapa discreto de posición × ángulo · celdas reales · sin interpolación.");self.trace_map_legend.setWordWrap(True);trace_layout.addWidget(self.trace_map_legend)
        self.trace_map=DiscreteAngleCellMap();trace_layout.addWidget(self.trace_map)
        self.export_trace_map=QPushButton("Exportar muestras x–θ CSV");self.export_trace_map.clicked.connect(self.export_trace_csv);trace_layout.addWidget(self.export_trace_map)
        self.trace_group.hide();root.addWidget(self.trace_group)
        self.compare_group=QGroupBox("Comparación de ingeniería")
        compare_layout=QVBoxLayout(self.compare_group);self.compare_notice=QLabel("Seleccioná dos variantes con corridas para comparar.");self.compare_notice.setWordWrap(True);compare_layout.addWidget(self.compare_notice)
        self.compare_table=QTableWidget(0,5);self.compare_table.setObjectName("engineeringComparisonTable");self.compare_table.setHorizontalHeaderLabels(["Elemento","Baseline","Variante","Δ","Estado"]);self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.compare_table.setMaximumHeight(220);compare_layout.addWidget(self.compare_table);root.addWidget(self.compare_group)
        self.design_study_group=QGroupBox("Exploración paramétrica · comparación de diseños")
        study_layout=QVBoxLayout(self.design_study_group)
        self.design_study_notice=QLabel("Los estudios se conservan con su manifiesto, configuración e identidad por punto.")
        self.design_study_notice.setWordWrap(True);study_layout.addWidget(self.design_study_notice)
        self.design_study_lifecycle_notice=QLabel("Presupuesto y ciclo de vida disponibles desde el manifiesto del estudio.")
        self.design_study_lifecycle_notice.setObjectName("designStudyLifecycleSummary")
        self.design_study_lifecycle_notice.setWordWrap(True);study_layout.addWidget(self.design_study_lifecycle_notice)
        study_open_row=QHBoxLayout();study_open_row.addWidget(QLabel("Estudios de este proyecto"))
        self.project_study_selector=QComboBox();self.project_study_selector.setObjectName("projectStudySelector");study_open_row.addWidget(self.project_study_selector,1)
        self.open_project_study_button=QPushButton("Abrir estudio")
        self.open_project_study_button.clicked.connect(self.open_selected_project_study);study_open_row.addWidget(self.open_project_study_button)
        self.resume_project_study_button=QPushButton("Reanudar estudio…")
        self.resume_project_study_button.setToolTip("Enviar el manifiesto seleccionado a Simular; se volverán a verificar proyecto, variante, baseline, ruta durable y checkpoints.")
        self.resume_project_study_button.clicked.connect(self.resume_selected_project_study)
        study_open_row.addWidget(self.resume_project_study_button)
        study_layout.addLayout(study_open_row)
        response_bar=QHBoxLayout();response_bar.addWidget(QLabel("Respuesta paramétrica"))
        self.design_response_metric=QComboBox();self.design_response_metric.setObjectName("designResponseMetric")
        for label,key in (("Potencia de freno (kW)","brake_power"),("Torque de freno (N·m)","brake_torque"),("BMEP (kPa)","BMEP")):
            self.design_response_metric.addItem(label,key)
        self.design_response_metric.currentIndexChanged.connect(self._refresh_design_response_plot)
        response_bar.addWidget(self.design_response_metric);response_bar.addStretch(1);study_layout.addLayout(response_bar)
        self.design_response_notice=QLabel("La respuesta sólo incluye métricas definidas en puntos periódicos observados; no se interpola ni se ajusta una curva.")
        self.design_response_notice.setWordWrap(True);study_layout.addWidget(self.design_response_notice)
        self.design_response_plot=CurvePlot();self.design_response_plot.setObjectName("designResponsePlot")
        self.design_response_plot.setMinimumHeight(210);study_layout.addWidget(self.design_response_plot)
        self.study_filter_group=QGroupBox("Filtros de vista · no modifican el estudio")
        filter_grid=QGridLayout(self.study_filter_group)
        self.study_filter_design=QComboBox();self.study_filter_design.setObjectName("studyFilterDesign")
        self.study_filter_rpm=QComboBox();self.study_filter_rpm.setObjectName("studyFilterRpm")
        self.study_filter_execution=QComboBox();self.study_filter_execution.setObjectName("studyFilterExecution")
        self.study_filter_periodicity=QComboBox();self.study_filter_periodicity.setObjectName("studyFilterPeriodicity")
        for widget in (self.study_filter_design,self.study_filter_rpm,
                       self.study_filter_execution,self.study_filter_periodicity):
            widget.currentIndexChanged.connect(self._apply_design_study_filters)
            widget.setMinimumContentsLength(12)
        filter_grid.addWidget(QLabel("Diseño"),0,0);filter_grid.addWidget(self.study_filter_design,0,1)
        filter_grid.addWidget(QLabel("RPM"),0,2);filter_grid.addWidget(self.study_filter_rpm,0,3)
        filter_grid.addWidget(QLabel("Ejecución"),1,0);filter_grid.addWidget(self.study_filter_execution,1,1)
        filter_grid.addWidget(QLabel("Periodicidad"),1,2);filter_grid.addWidget(self.study_filter_periodicity,1,3)
        self.clear_study_filters_button=QPushButton("Limpiar filtros")
        self.clear_study_filters_button.clicked.connect(self.clear_design_study_filters)
        filter_grid.addWidget(self.clear_study_filters_button,2,0,1,1)
        self.study_filter_count=QLabel("Puntos visibles: 0 de 0")
        self.study_filter_count.setObjectName("studyFilterVisibleCount")
        filter_grid.addWidget(self.study_filter_count,2,1,1,3)
        study_layout.addWidget(self.study_filter_group)
        self.design_study_table=QTableWidget(0,10);self.design_study_table.setObjectName("designStudyResults")
        self.design_study_table.setHorizontalHeaderLabels(["Diseño","Valor","Ejecución","Clasificación","Periodicidad","Ciclos","Potencia","Torque","BMEP","Δ potencia vs base"])
        self.design_study_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.design_study_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.design_study_table.horizontalHeader().setStretchLastSection(False);self.design_study_table.setMaximumHeight(230)
        for column,width in ((2,78),(3,200),(4,130)):
            self.design_study_table.horizontalHeader().setSectionResizeMode(
                column,QHeaderView.ResizeMode.Interactive)
            self.design_study_table.setColumnWidth(column,width)
        self.design_study_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.design_study_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.design_study_table.currentCellChanged.connect(self._design_study_point_selected)
        study_layout.addWidget(self.design_study_table)
        self.design_study_traceability_group=QGroupBox("Procedencia del punto seleccionado")
        traceability_layout=QVBoxLayout(self.design_study_traceability_group)
        self.design_study_traceability=QPlainTextEdit();self.design_study_traceability.setObjectName("designStudyPointTraceability")
        self.design_study_traceability.setReadOnly(True);self.design_study_traceability.setMaximumHeight(260)
        self.design_study_traceability.setPlaceholderText("Seleccioná un punto para consultar manifiestos, fuentes y hashes.")
        traceability_layout.addWidget(self.design_study_traceability);study_layout.addWidget(self.design_study_traceability_group)
        self.design_study_manifest=None;self.design_study_manifest_path=None;self.design_study_manifest_sha256=None
        self.design_study_reference=None;self._design_study_active_project_id=None
        self.factor_effects_group=QGroupBox("Contrastes factoriales 2×2 · descriptivos")
        factor_effects_layout=QVBoxLayout(self.factor_effects_group)
        self.factor_effects_notice=QLabel("Los contrastes requieren los cuatro resultados exactos, periódicos y compatibles.")
        self.factor_effects_notice.setWordWrap(True);factor_effects_layout.addWidget(self.factor_effects_notice)
        self.factor_effects_plot=FactorialEffectsPlot();factor_effects_layout.addWidget(self.factor_effects_plot)
        self.export_factorial_plot_button=QPushButton("Exportar gráfico factorial PNG + fuentes…")
        self.export_factorial_plot_button.setToolTip("Exporta la figura visible con el CSV exacto de contrastes y un recibo JSON que enlaza hashes del gráfico, CSV y manifiesto.")
        self.export_factorial_plot_button.clicked.connect(self.export_factorial_effect_plot)
        factor_effects_layout.addWidget(self.export_factorial_plot_button)
        self.factor_effects_table=QTableWidget(0,5);self.factor_effects_table.setObjectName("factorialEffects")
        self.factor_effects_table.setHorizontalHeaderLabels(["Métrica","Contraste","Valor","Estado","Definición"])
        self.factor_effects_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.factor_effects_table.horizontalHeader().setStretchLastSection(True);self.factor_effects_table.setMaximumHeight(280)
        factor_effects_layout.addWidget(self.factor_effects_table);study_layout.addWidget(self.factor_effects_group)
        self.factor_effects_group.hide()
        self.export_design_study_button=QPushButton("Exportar puntos seleccionados CSV…")
        self.export_design_study_button.setToolTip("CSV sin redondeo, con estados, identidades y SHA-256 del manifiesto ligado al proyecto.")
        self.export_design_study_button.clicked.connect(self.export_design_study_csv)
        self.export_design_study_button.setEnabled(False);study_layout.addWidget(self.export_design_study_button)
        self.export_full_design_study_button=QPushButton("Exportar matriz completa CSV…")
        self.export_full_design_study_button.setToolTip("Exporta todos los puntos del manifiesto, incluso los no seleccionados, sin imputar métricas ni alterar estados.")
        self.export_full_design_study_button.clicked.connect(self.export_full_design_study_csv)
        self.export_full_design_study_button.setEnabled(False);study_layout.addWidget(self.export_full_design_study_button)
        self.export_factorial_effects_button=QPushButton("Exportar matriz y contrastes factoriales CSV…")
        self.export_factorial_effects_button.setToolTip(
            "Exporta los cuatro puntos y sus contrastes descriptivos con procedencia exacta; los efectos no elegibles quedan vacíos.")
        self.export_factorial_effects_button.clicked.connect(self.export_factorial_effects_csv)
        self.export_factorial_effects_button.setEnabled(False);self.export_factorial_effects_button.hide()
        study_layout.addWidget(self.export_factorial_effects_button)
        self.study_csv_snapshot_group=QGroupBox("Estudio paramétrico importado · snapshot de sólo lectura")
        snapshot_layout=QVBoxLayout(self.study_csv_snapshot_group)
        self.study_csv_snapshot_notice=QLabel("Los snapshots conservan la tabla exportada y no pueden iniciar corridas.")
        self.study_csv_snapshot_notice.setWordWrap(True);snapshot_layout.addWidget(self.study_csv_snapshot_notice)
        self.study_csv_snapshot_table=QTableWidget(0,10);self.study_csv_snapshot_table.setObjectName("parametricStudyCsvSnapshot")
        self.study_csv_snapshot_table.setHorizontalHeaderLabels([
            "Punto","Diseño","RPM","Estado","Periodicidad","Ciclos","Potencia (kW)",
            "Torque (N·m)","BMEP (kPa)","Fuente al exportar"])
        self.study_csv_snapshot_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.study_csv_snapshot_table.horizontalHeader().setStretchLastSection(True)
        self.study_csv_snapshot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.study_csv_snapshot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.study_csv_snapshot_table.currentCellChanged.connect(self._study_csv_snapshot_row_selected)
        snapshot_layout.addWidget(self.study_csv_snapshot_table)
        self.study_csv_snapshot_detail=QPlainTextEdit();self.study_csv_snapshot_detail.setReadOnly(True)
        self.study_csv_snapshot_detail.setMaximumHeight(125);self.study_csv_snapshot_detail.setPlaceholderText(
            "Seleccioná un punto para consultar su procedencia exacta.")
        snapshot_layout.addWidget(self.study_csv_snapshot_detail);self.study_csv_snapshot_group.hide()
        self.factorial_csv_snapshot_group=QGroupBox("Matriz factorial importada · snapshot de sólo lectura")
        factorial_snapshot_layout=QVBoxLayout(self.factorial_csv_snapshot_group)
        self.factorial_csv_snapshot_notice=QLabel("El snapshot conserva cuatro diseños y nueve contrastes descriptivos; no inicia corridas.")
        self.factorial_csv_snapshot_notice.setWordWrap(True);factorial_snapshot_layout.addWidget(self.factorial_csv_snapshot_notice)
        self.factorial_csv_snapshot_points=QTableWidget(0,12);self.factorial_csv_snapshot_points.setObjectName("factorialCsvSnapshotPoints")
        self.factorial_csv_snapshot_points.setHorizontalHeaderLabels([
            "Punto","Factor A","Factor B","RPM","Ejecución","Clasificación","Periodicidad","Ciclos",
            "Potencia (kW)","Torque (N·m)","BMEP (kPa)","Fuente actual"])
        self.factorial_csv_snapshot_points.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.factorial_csv_snapshot_points.horizontalHeader().setStretchLastSection(True)
        self.factorial_csv_snapshot_points.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.factorial_csv_snapshot_points.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.factorial_csv_snapshot_points.currentCellChanged.connect(self._factorial_csv_snapshot_point_selected)
        factorial_snapshot_layout.addWidget(self.factorial_csv_snapshot_points)
        self.factorial_csv_snapshot_detail=QPlainTextEdit();self.factorial_csv_snapshot_detail.setReadOnly(True)
        self.factorial_csv_snapshot_detail.setMaximumHeight(140);factorial_snapshot_layout.addWidget(self.factorial_csv_snapshot_detail)
        self.factorial_csv_snapshot_contrasts=QTableWidget(0,6);self.factorial_csv_snapshot_contrasts.setObjectName("factorialCsvSnapshotContrasts")
        self.factorial_csv_snapshot_contrasts.setHorizontalHeaderLabels([
            "Métrica","Contraste","Valor","Estado","Definición","Motivo / fuentes"])
        self.factorial_csv_snapshot_contrasts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.factorial_csv_snapshot_contrasts.horizontalHeader().setStretchLastSection(True)
        self.factorial_csv_snapshot_contrasts.setMaximumHeight(330)
        self.factorial_csv_snapshot_contrasts.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.factorial_csv_snapshot_contrasts.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.factorial_csv_snapshot_contrasts.currentCellChanged.connect(self._factorial_csv_snapshot_contrast_selected)
        factorial_snapshot_layout.addWidget(self.factorial_csv_snapshot_contrasts)
        self.factorial_csv_snapshot_group.hide()
        self.cross_study_csv_snapshot_group=QGroupBox("Comparación entre estudios · snapshot CSV de sólo lectura")
        cross_snapshot_layout=QVBoxLayout(self.cross_study_csv_snapshot_group)
        self.cross_study_csv_snapshot_notice=QLabel("Se conservan los pares exactos, puntos sin pareja y estados de origen tal como fueron exportados.")
        self.cross_study_csv_snapshot_notice.setWordWrap(True);cross_snapshot_layout.addWidget(self.cross_study_csv_snapshot_notice)
        self.cross_study_csv_snapshot_table=QTableWidget(0,8);self.cross_study_csv_snapshot_table.setObjectName("crossStudyCsvSnapshot")
        self.cross_study_csv_snapshot_table.setHorizontalHeaderLabels([
            "Tipo","RPM","Diseño A","Estado A","Diseño B","Estado B","Métricas P / T / BMEP","Pareo / motivo"])
        self.cross_study_csv_snapshot_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column,width in enumerate((100,75,135,185,135,185,220,260)):
            self.cross_study_csv_snapshot_table.setColumnWidth(column,width)
        self.cross_study_csv_snapshot_table.horizontalHeader().setStretchLastSection(True)
        self.cross_study_csv_snapshot_table.setWordWrap(False)
        self.cross_study_csv_snapshot_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cross_study_csv_snapshot_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cross_study_csv_snapshot_table.currentCellChanged.connect(self._cross_study_csv_snapshot_row_selected)
        cross_snapshot_layout.addWidget(self.cross_study_csv_snapshot_table)
        self.cross_study_csv_snapshot_detail=QPlainTextEdit();self.cross_study_csv_snapshot_detail.setReadOnly(True)
        self.cross_study_csv_snapshot_detail.setMaximumHeight(170);cross_snapshot_layout.addWidget(self.cross_study_csv_snapshot_detail)
        self.cross_study_csv_snapshot_group.hide()
        self.study_comparison_group=QGroupBox("Comparar estudios guardados")
        comparison_layout=QVBoxLayout(self.study_comparison_group)
        comparison_bar=QHBoxLayout();comparison_layout.addLayout(comparison_bar)
        self.compare_studies_button=QPushButton("Seleccionar estudios…")
        self.compare_studies_button.clicked.connect(self.compare_project_studies);comparison_bar.addWidget(self.compare_studies_button)
        self.study_comparison_metric=QComboBox();self.study_comparison_metric.setObjectName("studyComparisonMetric")
        for label,key in (("Potencia (kW)","brake_power"),("Torque (N·m)","brake_torque"),("BMEP (kPa)","BMEP")):
            self.study_comparison_metric.addItem(label,key)
        self.study_comparison_metric.currentIndexChanged.connect(self._render_study_comparison)
        comparison_bar.addWidget(self.study_comparison_metric)
        self.export_study_comparison_button=QPushButton("Exportar comparación HTML…")
        self.export_study_comparison_button.clicked.connect(self.export_study_comparison)
        comparison_bar.addWidget(self.export_study_comparison_button)
        self.export_study_comparison_pdf_button=QPushButton("Exportar comparación PDF.")
        self.export_study_comparison_pdf_button.clicked.connect(self.export_study_comparison_pdf)
        comparison_bar.addWidget(self.export_study_comparison_pdf_button)
        self.export_study_comparison_csv_button=QPushButton("Exportar comparación CSV…")
        self.export_study_comparison_csv_button.setToolTip("CSV con filas pareadas y no pareadas, estados, valores observados y procedencia SHA-256.")
        self.export_study_comparison_csv_button.clicked.connect(self.export_study_comparison_csv)
        self.export_study_comparison_csv_button.setEnabled(False)
        comparison_bar.addWidget(self.export_study_comparison_csv_button);comparison_bar.addStretch(1)
        self.study_comparison_notice=QLabel("Elegí entre dos y cuatro estudios guardados en este proyecto. Se verifica cada manifiesto y artifact antes de comparar.")
        self.study_comparison_notice.setWordWrap(True);comparison_layout.addWidget(self.study_comparison_notice)
        self.study_comparison_response_notice=QLabel("La gráfica usa sólo extremos de pares exactos con ambos puntos PERIOD_1 y la métrica definida; no interpola ni conecta RPM.")
        self.study_comparison_response_notice.setWordWrap(True);comparison_layout.addWidget(self.study_comparison_response_notice)
        self.study_comparison_response_legend=QLabel("Sin series periódicas con la métrica seleccionada.")
        self.study_comparison_response_legend.setTextFormat(Qt.TextFormat.RichText)
        self.study_comparison_response_legend.setWordWrap(True);comparison_layout.addWidget(self.study_comparison_response_legend)
        self.study_comparison_response_plot=CurvePlot();self.study_comparison_response_plot.setObjectName("crossStudyResponsePlot")
        self.study_comparison_response_plot.pointSelected.connect(self._cross_study_response_point_selected)
        self.study_comparison_response_plot.setMinimumHeight(210);comparison_layout.addWidget(self.study_comparison_response_plot)
        comparison_filter_bar=QHBoxLayout();comparison_layout.addLayout(comparison_filter_bar)
        comparison_filter_bar.addWidget(QLabel("RPM exacta"))
        self.cross_study_rpm_filter=QComboBox();self.cross_study_rpm_filter.setObjectName("crossStudyRpmFilter")
        self.cross_study_rpm_filter.addItem("Todas",None)
        self.cross_study_rpm_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        comparison_filter_bar.addWidget(self.cross_study_rpm_filter)
        comparison_filter_bar.addWidget(QLabel("Pareamiento"))
        self.cross_study_pair_filter=QComboBox();self.cross_study_pair_filter.setObjectName("crossStudyPairFilter")
        self.cross_study_pair_filter.addItem("Todos", "all")
        self.cross_study_pair_filter.addItem("Pares exactos", "paired")
        self.cross_study_pair_filter.addItem("Puntos sin pareja", "unpaired")
        self.cross_study_pair_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        comparison_filter_bar.addWidget(self.cross_study_pair_filter)
        self.cross_study_filter_clear=QPushButton("Limpiar filtros")
        self.cross_study_filter_clear.clicked.connect(self._clear_cross_study_filters)
        comparison_filter_bar.addWidget(self.cross_study_filter_clear)
        comparison_filter_bar.addStretch(1)
        self.cross_study_filter_count=QLabel("0 de 0 filas visibles")
        self.cross_study_filter_count.setObjectName("crossStudyFilterCount")
        comparison_filter_bar.addWidget(self.cross_study_filter_count)
        periodicity_filter_bar=QHBoxLayout();comparison_layout.addLayout(periodicity_filter_bar)
        periodicity_filter_bar.addWidget(QLabel("Periodicidad del extremo A"))
        self.cross_study_periodicity_a_filter=QComboBox()
        self.cross_study_periodicity_a_filter.setObjectName("crossStudyPeriodicityAFilter")
        self.cross_study_periodicity_a_filter.addItem("Todos",None)
        self.cross_study_periodicity_a_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        periodicity_filter_bar.addWidget(self.cross_study_periodicity_a_filter)
        periodicity_filter_bar.addWidget(QLabel("Periodicidad del extremo B"))
        self.cross_study_periodicity_b_filter=QComboBox()
        self.cross_study_periodicity_b_filter.setObjectName("crossStudyPeriodicityBFilter")
        self.cross_study_periodicity_b_filter.addItem("Todos",None)
        self.cross_study_periodicity_b_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        periodicity_filter_bar.addWidget(self.cross_study_periodicity_b_filter)
        periodicity_filter_bar.addStretch(1)
        execution_filter_bar=QHBoxLayout();comparison_layout.addLayout(execution_filter_bar)
        execution_filter_bar.addWidget(QLabel("Ejecución del extremo A"))
        self.cross_study_execution_a_filter=QComboBox()
        self.cross_study_execution_a_filter.setObjectName("crossStudyExecutionAFilter")
        self.cross_study_execution_a_filter.addItem("Todos",None)
        self.cross_study_execution_a_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        execution_filter_bar.addWidget(self.cross_study_execution_a_filter)
        execution_filter_bar.addWidget(QLabel("Ejecución del extremo B"))
        self.cross_study_execution_b_filter=QComboBox()
        self.cross_study_execution_b_filter.setObjectName("crossStudyExecutionBFilter")
        self.cross_study_execution_b_filter.addItem("Todos",None)
        self.cross_study_execution_b_filter.currentIndexChanged.connect(self._apply_cross_study_filters)
        execution_filter_bar.addWidget(self.cross_study_execution_b_filter)
        execution_filter_bar.addStretch(1)
        self.study_comparison_table=QTableWidget(0,11);self.study_comparison_table.setObjectName("crossStudyComparison")
        self.study_comparison_table.setHorizontalHeaderLabels(["RPM","Diseño A","ID A","Estado A","Métrica A","Diseño B","ID B","Estado B","Métrica B","Δ B−A","Pareo"])
        self.study_comparison_table.horizontalHeaderItem(3).setToolTip(
            "Estado almacenado de ejecución / clasificación / periodicidad observada")
        self.study_comparison_table.horizontalHeaderItem(7).setToolTip(
            "Estado almacenado de ejecución / clasificación / periodicidad observada")
        self.study_comparison_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column,width in enumerate((60,170,75,205,70,170,75,205,70,75,150)):
            self.study_comparison_table.setColumnWidth(column,width)
        self.study_comparison_table.horizontalHeader().setStretchLastSection(True);self.study_comparison_table.setMaximumHeight(300)
        self.study_comparison_table.setSortingEnabled(True);comparison_layout.addWidget(self.study_comparison_table)
        self.study_comparison_point_details=QPlainTextEdit();self.study_comparison_point_details.setObjectName("crossStudyResponsePointDetails")
        self.study_comparison_point_details.setReadOnly(True);self.study_comparison_point_details.setMaximumHeight(170)
        self.study_comparison_point_details.setPlaceholderText("Seleccioná un marcador de la gráfica para inspeccionar su fila y procedencia exactas.")
        comparison_layout.addWidget(self.study_comparison_point_details)
        study_layout.addWidget(self.study_comparison_group)
        root.addWidget(self.design_study_group);self.design_study_group.hide()
        self.study_comparison=None
        self.details=QTableWidget(0,2);self.details.setHorizontalHeaderLabels(["Detalle del punto","Valor"]);self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.details.setMaximumHeight(190);root.addWidget(self.details)
        # Preserve all existing controls and contracts; organize presentation
        # around the designer's question rather than one long audit document.
        self.result_tabs=QTabWidget();self.result_tabs.setObjectName('resultViews')
        self.view_layouts=[]
        def view(label,widgets,layouts=()):
            page=QWidget();box=QVBoxLayout(page);box.setContentsMargins(4,5,4,4)
            for widget in widgets:
                root.removeWidget(widget);box.addWidget(widget)
            for section in layouts:
                root.removeItem(section);box.addLayout(section)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(page)
            self.result_tabs.addTab(scroll,label);self.view_layouts.append(box)
            return box
        view('Curvas',[self.power_curves])
        view('Variables',[self.plot,self.point_table])
        waves=view('Presiones y ondas',[self.trace_group])
        wave_help=QLabel('Las señales se muestran cuando las corridas contienen primarios compatibles. Un reporte agregado de curvas no contiene trazas ni geometría adicional.');wave_help.setWordWrap(True);waves.insertWidget(0,wave_help)
        view('Comparar',[self.compare_group,self.design_study_group,self.study_csv_snapshot_group,self.factorial_csv_snapshot_group,self.cross_study_csv_snapshot_group])
        view('Mediciones',[measured])
        view('Trazabilidad',[self.source_notice,self.path_label,self.details])
        # Source paths and identifiers stay available in Trazabilidad. Keep
        # provenance and scientific status visible in the normal workspace.
        bar.removeWidget(self.path_label)
        self.source_notice.setWordWrap(True)
        root.removeItem(cards)
        root.insertLayout(1,cards)
        for card in self.metric_cards:card.setMinimumHeight(42)
        root.removeItem(bar)
        self.view_layouts[1].insertLayout(0,bar)
        root.removeItem(baseline_row)
        self.view_layouts[3].insertLayout(0,baseline_row)
        root.removeWidget(self.condition_notice);self.view_layouts[3].insertWidget(1,self.condition_notice)
        title.hide();explanation.hide()
        self.variants.setFixedHeight(36)
        self.result_tabs.setMinimumHeight(240)
        root.removeItem(controls)
        root.addWidget(self.result_tabs,1);root.addLayout(controls)
        self.power_curves.plot.setMinimumHeight(150)
        self.metric_selector.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.variants.itemChanged.connect(self._update_engineering_compare);self.plot.pointSelected.connect(self.show_point);self.power_curves.pointSelected.connect(self.show_point)
        self.baseline_selector.currentIndexChanged.connect(self._baseline_changed)
        self.context.changed.connect(self._project_context_changed);self._project_context_changed()

    def set_compact_layout(self,compact):
        self.power_curves.set_compact_layout(compact)
        self.variants.setFixedHeight(26 if compact else 36)
        for card in self.metric_cards:card.setMinimumHeight(34 if compact else 42)
        self.setStyleSheet('QLabel#metricCard {padding:4px;font-size:9pt;} QLabel#notice {padding:4px;} QPushButton {padding:4px 8px;} QTabBar::tab {padding:4px 6px;min-height:16px;}' if compact else '')

    def _project_context_changed(self,*_):
        active_project_id=self.context.project.get("project_id")
        if (getattr(self,"design_study_manifest",None) is not None and
                self._design_study_active_project_id is not None and
                active_project_id!=self._design_study_active_project_id):
            self.design_study_manifest=None;self.design_study_manifest_path=None
            self.design_study_manifest_sha256=None;self.design_study_reference=None
            self._design_study_active_project_id=None;self.design_study_table.setRowCount(0)
            self.design_study_traceability.clear();self.design_study_group.hide()
        refs=self.context.project.get("result_references",[])
        signature=(self.context.project.get("project_id"),tuple(
            (str(ref.get("path","")),ref.get("artifact_sha256"),ref.get("identity_sha256"))
            for ref in refs))
        if signature!=self._project_reference_signature:
            self._project_reference_signature=signature
            paths=[Path(ref["path"]) for ref in refs if ref.get("path") and Path(ref["path"]).is_file()]
            if paths:self.open_runs(paths)
        self._refresh_project_studies()
        names={"base",*self.context.project["variants"]}
        data_names=set()
        if self.dataset:
            data_names={str(row.get("variant_id")) for row in self.dataset.get("points",[]) if row.get("variant_id")};names.update(data_names)
        prefs=settings();key=f"baseline_variant/{self.context.project['project_id']}"
        preferred=prefs.value(key)
        if not preferred:preferred="base"
        self.baseline_selector.blockSignals(True);self.baseline_selector.clear();self.baseline_selector.addItem("Sin baseline",None)
        self.baseline_selector.addItem("Motor base","base")
        for name in sorted(names-{"base"}):self.baseline_selector.addItem(name,name)
        index=self.baseline_selector.findData(preferred)
        if index<0:index=self.baseline_selector.findData(self.context.selected_variant or "base")
        self.baseline_selector.setCurrentIndex(index if index>=0 else 0);self.baseline_selector.blockSignals(False)
        self._reload_measurement_references()
        if self.dataset and self.dataset.get("points"):
            selected=next((row for row in self.dataset["points"]
                           if row.get("point_id")==self._selected_point_id),self.dataset["points"][0])
            self.show_point(selected)

    def _refresh_project_studies(self):
        refs=self.context.project.get("study_references",[])
        signature=(self.context.project.get("project_id"),tuple(
            (str(ref.get("path","")),ref.get("study_id"),ref.get("manifest_sha256"))
            for ref in refs if isinstance(ref,dict)))
        if signature!=self._study_reference_signature:
            self._study_reference_signature=signature
            self.study_comparison=None;self.study_comparison_table.setRowCount(0)
            self.export_study_comparison_csv_button.setEnabled(False)
            self.cross_study_rpm_filter.clear();self.cross_study_rpm_filter.addItem("Todas",None)
            self.cross_study_pair_filter.setCurrentIndex(0)
            self._reset_cross_study_periodicity_options();self._reset_cross_study_execution_options()
            self._apply_cross_study_filters()
            self.study_comparison_notice.setText("Elegí entre dos y cuatro estudios guardados en este proyecto. Se verifica cada manifiesto y artifact antes de comparar.")
        previous=self.project_study_selector.currentData()
        self.project_study_selector.blockSignals(True);self.project_study_selector.clear()
        for ref in refs:
            label=f"{ref.get('study_id','Estudio')} · {Path(ref.get('path','')).name or 'manifiesto'}"
            self.project_study_selector.addItem(label,dict(ref))
        if previous:
            index=next((i for i in range(self.project_study_selector.count())
                if self.project_study_selector.itemData(i)==previous),-1)
            if index>=0:self.project_study_selector.setCurrentIndex(index)
        self.project_study_selector.blockSignals(False)
        available=bool(refs)
        self.open_project_study_button.setEnabled(available)
        self.resume_project_study_button.setEnabled(available)
        self.design_study_group.setVisible(available or getattr(self,"design_study_manifest",None) is not None)
        self.compare_studies_button.setEnabled(len(refs)>=2)
        self.study_comparison_group.setVisible(len(refs)>=2 or self.study_comparison is not None)

    def compare_project_studies(self):
        references=self.context.project.get("study_references",[])
        if len(references)<2:
            self.study_comparison_notice.setText("Este proyecto necesita al menos dos estudios guardados para compararlos.")
            return False
        dialog=QDialog(self);dialog.setWindowTitle("Seleccionar estudios paramétricos")
        layout=QVBoxLayout(dialog);layout.addWidget(QLabel("Seleccioná de dos a cuatro manifiestos ligados al proyecto. El primero se toma como referencia visual."))
        listing=QListWidget();listing.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        for index,reference in enumerate(references):
            item=QListWidgetItem(f"{reference.get('study_id','Estudio')} · {Path(reference.get('path','')).name}")
            item.setData(Qt.ItemDataRole.UserRole,dict(reference));listing.addItem(item)
            if index<2:item.setSelected(True)
        layout.addWidget(listing)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return False
        selected=[item.data(Qt.ItemDataRole.UserRole) for item in listing.selectedItems()]
        if not 2<=len(selected)<=4:
            self.study_comparison_notice.setText("La comparación admite de dos a cuatro estudios por consulta.")
            return False
        self.compare_studies_button.setEnabled(False)
        self.study_comparison_notice.setText("Verificando manifiestos y artifacts con el importador de corridas…")
        run_background(_load_verified_study_comparison,selected,on_done=self._study_comparison_loaded,
            on_error=self._study_comparison_failed)
        return True

    def _study_comparison_loaded(self,comparison):
        self.study_comparison=comparison
        self.export_study_comparison_csv_button.setEnabled(True)
        self.compare_studies_button.setEnabled(len(self.context.project.get("study_references",[]))>=2)
        self._refresh_cross_study_rpm_options(comparison)
        self._refresh_cross_study_periodicity_options(comparison)
        self._refresh_cross_study_execution_options(comparison)
        self.study_comparison_group.show();self._render_study_comparison()

    def _refresh_cross_study_rpm_options(self,comparison):
        rpms={}
        for pair in comparison.get("pairs",[]):
            rpm=pair.get("rpm")
            if isinstance(rpm,(int,float)) and math.isfinite(float(rpm)):
                rpms[float(rpm)]=format_number(rpm)
        for item in comparison.get("unpaired",[]):
            rpm=(item.get("point") or {}).get("rpm")
            if isinstance(rpm,(int,float)) and math.isfinite(float(rpm)):
                rpms[float(rpm)]=format_number(rpm)
        self.cross_study_rpm_filter.blockSignals(True)
        self.cross_study_rpm_filter.clear();self.cross_study_rpm_filter.addItem("Todas",None)
        for rpm in sorted(rpms):
            self.cross_study_rpm_filter.addItem(format_number(rpm,significant=10),rpm)
            self.cross_study_rpm_filter.setItemData(
                self.cross_study_rpm_filter.count()-1,f"RPM exacta almacenada: {rpm!r}",
                Qt.ItemDataRole.ToolTipRole)
        self.cross_study_rpm_filter.setCurrentIndex(0);self.cross_study_rpm_filter.blockSignals(False)
        self.cross_study_pair_filter.setCurrentIndex(0)

    @staticmethod
    def _cross_study_periodicity_filter_value(point):
        if not isinstance(point,dict):return _CROSS_STUDY_NO_ENDPOINT
        value=point.get("periodicity")
        return str(value) if value not in (None,"") else "NOT_EVALUATED"

    def _refresh_cross_study_periodicity_options(self,comparison):
        states={"a":set(),"b":set()}
        for pair in comparison.get("pairs",[]):
            states["a"].add(self._cross_study_periodicity_filter_value(pair.get("point_a")))
            states["b"].add(self._cross_study_periodicity_filter_value(pair.get("point_b")))
        studies=comparison.get("studies",[])
        first_study=studies[0].get("study_id") if studies else None
        for item in comparison.get("unpaired",[]):
            side="a" if item.get("study_id")==first_study else "b"
            other="b" if side=="a" else "a"
            states[side].add(self._cross_study_periodicity_filter_value(item.get("point")))
            states[other].add(_CROSS_STUDY_NO_ENDPOINT)
        for side,combo in (("a",self.cross_study_periodicity_a_filter),
                           ("b",self.cross_study_periodicity_b_filter)):
            combo.blockSignals(True);combo.clear();combo.addItem("Todos",None)
            ordered=sorted(states[side],key=lambda value:(value==_CROSS_STUDY_NO_ENDPOINT,
                _state_label("NOT_REPORTED" if value==_CROSS_STUDY_NO_ENDPOINT else value).casefold()))
            for value in ordered:
                label=("Sin punto" if value==_CROSS_STUDY_NO_ENDPOINT else _state_label(value))
                combo.addItem(label,value)
            combo.setCurrentIndex(0);combo.blockSignals(False)

    @staticmethod
    def _cross_study_execution_filter_value(point):
        if not isinstance(point,dict):return _CROSS_STUDY_NO_ENDPOINT
        value=point.get("status")
        return str(value) if value not in (None,"") else "NOT_REPORTED"

    def _refresh_cross_study_execution_options(self,comparison):
        states={"a":set(),"b":set()}
        for pair in comparison.get("pairs",[]):
            states["a"].add(self._cross_study_execution_filter_value(pair.get("point_a")))
            states["b"].add(self._cross_study_execution_filter_value(pair.get("point_b")))
        studies=comparison.get("studies",[])
        first_study=studies[0].get("study_id") if studies else None
        for item in comparison.get("unpaired",[]):
            side="a" if item.get("study_id")==first_study else "b"
            other="b" if side=="a" else "a"
            states[side].add(self._cross_study_execution_filter_value(item.get("point")))
            states[other].add(_CROSS_STUDY_NO_ENDPOINT)
        for side,combo in (("a",self.cross_study_execution_a_filter),
                           ("b",self.cross_study_execution_b_filter)):
            combo.blockSignals(True);combo.clear();combo.addItem("Todos",None)
            ordered=sorted(states[side],key=lambda value:(value==_CROSS_STUDY_NO_ENDPOINT,
                _state_label("NOT_REPORTED" if value==_CROSS_STUDY_NO_ENDPOINT else value).casefold()))
            for value in ordered:
                label="Sin punto" if value==_CROSS_STUDY_NO_ENDPOINT else _state_label(value)
                combo.addItem(label,value)
            combo.setCurrentIndex(0);combo.blockSignals(False)

    def _clear_cross_study_filters(self):
        self.cross_study_rpm_filter.setCurrentIndex(0)
        self.cross_study_pair_filter.setCurrentIndex(0)
        self.cross_study_periodicity_a_filter.setCurrentIndex(0)
        self.cross_study_periodicity_b_filter.setCurrentIndex(0)
        self.cross_study_execution_a_filter.setCurrentIndex(0)
        self.cross_study_execution_b_filter.setCurrentIndex(0)
        self._apply_cross_study_filters()

    def _reset_cross_study_periodicity_options(self):
        for combo in (self.cross_study_periodicity_a_filter,self.cross_study_periodicity_b_filter):
            combo.blockSignals(True);combo.clear();combo.addItem("Todos",None);combo.blockSignals(False)

    def _reset_cross_study_execution_options(self):
        for combo in (self.cross_study_execution_a_filter,self.cross_study_execution_b_filter):
            combo.blockSignals(True);combo.clear();combo.addItem("Todos",None);combo.blockSignals(False)

    def _apply_cross_study_filters(self,*_):
        if not hasattr(self,"study_comparison_table"):return
        selected_rpm=self.cross_study_rpm_filter.currentData()
        pair_mode=self.cross_study_pair_filter.currentData() or "all"
        periodicity_a=self.cross_study_periodicity_a_filter.currentData()
        periodicity_b=self.cross_study_periodicity_b_filter.currentData()
        execution_a=self.cross_study_execution_a_filter.currentData()
        execution_b=self.cross_study_execution_b_filter.currentData()
        visible=0
        for row in range(self.study_comparison_table.rowCount()):
            item=self.study_comparison_table.item(row,0)
            metadata=item.data(Qt.ItemDataRole.UserRole+1) if item else None
            metadata=metadata if isinstance(metadata,dict) else {}
            periodicity_metadata=item.data(Qt.ItemDataRole.UserRole+2) if item else None
            periodicity_metadata=periodicity_metadata if isinstance(periodicity_metadata,dict) else {}
            execution_metadata=item.data(Qt.ItemDataRole.UserRole+3) if item else None
            execution_metadata=execution_metadata if isinstance(execution_metadata,dict) else {}
            row_rpm=metadata.get("rpm")
            paired=bool(metadata.get("paired"))
            show=(selected_rpm is None or row_rpm==selected_rpm)
            show=show and (pair_mode=="all" or (pair_mode=="paired")==paired)
            show=show and (periodicity_a is None or periodicity_metadata.get("periodicity_a")==periodicity_a)
            show=show and (periodicity_b is None or periodicity_metadata.get("periodicity_b")==periodicity_b)
            show=show and (execution_a is None or execution_metadata.get("execution_a")==execution_a)
            show=show and (execution_b is None or execution_metadata.get("execution_b")==execution_b)
            self.study_comparison_table.setRowHidden(row,not show)
            visible+=int(show)
        total=self.study_comparison_table.rowCount()
        self.cross_study_filter_count.setText(f"{visible} de {total} filas visibles")

    def _study_comparison_failed(self,error):
        self.compare_studies_button.setEnabled(len(self.context.project.get("study_references",[]))>=2)
        self.export_study_comparison_csv_button.setEnabled(False)
        self.study_comparison=None
        self.study_comparison_notice.setText(f"Comparación rechazada: {error}")
        self.study_comparison_table.setRowCount(0)
        self.cross_study_rpm_filter.clear();self.cross_study_rpm_filter.addItem("Todas",None)
        self.cross_study_pair_filter.setCurrentIndex(0)
        self._reset_cross_study_periodicity_options()
        self._reset_cross_study_execution_options()
        self._apply_cross_study_filters()
        self.study_comparison_response_plot.set_series([])
        self.study_comparison_point_details.clear()
        self.study_comparison_response_notice.setText("No hay una comparación verificada para graficar.")
        self.study_comparison_response_legend.setText("Sin series disponibles.")

    @staticmethod
    def _study_point_label(study,point):
        factors=point.get("factor_values") or []
        if factors:
            tags=[]
            for index,item in enumerate(factors):
                label=(item.get("parameter_id") or item.get("label") or "Factor").lower()
                short=("Transferencia" if "port:" in label or "transfer" in label else
                       "Cárter" if "crankcase" in label or "cárter" in label else f"F{index+1}")
                tags.append(f"{short} {format_number(item.get('value'))} {item.get('unit','')}".strip())
            return " · ".join(tags)
        if point.get("value") is not None:
            return f"{format_number(point['value'])} {point.get('unit') or ''}".strip()
        return str(point.get("label") or f"Punto {point.get('index')}")

    def _render_study_comparison(self,*_):
        comparison=self.study_comparison
        if not comparison:return
        metric=self.study_comparison_metric.currentData() or "brake_power"
        metric_labels={"brake_power":("Potencia de freno","kW"),
            "brake_torque":("Torque de freno","N·m"),"BMEP":("BMEP","kPa")}
        metric_label,metric_unit=metric_labels.get(metric,(metric,""))
        response_points={study["study_id"]:{} for study in comparison.get("studies",[])}
        eligible_pairs=0
        for pair_index,pair in enumerate(comparison.get("pairs",[])):
            point_a=pair.get("point_a") or {};point_b=pair.get("point_b") or {}
            value_a=point_a.get("metrics",{}).get(metric);value_b=point_b.get("metrics",{}).get(metric)
            if (point_a.get("periodicity")!="PERIOD_1" or point_b.get("periodicity")!="PERIOD_1" or
                    type(value_a) not in (int,float) or type(value_b) not in (int,float) or
                    not math.isfinite(float(value_a)) or not math.isfinite(float(value_b)) or
                    pair.get("pairing")!="EXACT_RPM_AND_OPERATING_CONTEXT"):
                continue
            eligible_pairs+=1
            for study_id,point,value in ((pair.get("study_a"),point_a,value_a),
                                         (pair.get("study_b"),point_b,value_b)):
                if study_id not in response_points:continue
                identity=(point.get("index"),float(pair["rpm"]))
                plotted=response_points[study_id].setdefault(identity,{
                    "rpm":float(pair["rpm"]),"value":float(value),"comparison_study_id":study_id,
                    "comparison_point_index":point.get("index"),"comparison_run_id":point.get("run_id"),
                    "comparison_source_run_id":point.get("source_run_id"),"comparison_rows":[]})
                if pair_index not in plotted["comparison_rows"]:plotted["comparison_rows"].append(pair_index)
        series=[{"name":str(study_id),"unit":metric_unit,"x_key":"rpm","x_label":"RPM",
                 "connect":False,"points":sorted(points.values(),key=lambda point:point["rpm"])}
                for study_id,points in response_points.items() if points]
        self.study_comparison_response_plot.set_series(series,y_scale_mode="data_margin")
        self.study_comparison_response_legend.setText("&nbsp;&nbsp;".join(
            f'<span style="color:{CurvePlot.COLORS[index%len(CurvePlot.COLORS)]};">●</span> '
            f'{html.escape(item["name"])} · {len(item["points"])} punto(s)'
            for index,item in enumerate(series)) or "Sin pares periódicos con esta métrica definida.")
        self.study_comparison_table.setSortingEnabled(False);self.study_comparison_table.setRowCount(0)
        studies={study["study_id"]:study for study in comparison["studies"]}
        rows=[]
        for pair_index,pair in enumerate(comparison["pairs"]):
            a=pair["point_a"];b=pair["point_b"]
            rows.append((pair["rpm"],pair["study_a"],a,pair["study_b"],b,
                pair["metrics"].get(metric,{}).get("delta"),"RPM y condiciones exactas",pair_index))
        for item in comparison["unpaired"]:
            if item["study_id"]==comparison["studies"][0]["study_id"]:
                rows.append((item["point"]["rpm"],item["study_id"],item["point"],"",None,None,
                    item.get("reason","Sin par exacto compatible"),None))
            else:
                rows.append((item["point"]["rpm"],"",None,item["study_id"],item["point"],None,
                    item.get("reason","Sin par exacto compatible"),None))
        self.study_comparison_table.setRowCount(len(rows))
        self.study_comparison_point_details.clear()
        for index,(rpm,a_id,a,b_id,b,delta,pairing,comparison_row) in enumerate(rows):
            def fmt_metric(point):
                value=(point or {}).get("metrics",{}).get(metric)
                periodic=str((point or {}).get("periodicity","" )).startswith("PERIOD_1")
                return format_number(value) if periodic and isinstance(value,(int,float)) and math.isfinite(float(value)) else "—"
            def state(point):
                if not point:return "—"
                values=[point.get("status") or "NOT_REPORTED"]
                if point.get("classification") not in (None,""):
                    values.append(point["classification"])
                values.append(point.get("periodicity") or "NOT_EVALUATED")
                labels=[]
                for value in values:
                    label=_state_label(value)
                    if label not in labels:labels.append(label)
                return " / ".join(labels)
            a_identity=(a or {}).get("engine_identity_sha256") or ""
            b_identity=(b or {}).get("engine_identity_sha256") or ""
            a_design=self._study_point_label(studies[a_id],a) if a else "—"
            b_design=self._study_point_label(studies[b_id],b) if b else "—"
            cells=[format_number(rpm),a_design,a_identity[:8] if a_identity else "—",state(a),fmt_metric(a),
                b_design,b_identity[:8] if b_identity else "—",state(b),fmt_metric(b),
                format_number(delta,signed=True) if isinstance(delta,(int,float)) else "—",pairing]
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column==0:
                    item.setData(Qt.ItemDataRole.UserRole,comparison_row)
                    item.setData(Qt.ItemDataRole.UserRole+1,{
                        "rpm":float(rpm) if isinstance(rpm,(int,float)) and math.isfinite(float(rpm)) else None,
                        "paired":comparison_row is not None})
                    item.setData(Qt.ItemDataRole.UserRole+2,{
                        "periodicity_a":self._cross_study_periodicity_filter_value(a),
                        "periodicity_b":self._cross_study_periodicity_filter_value(b)})
                    item.setData(Qt.ItemDataRole.UserRole+3,{
                        "execution_a":self._cross_study_execution_filter_value(a),
                        "execution_b":self._cross_study_execution_filter_value(b)})
                point=a if column in (1,2,3,4) else b
                if point is not None and column in (1,2,3,5,6,7):
                    study=studies[a_id if column in (1,2,3) else b_id]
                    tooltip=(f"Estudio: {study['study_id']}\nParámetro: {(study.get('parameter') or {}).get('label') or study.get('design_method')}\n"
                        f"Diseño: {self._study_point_label(study,point)}\nManifiesto: {study['manifest_path']}\n"
                        f"SHA-256 manifiesto: {study['manifest_sha256']}\nRPM exacta: {format_number(point['rpm'])}\n"
                        f"Estado guardado: {_state_label(point.get('status') or 'NOT_REPORTED')}\n"
                        f"Clasificación: {_state_label(point.get('classification') or 'NOT_REPORTED')}\n"
                        f"Periodicidad: {_state_label(point.get('periodicity') or 'NOT_EVALUATED')}\n"
                        f"Run fuente: {point.get('source_run_id') or 'No informado'}\n"
                        f"Motor SHA-256: {point.get('engine_identity_sha256')}\n"
                        f"Identidad de corrida SHA-256: {point.get('identity_sha256') or 'No disponible'}\n"
                        f"Resultado SHA-256: {point.get('result_sha256') or 'No disponible'}\n"
                        f"Artifact SHA-256: {point.get('result_artifact_sha256') or 'No disponible'}\n"
                        f"Ruta: {point.get('run_directory') or 'No informada'}")
                    item.setToolTip(tooltip)
                elif column==10:
                    item.setToolTip(str(value))
                self.study_comparison_table.setItem(index,column,item)
        self.study_comparison_table.setSortingEnabled(True)
        self._apply_cross_study_filters()
        self.study_comparison_notice.setText(
            f"Baseline común {comparison['baseline_engine_identity_sha256']} · {len(comparison['pairs'])} pares exactos · "
            f"{len(comparison['unpaired'])} puntos sin par · {comparison['notice']} Métrica seleccionada: {_STUDY_COMPARE_METRICS[metric][0]}.")
        excluded=len(comparison.get("pairs",[]))-eligible_pairs
        self.study_comparison_response_notice.setText(
            f"{metric_label} ({metric_unit}) · {eligible_pairs} par(es) exacto(s) con ambos puntos PERIOD_1 y métrica definida; "
            f"{excluded} par(es) exacto(s) excluido(s) por estado no periódico o valor indefinido. "
            "Sólo marcadores observados, sin interpolación ni ajuste. Los puntos sin pareja y estados completos permanecen en la tabla.")

    def _cross_study_response_point_selected(self,plotted_point):
        """Select the exact comparison row(s) represented by an observed plot marker."""
        comparison=self.study_comparison
        if not comparison or not isinstance(plotted_point,dict):return
        study_id=plotted_point.get("comparison_study_id")
        row_indices=plotted_point.get("comparison_rows") or []
        studies={study.get("study_id"):study for study in comparison.get("studies",[])}
        if study_id not in studies or not row_indices:return
        row_index=row_indices[0];pairs=comparison.get("pairs",[])
        if not isinstance(row_index,int) or not 0<=row_index<len(pairs):return
        pair=pairs[row_index]
        endpoint="point_a" if pair.get("study_a")==study_id else "point_b" if pair.get("study_b")==study_id else None
        if endpoint is None:return
        point=pair.get(endpoint) or {}
        if (point.get("index")!=plotted_point.get("comparison_point_index") or
                point.get("run_id")!=plotted_point.get("comparison_run_id") or
                point.get("source_run_id")!=plotted_point.get("comparison_source_run_id")):return
        study=studies[study_id]
        verification=("Verificada al cargar la comparación (hash e identidad)" if point.get("source_verified")
            else "No verificada al cargar la comparación")
        metric_value=plotted_point.get("value")
        linked=[]
        for candidate_index in row_indices:
            if not isinstance(candidate_index,int) or not 0<=candidate_index<len(pairs):continue
            candidate=pairs[candidate_index]
            other_side="point_b" if candidate.get("study_a")==study_id else "point_a"
            other_id=candidate.get("study_b") if candidate.get("study_a")==study_id else candidate.get("study_a")
            other=candidate.get(other_side) or {}
            linked.append(f"Fila {candidate_index+1}: {other_id} · run {other.get('source_run_id') or other.get('run_id') or 'No informado'}")
        metric_text=str(metric_value) if metric_value is not None else "No definida"
        details=["Marcador exacto seleccionado · respuesta observada, sin ajuste ni interpolación.",
            f"Estudio: {study_id}",f"Diseño: {self._study_point_label(study,point)}",
            f"RPM exacta: {point.get('rpm')}",
            f"Clasificación: {_state_label(point.get('classification') or point.get('status') or 'NOT_REPORTED')}",
            f"Periodicidad: {_state_label(point.get('periodicity') or 'NOT_EVALUATED')}",
            f"Ciclos completados: {point.get('cycles_completed') if point.get('cycles_completed') is not None else 'No informado'}",
            f"Métrica seleccionada · {self.study_comparison_metric.currentText()}: {metric_text}",
            f"Run: {point.get('run_id') or 'No informado'} · run fuente: {point.get('source_run_id') or 'No informado'}",
            f"Fuente: {verification}",f"Manifiesto: {study.get('manifest_path') or 'No informado'}",
            f"SHA-256 manifiesto: {study.get('manifest_sha256') or 'No disponible'}",
            f"Motor SHA-256: {point.get('engine_identity_sha256') or 'No disponible'}",
            f"Identidad corrida SHA-256: {point.get('identity_sha256') or 'No disponible'}",
            f"Resultado SHA-256: {point.get('result_sha256') or 'No disponible'}",
            f"Artifact SHA-256: {point.get('result_artifact_sha256') or 'No disponible'}",
            f"Ruta artifact: {point.get('run_directory') or 'No informada'}"]
        if point.get("context"):
            details.append("Contexto de operación: "+json.dumps(point["context"],ensure_ascii=False,sort_keys=True))
        if linked:details.append("Filas de comparación asociadas:\n"+"\n".join(linked))
        self.study_comparison_point_details.setPlainText("\n".join(details))
        for table_row in range(self.study_comparison_table.rowCount()):
            item=self.study_comparison_table.item(table_row,0)
            if item and item.data(Qt.ItemDataRole.UserRole)==row_index:
                self.study_comparison_table.setCurrentCell(table_row,0)
                self.study_comparison_table.selectRow(table_row)
                self.study_comparison_table.scrollToItem(item)
                break

    def export_study_comparison(self):
        if not self.study_comparison:return False
        default=Path(self.context.path).with_suffix(".comparacion-estudios.html") if self.context.path else Path.cwd()/"dino-comparacion-estudios.html"
        path,_=QFileDialog.getSaveFileName(self,"Exportar comparación paramétrica",str(default),"Informe HTML (*.html)")
        if not path:return False
        try:
            from .technical_report import write_study_comparison_report
            write_study_comparison_report(path,self.study_comparison)
            self.study_comparison_notice.setText(f"Comparación HTML exportada: {Path(path).name} · conserva procedencia y estados por punto.")
            return True
        except (OSError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"No se pudo exportar la comparación",str(exc));return False

    def export_study_comparison_pdf(self):
        if not self.study_comparison:return False
        default=Path(self.context.path).with_suffix(".comparacion-estudios.pdf") if self.context.path else Path.cwd()/"dino-comparacion-estudios.pdf"
        path,_=QFileDialog.getSaveFileName(self,"Exportar comparación paramétrica PDF",str(default),"Informe PDF (*.pdf)")
        if not path:return False
        if not path.lower().endswith('.pdf'):path+='.pdf'
        try:
            write_study_comparison_report_pdf(path,self.study_comparison)
            self.study_comparison_notice.setText(f"Comparación PDF exportada: {Path(path).name} — conserva procedencia y estados por punto.")
            return True
        except (OSError,RuntimeError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"No se pudo exportar la comparación PDF",str(exc));return False

    def export_study_comparison_csv(self):
        if not self.study_comparison:return False
        default=Path(self.context.path).with_suffix(".comparacion-estudios.csv") if self.context.path else Path.cwd()/"dino-comparacion-estudios.csv"
        path,_=QFileDialog.getSaveFileName(self,"Exportar comparación paramétrica como CSV",str(default),"CSV (*.csv)")
        if not path:return False
        try:
            rows=_build_cross_study_comparison_csv(self.study_comparison)
            if not rows:raise ValueError("la comparación no contiene pares ni puntos sin pareja para exportar")
            with Path(path).open("x",encoding="utf-8-sig",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=_CROSS_STUDY_CSV_FIELDS,extrasaction="ignore")
                writer.writeheader();writer.writerows(rows)
            digest=hashlib.sha256(Path(path).read_bytes()).hexdigest()
            self.study_comparison_notice.setText(
                f"{len(rows)} fila(s) exportadas sin redondeo · SHA-256 {digest} · "
                "pares exactos y puntos sin pareja conservados; métricas no definidas permanecen vacías.")
            return True
        except (OSError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"No se pudo exportar la comparación CSV",str(exc));return False

    def open_selected_project_study(self):
        reference=self.project_study_selector.currentData()
        if not reference:return False
        try:
            path=Path(reference["path"]).resolve();raw=path.read_bytes()
            digest=hashlib.sha256(raw).hexdigest()
            manifest=json.loads(raw.decode("utf-8"))
            if digest!=reference["manifest_sha256"]:
                raise ValueError("el SHA-256 no coincide con la referencia guardada")
            if (manifest.get("schema")!=reference["schema"] or
                    manifest.get("study_id")!=reference["study_id"] or
                    manifest.get("project_id")!=reference["source_project_id"]):
                raise ValueError("la identidad del manifiesto no coincide con su procedencia registrada")
            self.open_design_study(path,verified_reference=reference)
            return True
        except Exception as exc:
            self.design_study_group.show()
            self.design_study_notice.setText(f"Estudio rechazado de forma segura: {type(exc).__name__}: {exc}")
            return False

    def resume_selected_project_study(self):
        """Route the selected, project-registered study to the existing resume preflight."""
        reference=self.project_study_selector.currentData()
        if not isinstance(reference,dict):return False
        registered=next((item for item in self.context.project.get("study_references",[])
                         if isinstance(item,dict) and item==reference),None)
        if registered is None:
            self.design_study_notice.setText("Reanudación bloqueada: el manifiesto seleccionado ya no coincide con una referencia del proyecto activo.")
            return False
        self.resume_project_study_requested.emit(dict(registered))
        return True

    def _reload_measurement_references(self):
        loaded=[];errors=[]
        for ref in self.context.project.get("measurement_references",[]):
            try:
                path=Path(ref["path"])
                if not path.is_absolute() and self.context.path and ref["path"].startswith(("./", ".\\")):
                    path=(Path(self.context.path).resolve().parent/ref["path"][2:]).resolve()
                data=measurement_data.load_import(path)
                meta_hash=hashlib.sha256(path.read_bytes()).hexdigest()
                if (data["manifest"]["dataset_id"]!=ref["dataset_id"] or
                        data["manifest"]["csv_sha256"]!=ref["csv_sha256"] or meta_hash!=ref["metadata_sha256"]):
                    raise ValueError("La medición no coincide con los hashes guardados en el proyecto.")
                loaded.append(data)
            except Exception as exc:errors.append(f"{ref.get('path','medición')}: {exc}")
        self.measurement_datasets=loaded;self.measurement_selector.blockSignals(True);self.measurement_selector.clear()
        for data in loaded:
            meta=data["metadata"];self.measurement_selector.addItem(f"{meta['kind']} · {meta['engine']} · {meta['provenance']}",data["manifest"]["dataset_id"])
        self.measurement_selector.blockSignals(False)
        self.measurement_import_button.setEnabled(bool(self.context.path))
        if errors:self.measurement_notice.setText("No se pudieron recuperar algunas mediciones: "+"; ".join(errors))
        elif loaded:self.measurement_notice.setText(f"{len(loaded)} conjunto(s) medido(s) ligado(s) al proyecto. Contraste exacto · no es validación experimental.")
        self.compare_measurement()

    def import_measurement(self):
        if not self.context.path:
            QMessageBox.information(self,"Guardar proyecto","Guardá primero el proyecto para ligar la medición a una ruta que pueda recuperarse al reabrirlo.");return False
        csv_path,_=QFileDialog.getOpenFileName(self,"Importar medición de banco",str(Path(self.context.path).parent),"CSV (*.csv)")
        if not csv_path:return False
        dialog=QDialog(self);dialog.setWindowTitle("Declarar medición externa");form=QFormLayout(dialog)
        kind=QComboBox();kind.addItem("Potencia de freno","dyno_power");kind.addItem("Torque","dyno_torque");kind.addItem("Presión de cilindro por ciclo","pressure_trace")
        unit=QComboBox()
        cycle_period=QComboBox();cycle_period.addItem("360°",360);cycle_period.addItem("720°",720)
        def update_units():
            choices={"dyno_power":("kW","W","hp"),"dyno_torque":("N*m","lb-ft"),"pressure_trace":("Pa","kPa","bar")}[kind.currentData()]
            unit.clear();unit.addItems(choices);cycle_period.setEnabled(kind.currentData()=="pressure_trace")
        kind.currentIndexChanged.connect(update_units);update_units()
        provenance=QComboBox();provenance.addItem("Desconocido","UNKNOWN");provenance.addItem("Medido","MEASURED");provenance.addItem("Documentado","DOCUMENTED");provenance.addItem("Sintético de prueba","SYNTHETIC")
        fields={key:QLineEdit() for key in ("engine","configuration","conditions","source","notes")}
        form.addRow("Magnitud",kind);form.addRow("Unidad del CSV",unit);form.addRow("Clasificación",provenance)
        form.addRow("Período de ciclo",cycle_period)
        for key,label in (("engine","Motor"),("configuration","Configuración"),("conditions","Condiciones"),("source","Fuente"),("notes","Notas")):form.addRow(label,fields[key])
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return False
        try:
            period=cycle_period.currentData() if kind.currentData()=="pressure_trace" else None
            meta=measurement_data.declarations(kind.currentData(),unit.currentText(),cycle_period_deg=period,provenance=provenance.currentData(),**{key:edit.text() for key,edit in fields.items()})
            raw=Path(csv_path).read_bytes();prepared=measurement_data.prepare_import(raw,meta)
            project_path=Path(self.context.path).resolve();root=project_path.parent/(project_path.stem+".measurements")
            root.mkdir(parents=True,exist_ok=True)
            imported=measurement_data.save_import(root/uuid.uuid4().hex,prepared);manifest_path=Path(imported["path"])
            try:stored_path="./"+manifest_path.parent.relative_to(project_path.parent).as_posix()+"/metadata.json"
            except ValueError:stored_path=str(manifest_path)
            ref={"path":stored_path,"dataset_id":imported["manifest"]["dataset_id"],
                 "metadata_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                 "csv_sha256":imported["manifest"]["csv_sha256"],"classification":meta["provenance"]}
            project=self.context.project;project.setdefault("measurement_references",[]).append(ref);validate_project(project)
            self.context.dirty=True;self.context.changed.emit();self.measurement_notice.setText("Medición importada y ligada al proyecto. Guardá el proyecto para persistir la referencia. Datos sintéticos de prueba no validan el solver.")
            return True
        except Exception as exc:
            QMessageBox.warning(self,"No se pudo importar la medición",str(exc));return False

    def compare_measurement(self,*_):
        self.measurement_table.setRowCount(0)
        self._measurement_export_rows=[]
        if not getattr(self,"measurement_datasets",None) or self.measurement_selector.currentIndex()<0 or not self.dataset:return
        external=self.measurement_datasets[self.measurement_selector.currentIndex()];meta=external["metadata"]
        variant=self.baseline_selector.currentData() or "base";simulated=[]
        if meta["kind"]=="pressure_trace":
            rpm=self.trace_rpm.currentData()
            if rpm is None:
                self.measurement_notice.setText("Elegí una RPM de la corrida para contrastar la traza; no se mezclan condiciones ni ciclos.");return
            traces=[trace for trace in self.dataset.get("traces",[]) if trace.get("variant_id")==variant and trace.get("rpm")==rpm]
            for trace in traces:
                channel=trace.get("channels",{}).get("cylinder_pressure_pa",{})
                for angle,value in zip(trace.get("angles_deg",[]),channel.get("values",[])):
                    if value is not None:simulated.append({"cycle":trace["cycle"],"x":angle,"value":value})
            unit=meta["canonical_value_unit"]
            if not simulated:
                self.measurement_notice.setText("La corrida seleccionada no tiene trazas de presión del cilindro para esa RPM.");return
        else:
            metric="brake_power" if meta["kind"]=="dyno_power" else "brake_torque" if meta["kind"]=="dyno_torque" else None
            if metric is None:return
            for point in self.dataset.get("points",[]):
                if point.get("variant_id")!=variant or point.get(metric+"_status")!="DEFINED":continue
                value=point.get(metric)
                if value is not None:simulated.append({"x":point["rpm"],"value":float(value)*(1000 if metric=="brake_power" else 1)})
            unit=meta["canonical_value_unit"]
        comparison=measurement_data.exploratory_overlay(external,simulated,simulated_unit=unit)
        # Keep the full source values separate from the compact UI rendering.
        # The table intentionally uses human-readable precision, while an
        # exported comparison must retain the exact imported/calculated values.
        self._measurement_export_rows=list(comparison["rows"])
        self.measurement_table.setHorizontalHeaderLabels(["Ciclo / ángulo (°CA)" if meta["kind"]=="pressure_trace" else "RPM",
            "Medido", "Incertidumbre", "Simulado", "Simulado − medido"])
        if meta["kind"]=="pressure_trace":
            measured_points=[{"angle_deg":row["x"],"value":row["value"]} for row in external["rows"]]
            simulated_points=[{"angle_deg":row["key"][1],"value":row["simulated"]} for row in comparison["rows"] if row["simulated"] is not None]
            x_key="angle_deg";x_label="Ángulo de cigüeñal (°)"
        else:
            measured_points=[{"rpm":row["x"],"value":row["value"]} for row in external["rows"]]
            simulated_points=[{"rpm":row["key"],"value":row["simulated"]} for row in comparison["rows"] if row["simulated"] is not None]
            x_key="rpm";x_label="RPM"
        self.measurement_plot.set_series([
            {"name":"Medido · "+meta["provenance"],"unit":unit,"x_label":x_label,"x_key":x_key,"points":measured_points},
            {"name":"Corrida · coordenadas coincidentes","unit":unit,"x_label":x_label,"x_key":x_key,"points":simulated_points}])
        self.measurement_table.setRowCount(len(comparison["rows"]))
        for row,data in enumerate(comparison["rows"]):
            values=(data["key"],data["measured"],data["uncertainty"],data["simulated"],data["difference"])
            for column,value in enumerate(values):
                shown=("—" if value is None else " / ".join(format_number(part) for part in value)
                       if isinstance(value,tuple) else format_number(value))
                item=QTableWidgetItem(shown);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.measurement_table.setItem(row,column,item)
        self.measurement_notice.setText(f"{meta['kind']} · {meta['canonical_value_unit']} · {meta['provenance']} · {meta['engine']} · {meta['configuration']} · {meta['conditions']} · {comparison['metrics']['matched_count']} coincidencias exactas · sin interpolación. {comparison['notice']}")
        run_ids=sorted({str(row.get("run_id")) for row in self.dataset.get("points",[]) if row.get("variant_id")==variant and row.get("run_id")})
        self._measurement_export_metadata={"dataset_id":comparison["dataset_id"],"provenance":meta["provenance"],
            "source":meta["source"],"engine":meta["engine"],"configuration":meta["configuration"],
            "conditions":meta["conditions"],"variant":variant,"run_ids":";".join(run_ids),
            "comparison_status":comparison["status"],"interpolation":comparison["interpolation"]}

    def export_measurement_comparison(self):
        if self.measurement_table.rowCount()==0:return False
        path,_=QFileDialog.getSaveFileName(self,"Exportar contraste de mediciones",str(Path(self.context.path).parent if self.context.path else Path.cwd()),"CSV (*.csv)")
        if not path:return False
        try:
            with Path(path).open("w",encoding="utf-8-sig",newline="") as stream:
                writer=csv.writer(stream);metadata=self._measurement_export_metadata
                context_fields=["dataset_id","provenance","source","engine","configuration","conditions","variant","run_ids","comparison_status","interpolation"]
                writer.writerow(context_fields+[self.measurement_table.horizontalHeaderItem(c).text() for c in range(self.measurement_table.columnCount())])
                for row in self._measurement_export_rows:
                    values=(row["key"],row["measured"],row["uncertainty"],row["simulated"],row["difference"])
                    writer.writerow([metadata[key] for key in context_fields]+[
                        json.dumps(value,ensure_ascii=False,separators=(",",":"))
                        if isinstance(value,(dict,list,tuple)) else value for value in values])
            return True
        except OSError as exc:
            QMessageBox.warning(self,"No se pudo exportar el contraste",str(exc));return False

    def _baseline_changed(self,*_):
        name=self.baseline_selector.currentData()
        prefs=settings();pref_key=f"baseline_variant/{self.context.project['project_id']}"
        if name is None:prefs.remove(pref_key)
        else:prefs.setValue(pref_key,name)
        if name is None:
            self.baseline_notice.setText("Sin baseline seleccionada. Las curvas muestran sólo los puntos realmente disponibles.");self.redraw();return
        base=self.context.project["base_engine"] if name=="base" else self.context.project["variants"].get(name)
        if base is None:
            self.baseline_notice.setText(f"Baseline {name}: configuración del proyecto no disponible; se conserva únicamente la comparación de observables cargados.");self.redraw();return
        from ..engine_variants import compare_configurations
        diffs=[]
        baseline_hashes={row.get("point_configuration_sha256") for row in (self.dataset or {}).get("points",[]) if row.get("variant_id")==name}
        baseline_matches=bool(base.get("native_configuration_sha256") and base.get("native_configuration_sha256") in baseline_hashes)
        for i in range(self.variants.count()):
            candidate=self.variants.item(i).text()
            if candidate==name or self.variants.item(i).checkState()!=Qt.CheckState.Checked:continue
            other=self.context.project["base_engine"] if candidate=="base" else self.context.project["variants"].get(candidate)
            hashes={row.get("point_configuration_sha256") for row in (self.dataset or {}).get("points",[]) if row.get("variant_id")==candidate}
            if other is not None and baseline_matches and other.get("native_configuration_sha256") in hashes:
                changes=compare_configurations(base,other);descriptions=[]
                for change in changes[:4]:
                    descriptions.append(self._engineering_change(change,base,other))
                suffix="; …" if len(changes)>4 else ""
                diffs.append(f"{candidate}: {len(changes)} diferencias nativas ({'; '.join(descriptions)}{suffix}) · hashes coinciden")
            elif other is not None:diffs.append(f"{candidate}: corridas presentes; diff de geometría no confirmado contra sus hashes")
        self.baseline_notice.setText(f"Baseline {name} · " + ("; ".join(diffs) if diffs else ("hash de geometría de corrida verificado." if baseline_matches else "configuración actual sin hash de corrida verificable.")))
        self._update_condition_notice()
        self._update_engineering_compare()
        self.redraw()

    def _update_engineering_compare(self,*_):
        self.compare_table.setRowCount(0)
        baseline_name=self.baseline_selector.currentData() if hasattr(self,"baseline_selector") else None
        selected=[self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked]
        candidate_run=next((name for name in selected if self._project_variant_for_run(name) not in (None,baseline_name)),None)
        candidate_name=self._project_variant_for_run(candidate_run) if candidate_run else None
        if not baseline_name or not candidate_name:
            self.compare_notice.setText("Seleccioná baseline y variante para ver diferencias geométricas y métricas.")
            return
        base=self.context.project["base_engine"] if baseline_name=="base" else self.context.project["variants"].get(baseline_name)
        candidate=self.context.project["base_engine"] if candidate_name=="base" else self.context.project["variants"].get(candidate_name)
        rows=[]
        if base is not None and candidate is not None:
            from ..engine_variants import compare_configurations
            for change in compare_configurations(base,candidate):
                path=change.get("path","").replace("/native_configuration/","")
                # The native ducts, species, and their discretization are
                # derived backend state. Report the editable source geometry,
                # not dozens of low-level mesh coordinates and inventories.
                if path.startswith(("ducts/","duct_species/","initial_duct_states/")) or any(
                    part in f"/{path}/" for part in ("/ducts/","/duct_species/","/initial_duct_states/")
                ):
                    continue
                parts=path.split("/");tail=parts[-1]
                labels={"length_mm":"longitud","inlet_diameter_mm":"Ø entrada",
                    "outlet_diameter_mm":"Ø salida","bore_mm":"Ø cilindro",
                    "stroke_mm":"carrera","rod_length_mm":"biela",
                    "volume_bdc_cm3":"volumen PMI","cylinder_compression_ratio":"relación de compresión",
                    "reference_rpm":"RPM de referencia"}
                label=labels.get(tail,tail.replace("_mm"," ").replace("_"," "))
                if "geometry_identity/chamber/sections" in path:
                    try:
                        section_index=int(parts[parts.index("sections")+1])
                        from ..engine_variants import escape_sections
                        label=f"{escape_sections(candidate)[section_index]['name']} · {label}"
                    except (ValueError,IndexError,KeyError):pass
                before=change.get("before");after=change.get("after");unit=change.get("unit","")
                fmt=lambda x: format_number(x) if isinstance(x,(int,float)) else str(x)
                delta=f"{format_number(after-before,signed=True)} {unit}".strip() if isinstance(before,(int,float)) and isinstance(after,(int,float)) else "—"
                state="Geometría del proyecto" if any(k in path for k in ("geometry_identity","slider_crank","port_binding")) else "Configuración declarada"
                rows.append((label,f"{fmt(before)} {unit}".strip(),f"{fmt(after)} {unit}".strip(),delta,state))
                if len(rows)>=12:break
        points=(self.dataset or {}).get("points",[])
        baseline_runs={name for name in selected if self._project_variant_for_run(name)==baseline_name}
        candidate_runs={name for name in selected if self._project_variant_for_run(name)==candidate_name}
        bpoints=[r for r in points if r.get("variant_id") in baseline_runs]
        cpoints=[r for r in points if r.get("variant_id") in candidate_runs]
        pairs=[]
        for b in bpoints:
            for c in cpoints:
                if b.get("rpm")!=c.get("rpm"):continue
                fields=("fuel_id","afr_kg_air_per_kg_fuel","mesh_resolution","total_finite_volume_cells","cycles_requested","solver_identity_sha256","implementation_identity_sha256")
                mismatches=[key for key in fields if b.get(key) is not None and c.get(key) is not None and b.get(key)!=c.get(key)]
                pairs.append((len(mismatches),b,c,mismatches))
        pair=min(pairs,key=lambda p:(p[0],p[1].get("rpm",0))) if pairs else None
        if pair:
            _,b,c,mismatches=pair
            for label,key in (("Potencia de freno","brake_power"),("Torque","brake_torque"),("BMEP","BMEP"),("IMEP","IMEP"),("FMEP","FMEP")):
                bval=b.get(key);cval=c.get(key);bs=b.get(key+"_status");cs=c.get(key+"_status")
                defined=bs=="DEFINED" and cs=="DEFINED" and isinstance(bval,(int,float)) and isinstance(cval,(int,float))
                unit={"Potencia de freno":"kW","Torque":"N·m","BMEP":"kPa","IMEP":"kPa","FMEP":"kPa"}[label]
                reason="Definido" if defined else str(c.get(key+"_reason") or b.get(key+"_reason") or "No definido por el artifact")
                rows.append((label,f"{format_number(bval)} {unit}" if defined else "—",f"{format_number(cval)} {unit}" if defined else "—",f"{format_number(cval-bval,signed=True)} {unit}" if defined else "—",reason))
            if b.get('transient_estimates') is not None and c.get('transient_estimates') is not None:
                for label,key,unit in (("Potencia transitoria","brake_power","kW"),("Torque transitorio","brake_torque","N·m")):
                    x=b['transient_estimates'].get(key);y=c['transient_estimates'].get(key)
                    if isinstance(x,(int,float)) and isinstance(y,(int,float)):
                        rows.append((label,f"{format_number(x,5)} {unit}",f"{format_number(y,5)} {unit}",f"{format_number(y-x,5,signed=True)} {unit}","NO CONVERGIDO; diferencia transitoria, no ganancia confirmada" if _nonconverged(b) or _nonconverged(c) else "Estimación de ingeniería"))
                for label in ("Trabajo indicado (J/ciclo)","Aire atrapado al cierre (mg)","Calor de combustión (J/ciclo)"):
                    x=b.get('engineering_diagnostics',{}).get(label);y=c.get('engineering_diagnostics',{}).get(label)
                    if isinstance(x,(int,float)) and isinstance(y,(int,float)):
                        rows.append((label,format_number(x,5),format_number(y,5),format_number(y-x,5,signed=True),"Último ciclo; no atribución estacionaria"))
            identity_fields=("solver_identity_sha256","implementation_identity_sha256")
            identity_known=any(b.get(key) is not None and c.get(key) is not None for key in identity_fields)
            identity_matches=identity_known and all(b.get(key)==c.get(key) for key in identity_fields if b.get(key) is not None and c.get(key) is not None)
            condition="Mismo RPM; condiciones declaradas coinciden" if not mismatches else "Advertencia: difieren "+", ".join(mismatches)
            if not identity_known:condition+="; identidad del solver por punto no informada"
            elif not identity_matches:condition+="; identidad del solver distinta"
            if _nonconverged(b) or _nonconverged(c):condition+="; TRANSITORIOS: no demuestra ganancia de potencia del escape"
            self.compare_notice.setText(f"{baseline_name} vs {candidate_name} · {format_number(b.get('rpm'))} RPM · {condition}. La identidad de configuración conserva las diferencias geométricas mostradas.")
        else:
            self.compare_notice.setText(f"{baseline_name} vs {candidate_name}: sin par de corridas a la misma RPM. Se muestra sólo el diff geométrico del proyecto; no se comparan métricas entre condiciones distintas.")
        self.compare_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                item=QTableWidgetItem(_state_label(value) if j==4 else str(value));item.setToolTip(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.compare_table.setItem(i,j,item)

    def _project_variant_for_run(self,variant_id):
        """Resolve imported history labels to this project's immutable variants."""
        if not variant_id:return None
        label=str(variant_id)
        prefix=f"{self.context.project.get('project_id')} / "
        if label.startswith(prefix):label=label[len(prefix):]
        # Prefer an explicit project variant label over configuration hash
        # matching. A named variant may intentionally equal base geometry;
        # hash-first matching would then alias its imported run to "base" and
        # make the selected baseline appear to have no matching RPM point.
        if label in self.context.project.get("variants",{}):return label
        if label in {"base","Motor base"}:return "base"
        configurations=[("base",self.context.project.get("base_engine",{}))]
        configurations.extend(self.context.project.get("variants",{}).items())
        data_points=[r for r in (self.dataset or {}).get("points",[]) if r.get("variant_id")==variant_id]
        hashes={r.get("point_configuration_sha256") or r.get("configuration_sha256") for r in data_points}
        hashes.discard(None)
        for name,configuration in configurations:
            native_hash=configuration.get("native_configuration_sha256")
            if native_hash and native_hash in hashes:return name
        return "base" if label in {"base","Motor base"} else None

    @staticmethod
    def _engineering_change(change,baseline,candidate):
        path=change.get("path","").replace("/native_configuration/","")
        unit=change.get("unit") or ""
        before,after=change.get("before"),change.get("after")
        label=path
        parts=path.split("/")
        if "chamber/sections" in path:
            try:
                i=int(parts[parts.index("sections")+1]);name=__import__("motorsim.engine_variants",fromlist=["escape_sections"]).escape_sections(candidate)[i]["name"]
                tail=parts[-1];label=f"{name} · "+({"length_mm":"longitud","inlet_diameter_mm":"Ø entrada","outlet_diameter_mm":"Ø salida"}.get(tail,tail))
            except (ValueError,IndexError,KeyError):pass
        elif parts[-1]=="bore_mm":label="Diámetro de cilindro"
        elif parts[-1]=="stroke_mm":label="Carrera"
        elif parts[-1]=="rod_length_mm":label="Longitud de biela"
        def fmt(value):return format_number(value) if isinstance(value,(int,float)) else str(value)
        return f"{label}: {fmt(before)} → {fmt(after)} {unit}".strip()

    def _update_condition_notice(self):
        if not self.dataset or not isinstance(self.dataset.get("points"),list):
            self.condition_notice.setText("Condiciones entre corridas: sin datos cargados.");return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        points=[row for row in self.dataset["points"] if row.get("variant_id") in selected]
        names=sorted({r.get('variant_id') for r in points})
        pairs=[(a,b) for a in points for b in points if len(names)>=2 and a.get('variant_id')==names[0] and b.get('variant_id')==names[1] and a.get('rpm')==b.get('rpm')]
        if not pairs:
            self.condition_notice.setText('Sin pares A/B a la misma RPM; no se comparan condiciones entre RPM distintas.');return
        fields=("fuel_id","afr_kg_air_per_kg_fuel","mesh_resolution","total_finite_volume_cells","cycles_requested","point_configuration_sha256")
        differing=[key for key in fields if any(a.get(key) is not None and b.get(key) is not None and a[key]!=b[key] for a,b in pairs)]
        labels={"rpm":"RPM","fuel_id":"combustible","afr_kg_air_per_kg_fuel":"AFR","mesh_resolution":"resolución de malla","total_finite_volume_cells":"cantidad de celdas","cycles_requested":"horizonte","point_configuration_sha256":"identidad de configuración"}
        named=[labels.get(key,key) for key in differing]
        if differing==['point_configuration_sha256']:
            self.condition_notice.setText("Configuraciones distintas: consultar el diff geométrico. Los demás campos reportados coinciden; esto no demuestra igualdad de parámetros no informados ni convergencia.")
        else:
            self.condition_notice.setText(("Advertencia: las corridas difieren en "+", ".join(named)+"; la comparación no aísla sólo el cambio de escape." ) if differing else "Condiciones comparables en los campos reportados; los campos ausentes no se asumen iguales." )
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,"Importar resultados · CSV con JSON compañero, o reporte JSON",str(artifact_root()),"Reportes y datos (*.json *.csv)")
        if path:self.load(Path(path))
    def choose_historical(self):
        candidate=impl2_historical_report_candidate()
        if candidate.is_file():self.load(candidate,historical=True);return
        path,_=QFileDialog.getOpenFileName(self,"Abrir evidencia IMPL2 histórica",str(artifact_root()),"Reporte IMPL2 (*.json *.csv)")
        if path:self.load(Path(path),historical=True)
    def choose_exploratory(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Abrir corridas EXPLORATORY",str(artifact_root()),"Ejecución Dino (result.json)")
        if paths:self.open_runs(paths)
    def open_runs(self,paths):
        """Load one or more indexed runs through the full independent importer."""
        if paths:
            self.path_label.setText("Verificando artifacts EXPLORATORY…")
            from ..power_curve import import_curve_runs
            run_background(import_curve_runs,paths,on_done=self._loaded_exploratory,on_error=self._exploratory_failed)

    def open_design_study(self,manifest_path,verified_reference=None):
        """Open only the study's saved points and join metrics by their run IDs."""
        try:
            if isinstance(manifest_path,dict):
                verified_reference=manifest_path
                manifest_path=verified_reference["path"]
            path=Path(manifest_path).resolve()
            raw=path.read_bytes()
            if verified_reference is not None and hashlib.sha256(raw).hexdigest()!=verified_reference.get("manifest_sha256"):
                raise ValueError("el SHA-256 del manifiesto cambió antes de cargarlo")
            manifest=json.loads(raw.decode("utf-8"))
            if manifest.get("schema")!="DINO_PARAMETRIC_DESIGN_STUDY_V1":
                raise ValueError("manifiesto paramétrico no compatible")
            if verified_reference is not None and (
                    manifest.get("study_id")!=verified_reference.get("study_id") or
                    manifest.get("project_id")!=verified_reference.get("source_project_id")):
                raise ValueError("identidad del manifiesto incompatible con referencia del proyecto")
            self.design_study_manifest=manifest;self.design_study_manifest_path=path
            self.design_study_manifest_sha256=hashlib.sha256(raw).hexdigest()
            self.design_study_reference=dict(verified_reference) if verified_reference else None
            self._design_study_active_project_id=self.context.project.get("project_id")
            run_paths=[row["run_directory"] for row in manifest.get("points",[])
                       if row.get("run_directory") and Path(row["run_directory"]).joinpath("result.json").is_file()]
            self._update_design_study_summary()
            if run_paths:self.open_runs(run_paths)
        except Exception as exc:
            self.design_study_group.show()
            self.design_study_notice.setText(f"Estudio paramétrico no disponible: {type(exc).__name__}: {exc}")

    def _design_study_point_selected(self,row,*_):
        manifest=getattr(self,"design_study_manifest",None)
        if not manifest or row<0 or row>=len(manifest.get("points",[])):
            self.design_study_traceability.clear();return
        point=manifest["points"][row]
        manifest_path=getattr(self,"design_study_manifest_path",None)
        expected_manifest_hash=getattr(self,"design_study_manifest_sha256",None)
        actual_manifest_hash=None
        try:
            if manifest_path:actual_manifest_hash=hashlib.sha256(Path(manifest_path).read_bytes()).hexdigest()
        except OSError:pass
        manifest_state=("Coincide con el snapshot cargado" if actual_manifest_hash and actual_manifest_hash==expected_manifest_hash
            else "El archivo no está disponible" if actual_manifest_hash is None
            else "CAMBIÓ desde la carga; se conserva el snapshot en memoria")
        reference=self.design_study_reference or {}
        project_hash=reference.get("manifest_sha256")
        if project_hash is None:reference_state="Estudio abierto sin referencia SHA registrada en el proyecto"
        elif expected_manifest_hash==project_hash:reference_state="Coincide con el SHA registrado por el proyecto"
        else:reference_state="No coincide con el SHA registrado por el proyecto"
        exported=None;source_error=None
        if manifest.get("schema")=="DINO_PARAMETRIC_DESIGN_STUDY_V1":
            try:
                exported=_build_parametric_study_export(manifest,manifest_path or "",expected_manifest_hash or "",
                    [row],(self.dataset or {}).get("points",[]))[0]
            except (OSError,KeyError,TypeError,ValueError) as exc:source_error=str(exc)
        source_state={
            "VERIFIED_HASH_AND_IDENTITY":"Verificada: hash e identidad de la corrida coinciden",
            "NOT_LOADED":"Fuente no cargada en esta sesión; no se verificó",
            "NO_EXACT_ARTIFACT_MATCH":"Falló la búsqueda: no coincide un artifact exacto",
            "SOURCE_ARTIFACT_CHANGED":"Falló la verificación: el artifact cambió o su identidad no coincide",
        }.get((exported or {}).get("source_verification"),
            f"No se pudo verificar esta fuente · {source_error or 'el snapshot no declara un schema compatible'}")
        rpm_envelope=manifest.get("design_method")=="RPM_ENVELOPE_V1"
        group=next((item for item in manifest.get("groups",[])
            if item.get("index")==point.get("design_index")),{}) if rpm_envelope else {}
        sweep_path=point.get("sweep_manifest") or group.get("sweep_manifest")
        sweep_hash=point.get("sweep_manifest_sha256") or group.get("sweep_manifest_sha256")
        actual_sweep_hash=None
        if rpm_envelope and sweep_path:
            try:actual_sweep_hash=hashlib.sha256(Path(sweep_path).read_bytes()).hexdigest()
            except OSError:pass
        if not rpm_envelope:sweep_state="No aplica a este método de estudio"
        elif not sweep_path or not sweep_hash:sweep_state="No informado en el manifiesto"
        elif actual_sweep_hash is None:sweep_state="No disponible; no se pudo leer el manifiesto del barrido"
        elif actual_sweep_hash==sweep_hash:sweep_state="Verificado: hash coincide"
        else:sweep_state="FALLÓ: el hash del manifiesto del barrido cambió"
        lines=[f"Estudio: {manifest.get('study_id') or 'No informado'} · {manifest.get('design_method') or 'método no informado'}",
            f"Manifiesto: {manifest_path or 'Ruta no informada'}",
            f"SHA-256 guardado: {expected_manifest_hash or 'No disponible'}",
            f"SHA-256 actual: {actual_manifest_hash or 'No disponible'} · {manifest_state}",
            f"Referencia del proyecto: {reference_state}",
            f"Punto {point.get('index',row)} · RPM {format_number(point.get('rpm',manifest.get('rpm'))) if point.get('rpm',manifest.get('rpm')) is not None else 'No informada'}",
            f"Estado de ejecución: {_state_label(point.get('status') or 'NOT_REPORTED')}",
            f"Clasificación: {_state_label(point.get('classification') or 'NOT_REPORTED')}",
            f"Periodicidad observada: {_state_label(point.get('periodicity') or 'NOT_EVALUATED')}",
            f"Run: {point.get('source_run_id') or point.get('historical_source_run_id') or point.get('run_id') or 'No informado'}",
            f"Ruta del resultado: {point.get('run_directory') or 'No informada'}",
            f"Motor SHA-256: {point.get('engine_identity_sha256') or point.get('identity_sha256') or 'No informado'}",
            f"SHA-256 de resultado guardado: {point.get('result_sha256') or 'No informado'} · verificado: {(exported or {}).get('result_sha256') or 'No disponible'} · artifact guardado: {point.get('result_artifact_sha256') or 'No informado'}",
            f"Verificación de fuente: {source_state}",
            f"Manifiesto RPM anidado: {sweep_path or ('No informado' if rpm_envelope else 'No aplica')}",
            f"SHA-256 RPM guardado: {sweep_hash or ('No informado' if rpm_envelope else 'No aplica')} · actual: {actual_sweep_hash or 'No disponible' if rpm_envelope else 'No aplica'} · {sweep_state}",
            f"Validación científica: {manifest.get('scientific_validation','NOT_CLAIMED')} (no se infiere del estado de ejecución)"]
        self.design_study_traceability.setPlainText("\n".join(lines))

    def _refresh_design_study_filters(self):
        manifest=getattr(self,"design_study_manifest",None) or {};points=manifest.get("points",[])
        imported_by_run={str(row.get("run_id")):row for row in (self.dataset or {}).get("points",[])
            if row.get("run_id") is not None}
        controls=(self.study_filter_design,self.study_filter_rpm,
            self.study_filter_execution,self.study_filter_periodicity)
        for control in controls:control.blockSignals(True);control.clear()
        self.study_filter_design.addItem("Todos los diseños",None)
        designs={};rpms=set();statuses=set();periodicities=set()
        is_envelope=manifest.get("design_method")=="RPM_ENVELOPE_V1"
        for index,point in enumerate(points):
            design_index=point.get("design_index",index) if is_envelope else index
            label=(self.design_study_table.item(index,0).text()
                if index<self.design_study_table.rowCount() and self.design_study_table.item(index,0)
                else f"Diseño {int(design_index)+1}")
            if not is_envelope and index<self.design_study_table.rowCount() and self.design_study_table.item(index,1):
                label+=f" · {self.design_study_table.item(index,1).text()}"
            designs.setdefault(design_index,label)
            rpm=point.get("rpm")
            if rpm is None and not is_envelope:rpm=manifest.get("rpm")
            rpms.add(rpm if type(rpm) in (int,float) and math.isfinite(float(rpm)) else _STUDY_FILTER_MISSING)
            status=point.get("status")
            statuses.add(status if isinstance(status,str) and status else _STUDY_FILTER_MISSING)
            imported=imported_by_run.get(str(point.get("source_run_id") or point.get("run_id")),{})
            periodicity=imported.get("periodicity") or point.get("periodicity")
            periodicities.add(periodicity if isinstance(periodicity,str) and periodicity else _STUDY_FILTER_MISSING)
        for design_index,label in sorted(designs.items(),key=lambda item:str(item[0])):
            self.study_filter_design.addItem(label,design_index)
        self.study_filter_rpm.addItem("Todas las RPM",None)
        for rpm in sorted(rpms,key=lambda value:(value==_STUDY_FILTER_MISSING,
                                                   float(value) if value!=_STUDY_FILTER_MISSING else 0)):
            self.study_filter_rpm.addItem("RPM no registrada/válida" if rpm==_STUDY_FILTER_MISSING
                else f"{format_number(rpm)} RPM",rpm)
        self.study_filter_execution.addItem("Todos los estados",None)
        for status in sorted(statuses,key=lambda value:(value==_STUDY_FILTER_MISSING,str(value))):
            self.study_filter_execution.addItem("Estado no informado" if status==_STUDY_FILTER_MISSING
                else self._study_execution_state_label(status),status)
        self.study_filter_periodicity.addItem("Todas las periodicidades",None)
        for periodicity in sorted(periodicities,key=lambda value:(value==_STUDY_FILTER_MISSING,str(value))):
            self.study_filter_periodicity.addItem("Periodicidad no informada" if periodicity==_STUDY_FILTER_MISSING
                else _state_label(periodicity),periodicity)
        for control in controls:control.blockSignals(False)
        self._apply_design_study_filters()

    @staticmethod
    def _study_filter_matches(value,selected):
        if selected is None:return True
        if selected==_STUDY_FILTER_MISSING:return value is None
        return value==selected

    @staticmethod
    def _study_execution_state_label(value):
        labels={"COMPLETE":"Completo","CACHED":"Reutilizado","PREPARED":"Preparado",
            "RUNNING":"En ejecución","PARTIAL":"Parcial","CANCELLED":"Cancelado",
            "FAILED":"Falló","ERROR":"Error"}
        return labels.get(value,_state_label(value))

    def _apply_design_study_filters(self,*_):
        manifest=getattr(self,"design_study_manifest",None) or {};points=manifest.get("points",[])
        imported_by_run={str(row.get("run_id")):row for row in (self.dataset or {}).get("points",[])
            if row.get("run_id") is not None}
        design_filter=self.study_filter_design.currentData();rpm_filter=self.study_filter_rpm.currentData()
        execution_filter=self.study_filter_execution.currentData();periodicity_filter=self.study_filter_periodicity.currentData()
        is_envelope=manifest.get("design_method")=="RPM_ENVELOPE_V1";visible=0
        for index in range(self.design_study_table.rowCount()):
            point=points[index] if index<len(points) else {}
            design_index=point.get("design_index",index) if is_envelope else index
            rpm=point.get("rpm")
            if rpm is None and not is_envelope:rpm=manifest.get("rpm")
            status=point.get("status") if isinstance(point.get("status"),str) else None
            imported=imported_by_run.get(str(point.get("source_run_id") or point.get("run_id")),{})
            periodicity=imported.get("periodicity") or point.get("periodicity")
            periodicity=periodicity if isinstance(periodicity,str) else None
            rpm_value=rpm if type(rpm) in (int,float) and math.isfinite(float(rpm)) else None
            match=(self._study_filter_matches(design_index,design_filter) and
                self._study_filter_matches(rpm_value,rpm_filter) and
                self._study_filter_matches(status,execution_filter) and
                self._study_filter_matches(periodicity,periodicity_filter))
            self.design_study_table.setRowHidden(index,not match);visible+=int(match)
        self.design_study_table.clearSelection()
        current=self.design_study_table.currentRow()
        if current>=0 and self.design_study_table.isRowHidden(current):self.design_study_table.setCurrentCell(-1,-1)
        self.study_filter_count.setText(f"Puntos visibles: {visible} de {len(points)} · la exportación completa incluye todos")

    def clear_design_study_filters(self):
        for control in (self.study_filter_design,self.study_filter_rpm,
            self.study_filter_execution,self.study_filter_periodicity):control.setCurrentIndex(0)
        self._apply_design_study_filters()

    def _loaded_exploratory(self,data):
        requested_rpms=_referenced_curve_rpms(self.context.project,data)
        if requested_rpms:data['requested_rpms']=requested_rpms
        self.dataset=data;self.source=None;self.source_kind="EXPLORATORY";self.path_label.setText(f"{len(data['points'])} ciclos EXPLORATORY · provisional · no interpolación · no validación experimental")
        runs=sorted({str(r.get("run_id")) for r in data["points"] if r.get("run_id")})
        variants_shown=sorted({str(r.get("variant_id")) for r in data["points"]})
        self.source_notice.setText(f"Corridas exploratorias · variantes: {', '.join(variants_shown)} · sólo lectura, sin asociación automática al proyecto · sin validación experimental.")
        variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
        for name in variants:
            item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
        self._project_context_changed()
        self.variants.blockSignals(False)
        self.trace_metric.blockSignals(True);self.trace_metric.clear()
        traces=data.get("traces",[])
        self.trace_rpm.blockSignals(True);self.trace_rpm.clear();self.trace_rpm.addItem('Todas las RPM',None)
        for rpm in sorted({t['rpm'] for t in traces}):self.trace_rpm.addItem(f'{format_number(rpm)} RPM',rpm)
        self.trace_rpm.blockSignals(False)
        common=(set.intersection(*(set(row.get("channels",{})) for row in traces)
                                 if traces else [set()]))
        options=[]
        for key in sorted(common):
            if key.startswith("duct:exhaust:cell:") and key.endswith(":pressure_pa"):
                options.append((f"Presión absoluta escape · celda {key.split(':')[3]} (bar abs)",key))
            elif key.startswith("duct:exhaust:face:") and key.endswith(":mass_flow_kg_s"):
                options.append((f"Flujo escape · cara {key.split(':')[3]} (kg/s)",key))
        if "cylinder_pressure_pa" in common:
            options.append(("Presión absoluta cilindro (bar abs)","cylinder_pressure_pa"))
        for label,key in options:self.trace_metric.addItem(label,key)
        self.trace_metric.blockSignals(False)
        self.trace_group.setVisible(bool(traces and options))
        if traces and options:self.trace_status.setText("Conservación interna · sin auditoría independiente · muestras aceptadas" if data.get("audit_method")=="INTERNAL_CONSERVATION_NO_REPLAY" else "Integridad según formato · consultar auditoría por corrida" if data.get("audit_method")=="MIXED_SCHEMAS" else "Primarios re-auditados · ángulos comunes exactos · sin interpolación")
        elif not traces:self.trace_status.setText("Los primarios seleccionados no contienen trazas de presión/flujo disponibles.")
        else:self.trace_status.setText("No hay canales de presión/flujo comunes en los primarios seleccionados.")
        if not traces or not options:
            reason="No hay trazas auditadas de presión/flujo disponibles." if not traces else "No hay canales de presión/flujo comunes para superponer."
            self.source_notice.setText(self.source_notice.text()+" "+reason)
        self.redraw();self.redraw_trace();self._redraw_trace_map();self._update_condition_notice();self._update_engineering_compare();self._dataset_summary();self.evidence_updated.emit()
        self._update_design_study_summary()

    def _update_design_study_summary(self):
        manifest=getattr(self,"design_study_manifest",None)
        if not manifest:return
        self.export_design_study_button.setEnabled(bool(getattr(self,"design_study_manifest_path",None)))
        is_envelope=manifest.get("design_method")=="RPM_ENVELOPE_V1"
        is_factorial=manifest.get("design_method")=="FACTORIAL_2X2_V1"
        self.export_full_design_study_button.setVisible(not is_factorial)
        self.export_full_design_study_button.setEnabled(not is_factorial and
            bool(getattr(self,"design_study_manifest_path",None)) and bool(manifest.get("points")))
        self.export_factorial_effects_button.setVisible(is_factorial)
        self.export_factorial_effects_button.setEnabled(is_factorial and bool(getattr(self,"design_study_manifest_path",None)))
        self.export_factorial_plot_button.setVisible(is_factorial)
        self.export_factorial_plot_button.setEnabled(is_factorial and bool(getattr(self,"design_study_manifest_path",None)))
        dataset_points={str(row.get("run_id")):row for row in (self.dataset or {}).get("points",[])
                        if row.get("run_id") is not None}
        baseline_rows=[row for row in manifest.get("points",[]) if row.get("baseline")]
        baseline_points={str(row.get("rpm")):dataset_points.get(str(row.get("source_run_id") or row.get("run_id")))
            for row in baseline_rows} if is_envelope else {}
        baseline_row=next(iter(baseline_rows),None)
        baseline_point=(dataset_points.get(str(baseline_row.get("source_run_id") or baseline_row.get("run_id")))
            if baseline_row and not is_envelope else None)
        values={key:(baseline_point.get(key) if baseline_point and baseline_point.get(key+"_status")=="DEFINED" else None)
                for key in ("brake_power","brake_torque","BMEP")}
        point_name=manifest.get("parameter",{}).get("label","Parámetro")
        rpm_summary=("RPM: "+", ".join(format_number(value) for value in manifest["rpms"])
            if is_envelope else f"{manifest.get('rpm'):g} RPM")
        self.design_study_notice.setText(
            f"{manifest.get('study_id')} · {point_name} · {rpm_summary} · "
            f"EXPLORATORY · periodicidad evaluada por punto · validación científica NO RECLAMADA · "
            f"manifiesto: {getattr(self,'design_study_manifest_path','—')}")
        total_budget=manifest.get("total_budget_seconds")
        elapsed=manifest.get("elapsed_seconds")
        budget_text=(f"Presupuesto asignado: {format_number(total_budget)} s"
                     if isinstance(total_budget,(int,float)) and not isinstance(total_budget,bool)
                     else "Presupuesto asignado: no registrado")
        elapsed_text=(f"tiempo consumido registrado: {format_number(elapsed)} s"
                      if isinstance(elapsed,(int,float)) and not isinstance(elapsed,bool)
                      else "tiempo consumido: no registrado")
        rows=manifest.get("points",[])
        completed=sum(row.get("status") in {"COMPLETE","CACHED"} for row in rows)
        lifecycle_status={"PREPARED":"Preparado","RUNNING":"En ejecución","COMPLETE":"Completo",
            "PARTIAL":"Parcial","CANCELLED":"Cancelado"}.get(manifest.get("status"),"Estado no informado")
        stop_reason={"CANCELLED":"cancelación solicitada","BUDGET_EXHAUSTED":"presupuesto total agotado",
            "POINT_BUDGET_EXHAUSTED":"presupuesto del punto agotado","POINT_INCOMPLETE":"punto incompleto",
            "FAILED_CLOSED":"fallo cerrado","ALL_POINTS_FINISHED":"todos los puntos procesados",
            "ALL_DESIGNS_FINISHED":"todos los diseños procesados"}.get(manifest.get("stop_reason"))
        point_text=(f"puntos completos: {completed}/{len(rows)} · incompletos/no iniciados: {len(rows)-completed}"
                    if rows else "puntos: no registrados")
        lifecycle_text=f"Estado: {lifecycle_status} · {point_text}"
        if stop_reason:lifecycle_text+=f" · motivo: {stop_reason}"
        self.design_study_lifecycle_notice.setText(" · ".join((budget_text,elapsed_text,lifecycle_text)) +
            ". No se estima el tiempo restante de cálculo.")
        self.design_study_table.setRowCount(len(manifest.get("points",[])))
        for index,row in enumerate(manifest.get("points",[])):
            point=dataset_points.get(str(row.get("source_run_id") or row.get("run_id")),{})
            metrics=[]
            for key in ("brake_power","brake_torque","BMEP"):
                value=point.get(key) if point.get(key+"_status")=="DEFINED" else None
                metrics.append(format_number(value) if isinstance(value,(int,float)) else "—")
            power=point.get("brake_power") if point.get("brake_power_status")=="DEFINED" else None
            comparison_baseline=(baseline_points.get(str(row.get("rpm"))) if is_envelope else baseline_point)
            baseline_power=(comparison_baseline.get("brake_power") if comparison_baseline and comparison_baseline.get("brake_power_status")=="DEFINED" else values["brake_power"])
            delta=(format_number(power-baseline_power,signed=True) if isinstance(power,(int,float)) and isinstance(baseline_power,(int,float)) else "—")
            design_index=row.get("design_index",index) if is_envelope else index
            design_label="Baseline" if row.get("baseline") else f"Diseño {int(design_index)+1}"
            if row.get("status")=="CACHED" and row.get("reused_verified"):
                design_label += " · histórico verificado"
            factor_values=row.get("factor_values") or []
            factor_labels={factor.get("parameter",{}).get("id"):factor.get("parameter",{}).get("label") or
                factor.get("parameter",{}).get("id") for factor in manifest.get("factors",[])
                if isinstance(factor,dict) and isinstance(factor.get("parameter"),dict)}
            value_text=(" · ".join(
                f"{item.get('label') or factor_labels.get(item.get('parameter_id')) or item.get('parameter_id') or 'Factor'}="
                f"{format_number(item.get('value'))} {item.get('unit') or ''}".rstrip()
                for item in factor_values if isinstance(item,dict))
                        if factor_values else f"{format_number(row.get('value'))} {row.get('unit','')}")
            if is_envelope:value_text+=f" · {format_number(row.get('rpm'))} RPM"
            classification=point.get("classification") or row.get("classification") or "NOT_REPORTED"
            execution=self._study_execution_state_label(row.get("status") or "NOT_REPORTED")
            cells=[design_label,value_text,execution,
                _state_label(classification),
                _state_label(point.get("periodicity") or row.get("periodicity") or "NOT_EVALUATED"),
                str(point.get("cycles_completed",row.get("cycles_completed",0))),*metrics,delta]
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column==0:item.setData(Qt.ItemDataRole.UserRole,{"point_index":index,"manifest_point":row})
                if column==0:
                    trace=(f"Run de origen: {row.get('source_run_id') or row.get('run_id') or 'No informado'}\n"
                        f"Proyecto de origen: {row.get('historical_source_project_id') or 'No informado'}\n"
                        f"Ruta del resultado: {row.get('run_directory') or 'No informada'}\n"
                        f"Identidad de motor SHA-256: {row.get('identity_sha256') or row.get('engine_identity_sha256') or 'No disponible'}\n"
                        f"SHA-256 de result.json: {row.get('result_artifact_sha256') or 'No disponible'}\n"
                        f"SHA-256 de resultado: {row.get('result_sha256') or 'No disponible'}\n"
                        f"Reuso verificado: {'Sí · corrida histórica reutilizada tras verificar identidad y artefactos' if row.get('reused_verified') else 'No'}")
                    if row.get("history_reuse_policy"):
                        trace+=f"\nPolítica de reuso: {row['history_reuse_policy']}"
                    item.setToolTip(str(value)+"\n\n"+trace)
                elif column in (2,3,4,9):item.setToolTip(str(value))
                self.design_study_table.setItem(index,column,item)
        self._refresh_design_study_filters()
        if self.design_study_table.rowCount():
            self.design_study_table.setCurrentCell(0,0);self._design_study_point_selected(0)
        else:self.design_study_traceability.clear()
        self._refresh_design_response_plot()
        self._update_factorial_effects()
        self.design_study_group.show()

    def _update_factorial_effects(self):
        manifest=getattr(self,"design_study_manifest",None)
        available=bool(manifest and manifest.get("design_method")=="FACTORIAL_2X2_V1")
        self.factor_effects_group.setVisible(available)
        if not available:
            self.factor_effects_table.setRowCount(0);self.factor_effects_plot.set_effects(None);return
        effects=_factorial_effects_from_study(manifest,(self.dataset or {}).get("points",[]))
        self.factor_effects_plot.set_effects(effects)
        self.factor_effects_table.setRowCount(0)
        if not effects:
            self.factor_effects_notice.setText("El estudio factorial no contiene una matriz compatible.");return
        if effects["status"]=="AVAILABLE":
            factor_summary="; ".join(f"{factor['label']}: {factor['values']} {factor['unit']}".strip()
                for factor in effects["factors"])
            self.factor_effects_notice.setText(
                f"Contrastes descriptivos calculados para cuatro fuentes verificadas PERIOD_1 a {format_number(effects['rpm'])} RPM · "
                f"{factor_summary}. No son atribución causal ni validación predictiva.")
        else:
            self.factor_effects_notice.setText(
                f"Efectos no disponibles · {effects['reason']} Se conservan los cuatro puntos y sus estados; no se imputan ni interpolan resultados.")
        rows=[]
        for metric in effects["metrics"]:
            for effect in metric["effects"]:
                value=effect.get("value")
                status=("Descriptivo · no validado" if metric["status"]=="DEFINED" else
                    f"No disponible · {metric.get('reason') or effects.get('reason') or 'métrica no definida'}")
                rows.append((metric["label"],effect["term"],
                    f"{format_number(value,signed=True)} {effect['unit']}" if isinstance(value,(int,float)) else "—",
                    status,effect["formula"]))
        self.factor_effects_table.setRowCount(len(rows))
        for row_index,cells in enumerate(rows):
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column==4:item.setToolTip(str(value))
                if column==3:item.setToolTip(str(value))
                self.factor_effects_table.setItem(row_index,column,item)

    def export_design_study_csv(self):
        return self._export_design_study_csv(full_matrix=False)

    def export_full_design_study_csv(self):
        return self._export_design_study_csv(full_matrix=True)

    def _export_design_study_csv(self,*,full_matrix):
        manifest=getattr(self,"design_study_manifest",None)
        manifest_path=getattr(self,"design_study_manifest_path",None)
        if not manifest or not manifest_path:return False
        selected=(list(range(len(manifest.get("points",[])))) if full_matrix else
            sorted({index.row() for index in self.design_study_table.selectionModel().selectedRows()}))
        if not selected:
            self.design_study_notice.setText("El estudio no contiene puntos exportables." if full_matrix else
                "Seleccioná uno o más puntos de la matriz para exportarlos.")
            return False
        directory=Path(self.context.path).parent if self.context.path else Path.cwd()
        suggested=(directory/f"{manifest.get('study_id') or 'parametric-study'}-matriz-completa.csv"
            if full_matrix else directory)
        title="Exportar matriz paramétrica completa" if full_matrix else "Exportar puntos del estudio paramétrico"
        path,_=QFileDialog.getSaveFileName(self,title,str(suggested),"CSV (*.csv)")
        if not path:return False
        try:
            source=Path(manifest_path).resolve();raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            live=json.loads(raw.decode("utf-8"))
            reference=next((ref for ref in self.context.project.get("study_references",[])
                if Path(ref.get("path","")).resolve()==source),None)
            if (live!=manifest or not reference or reference.get("manifest_sha256")!=digest or
                    reference.get("study_id")!=manifest.get("study_id")):
                raise ValueError("el manifiesto cambió o no coincide con la referencia SHA guardada en el proyecto")
            imported_points=(self.dataset or {}).get("points",[])
            records=_build_parametric_study_export(live,source,digest,selected,imported_points)
            if len(records)!=len(selected):raise ValueError("la matriz cambió desde que se abrió el estudio")
            with Path(path).open("x",encoding="utf-8-sig",newline="") as stream:
                writer=csv.DictWriter(stream,fieldnames=_STUDY_EXPORT_FIELDS,extrasaction="ignore")
                writer.writeheader();writer.writerows(records)
            self.design_study_notice.setText(
                f"{len(records)} punto(s){' de la matriz completa' if full_matrix else ''} exportado(s) sin redondeo · SHA-256 del manifiesto {digest} · "
                "estados y fuentes conservados; valores ausentes permanecen vacíos.")
            return True
        except (OSError,ValueError,TypeError) as exc:
            QMessageBox.warning(self,"No se pudo exportar la matriz paramétrica",str(exc));return False

    def export_factorial_effects_csv(self):
        manifest=getattr(self,"design_study_manifest",None)
        manifest_path=getattr(self,"design_study_manifest_path",None)
        if not manifest or not manifest_path or manifest.get("design_method")!="FACTORIAL_2X2_V1":return False
        suggested=Path(self.context.path).parent if self.context.path else Path.cwd()
        suggested=suggested/f"{manifest.get('study_id') or 'factorial-study'}-contrasts.csv"
        path,_=QFileDialog.getSaveFileName(self,"Exportar matriz y contrastes factoriales",str(suggested),"CSV (*.csv)")
        if not path:return False
        try:
            source=Path(manifest_path).resolve();raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            live=json.loads(raw.decode("utf-8"))
            reference=next((ref for ref in self.context.project.get("study_references",[])
                if Path(ref.get("path","")).resolve()==source),None)
            if (live!=manifest or not reference or reference.get("manifest_sha256")!=digest or
                    reference.get("study_id")!=manifest.get("study_id")):
                raise ValueError("el manifiesto cambió o no coincide con la referencia SHA guardada en el proyecto")
            rows=_build_factorial_effects_csv(source,digest,live,(self.dataset or {}).get("points",[]))
            _write_factorial_effects_csv(path,rows)
            unavailable=sum(row["record_type"]=="CONTRAST" and row["contrast_status"]!="DESCRIPTIVE_DEFINED" for row in rows)
            self.design_study_notice.setText(
                f"4 puntos y 9 contrastes exportados · {unavailable} contraste(s) no disponibles conservados sin valor · "
                f"SHA-256 manifiesto {digest} · la exportación no implica validación predictiva.")
            return True
        except (OSError,ValueError,TypeError,csv.Error) as exc:
            QMessageBox.warning(self,"No se pudo exportar el estudio factorial",str(exc));return False

    def export_factorial_effect_plot(self):
        """Export the displayed factorial chart with exact source CSV and hashes."""
        manifest=getattr(self,"design_study_manifest",None)
        manifest_path=getattr(self,"design_study_manifest_path",None)
        if not manifest or not manifest_path or manifest.get("design_method")!="FACTORIAL_2X2_V1":return False
        suggested=Path(self.context.path).parent if self.context.path else Path.cwd()
        suggested=suggested/f"{manifest.get('study_id') or 'factorial-study'}-effects.png"
        selected,_=QFileDialog.getSaveFileName(self,"Exportar gráfico y fuentes factoriales",str(suggested),"PNG (*.png)")
        if not selected:return False
        output=Path(selected)
        if output.suffix.lower()!=".png":output=output.with_suffix(".png")
        csv_path=output.with_name(output.stem+".factorial-effects.csv")
        receipt_path=output.with_name(output.stem+".factorial-effects.json")
        created=[]
        try:
            source=Path(manifest_path).resolve();raw=source.read_bytes();manifest_digest=hashlib.sha256(raw).hexdigest()
            live=json.loads(raw.decode("utf-8"))
            reference=next((ref for ref in self.context.project.get("study_references",[])
                if Path(ref.get("path","")).resolve()==source),None)
            if (live!=manifest or not reference or reference.get("manifest_sha256")!=manifest_digest or
                    reference.get("study_id")!=manifest.get("study_id") or
                    reference.get("schema")!=manifest.get("schema") or
                    reference.get("source_project_id")!=manifest.get("project_id")):
                raise ValueError("el manifiesto cambió o no coincide con la referencia SHA guardada en el proyecto")
            current_effects=_factorial_effects_from_study(live,(self.dataset or {}).get("points",[]))
            if not current_effects or current_effects.get("metrics")!=self.factor_effects_plot.metrics:
                raise ValueError("la figura visible no coincide con los contrastes verificados actuales; reabrí el estudio antes de exportar")
            rows=_build_factorial_effects_csv(source,manifest_digest,live,(self.dataset or {}).get("points",[]))
            csv_stream=io.StringIO(newline="")
            writer=csv.DictWriter(csv_stream,fieldnames=_FACTORIAL_EFFECTS_CSV_FIELDS,extrasaction="raise")
            writer.writeheader();writer.writerows(rows)
            csv_bytes=("\ufeff"+csv_stream.getvalue()).encode("utf-8")
            csv_digest=hashlib.sha256(csv_bytes).hexdigest()
            image=self.factor_effects_plot.grab().toImage();buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            image_writer=QImageWriter(buffer,b"png")
            image_writer.setText("Dino.study_id",str(manifest.get("study_id") or ""))
            image_writer.setText("Dino.manifest_sha256",manifest_digest)
            image_writer.setText("Dino.factorial_csv_sha256",csv_digest)
            image_writer.setText("Dino.scientific_qualification","Descriptive factorial contrasts; NOT_CLAIMED; not predictive validation")
            if not image_writer.write(image):raise OSError(image_writer.errorString())
            png_bytes=bytes(buffer.data());buffer.close()
            qualification=("Contrastes factoriales descriptivos; NOT_CLAIMED; no constituyen validación predictiva ni inferencia causal.")
            receipt={"schema":"DINO_FACTORIAL_EFFECT_PLOT_EXPORT_V1","study_id":manifest.get("study_id"),
                "project_id":manifest.get("project_id"),"scientific_validation":"NOT_CLAIMED",
                "qualification":qualification,"manifest_path":str(source),"manifest_sha256":manifest_digest,
                "csv_path":str(csv_path.resolve()),"csv_sha256":csv_digest,
                "plot_path":str(output.resolve()),"plot_sha256":hashlib.sha256(png_bytes).hexdigest(),
                "effects_status":(self.factor_effects_plot.metrics and
                    ("AVAILABLE" if all(metric.get("status")=="DEFINED" for metric in self.factor_effects_plot.metrics) else "PARTIAL_OR_UNAVAILABLE")) or "UNAVAILABLE",
                "effects":self.factor_effects_plot.metrics}
            outputs=((output,png_bytes),(csv_path,csv_bytes),
                (receipt_path,(json.dumps(receipt,indent=2,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")))
            for target,_data in outputs:
                if target.exists():raise FileExistsError(f"no se sobrescriben artifacts existentes: {target}")
            for target,data in outputs:
                with target.open("xb") as stream:
                    created.append(target);stream.write(data)
            self.factor_effects_notice.setText(
                f"PNG, CSV de 13 filas y recibo exportados sin sobrescribir · SHA-256 manifiesto {manifest_digest} · "
                f"SHA-256 CSV {csv_digest} · {qualification}")
            return True
        except (OSError,ValueError,TypeError,csv.Error) as exc:
            for target in created:
                try:target.unlink(missing_ok=True)
                except OSError:pass
            QMessageBox.warning(self,"No se pudo exportar el gráfico factorial",str(exc));return False

    def _refresh_design_response_plot(self,*_):
        manifest=getattr(self,"design_study_manifest",None)
        if not manifest:return
        if manifest.get("design_method")=="RPM_ENVELOPE_V1":
            self.design_response_plot.set_series([])
            self.design_response_notice.setText("Envolvente RPM: se conservan los puntos exactos por diseño y régimen en la tabla y en las curvas principales. No se mezclan RPM en una respuesta geométrica 1D; los estados no periódicos permanecen identificados.")
            return
        parameter=manifest.get("parameter",{})
        if parameter.get("axes"):
            self.design_response_plot.set_series([])
            self.design_response_notice.setText(
                "Estudio de dos factores: los cuatro diseños se conservan en la tabla. "
                "No se reduce una matriz factorial a una respuesta unidimensional ni se infieren efectos.")
            return
        points_by_run={str(row.get("run_id")):row for row in (self.dataset or {}).get("points",[])}
        metric=self.design_response_metric.currentData() or "brake_power"
        metric_labels={"brake_power":("Potencia de freno","kW"),
            "brake_torque":("Torque de freno","N·m"),"BMEP":("BMEP","kPa")}
        label,unit=metric_labels[metric]
        baseline_points=[];alternate_points=[];valid_count=0
        for study_point in manifest.get("points",[]):
            source_id=study_point.get("source_run_id") or study_point.get("run_id")
            result=points_by_run.get(str(source_id),{})
            periodicity=result.get("periodicity") or result.get("classification")
            value=result.get(metric)
            valid=(periodicity in {"PERIOD_1","PERIOD_2"} and
                result.get(metric+"_status")=="DEFINED" and type(value) in (int,float) and math.isfinite(float(value)))
            point={"parameter_value":study_point.get("value"),"value":float(value) if valid else None,
                "reason":None if valid else (result.get("classification") or study_point.get("status") or "Métrica no definida")}
            if valid:valid_count+=1
            (baseline_points if study_point.get("baseline") else alternate_points).append(point)
        series=[{"name":"Baseline","role":"baseline","x_key":"parameter_value",
                 "x_label":f"{parameter.get('label','Parámetro')} ({parameter.get('unit','')})",
                 "unit":unit,"connect":False,"points":baseline_points},
                {"name":"Diseños alternativos","x_key":"parameter_value",
                 "x_label":f"{parameter.get('label','Parámetro')} ({parameter.get('unit','')})",
                 "unit":unit,"connect":False,"points":alternate_points}]
        self.design_response_plot.set_series(series,y_scale_mode="data_margin")
        self.design_response_notice.setText(
            f"{label} · {valid_count} punto(s) periódico(s) con métrica definida. "
            "Sólo marcadores observados; los puntos ausentes y no convergidos siguen visibles en la tabla. Sin interpolación ni ajuste.")
    def _exploratory_failed(self,message):
        self.path_label.setText("Ejecución EXPLORATORY inválida");self.trace_group.hide();QMessageBox.warning(self,"Artifact exploratorio inválido",message)
    def load(self,path,*,historical=False):
        path=Path(path)
        if path.suffix.lower() in {".json",".csv"}:
            try:
                metadata=path.with_suffix('.json') if path.suffix.lower()=='.csv' else path
                raw=json.loads(metadata.read_text(encoding="utf-8"))
                historical=historical or raw.get("schema")=="FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1"
            except (OSError,ValueError):pass
        self.loading=True;self.trace_group.hide();self.path_label.setText(f"Cargando {path}…")
        def done(data):
            if data.get("schema")==CROSS_STUDY_CSV_SNAPSHOT_SCHEMA:
                self._show_cross_study_csv_snapshot(data,path)
                return
            if data.get("schema")==PARAMETRIC_STUDY_SNAPSHOT_SCHEMA:
                self._show_parametric_study_csv_snapshot(data,path)
                return
            if data.get("schema")==PARAMETRIC_FACTORIAL_SNAPSHOT_SCHEMA:
                self._show_parametric_factorial_csv_snapshot(data,path)
                return
            self.variants.show();self.baseline_label.show();self.baseline_selector.show();self.baseline_notice.show()
            self.export_report_button.show();self.export_table_button.show();self.export_plot_button.show()
            self.study_csv_snapshot_group.hide();self.factorial_csv_snapshot_group.hide();self.cross_study_csv_snapshot_group.hide()
            self.dataset=data;self.source=path
            legacy=data.get("schema")=="DINO_DESKTOP_LEGACY_HISTORICAL_SUMMARY_V1"
            self.source_kind="LEGACY_HISTORICAL" if legacy else "HISTORICAL_IMPL2" if historical else "IMPORTED_EXTERNAL"
            if legacy:
                self.source_notice.setText("Resultado heredado · sólo resumen almacenado · sin curva de potencia/torque ni validación experimental. El estado científico original se conserva.")
            elif historical:
                self.source_notice.setText("EVIDENCIA HISTÓRICA IMPL2 · sintética · importada explícitamente · no pertenece a la corrida actual de este proyecto · validación experimental no realizada.")
            else:
                self.source_notice.setText(f"Datos importados desde fuera del proyecto {self.context.project['project_id']}. Se conservan su provenance, identidades, huecos y clasificaciones originales.")
            self.path_label.setText(f"{path} · {len(data['points'])} puntos · {data['provenance']} · validación experimental {data['experimental_validation']}")
            variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
            for name in variants:
                item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
            self.variants.blockSignals(False);self._project_context_changed();self.loading=False;self.redraw();self._baseline_changed();self._dataset_summary();self.evidence_updated.emit()
        def fail(message):
            self.loading=False;self.path_label.setText("No se pudieron cargar los datos; selección anterior conservada")
            QMessageBox.warning(self,"Importación inválida",'No se pudo validar el CSV o reporte seleccionado. Los snapshots paramétricos son de sólo lectura; los CSV históricos conservan su JSON compañero.\n\nDetalle: '+message)
        run_background(load_results,path,on_done=done,on_error=fail)

    def _show_parametric_study_csv_snapshot(self,data,path):
        snapshot=data.get("snapshot") or {};points=data.get("snapshot_points") or []
        self.dataset=data;self.source=Path(path);self.source_kind="PARAMETRIC_STUDY_CSV_SNAPSHOT";self.loading=False
        self.trace_group.hide();self.compare_group.hide();self.design_study_group.hide();self.study_comparison_group.hide()
        self.variants.hide();self.baseline_label.hide();self.baseline_selector.hide();self.baseline_notice.hide()
        self.export_report_button.hide();self.export_table_button.hide();self.export_plot_button.hide()
        self.factorial_csv_snapshot_group.hide();self.cross_study_csv_snapshot_group.hide();self.study_csv_snapshot_group.show();self.result_tabs.setCurrentIndex(3)
        self.source_notice.setText(
            "Snapshot CSV paramétrico de sólo lectura. Los valores se presentan como se exportaron; "
            "no inicia ni reconstruye corridas, y la validación predictiva no se infiere del archivo.")
        self.path_label.setText(f"{Path(path)} · {len(points)} punto(s) · CSV SHA-256 {snapshot.get('csv_sha256','No disponible')}")
        self.run_summary.setText(
            f"Snapshot paramétrico · {snapshot.get('study_id','estudio sin ID')} · {len(points)} punto(s) seleccionados · "
            f"estado científico {snapshot.get('scientific_validation','NOT_CLAIMED')}")
        self.study_csv_snapshot_notice.setText(
            f"Estudio {snapshot.get('study_id')} · método {snapshot.get('design_method')} · "
            f"manifiesto SHA-256 {snapshot.get('manifest_sha256')} · CSV SHA-256 {snapshot.get('csv_sha256')} · "
            f"fuentes: estado registrado al exportar (no re-verificado en este snapshot) · sólo lectura · "
            f"validación científica {snapshot.get('scientific_validation','NOT_CLAIMED')}.")
        self.study_csv_snapshot_table.setRowCount(len(points))
        for index,point in enumerate(points):
            factors=[]
            for item in point.get("factor_values",[]):
                if not isinstance(item,dict):continue
                label=item.get("label") or item.get("parameter_id") or item.get("id") or "Factor"
                value=item.get("value")
                factors.append(f"{label}={value if value is not None else '—'} {item.get('unit') or ''}".rstrip())
            design=" · ".join(factors) or f"{point.get('design_value','')} {point.get('design_unit','')}".strip()
            verification=point.get("source_verification")
            source_state=("Verificada al exportar" if point.get("source_verified_at_export") else {
                "NOT_LOADED":"Fuente no cargada al exportar",
                "NO_EXACT_ARTIFACT_MATCH":"Sin coincidencia exacta de fuente al exportar",
                "SOURCE_ARTIFACT_CHANGED":"Artifact fuente alterado al exportar",
                "VERIFIED_HASH_AND_IDENTITY":"Verificada al exportar",
            }.get(verification,"No verificada al exportar"))
            cells=[str(point.get("point_index")),design,point.get("rpm",""),
                _state_label(point.get("classification") or point.get("execution_status") or "Sin informar"),
                _state_label(point.get("periodicity") or "NOT_REPORTED"),point.get("cycles_completed",""),
                point.get("brake_power_kw") or "—",point.get("brake_torque_nm") or "—",
                point.get("BMEP_kpa") or "—",source_state]
            detail=json.dumps(point,ensure_ascii=False,indent=2,sort_keys=True)
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(Qt.ItemDataRole.UserRole,detail);item.setToolTip(detail)
                self.study_csv_snapshot_table.setItem(index,column,item)
        self.study_csv_snapshot_detail.clear()
        if points:
            self.study_csv_snapshot_table.setCurrentCell(0,0)
            self._study_csv_snapshot_row_selected(0,0,-1,-1)
        else:self.study_csv_snapshot_detail.setPlainText("El snapshot no contiene puntos.")
        self.plot.set_series([]);self.power_curves.set_dataset(None,set());self.trace_plot.set_series([])
        self.trace_map.set_grid([],[]);self.point_table.setRowCount(0);self.details.setRowCount(0)
        for card,name in zip(self.metric_cards,('Potencia','Torque','BMEP','Auditoría')):card.setText(name+'\n—')
        self.result_tabs.setCurrentIndex(3);self.evidence_updated.emit()

    def _study_csv_snapshot_row_selected(self,row,column,previous_row,previous_column):
        item=self.study_csv_snapshot_table.item(row,0) if row>=0 else None
        self.study_csv_snapshot_detail.setPlainText(item.data(Qt.ItemDataRole.UserRole) if item else "")

    def _show_parametric_factorial_csv_snapshot(self,data,path):
        snapshot=data.get("snapshot") or {};points=data.get("snapshot_points") or []
        contrasts=data.get("snapshot_contrasts") or []
        self.dataset=data;self.source=Path(path);self.source_kind="PARAMETRIC_FACTORIAL_CSV_SNAPSHOT";self.loading=False
        self.trace_group.hide();self.compare_group.hide();self.design_study_group.hide();self.study_comparison_group.hide()
        self.study_csv_snapshot_group.hide();self.cross_study_csv_snapshot_group.hide();self.factorial_csv_snapshot_group.show()
        self.variants.hide();self.baseline_label.hide();self.baseline_selector.hide();self.baseline_notice.hide()
        self.export_report_button.hide();self.export_table_button.hide();self.export_plot_button.hide()
        self.result_tabs.setCurrentIndex(3)
        self.source_notice.setText(
            "Snapshot factorial CSV de sólo lectura. No crea corridas, no entra en curvas normales y no implica atribución causal ni validación predictiva.")
        self.path_label.setText(f"{Path(path)} · CSV SHA-256 {snapshot.get('csv_sha256','No disponible')}")
        self.run_summary.setText(
            f"Snapshot factorial · {snapshot.get('study_id','estudio sin ID')} · 4 puntos · 9 contrastes descriptivos · "
            f"validación científica {snapshot.get('scientific_validation','NOT_CLAIMED')}")
        manifest_state={"CURRENT_HASH_AND_IDENTITY_MATCH":"hash e identidad actuales coinciden",
            "CHANGED":"el manifiesto actual cambió", "UNAVAILABLE":"manifiesto original no disponible",
            "UNAVAILABLE_OR_INVALID":"no se pudo leer o validar el manifiesto actual",
            "IDENTITY_MISMATCH":"la identidad del manifiesto actual no coincide"}.get(
                snapshot.get("manifest_current_verification"),"estado del manifiesto actual no disponible")
        source_counts={}
        for point in points:
            state=point.get("current_source_verification","SOURCE_UNAVAILABLE")
            source_counts[state]=source_counts.get(state,0)+1
        source_labels={"CURRENT_HASH_AND_IDENTITY_MATCH":"verificado ahora (hash e identidad)",
            "SOURCE_UNAVAILABLE":"no disponible ahora; registrado verificado al exportar",
            "SOURCE_UNAVAILABLE_OR_INVALID":"no se pudo re-verificar ahora",
            "SOURCE_CHANGED_OR_IDENTITY_MISMATCH":"hash o identidad actual no coincide"}
        source_summary="; ".join(f"{count} {source_labels.get(state,'estado de fuente no disponible')}"
            for state,count in sorted(source_counts.items())) or "sin fuentes"
        bindings=snapshot.get("contrast_source_bindings")
        binding_notice=("El CSV de origen omitió los IDs/hashes fuente en filas CONTRAST; no se reconstruyen. Se conservan los cuatro registros POINT."
            if bindings=="MISSING_IN_EXPORTED_CONTRAST_ROWS" else "Las filas CONTRAST enlazan las cuatro fuentes POINT.")
        self.factorial_csv_snapshot_notice.setText(
            f"Estudio {snapshot.get('study_id')} · FACTORIAL_2X2_V1 · manifiesto SHA-256 {snapshot.get('manifest_sha256')} ({manifest_state}) · "
            f"CSV SHA-256 {snapshot.get('csv_sha256')} · verificación original registrada al exportar; revisión actual de artifacts: {source_summary} · "
            f"{binding_notice} · sólo lectura · validación científica {snapshot.get('scientific_validation','NOT_CLAIMED')}.")
        source_labels={"CURRENT_HASH_AND_IDENTITY_MATCH":"Verificada ahora",
            "SOURCE_UNAVAILABLE":"No disponible ahora · verificada al exportar",
            "SOURCE_UNAVAILABLE_OR_INVALID":"No se pudo re-verificar ahora",
            "SOURCE_CHANGED_OR_IDENTITY_MISMATCH":"Hash o identidad actual no coincide"}
        self.factorial_csv_snapshot_points.setRowCount(len(points))
        point_details=[]
        for index,point in enumerate(points):
            detail=json.dumps(point,ensure_ascii=False,indent=2,sort_keys=True);point_details.append(detail)
            factor_a=f"{point.get('factor_a_value','')} {point.get('factor_a_unit') or ''}".strip()
            factor_b=f"{point.get('factor_b_value','')} {point.get('factor_b_unit') or ''}".strip()
            source_state=source_labels.get(point.get("current_source_verification"),"Estado actual no disponible")
            cells=[point.get("point_index",""),factor_a,factor_b,point.get("rpm",""),
                point.get("execution_status",""),_state_label(point.get("classification") or "NOT_REPORTED"),
                _state_label(point.get("periodicity") or "NOT_REPORTED"),point.get("cycles_completed",""),
                point.get("brake_power_kw") or "—",point.get("brake_torque_nm") or "—",
                point.get("BMEP_kpa") or "—",source_state]
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(detail);item.setData(Qt.ItemDataRole.UserRole,detail)
                self.factorial_csv_snapshot_points.setItem(index,column,item)
        self.factorial_csv_snapshot_detail.setPlainText(point_details[0] if point_details else "El snapshot no contiene puntos.")
        self.factorial_csv_snapshot_contrasts.setRowCount(len(contrasts))
        for index,row in enumerate(contrasts):
            defined=row.get("contrast_status")=="DESCRIPTIVE_DEFINED"
            state="Descriptivo disponible · no validado" if defined else "No disponible · sin valor imputado"
            binding=row.get("contrast_source_binding_status")
            reason=row.get("contrast_reason") or (
                "Binding de fuentes ausente en fila CONTRAST; ver los cuatro puntos." if binding=="NOT_PRESENT_IN_EXPORTED_CONTRAST_ROW" else "—")
            cells=[row.get("metric_label") or row.get("metric_id"),row.get("contrast_term"),
                f"{row.get('contrast_value')} {row.get('contrast_unit') or ''}".strip() if defined else "—",
                state,row.get("contrast_formula") or "No informada",reason]
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column in (4,5):item.setToolTip(str(value))
                if column==0:
                    item.setData(Qt.ItemDataRole.UserRole,self._factorial_contrast_traceability_detail(row))
                self.factorial_csv_snapshot_contrasts.setItem(index,column,item)
        if points:self.factorial_csv_snapshot_points.setCurrentCell(0,0)
        self.plot.set_series([]);self.power_curves.set_dataset(None,set());self.trace_plot.set_series([])
        self.trace_map.set_grid([],[]);self.point_table.setRowCount(0);self.details.setRowCount(0)
        for card,name in zip(self.metric_cards,("Potencia","Torque","BMEP","Auditoría")):card.setText(name+"\n—")
        self.evidence_updated.emit()

    def _factorial_csv_snapshot_point_selected(self,row,column,previous_row,previous_column):
        item=self.factorial_csv_snapshot_points.item(row,0) if row>=0 else None
        self.factorial_csv_snapshot_detail.setPlainText(item.data(Qt.ItemDataRole.UserRole) if item else "")

    @staticmethod
    def _factorial_contrast_traceability_detail(row):
        binding=row.get("contrast_source_binding_status")
        binding_label={"MATCHES_POINT_ROWS":"Los cuatro IDs y hashes coinciden con las filas POINT del mismo CSV.",
            "NOT_PRESENT_IN_EXPORTED_CONTRAST_ROW":"El CSV no registró bindings para este contraste; no se reconstruyen."}.get(
                binding,"Estado de binding no disponible.")
        try:
            source_ids=json.loads(row.get("contrast_source_run_ids_json") or "[]")
        except (TypeError,json.JSONDecodeError):
            source_ids=[]
        try:
            result_hashes=json.loads(row.get("contrast_source_result_sha256s_json") or "[]")
        except (TypeError,json.JSONDecodeError):
            result_hashes=[]
        detail={"metric_id":row.get("metric_id"),"contrast_term":row.get("contrast_term"),
            "contrast_status":row.get("contrast_status"),"contrast_formula":row.get("contrast_formula"),
            "contrast_source_binding_status":binding,
            "binding_interpretation":binding_label,
            "contrast_source_run_ids":source_ids,
            "contrast_source_result_sha256s":result_hashes}
        return json.dumps(detail,ensure_ascii=False,indent=2,sort_keys=True)

    def _factorial_csv_snapshot_contrast_selected(self,row,column,previous_row,previous_column):
        item=self.factorial_csv_snapshot_contrasts.item(row,0) if row>=0 else None
        self.factorial_csv_snapshot_detail.setPlainText(item.data(Qt.ItemDataRole.UserRole) if item else "")

    def _show_cross_study_csv_snapshot(self,data,path):
        rows=data.get("rows") or [];statuses=data.get("source_statuses") or {}
        self.dataset=data;self.source=Path(path);self.source_kind="CROSS_STUDY_COMPARISON_CSV_SNAPSHOT";self.loading=False
        self.trace_group.hide();self.compare_group.hide();self.design_study_group.hide();self.study_comparison_group.hide()
        self.variants.hide();self.baseline_label.hide();self.baseline_selector.hide();self.baseline_notice.hide()
        self.export_report_button.hide();self.export_table_button.hide();self.export_plot_button.hide()
        self.study_csv_snapshot_group.hide();self.factorial_csv_snapshot_group.hide();self.cross_study_csv_snapshot_group.show()
        self.result_tabs.setCurrentIndex(3)
        self.source_notice.setText("Snapshot de comparación paramétrica de sólo lectura. Las filas y decisiones de pareo se importan tal como fueron exportadas; no se recalculan ni implican validación predictiva.")
        self.path_label.setText(f"{Path(path)} · {len(rows)} fila(s) · CSV SHA-256 {data.get('source_sha256')}")
        self.run_summary.setText(f"Comparación entre {len(data.get('study_ids') or [])} estudios · {len(rows)} filas · validación científica {_state_label(data.get('scientific_validation') or 'NOT_CLAIMED')}")
        current_counts={}
        for row_status in statuses.values():
            for state in row_status.values():current_counts[state]=current_counts.get(state,0)+1
        state_labels={"HASH_E_IDENTIDAD_ACTUALES_COINCIDEN":"hash e identidad actuales coinciden",
            "NO_VERIFICADA_AL_EXPORTAR":"no verificada al exportar",
            "FUENTE_NO_DISPONIBLE":"fuente original no disponible ahora",
            "FUENTE_NO_DISPONIBLE_O_INVALIDA":"fuente original no legible ahora"}
        source_summary="; ".join(f"{count} {state_labels.get(state,state)}" for state,count in sorted(current_counts.items())) or "sin referencias de artifacts"
        self.cross_study_csv_snapshot_notice.setText(
            f"CSV SHA-256 {data.get('source_sha256')} · baseline SHA-256 {data.get('baseline_engine_identity_sha256')} · "
            f"fuentes: {source_summary} · solo lectura · estado científico {_state_label(data.get('scientific_validation') or 'NOT_CLAIMED')}. "
            "Los campos vacíos permanecen vacíos; no se estiman métricas.")
        self.cross_study_csv_snapshot_table.setRowCount(len(rows));details=[]
        for index,row in enumerate(rows):
            state=statuses.get(index,{})
            def endpoint(side):
                study=row.get(f"study_{side}_id") or "—"
                value=row.get(f"point_{side}_design_value")
                design=(f"{value} {row.get(f'point_{side}_design_unit') or ''}".strip() if value else "—")
                classification=row.get(f"point_{side}_classification")
                periodicity=row.get(f"point_{side}_periodicity")
                rendered=" · ".join(part for part in (_state_label(classification or "NOT_REPORTED"),_state_label(periodicity or "NOT_REPORTED")) if part)
                return study,design,rendered or "—"
            a=endpoint("a");b=endpoint("b")
            metric_summary=" · ".join((
                "P " + " / ".join(row.get(name) or "—" for name in ("brake_power_a_kw","brake_power_b_kw","brake_power_delta_kw")),
                "T " + " / ".join(row.get(name) or "—" for name in ("brake_torque_a_nm","brake_torque_b_nm","brake_torque_delta_nm")),
                "BMEP " + " / ".join(row.get(name) or "—" for name in ("BMEP_a_kpa","BMEP_b_kpa","BMEP_delta_kpa"))))
            reason=(row.get("pairing_reason") or "RPM y contexto exactos"
                if row.get("pairing_status")=="EXACT_RPM_AND_OPERATING_CONTEXT" else
                row.get("pairing_reason") or _state_label(row.get("pairing_status") or "NOT_REPORTED"))
            cells=["Pareja exacta" if row.get("row_type")=="EXACT_PAIR" else "Sin pareja",
                row.get("rpm") or "—",a[1],a[2],b[1],b[2],metric_summary,reason]
            detail={"fila_exportada":row,"verificacion_actual_de_fuentes":state,
                "nota":"Snapshot de solo lectura; valores y clasificación conservados del CSV, sin recalcular."}
            detail_text=json.dumps(detail,ensure_ascii=False,indent=2,sort_keys=True);details.append(detail_text)
            for column,value in enumerate(cells):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setToolTip(detail_text);item.setData(Qt.ItemDataRole.UserRole,detail_text)
                self.cross_study_csv_snapshot_table.setItem(index,column,item)
        if rows:
            self.cross_study_csv_snapshot_table.setCurrentCell(0,0)
            self.cross_study_csv_snapshot_detail.setPlainText(details[0])
        else:self.cross_study_csv_snapshot_detail.setPlainText("El snapshot no contiene filas.")
        self.plot.set_series([]);self.power_curves.set_dataset(None,set());self.trace_plot.set_series([])
        self.trace_map.set_grid([],[]);self.point_table.setRowCount(0);self.details.setRowCount(0)
        for card,name in zip(self.metric_cards,("Potencia","Torque","BMEP","Auditoría")):card.setText(name+"\n—")
        self.evidence_updated.emit()

    def _cross_study_csv_snapshot_row_selected(self,row,column,previous_row,previous_column):
        item=self.cross_study_csv_snapshot_table.item(row,0) if row>=0 else None
        self.cross_study_csv_snapshot_detail.setPlainText(item.data(Qt.ItemDataRole.UserRole) if item else "")

    def _dataset_summary(self):
        rows=self.dataset.get('points',[]) if self.dataset else []
        states=sorted({_state_label(row.get('classification')) or 'Sin clasificación' for row in rows})
        kind={'HISTORICAL_IMPL2':'Histórico sintético','LEGACY_HISTORICAL':'Histórico heredado · sin métricas de prestaciones'}.get(getattr(self,'source_kind',None),'Resultados exploratorios / importados')
        self.run_summary.setText(f"{kind} · {len(rows)} puntos · {'; '.join(states)}")
        for table in (self.point_table,self.power_curves.points):
            table.setCurrentCell(-1,-1);table.clearSelection()
        self.details.setRowCount(0)
        for card,name in zip(self.metric_cards,('Potencia','Torque','BMEP','Auditoría')):card.setText(name+'\n—')
        if rows:self.show_point(rows[0])
    def redraw(self,*_):
        if not self.dataset:return
        metric=METRICS[self.metric_selector.currentText()];unit=self.metric_selector.currentText().split('(')[-1].rstrip(')')
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[]
        baseline=self.baseline_selector.currentData();ordered_names=sorted(selected)
        if baseline in ordered_names:ordered_names=[baseline]+[name for name in ordered_names if name!=baseline]
        for name in ordered_names:
            points=[]
            for row in sorted((r for r in self.dataset['points'] if r['variant_id']==name),key=lambda r:r['rpm']):
                status=row.get(metric+'_status');value=row.get(metric) if status=='DEFINED' else None
                points.append({"rpm":row['rpm'],"value":value,"classification":row['classification'],"status":status,"reason":row.get(metric+'_reason'),"point":row})
            series.append({"name":("Baseline · " if name==baseline else "")+name,"unit":unit,"role":"baseline" if name==baseline else "variant","points":points})
        self.unit.setText(f"{unit} · los estados sin valor permanecen como huecos · sin interpolación")
        self.plot.set_series(series)
        rows=sorted((r for r in self.dataset['points'] if r['variant_id'] in selected),key=lambda r:(r['variant_id'],r['rpm']))
        self.point_table.blockSignals(True);self.point_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            periodicity=row.get('periodicity')
            if periodicity is None:
                periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
            cons=row.get('conservation')
            if isinstance(cons,dict) and cons and all(value in ("PASS",True) for value in cons.values()):cons_state="PASS"
            elif isinstance(cons,dict) and any(value=="FAIL" or (isinstance(value,dict) and value.get("status")=="FAIL") for value in cons.values()):cons_state="FAIL"
            else:cons_state="REPORTADA" if cons else "NO REPORTADA"
            values=[row['variant_id'],format_number(row['rpm']),_state_label(row['classification']),_state_label(periodicity),
                    _state_label(row.get('audit_status','NOT_REPORTED')),row.get('cycles_completed'),cons_state,
                    format_number(row.get('BMEP')) if row.get('BMEP_status')=='DEFINED' and row.get('BMEP') is not None else None]
            for j,value in enumerate(values):
                item=QTableWidgetItem('—' if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,row);self.point_table.setItem(i,j,item)
        self.point_table.blockSignals(False)
        self._update_condition_notice()
        self._update_engineering_compare()
        self.power_curves.set_dataset(self.dataset, selected)
        self.compare_measurement()
    def redraw_trace(self,*_):
        if not self.dataset or self.dataset.get("schema") not in {"DINO_EXPLORATORY_COMPARISON_V1","DINO_DESKTOP_ENGINEERING_DATA_V1"}:
            self.trace_plot.set_series([]);self.trace_legend.setText("");return
        key=self.trace_metric.currentData()
        if not key:
            self.trace_plot.set_series([]);self.trace_legend.setText("");self._redraw_trace_map();return
        selected={self.variants.item(i).text() for i in range(self.variants.count())
                  if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[];labels=[]
        for trace in self.dataset.get("traces",[]):
            if trace.get("variant_id") not in selected:continue
            if self.trace_rpm.currentData() is not None and trace.get('rpm')!=self.trace_rpm.currentData():continue
            channel=trace.get("channels",{}).get(key)
            if not isinstance(channel,dict):continue
            name=f"{trace['variant_id']} · {format_number(trace['rpm'])} RPM · ciclo {trace['cycle']}"
            labels.append(name)
            pressure=key.endswith("pressure_pa")
            unit="bar abs" if pressure else channel.get("unit","")
            values=[(float(value)/100000.0 if value is not None else None) for value in channel.get("values",[])] if pressure else channel.get("values",[])
            baseline=self.baseline_selector.currentData()==trace.get("variant_id")
            series.append({"name":name,"unit":unit,"role":"baseline" if baseline else "variant",
                "x_key":"angle_deg","x_label":"Ángulo de cigüeñal (°)",
                "points":[{"angle_deg":angle,"value":value}
                           for angle,value in zip(trace["angles_deg"],values)]})
        pressure=key.endswith("pressure_pa")
        self.trace_plot.set_series(series,y_scale_mode="nonnegative_data_margin" if pressure else "data_margin")
        self.trace_legend.setText("Series: " + " | ".join(labels) if labels else "Sin trazas disponibles")
        self._redraw_trace_map()

    def _redraw_trace_map(self):
        """Render exact cell/angle samples into a discrete QImage without interpolation."""
        if not self.dataset or self.dataset.get("schema") not in {"DINO_EXPLORATORY_COMPARISON_V1","DINO_DESKTOP_ENGINEERING_DATA_V1"}:
            self.trace_map.set_grid([],[]);return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        key=self.trace_metric.currentData()
        if not key or not key.startswith("duct:exhaust:"):
            self.trace_map.set_grid([],[]);return
        family="cell" if ":cell:" in key else ("face" if ":face:" in key else None)
        if family is None:self.trace_map.set_grid([],[]);return
        suffix=key.rsplit(":",1)[-1];channels=[];angles=set()
        traces=[trace for trace in self.dataset.get("traces",[]) if trace.get("variant_id") in selected and
                (self.trace_rpm.currentData() is None or trace.get('rpm')==self.trace_rpm.currentData())]
        for trace in traces:
            for channel,channel_doc in (trace.get("channels") or {}).items():
                if not (channel.startswith(f"duct:exhaust:{family}:") and channel.endswith(":"+suffix)):continue
                values=channel_doc.get("values",[]) if isinstance(channel_doc,dict) else channel_doc
                angles.update(float(a) for a in trace.get("angles_deg",[]))
                index=int(channel.split(":")[3]);positions=self._trace_positions(trace,family)
                if family=="cell" and index+1<len(positions):length=abs(float(positions[index+1])-float(positions[index]))*1000;position=(float(positions[index])+float(positions[index+1]))/2
                elif index<len(positions):length=1.;position=float(positions[index])
                else:length=1.;position=None
                label=f"{trace.get('variant_id','variante')} · {family} {index} · {trace.get('run_id','run')}"
                channels.append({"trace":trace,"label":label,"index":index,"values_by_angle":{float(a):v for a,v in zip(trace.get("angles_deg",[]),values)},"length_mm":length,"position_m":position})
        ordered=sorted(angles);rows=[]
        for entry in channels:
            rows.append({"label":entry["label"],"group":f"{entry['trace'].get('variant_id')} · {entry['trace'].get('run_id')} · {entry['trace'].get('cycle')}","length_mm":entry["length_mm"],"position_m":entry["position_m"],"values":[entry["values_by_angle"].get(angle) for angle in ordered]})
        self.trace_map.set_grid(ordered,rows)
        value_range=self.trace_map.value_range
        self.trace_map_legend.setText((f"Mapa discreto posición × ángulo · escala {format_number(value_range[0],5)}–{format_number(value_range[1],5)} · celdas reales en bandas proporcionales · muestras exactas, sin interpolar." if value_range else "Mapa discreto posición × ángulo · no hay muestras numéricas disponibles; no se interpolan ni se sustituyen datos ausentes."))
        self.trace_map.setToolTip("QImage construido con muestras originales. Cada banda representa una celda espacial y cada bloque coloreado conserva un valor muestreado; las ausencias quedan vacías.")

    def _trace_positions(self,trace,family):
        """Resolve positions only when the loaded run hash matches this project config exactly."""
        point=next((row for row in (self.dataset or {}).get("points",[]) if row.get("point_id")==trace.get("point_id")),None)
        variant=trace.get("variant_id");engine=(self.context.project["base_engine"] if variant=="base" else self.context.project["variants"].get(variant))
        if not point or not engine or point.get("point_configuration_sha256")!=engine.get("native_configuration_sha256"):
            return []
        duct=next((d for d in engine["native_configuration"].get("ducts",[]) if d.get("id")=="exhaust"),None)
        mesh=(duct or {}).get("mesh",{})
        return mesh.get("faces" if family=="cell" else "centers",[])
    def _point_row_selected(self,row,*_):
        if row<0 or self.point_table.item(row,0) is None:return
        data=self.point_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        if data:self.show_point({"point":data,"rpm":data['rpm'],"value":None})
    def show_point(self,point):
        row=point.get('point',point)
        self._selected_point_id=row.get("point_id")
        if row.get('rpm') is not None:
            index=self.trace_rpm.findData(row['rpm'])
            if index>=0:self.trace_rpm.setCurrentIndex(index)
        def card(label,key,unit):
            status=row.get(key+"_status");value=row.get(key)
            if status=="DEFINED" and value is not None:return f"{label}\n{format_number(value,5)} {unit}"
            transient=row.get("transient_estimates",{}).get(key)
            if transient is not None:return f"{label}\n{format_number(transient,5)} {unit} · TRANSITORIO, NO CONVERGIDO"
            reason=row.get(key+"_reason") or row.get(key+"_status") or "No reportado"
            return f"{label}\nNo definido · {_state_label(reason)}"
        self.metric_cards[0].setText(card("Potencia","brake_power","kW"))
        self.metric_cards[1].setText(card("Torque","brake_torque","N·m"))
        self.metric_cards[2].setText(card("BMEP","BMEP","kPa"))
        self.metric_cards[3].setText(f"Auditoría\n{_state_label(row.get('audit_status','NOT_REPORTED'))}")
        self.metric_cards[3].setToolTip(f"Código original: {row.get('audit_status','NOT_REPORTED')}\nRecomputada: {_state_label(row.get('audit_recomputed','NOT_REPORTED'))}. Detalle completo en Trazabilidad.")
        conservation=row.get('conservation')
        conservation_label=("balance interno · máx. residuo relativo "+format_number(max(conservation['relative'].values()),3) if isinstance(conservation,dict) and conservation.get('relative') else 'reportada' if conservation else 'no reportada')
        kind={'HISTORICAL_IMPL2':'Histórico sintético · ','LEGACY_HISTORICAL':'Histórico heredado · '}.get(getattr(self,'source_kind',None),'Resultado exploratorio / importado · ')
        self.run_summary.setText(kind+f"{row.get('variant_id','Variante no informada')} · {format_number(row.get('rpm'))} RPM · {_state_label(row.get('classification'))} · periodicidad {_state_label(row.get('periodicity') or row.get('classification'))} · {conservation_label}")
        periodicity=row.get('periodicity')
        if periodicity is None:
            periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
        items=[("Proyecto del resultado",row.get('project_id') or 'No informado en el artefacto'),
            ("Proyecto abierto",self.context.project["project_id"]), ("RPM",row.get('rpm')), ("Variante",row.get('variant_id')),
            ("Modo",row.get('mode','NOT_REPORTED · historical aggregate')),
            ("Clasificación",row.get('classification')), ("Periodicidad",periodicity),
            ("Auditoría primaria",row.get('audit_status','NOT_REPORTED')),
            ("Auditoría recomputada",row.get('audit_recomputed','NOT_REPORTED')),
            ("Auditoría registrada en el artifact heredado",row.get('historical_audit_status')),
            ("Gate registrado en el artifact heredado",row.get('historical_hard_gate')),
            ("Ciclos registrados",row.get('legacy_cycle_summary')),
            ("Resultado SHA-256",row.get('result_sha256')), ("Primario SHA-256",row.get('primary_sha256')),
            ("Configuración SHA-256",row.get('point_configuration_sha256')),
            ("Checkpoint SHA-256",row.get('checkpoint_sha256')),
            ("Carpeta de artifacts",row.get('artifact_directory')),
            ("Condiciones de operación",row.get('operating_conditions')),
            ("Ciclos completados",row.get('cycles_completed')),
            ("Tiempo acumulado (s)",row.get('elapsed_seconds')),
            ("Estabilidad observada; no sustituye periodicidad global",row.get('stability_observed')),
            ("Métrica",row.get(METRICS[self.metric_selector.currentText()])),
            ("Estado métrica",row.get(METRICS[self.metric_selector.currentText()]+'_status')),
            ("Motivo",row.get(METRICS[self.metric_selector.currentText()]+'_reason')),
            ("Conservación",row.get('conservation')),
            ("Puertas de plausibilidad",row.get('hard_gates')),
            ("Validación experimental",row.get('experimental_validation',self.dataset.get('experimental_validation','NOT_REPORTED'))),
            ("Procedencia",self.dataset.get('provenance','No informada'))]
        gates=row.get('hard_gates')
        items=list(row.get("engineering_diagnostics",{}).items())+items
        if isinstance(gates,dict) and "status" not in gates:
            items.extend((f"Puerta de plausibilidad · {name}",value)
                         for name,value in sorted(gates.items()))
        self.details.setRowCount(len(items))
        for i,(a,b) in enumerate(items):
            left=QTableWidgetItem(field_label(a));right=QTableWidgetItem(display_value(b))
            if str(a)!=left.text():left.setToolTip(f"Clave original: {a}")
            raw=(str(b) if b is not None else 'No informado')
            if raw!=right.text():right.setToolTip(f"Dato original: {raw}")
            self.details.setItem(i,0,left);self.details.setItem(i,1,right)
        self.evidence_updated.emit()
    def export_csv(self):
        if not self.dataset:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar tabla","dino-resultados.csv","CSV (*.csv)")
        if not path:return
        try:
            companion=Path(path).with_suffix('.json')
            reusable=self.dataset.get('schema')=='MOTORSIM_IMPORTED_CURVE_DATASET_V1'
            if reusable and companion.exists():
                raise FileExistsError(f"Ya existe {companion.name}. Elegí otro nombre para conservar ese archivo.")
            if reusable:json.dumps(self.dataset,allow_nan=False)
            keys=sorted(set().union(*(row.keys() for row in self.dataset['points'])))
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader()
                for row in self.dataset['points']:writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in keys})
            if reusable:
                from ..engine_results import SCHEMA
                report={"schema":SCHEMA,**self.dataset['identity'],
                    "experimental_validation":"NOT_PERFORMED","units":self.dataset['units'],
                    "points":self.dataset['points'],"campaign_status":self.dataset.get('campaign_status'),
                    "csv":Path(path).name,"csv_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                with companion.open('x',encoding='utf-8') as stream:
                    json.dump(report,stream,ensure_ascii=False,allow_nan=False,indent=2)
                self.path_label.setText(f"Exportado: {Path(path).name} + {companion.name}. Conservá ambos para reabrir los resultados.")
            else:
                self.path_label.setText("Tabla CSV exportada para consulta. Para reabrir corridas exploratorias, conservá result.json y sus artifacts originales.")
        except (OSError,ValueError) as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
    def _technical_report_args(self):
        selected=[self.variants.item(i).text() for i in range(self.variants.count())
                  if self.variants.item(i).checkState()==Qt.CheckState.Checked]
        return dict(source_kind=getattr(self,'source_kind','UNKNOWN'),
            selected_variants=selected,source_path=self.source,
            active_project_id=self.context.project.get('project_id'),
            design_study_manifest=getattr(self,'design_study_manifest',None),
            design_study_manifest_path=getattr(self,'design_study_manifest_path',None),
            design_study_manifest_sha256=getattr(self,'design_study_manifest_sha256',None),
            design_study_reference=getattr(self,'design_study_reference',None),
            factorial_effects=_factorial_effects_from_study(
                getattr(self,'design_study_manifest',None),(self.dataset or {}).get('points',[])))

    def export_technical_report(self):
        if not self.dataset:return False
        default=Path(self.source).with_suffix('.informe.html') if self.source else Path.cwd()/'dino-informe-tecnico.html'
        path,_=QFileDialog.getSaveFileName(self,"Exportar informe técnico autosuficiente",str(default),"Informe HTML (*.html)")
        if not path:return False
        try:
            write_technical_report(path,self.dataset,**self._technical_report_args())
            self.path_label.setText(f"Informe técnico autosuficiente exportado: {Path(path).name}")
            return True
        except (OSError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"No se pudo exportar el informe técnico",str(exc));return False

    def export_technical_report_pdf(self):
        if not self.dataset:return False
        default=Path(self.source).with_suffix('.informe.pdf') if self.source else Path.cwd()/'dino-informe-tecnico.pdf'
        path,_=QFileDialog.getSaveFileName(self,"Exportar informe técnico PDF",str(default),"Informe PDF (*.pdf)")
        if not path:return False
        if not path.lower().endswith('.pdf'):path+='.pdf'
        try:
            write_technical_report_pdf(path,self.dataset,**self._technical_report_args())
            self.path_label.setText(f"Informe técnico PDF exportado: {Path(path).name}")
            return True
        except (OSError,RuntimeError,TypeError,ValueError) as exc:
            QMessageBox.warning(self,"No se pudo exportar el informe PDF",str(exc));return False

    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,"Exportar gráfico","dino-curva.png","PNG (*.png)")
        if path:
            pix=QPixmap(self.plot.size());self.plot.render(pix)
            if not pix.save(path,"PNG"):QMessageBox.warning(self,"Error de escritura","No se pudo guardar el gráfico.")
    def export_trace_csv(self):
        if not self.trace_map.raw_samples:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar muestras originales x–θ","dino-mapa-ondas.csv","CSV (*.csv)")
        if not path:return
        angles=self.trace_map.angles
        try:
            with open(path,"w",encoding="utf-8-sig",newline="") as stream:
                writer=csv.writer(stream);writer.writerow(["Señal/celda","Posición (m)","Ángulo (deg)","Valor"])
                for row in self.trace_map.raw_samples:
                    for angle,value in zip(angles,row["values"]):writer.writerow([row["label"],row["position_m"],angle,value])
        except OSError as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
