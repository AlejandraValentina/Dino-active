"""Magnitudes indicadas derivadas de trabajo guardado, sin integrar ni aplicar pérdidas."""
import math
from .reference_results import ResultError

NOTICE = 'Magnitudes indicadas derivadas del trabajo p·dV. No incluyen fricción ni pérdidas mecánicas.'


def indicated_output(work_j, rpm, cycle):
    """Devuelve W y N·m sin redondear; no son magnitudes al eje."""
    if cycle not in ('2T', '4T'):
        raise ResultError('Ciclo inválido para magnitudes indicadas.')
    for value, name in ((work_j, 'Trabajo indicado'), (rpm, 'RPM')):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ResultError(name+' debe ser un número finito.')
    if rpm <= 0:
        raise ResultError('RPM debe ser positiva.')
    revolutions = 1 if cycle == '2T' else 2
    power = work_j * (rpm / (60 * revolutions))
    torque = work_j / (2 * math.pi * revolutions)
    if not all(math.isfinite(value) for value in (power, torque)):
        raise ResultError('Magnitudes indicadas fuera del rango numérico.')
    return dict(indicated_power_W=power, indicated_torque_Nm=torque)


def result_metrics(result):
    """Solo resultados previamente cargados/validados; diagnósticos no se grafican."""
    if result['status'] != 'converged':
        return None
    case = result['inputs']['case']
    last = result['result']['cycles'][-1]
    return dict(rpm=case['rpm'], cycle=case['project_geometry']['cycle'],
                W_C_J=last['W_C_J'], p_max_Pa=last['p_max_Pa'],
                **indicated_output(last['W_C_J'], case['rpm'], case['project_geometry']['cycle']))


def sweep_metrics(sweep):
    """Preserva orden, huecos y procedencia del barrido validado."""
    index = sweep['index']
    cycle = index['common_inputs']['case']['project_geometry']['cycle']
    if cycle not in ('2T', '4T') or len(index['points']) != len(sweep['results']):
        raise ResultError('Barrido incompatible con Rendimiento.')
    rows = []
    for point, result in zip(index['points'], sweep['results']):
        row = dict(rpm=point['rpm'], state=point['state'], reason=point['reason'], metrics=None)
        if result is not None:
            case = result['inputs']['case']
            if case['project_geometry']['cycle'] != cycle or case['rpm'] != point['rpm'] or result['status'] != point['state']:
                raise ResultError('Punto ajeno al ciclo, régimen o estado del barrido.')
        if point['state'] == 'converged':
            if result is None:raise ResultError('Punto convergido sin resultado validado.')
            row['metrics'] = result_metrics(result)
        rows.append(row)
    return rows


def export_performance_csv(folder, sweep):
    from .comparison import write_csv_files
    rows=sweep_metrics(sweep)
    fields=('W_C_J','indicated_power_W','indicated_torque_Nm','p_max_Pa')
    data=[['series_id','run_id','cycle','rpm','state',*fields,'reason']]
    cycle=sweep['index']['common_inputs']['case']['project_geometry']['cycle']
    for row,point in zip(rows,sweep['index']['points']):
        data.append([sweep['index']['series_id'],point['run_id'],cycle,row['rpm'],row['state'],
                     *[(row['metrics'] or {}).get(key) for key in fields],row['reason']])
    return write_csv_files(folder,[('rendimiento.csv',data)])
