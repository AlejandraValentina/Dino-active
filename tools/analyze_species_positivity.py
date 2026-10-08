"""Análisis offline: compara JSON guardados, sin volver a integrar."""
import argparse
import json
import math
from pathlib import Path
from motorsim.prototype import write_json

ROOT=Path(__file__).resolve().parents[1]


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def max_difference(a,b):
    if isinstance(a,dict) and isinstance(b,dict):
        return max((max_difference(a[k],b[k]) for k in a.keys()&b.keys()),default=0.)
    if isinstance(a,list) and isinstance(b,list):
        return max((max_difference(x,y) for x,y in zip(a,b)),default=0.)
    if type(a) in (int,float) and type(b) in (int,float): return abs(a-b)
    return 0.


def analyze(folder):
    campaign=read(folder/'campaign.json')
    comparison=[]
    for row in [campaign['baseline'],*campaign['rows']]:
        rpm=row['rpm']; label=str(rpm) if row['candidate'] else '3000-baseline'
        if row['stop']=='límite de 60 segundos por resolución': row['status']='FAIL_TIME_BUDGET'
        new=read(folder/f'{label}.json')
        old=read(ROOT/f'results/frontera-baja-2t-20260917/{rpm}.json')
        a,b=new['result'],old['result']
        record=dict(label=label,manifest_equal=new['case']==old['case'],
                    exact_fields={k:a[k]==v for k,v in b.items() if k!='seconds'},
                    historical_integration_seconds=b['seconds'])
        record['scientific_exact_equal']=all(record['exact_fields'].values())
        row['manifest_equal']=record['manifest_equal']
        row['scientific_exact_equal']=record['scientific_exact_equal']
        record['cycle_differences']=[dict(cycle=c['cycle'],
            W_delta_J=c['W_C_J']-d['W_C_J'],pmax_delta_Pa=c['p_max_Pa']-d['p_max_Pa'],
            max_state_difference=[max(abs(c['state'][i]-d['state'][i]) for i in range(j,12,3)) for j in range(3)],
            discrete_fresh_residual_difference=max(abs(c['discrete'][k]['residual_kg_j_kg'][2]-d['discrete'][k]['residual_kg_j_kg'][2]) for k in c['discrete']),
            global_fresh_residual_kg=c['discrete']['global']['residual_kg_j_kg'][2])
            for c,d in zip(a['cycles'],b['cycles'])]
        pairs=[(x,y) for ca,cb in zip(a['last_two_cycles'],b['last_two_cycles'])
               for x,y in zip(ca,cb) if x['angle_deg']==y['angle_deg']]
        record['matched_sample_count']=len(pairs)
        record['max_matched_sample_differences']={k:max((max_difference(x[k],y[k]) for x,y in pairs),default=None)
            for k in ('state','p_T_Y','flows_kg_s_W_kg_s','W_C_J','Q_J','converted_kg')}
        events=[json.loads(line) for line in (folder/f'{label}-limiter.jsonl').read_text(encoding='utf-8').splitlines()]
        counts={}
        for event in events:
            key=str(event['cycle']); counts[key]=counts.get(key,0)+1
        record['limiter_by_cycle']=counts
        record['limiter_angle_range_deg']=[min(e['angle_deg'] for e in events),max(e['angle_deg'] for e in events)] if events else None
        # Compare correction scale with actual inventory ulps, not an invented tolerance.
        masses=[r['state'][i] for cycle in a['last_two_cycles'] for r in cycle for i in range(0,12,3)]
        largest_ulp=max((math.ulp(m) for m in masses),default=None)
        record['largest_sample_mass_ulp_kg']=largest_ulp
        record['max_correction_over_largest_sample_mass_ulp']=row['limiter_max_single_correction_kg']/largest_ulp if largest_ulp else None
        comparison.append(record)
    baseline=campaign['baseline']; candidate=next(r for r in campaign['rows'] if r['rpm']==3000)
    performance={k:dict(before=baseline[k],after=candidate[k],ratio=candidate[k]/baseline[k])
                 for k in ('wall_seconds','integration_seconds')}
    result=dict(comparisons=comparison,performance_3000=performance,
        note='JSON normalizados por lectura: no confundir listas persistidas con tuplas en memoria. '
             'Los flags de comparación del log original son defectuosos por esa diferencia de representación; '
             'esta comparación offline es la evidencia autoritativa. No se reejecutó el solver.')
    write_json(folder/'comparison.json',result)
    campaign['comparison_note']=result['note']
    write_json(folder/'campaign.json',campaign)
    lines=['# Campaña candidata de positividad 2T','',
        '| RPM | Estado | Ciclos | Mín. medio paso ° | Rechazos | W J | pmax Pa | Balance independiente % | Activaciones | α mín. | Corrección kg |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in campaign['rows']:
        values=[r['rpm'],r['status'],r['cycles'],r['minimum_half_step_deg'],sum(r['rejections'].values()),r['W_C_J'],r['pmax_Pa'],
            None if r['worst_independent'] is None else 100*r['worst_independent'],r['limiter_activation_count'],r['limiter_min_alpha'],r['limiter_total_corrected_fresh_kg']]
        lines.append('| '+' | '.join('—' if v is None else f'{v:.9g}' if isinstance(v,float) else str(v) for v in values)+' |')
    lines.extend(['','W/pmax/balance corresponden al último ciclo completo; no existen donde se muestra —.',
        'Correcciones incluyen intentos rechazados y subetapas, no masa neta de la trayectoria aceptada.',
        'La tabla no decide aceptación. Comparación exacta por campos y performance: comparison.json.',''])
    (folder/'summary.md').write_text('\n'.join(lines),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('folder',type=Path)
    analyze(parser.parse_args().folder)
