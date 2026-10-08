"""Aceptación R2 posterior a R1; no integra ni cambia el criterio histórico."""
import math
from .simulation import sensitivity, balances_ok


def evaluate_r2(runs):
    try:
        if len(runs)!=3: raise ValueError('Se requieren A/B/C completos.')
        curves=[]; finals=[]
        for run in runs:
            if run['converged'] is not True or not 7<=len(run['cycles'])<=30:
                raise ValueError('Falta convergencia completa.')
            if (not 0<=run['seconds']<=60 or not 0<=run['peak_MiB']<=512
                    or not 0<run['rhs_evaluations']<=2000000):
                raise ValueError('Presupuesto incumplido.')
            for cycle in run['cycles'][-3:]:
                for key in ('discrete','independent'):
                    if set(cycle[key])!={'I','C','E','global'}: raise ValueError('Balances incompletos.')
                    for record in cycle[key].values():
                        values=record['normalized_m_u_f']
                        if len(values)!=3 or any(not math.isfinite(v) or v<0 for v in values):
                            raise ValueError('Balance inválido.')
                for key,limit in (('m_relative',.002),('U_relative',.002),('Y_absolute',.002),('W_relative',.005),('p_curve_relative',.005)):
                    value=cycle['convergence'][key]
                    if not math.isfinite(value) or not 0<=value<=limit: raise ValueError('Convergencia fuera de criterio.')
                if (cycle['cycle']<5 or not cycle['convergence']['passed'] or
                    not balances_ok(cycle['discrete'],cycle['independent']) or
                    cycle['Q_J']<=0 or cycle['F_s_kg']<=0):
                    raise ValueError('Convergencia/balances/aporte incumplidos.')
                if len(cycle['state'])!=9 or len(cycle['Y'])!=3 or len(cycle['net_link_mass_kg'])!=4:
                    raise ValueError('Dimensiones incorrectas.')
                if (any(not math.isfinite(cycle[key]) for key in ('Q_J','F_s_kg','W_C_J','p_max_Pa'))
                        or not 1000<=cycle['p_max_Pa']<=2e7
                        or any(not math.isfinite(v) for v in cycle['net_link_mass_kg'])):
                    raise ValueError('Magnitud no física o no finita.')
                for i in range(3):
                    m,u,f=cycle['state'][3*i:3*i+3]
                    if not all(math.isfinite(v) for v in (m,u,f)) or min(m,u)<=0 or not 0<=f<=m:
                        raise ValueError('Estado no físico.')
                    y=cycle['Y'][i]
                    if not 0<=y<=1 or not math.isclose(y,f/m,rel_tol=1e-10,abs_tol=1e-14):
                        raise ValueError('Fracción fresca no física o incoherente.')
            if len(run['last_two_cycles'])!=2:raise ValueError('Faltan dos ciclos de muestras.')
            for samples,cycle in zip(run['last_two_cycles'],run['cycles'][-2:]):
                if len(samples)!=1441 or any(row['angle_deg']!=720*(cycle['cycle']-1)+i*.5 for i,row in enumerate(samples)):
                    raise ValueError('Fase/muestras incorrectas.')
                for row in samples:
                    if len(row['p_T_Y'])!=3:raise ValueError('Volúmenes incompletos.')
                    for p,t,y in row['p_T_Y']:
                        if not 1000<=p<=2e7 or not 100<=t<=4000 or not 0<=y<=1:
                            raise ValueError('Muestra fuera del dominio físico.')
            rows=run['last_two_cycles'][-1];last=run['cycles'][-1]
            if len(rows)!=1441 or any(row['angle_deg']!=720*(last['cycle']-1)+i*.5 for i,row in enumerate(rows)):
                raise ValueError('Fase/muestras incorrectas.')
            curves.append([row['p_T_Y'][1][0] for row in rows]);finals.append(last)
        original=sensitivity(runs,cylinder=1)
        spread=lambda values:max(values)-min(values)
        scale=max(100000.,*(c['p_max_Pa'] for c in finals))
        values=dict(W_C_J=spread([c['W_C_J'] for c in finals])/max(1.,*(abs(c['W_C_J']) for c in finals)),
            p_max_Pa=spread([c['p_max_Pa'] for c in finals])/scale,
            curve=max(spread(v) for v in zip(*curves))/scale,
            links=[spread(v)/max(1e-7,*map(abs,v)) for v in zip(*(c['net_link_mass_kg'] for c in finals))],
            Y=[spread(v) for v in zip(*(c['Y'] for c in finals))])
        practical=all(math.isfinite(v) and v<=1e-4 for v in
                      (values['W_C_J'],values['p_max_Pa'],values['curve'],*values['links'])) and all(
                      math.isfinite(v) and v<=5e-5 for v in values['Y'])
        passed=original['tolerances_passed'] and (original['decreasing_discrepancy'] or practical)
        temporal=[]
        for run,curve in zip(runs,curves):
            a,b=run['cycles'][-2:];previous=[r['p_T_Y'][1][0] for r in run['last_two_cycles'][-2]]
            temporal.append(dict(W_C_J=abs(b['W_C_J']-a['W_C_J']),p_max_Pa=abs(b['p_max_Pa']-a['p_max_Pa']),
                curve_Pa=max(abs(x-y) for x,y in zip(previous,curve)),
                Y=[abs(x-y) for x,y in zip(a['Y'],b['Y'])],
                links_kg=[abs(x-y) for x,y in zip(a['net_link_mass_kg'],b['net_link_mass_kg'])],
                monitored_pmax=b['p_max_Pa'],sampled_pmax=max(curve)))
        return dict(revision='R2',passed=passed,original_R1=original,spread=values,
                    practical_stability=practical,route='normal' if original['decreasing_discrepancy'] else
                    ('practical' if passed else 'blocked'),last_cycle_differences=temporal)
    except (ValueError,KeyError,TypeError,IndexError,ZeroDivisionError) as exc:
        return dict(revision='R2',passed=False,reason=str(exc))
