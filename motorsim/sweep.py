"""Barrido acotado secuencial e índice local; sin Qt ni redes de campañas."""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

from .project import Project, ProjectError
from .project_case import validate_rpm
from .reference_results import PROFILE, ResultError, load_result, project_inputs, validated_model


def plan_rpms(start, end, step, cycle='2T'):
    validate_rpm(start, cycle); validate_rpm(end, cycle)
    if type(step) is not int or step <= 0:
        raise ProjectError('Incremento: debe ser un entero positivo.')
    if end <= start or (end-start) % step:
        raise ProjectError('Barrido: orden ascendente y llegada exacta al extremo final; no se ajustan valores.')
    count = (end-start)//step+1
    if not 2 <= count <= 5:
        raise ProjectError('Barrido: se requieren entre 2 y 5 puntos distintos.')
    return list(range(start, end+1, step))


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {'common_inputs', 'rpms'}:
        raise ResultError('Solicitud de barrido ilegible.')
    rpms=request['rpms']
    if not isinstance(rpms,list) or not 2<=len(rpms)<=5:
        raise ResultError('Lista de RPM incompleta.')
    inputs=request['common_inputs']
    _,profile=validated_model(inputs)
    cycle=inputs['case']['project_geometry']['cycle']
    for rpm in rpms:validate_rpm(rpm, cycle)
    if plan_rpms(rpms[0],rpms[-1],rpms[1]-rpms[0],cycle) != rpms:
        raise ResultError('Lista irregular de RPM.')
    if (profile != PROFILE or inputs.get('operating_point') != {'rpm':rpms[0]}
            or 'series_context' in inputs or 'origin' not in inputs):
        raise ResultError('Barrido: copia de proyecto, primer régimen y perfil B requeridos.')
    return json.loads(json.dumps(request))


def point_inputs(common, series_id, index, rpm):
    result = project_inputs(Project.from_dict(common['project_snapshot']),common['origin'],rpm=rpm,
                            series_context=dict(series_id=series_id,point_index=index))
    if common['project_snapshot'].get('format_version') == 5:
        result['project_snapshot'].pop('four_stroke')
        result['project_snapshot']['format_version'] = 5
    return result


def write_index(folder, index):
    # Solo el índice de esta carpeta exclusiva se actualiza; los puntos nunca se sobrescriben.
    temporary=None
    try:
        with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=folder,prefix='.series-',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(index,stream,ensure_ascii=False,allow_nan=False,indent=2)
        os.replace(temporary,folder/'series.json')
    finally:
        if temporary and temporary.exists():temporary.unlink()


def execute_sweep(folder, cancelled, report, request, *, run_point=None):
    from .reference_run import execute
    run_point=run_point or execute
    request=validate_request(request)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    started=time.monotonic()
    index=dict(format='motorsim-rpm-sweep',version=1,series_id=uuid.uuid4().hex,**request,
        state='running',reason='En curso',integration_seconds=0.,wall_seconds=0.,
        points=[dict(rpm=rpm,state='not_executed',reason='Pendiente',result=None,run_id=None,
                     manifest_sha256=None,timings=None) for rpm in request['rpms']])
    write_index(folder,index)
    report(dict(event='sweep_started',series_id=index['series_id']))
    for i,record in enumerate(index['points']):
        if cancelled.is_set():
            index.update(state='cancelled',reason='Cancelado entre puntos')
            break
        if index['integration_seconds']>=300:
            index.update(state='stopped',reason='Presupuesto acumulado de integración agotado')
            break
        record.update(state='running',reason='En ejecución')
        write_index(folder,index)
        report(dict(event='point_start',point_index=i,point_total=len(index['points']),rpm=record['rpm']))
        timings={}
        def progress(data):
            if data.get('event')=='finished':
                timings.update(data['timings'])
                return
            report(dict(data, point_index=i,point_total=len(index['points']),rpm=record['rpm'],
                    series_seconds=time.monotonic()-started,
                    accumulated_integration=index['integration_seconds']))
        try:
            inputs=point_inputs(index['common_inputs'],index['series_id'],i,record['rpm'])
            child=folder/f'point-{i+1:02}'
            run_point(child,cancelled,progress,inputs=inputs)
            result=load_result(child/'manifest.json')
            if result['inputs']!=inputs:raise ResultError('Punto ajeno a las entradas de la serie.')
            record.update(state=result['status'],reason=result['result']['stop'],result=f'point-{i+1:02}/manifest.json',
                run_id=result['manifest']['run_id'],manifest_sha256=hashlib.sha256((child/'manifest.json').read_bytes()).hexdigest(),
                timings=timings)
            index['integration_seconds']+=result['result']['seconds']
        except (OSError,ValueError,RuntimeError) as exc:
            record.update(state='error',reason=f'{type(exc).__name__}: {exc}')
        index['wall_seconds']=time.monotonic()-started
        write_index(folder,index)
        report(dict(event='point_finished',point_index=i,rpm=record['rpm'],state=record['state'],
                    series_seconds=index['wall_seconds']))
        if record['state']!='converged':
            index.update(state='cancelled' if record['state']=='cancelled' or cancelled.is_set() else 'stopped',reason=record['reason'])
            break
    else:
        index.update(state='converged',reason='Todos los puntos convergieron')
    if cancelled.is_set():index.update(state='cancelled',reason='Cancelación solicitada; sin iniciar puntos restantes')
    for point in index['points']:
        if point['state']=='not_executed':point['reason']='No ejecutado: '+index['reason']
    index['wall_seconds']=time.monotonic()-started
    write_index(folder,index)
    report(dict(event='sweep_finished',state=index['state'],path=str(folder/'series.json'),
                integration_seconds=index['integration_seconds'],wall_seconds=time.monotonic()-started))
    return 0 if index['state']=='converged' else (130 if index['state']=='cancelled' else 2)


def load_sweep(path):
    try:
        path=Path(path)
        if path.name!='series.json' or path.stat().st_size>2*1024*1024:raise ResultError('Elegí series.json de tamaño admitido.')
        index=json.loads(path.read_text(encoding='utf-8'))
        if (index['format']!='motorsim-rpm-sweep' or type(index['version']) is not int or index['version']!=1
                or not isinstance(index['series_id'],str) or re.fullmatch('[0-9a-f]{32}',index['series_id']) is None):
            raise ResultError('Identidad/formato de serie inválido.')
        validate_request({k:index[k] for k in ('common_inputs','rpms')})
        if index['state'] not in ('running','converged','cancelled','stopped') or not isinstance(index['reason'],str):
            raise ResultError('Estado de serie inválido.')
        for key in ('integration_seconds','wall_seconds',*(['interface_wall_seconds'] if 'interface_wall_seconds' in index else [])):
            if type(index[key]) not in (int,float) or not math.isfinite(index[key]) or index[key]<0:raise ResultError('Tiempo de serie inválido.')
        if len(index['points'])!=len(index['rpms']):raise ResultError('Cantidad de puntos contradictoria.')
        results=[];stopped=False;total=0.
        for i,(rpm,record) in enumerate(zip(index['rpms'],index['points'])):
            if record['rpm']!=rpm or record['state'] not in ('not_executed','running','converged','cancelled','not_converged','error'):
                raise ResultError('Punto/régimen inválido.')
            if not isinstance(record['reason'],str):raise ResultError('Motivo de punto inválido.')
            if stopped and record['state']!='not_executed':raise ResultError('Punto ejecutado después de una interrupción.')
            result=None
            if record['result'] is not None:
                if record['result']!=f'point-{i+1:02}/manifest.json':raise ResultError('Ruta de punto no admitida.')
                target=(path.parent/record['result']).resolve()
                if not target.is_relative_to(path.parent.resolve()):raise ResultError('Ruta externa de punto.')
                if hashlib.sha256(target.read_bytes()).hexdigest()!=record['manifest_sha256']:raise ResultError('Manifiesto de punto alterado.')
                result=load_result(target)
                if (result['inputs']!=point_inputs(index['common_inputs'],index['series_id'],i,rpm)
                        or result['manifest']['run_id']!=record['run_id'] or result['status']!=record['state']
                        or result['result']['stop']!=record['reason']):
                    raise ResultError('Punto ajeno a esta serie o estado contradictorio.')
                timing=record['timings']
                if not isinstance(timing,dict) or set(timing)!={'setup_seconds','writing_seconds','integration_seconds','wall_seconds'}:
                    raise ResultError('Faltan tiempos separados del punto.')
                if any(type(t) not in (int,float) or not math.isfinite(t) or t<0 for t in timing.values()):raise ResultError('Tiempo de punto inválido.')
                if timing['integration_seconds']!=result['result']['seconds']:raise ResultError('Tiempo de integración contradictorio.')
                total+=timing['integration_seconds']
            elif record['state'] not in ('not_executed','running','error') or record['run_id'] is not None or record['timings'] is not None or record['manifest_sha256'] is not None:
                raise ResultError('Punto sin resultado contradictorio.')
            if record['state']!='converged':stopped=True
            if record['state']=='running' and index['state']!='running':raise ResultError('Punto activo en serie terminada.')
            results.append(result)
        if not math.isclose(total,index['integration_seconds'],rel_tol=1e-12,abs_tol=1e-9):raise ResultError('Suma de integración incoherente.')
        if index['state']=='stopped' and not stopped:raise ResultError('Serie interrumpida sin interrupción.')
        if index['state']=='converged' and stopped:raise ResultError('Barrido sin todos los puntos convergidos.')
        return dict(index=index,results=results,path=path.resolve())
    except (OSError,ValueError,KeyError,TypeError,IndexError,ArithmeticError,RuntimeError) as exc:
        raise ResultError(f'Barrido ilegible: {exc}') from exc
