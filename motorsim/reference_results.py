"""Resultados de referencia o proyecto bajo condiciones fijas; sin Qt."""
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
import math
import os
import re
import time
from pathlib import Path
import uuid

from .adaptive import PROFILES
from .simulation import CV, Model, balances_ok, TWO_LAYOUT
from .four_stroke import FourStrokeModel, FourStrokeCase, SCENARIO_4T
from .simulation_case import SyntheticCase
from .prototype import write_json
from .project import Project
from .project_case import build_project_case, SCENARIO_ID, RPM_SCENARIO_ID, validate_rpm

PROFILE = PROFILES[1]
BAND_PA = 100
MODEL_VERSION = 'four-cv-0d-prescribed-heat-v1-external-regularized-rk4-v1'
FOUR_MODEL_VERSION = 'three-cv-0d-prescribed-heat-720-v1-external-regularized-rk4-v1'

def make_model(case=None, *, cycle='2T'):
    return FourStrokeModel(case) if cycle=='4T' or (case and case.project_geometry.cycle=='4T') else Model(case,external_band_pa=BAND_PA)


UNITS = dict(angle='deg continuous', pressure='Pa absolute', volume='m3',
             mass='kg', energy='J', time='s', temperature='K', fresh_fraction='1')
FILES = ('case.json', 'summary.json', 'samples.json')


class ResultError(ValueError):
    pass


def reference_inputs(cycle='2T'):
    model = make_model(cycle=cycle)
    four=cycle=='4T'
    return json.loads(json.dumps(dict(case=model.case.manifest(), profile=asdict(PROFILE),
        variant=dict(external_links=[0, 3] if four else [0, 5], delta_p_Pa=BAND_PA, calibrated=False),
        model_version=FOUR_MODEL_VERSION if four else MODEL_VERSION, initial_state=model.initial_state()[:model.layout.physical])))


def project_inputs(project, origin, profile=PROFILE, *, rpm=None, series_context=None):
    if profile not in (PROFILE, PROFILES[2]):
        raise ResultError('Solo perfiles B o C de comprobación.')
    _require(isinstance(origin, dict) and set(origin) == {'kind', 'project_name', 'source_path', 'dirty'},
             'Procedencia incompleta.')
    _require(origin['kind'] == 'project' and origin['project_name'] == project.name
             and type(origin['dirty']) is bool
             and (origin['source_path'] is None or isinstance(origin['source_path'], str)),
             'Identificación del proyecto inválida.')
    case, mapping = build_project_case(project, rpm=rpm)
    model = make_model(case)
    four=project.cycle=='4T'
    extra = {}
    if rpm is not None:
        extra['operating_point'] = dict(rpm=validate_rpm(rpm, project.cycle))
    if series_context is not None:
        _require(rpm is not None and isinstance(series_context, dict)
                 and set(series_context) == {'series_id', 'point_index'}
                 and isinstance(series_context['series_id'], str)
                 and re.fullmatch('[0-9a-f]{32}', series_context['series_id']) is not None
                 and type(series_context['point_index']) is int and 0 <= series_context['point_index'] < 5,
                 'Vínculo de serie inválido.')
        extra['series_context'] = series_context
    return json.loads(json.dumps(dict(case=case.manifest(), profile=asdict(profile),
        origin=origin, project_snapshot=project.to_dict(),
        **({'valve_mapping':mapping} if four else {'port_mapping':mapping}),
        scenario_identifier=SCENARIO_4T if four else (RPM_SCENARIO_ID if rpm is not None else SCENARIO_ID),
        variant=dict(external_links=[0, 3] if four else [0, 5], delta_p_Pa=BAND_PA, calibrated=False),
        model_version=FOUR_MODEL_VERSION if four else MODEL_VERSION, initial_state=model.initial_state()[:model.layout.physical], **extra)))


def validated_model(inputs):
    """Reconstruir todo el contrato; ningún parámetro libre llega al núcleo."""
    four=inputs.get('model_version')==FOUR_MODEL_VERSION
    if 'origin' not in inputs:
        cycle='4T' if four else '2T'
        expected, model, profile = reference_inputs(cycle), make_model(cycle=cycle), PROFILE
    else:
        project = Project.from_dict(inputs['project_snapshot'])
        profile = next((p for p in (PROFILE, PROFILES[2]) if asdict(p) == inputs['profile']), None)
        _require(profile is not None, 'Perfil no admitido.')
        rpm = None
        if 'operating_point' in inputs:
            _require(isinstance(inputs['operating_point'], dict) and set(inputs['operating_point']) == {'rpm'}, 'Punto operativo inválido.')
            rpm = validate_rpm(inputs['operating_point']['rpm'], project.cycle)
        expected = project_inputs(project, inputs['origin'], profile, rpm=rpm, series_context=inputs.get('series_context'))
        if inputs['project_snapshot'].get('format_version') == 5:
            expected['project_snapshot'].pop('four_stroke')
            expected['project_snapshot']['format_version'] = 5
        case, _ = build_project_case(project, rpm=rpm)
        model = make_model(case)
    _require(json.dumps(inputs, sort_keys=True) == json.dumps(expected, sort_keys=True),
             'Entradas no corresponden al modelo y escenario declarados.')
    return model, profile


def new_output_path():
    root = Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'.local/share')))/'MotorSim'/'Resultados'
    return root/(datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:10])


def save_result(folder, result, status, inputs, environment, *, timing_context=None):
    """El llamador crea una carpeta exclusiva; manifiesto escrito al final."""
    writing_started = time.monotonic()
    run_id = uuid.uuid4().hex
    compact = {k: v for k, v in result.items() if k not in ('last_two_cycles', 'partial')}
    partial = result.get('partial')
    if partial:
        compact['partial'] = {k: v for k, v in partial.items() if k != 'samples'}
    payloads = [dict(inputs=inputs), dict(status=status, result=compact, environment=environment),
                dict(cycles=result.get('last_two_cycles', []), partial=partial.get('samples', []) if partial else [])]
    hashes = {}
    for name, payload in zip(FILES, payloads):
        write_json(folder/name, dict(run_id=run_id, **payload))
        hashes[name] = hashlib.sha256((folder/name).read_bytes()).hexdigest()
    manifest = dict(format='motorsim-reference-result', version=4 if inputs['model_version']==FOUR_MODEL_VERSION else 3 if 'operating_point' in inputs else (2 if 'origin' in inputs else 1),
               model_version=inputs['model_version'], run_id=run_id, units=UNITS, files=hashes)
    write_json(folder/'manifest.json', manifest)
    timings=None
    if timing_context is not None:
        timings=dict(setup_seconds=timing_context['setup_seconds'],writing_seconds=time.monotonic()-writing_started,
                     integration_seconds=result['seconds'],wall_seconds=time.monotonic()-timing_context['started'])
        # Campo opcional ya admitido por el lector v1–v4; solo nuevas escrituras.
        manifest['timings']=timings
        write_json(folder/'manifest.json',manifest)
    return timings



def _require(condition, text):
    if not condition:
        raise ResultError(text)


def _finite(value):
    if isinstance(value, dict):
        for v in value.values():
            _finite(v)
    elif isinstance(value, list):
        for v in value:
            _finite(v)
    elif type(value) in (float, int):
        _require(math.isfinite(value), 'Valor no finito.')


def _number(value, minimum=None):
    _require(type(value) in (int, float) and math.isfinite(value), 'Se esperaba un número finito.')
    _require(minimum is None or value >= minimum, 'Número fuera de rango.')


def _vector(value, length):
    _require(isinstance(value, list) and len(value) == length, 'Dimensión de datos incorrecta.')
    for item in value:
        _number(item)


def _balances(value, layout=TWO_LAYOUT):
    _require(isinstance(value, dict) and set(value) == set(layout.cv)|{'global'}, 'Volúmenes del balance incorrectos.')
    for record in value.values():
        _vector(record['normalized_m_u_f'], 3)
        _vector(record['residual_kg_j_kg'], 3)
        _require(min(record['normalized_m_u_f']) >= 0, 'Residuo normalizado negativo.')


def _cycle(cycle, index, layout=TWO_LAYOUT):
    _require('K' in layout.cv or 'W_K_J' not in cycle, 'W_K no aplica al modelo 4T.')
    _require(cycle['cycle'] == index, 'Secuencia de ciclos incorrecta.')
    _vector(cycle['state'], layout.physical)
    _vector(cycle['Y'], len(layout.cv))
    _vector(cycle['net_link_mass_kg'], len(layout.ends))
    for key in ('W_C_J', 'p_max_Pa', 'F_s_kg', 'Q_J', 'converted_kg') + (('W_K_J',) if 'K' in layout.cv else ()):
        _number(cycle[key])
    _require(1000 <= cycle['p_max_Pa'] <= 2e7, 'Presión máxima fuera del dominio.')
    for j in range(len(layout.cv)):
        m, u, f = cycle['state'][3*j:3*j+3]
        _require(m > 0 and u > 0 and 0 <= f <= m and 0 <= cycle['Y'][j] <= 1
                 and math.isclose(cycle['Y'][j], f/m, rel_tol=1e-10, abs_tol=1e-14),
                 'Inventario final no físico o incoherente.')
    for key in ('discrete', 'independent'):
        _balances(cycle[key],layout)
    valid = balances_ok(cycle['discrete'], cycle['independent'])
    _require(type(cycle['balances_passed']) is bool and cycle['balances_passed'] == valid,
             'Estado de balances contradictorio.')
    conv = cycle['convergence']
    _require(type(conv['passed']) is bool, 'Convergencia ilegible.')
    if conv['passed']:
        _require(valid and cycle['F_s_kg'] > 0 and cycle['Q_J'] > 0, 'Convergencia sin balances/aporte.')
        for key, limit in (('m_relative', .002), ('U_relative', .002), ('Y_absolute', .002),
                           ('W_relative', .005), ('p_curve_relative', .005)):
            _number(conv[key], 0)
            _require(conv[key] <= limit, 'Convergencia fuera de criterio.')


def _samples(rows, complete, cycle=None, model=None):
    model = model or Model(external_band_pa=BAND_PA)
    case = model.case
    layout=model.layout
    work_keys=('W_C_J',)+( ('W_K_J',) if 'K' in layout.cv else ())
    _require(isinstance(rows, list) and len(rows) <= 2*layout.period+1, 'Muestras incorrectas.')
    if complete:
        _require(len(rows) == 2*layout.period+1, 'Ciclo de muestras incompleto.')
    for i, row in enumerate(rows):
        _require('K' in layout.cv or 'W_K_J' not in row, 'W_K no aplica a 4T.')
        for key in ('angle_deg', 'time_s', 'Q_J', 'converted_kg')+work_keys:
            _number(row[key])
        _vector(row['state'], layout.physical)
        _vector(row['V_m3'], len(layout.cv))
        _require(len(row['p_T_Y']) == len(layout.cv) and len(row['flows_kg_s_W_kg_s']) == len(layout.ends), 'Muestras de CV/enlaces incorrectas.')
        for node in row['p_T_Y']:
            _vector(node, 3)
            _require(1000 <= node[0] <= 2e7 and 100 <= node[1] <= 4000 and 0 <= node[2] <= 1,
                     'Estado físico fuera de dominio.')
        for flow in row['flows_kg_s_W_kg_s']:
            _vector(flow, 3)
        _, (_, volumes, flows) = model.evaluate(row['angle_deg'], row['state'])
        _require(all(math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-20)
                     for a, b in zip(row['V_m3'], volumes)), 'Volúmenes ajenos a la geometría declarada.')
        _require(all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
                     for stored, actual in zip(row['flows_kg_s_W_kg_s'], flows)
                     for a, b in zip(stored, actual)), 'Flujos ajenos al estado/modelo declarado.')
        for j in range(len(layout.cv)):
            m, u, f = row['state'][3*j:3*j+3]
            volume = row['V_m3'][j]
            _require(m > 0 and u > 0 and 0 <= f <= m and volume > 0, 'Inventario no físico.')
            p, t, y = row['p_T_Y'][j]
            _require(math.isclose(p, (case.gamma-1)*u/volume, rel_tol=1e-10)
                     and math.isclose(t, u/(m*case.gas_r/(case.gamma-1)), rel_tol=1e-10)
                     and math.isclose(y, f/m, rel_tol=1e-10, abs_tol=1e-14), 'Unidades/estado incoherentes.')
        _require(math.isclose(row['time_s'], (row['angle_deg']-case.initial_angle_deg)/(6*case.rpm), abs_tol=1e-12), 'Tiempo/ángulo incoherente.')
        if i:
            _require(row['angle_deg'] == rows[0]['angle_deg']+.5*i, 'Ángulo discontinuo o desordenado.')
    if complete:
        _require(rows[0]['angle_deg'] == case.initial_angle_deg+layout.period*(cycle['cycle']-1), 'Muestras de otro ciclo.')
        _require(cycle['p_max_Pa'] >= max(r['p_T_Y'][layout.cylinder][0] for r in rows),
                 'Presión máxima inferior a las muestras.')
        _require(rows[-1]['state'] == cycle['state'], 'Estado final no corresponde al resumen.')
        for key in ('Q_J', 'converted_kg')+work_keys:
            _require(rows[-1][key] == cycle[key], 'Muestras/resumen no corresponden.')


def load_result(path):
    """Datos declarativos, nombres fijos y hashes; nunca ejecutar contenido."""
    try:
        path = Path(path)
        def read(name):
            file = path.parent/name
            _require(file.stat().st_size <= 16*1024*1024, 'Archivo demasiado grande.')
            raw = file.read_bytes()
            value = json.loads(raw)
            _require(isinstance(value, dict), 'Se esperaba un objeto JSON.')
            _finite(value)
            return raw, value
        _require(path.name == 'manifest.json', 'Elegí manifest.json del resultado.')
        _, manifest = read('manifest.json')
        _require(manifest['format'] == 'motorsim-reference-result' and type(manifest['version']) is int and manifest['version'] in (1, 2, 3, 4)
                 and manifest['model_version'] == (FOUR_MODEL_VERSION if manifest['version']==4 else MODEL_VERSION) and manifest['units'] == UNITS,
                 'Formato, modelo o unidades no admitidos.')
        _require(set(manifest['files']) == set(FILES), 'Archivos vinculados incorrectos.')
        payloads = []
        for name in FILES:
            raw, value = read(name)
            _require(hashlib.sha256(raw).hexdigest() == manifest['files'][name]
                     and value['run_id'] == manifest['run_id'], 'Archivos de ejecuciones distintas o alterados.')
            payloads.append(value)
        case, summary, samples = payloads
        if manifest['version'] < 4:
            _require(('origin' in case['inputs']) == (manifest['version'] >= 2)
                     and ('operating_point' in case['inputs']) == (manifest['version'] == 3), 'Origen/versión contradictorios.')
        _require(case['inputs']['model_version']==manifest['model_version'],'Modelo contradictorio.')
        model, profile = validated_model(case['inputs'])
        status, result = summary['status'], summary['result']
        _require(status in ('converged', 'cancelled', 'not_converged', 'error'), 'Finalización desconocida.')
        _require(isinstance(result['stop'], str) and bool(result['stop']) and len(result['stop']) <= 4096, 'Motivo ilegible.')
        _number(result['seconds'], 0)
        _number(result['peak_process_MiB'], 0)
        _require(result['profile'] == asdict(profile), 'Perfil incorrecto.')
        if 'timings' in manifest:
            timing=manifest['timings']
            required={'setup_seconds','writing_seconds','integration_seconds','wall_seconds'}
            _require(isinstance(timing,dict) and set(timing) in (required,required|{'interface_wall_seconds'}), 'Tiempos separados inválidos.')
            for value in timing.values():_number(value,0)
            _require(timing['integration_seconds']==result['seconds'],'Tiempo de integración contradictorio.')
        cycles = result['cycles']
        _require(isinstance(cycles, list) and len(cycles) <= 30, 'Cantidad de ciclos incorrecta.')
        for i, cycle in enumerate(cycles, 1):
            _cycle(cycle, i, model.layout)
        _require(type(result['converged']) is bool and result['converged'] == (status == 'converged'), 'Estado contradictorio.')
        if status == 'converged':
            _require(len(cycles) >= 7 and all(c['cycle'] >= 5 and c['convergence']['passed'] for c in cycles[-3:]),
                     'Faltan tres ciclos de convergencia completa.')
        _require(len(samples['cycles']) == min(2, len(cycles)), 'Faltan muestras de los últimos ciclos.')
        for rows, cycle in zip(samples['cycles'], cycles[-2:]):
            _samples(rows, True, cycle, model)
        _samples(samples['partial'], False, model=model)
        return dict(manifest=manifest, inputs=case['inputs'], status=status, result=result,
                    samples=samples, path=path.resolve())
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError, RecursionError, RuntimeError) as exc:
        raise ResultError(f'Resultado ilegible: {exc}') from exc
