"""Reproducción offline de intentos guardados, a su paso original, sin campaña.

No se evalúan derivadas con estados inválidos ni se prosigue un paso rechazado.
Las reducciones sugeridas se calculan algebraicamente, no se integran.
"""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

from motorsim.adaptive import error_norm
from motorsim.examples import example_project
from motorsim.intake import intake_results
from motorsim.ports import port_results
from motorsim.project_case import build_project_case
from motorsim.prototype import write_json
from motorsim.reference_results import BAND_PA, PROFILE
from motorsim.simulation import Model, InvalidStage, rk4, burn_fraction


def thermo(model, angle, state):
    volumes, _, areas = model.geometry(angle)
    values = {}
    for i, name in enumerate(model.layout.cv):
        m, u, f = state[3*i:3*i+3]
        t = u/(m*model.cv)
        values[name] = dict(p_Pa=m*model.case.gas_r*t/volumes[i], T_K=t,
            m_kg=m, U_J=u, F_kg=f, Y=f/m, volume_m3=volumes[i])
    return dict(cv=values, areas_m2=list(areas))


def snapshot(model, angle, state, heat):
    data = dict(angle_deg=angle, heat=heat, **thermo(model,angle,state))
    derivative, (nodes, _, flows) = model.evaluate(angle,state,heat)
    links = []
    for j, ((left,right), flow, area) in enumerate(zip(model.layout.ends,flows,data['areas_m2'])):
        ln = model.case.reservoirs_pty[0] if left is None else nodes[left]
        rn = model.case.reservoirs_pty[1] if right is None else nodes[right]
        lname = 'reservoir-in' if left is None else model.layout.cv[left]
        rname = 'reservoir-out' if right is None else model.layout.cv[right]
        forward = flow[0] >= 0
        donor, receiver = (ln,rn) if forward else (rn,ln)
        links.append(dict(index=j, left=lname, right=rname, area_m2=area,
            mass_kg_s=flow[0], enthalpy_W=flow[1], fresh_kg_s=flow[2],
            donor=(lname if forward else rname) if flow[0] else None,
            receiver=(rname if forward else lname) if flow[0] else None,
            upstream_p_Pa=donor[0], downstream_p_Pa=receiver[0], donor_Y=donor[2],
            dp_left_minus_right_Pa=ln[0]-rn[0], backflow=flow[0]<0,
            regularized=j in (0,5),
            fresh_donor_consistent=flow[2] == flow[0]*donor[2] if j not in (0,5) else
                math.isclose(flow[2],flow[0]*donor[2],abs_tol=1e-24,rel_tol=1e-14)))
    data.update(links=links, derivatives={name:dict(zip(('dm_dt','dU_dt','dF_dt'),derivative[3*i:3*i+3]))
        for i,name in enumerate(model.layout.cv)}, Bdot_kg_s=derivative[model.layout.burn],
        global_fresh_derivative=sum(derivative[3*i+2] for i in range(4)),
        boundary_fresh_net=flows[0][2]-flows[-1][2], heat_active=heat is not None)
    return data


def replay_attempt(model, context):
    """Mismas operaciones y orden de Stepper.advance; solo registra sus llamadas."""
    angle, state, heat, h = (context[k] for k in ('angle','state','heat','h'))
    dt = h/model.rate
    groups = []
    def step(t,y,length,label):
        group = dict(label=label,t=t,dt_s=length,full_angle_deg=length*model.rate,stages=[])
        groups.append(group)
        def rhs(offset, candidate):
            a=angle+offset*model.rate
            record=dict(stage='K'+str(len(group['stages'])+1),time_offset_s=offset,state=candidate.copy())
            group['stages'].append(record)
            try:
                value=model.evaluate(a,candidate,heat)[0]
                record['snapshot']=snapshot(model,a,candidate,heat)
                return value
            except InvalidStage as exc:
                record.update(error=str(exc),angle_deg=a,thermo_only=thermo(model,a,candidate))
                raise
        def project(offset,candidate): return model.analytic(angle+offset*model.rate,candidate,heat)
        result=rk4(t,y,length,rhs,project)
        a,b=angle+t*model.rate,angle+(t+length)*model.rate
        converted=heat[1]*(burn_fraction(b,heat[0])-burn_fraction(a,heat[0])) if heat else 0.
        result[model.layout.burn]=y[model.layout.burn]+converted
        model.evaluate(b,result,heat)
        group['endpoint']=snapshot(model,b,result,heat)
        return result
    try:
        full=step(0.,state.copy(),dt,'full')
        middle=step(0.,state.copy(),dt/2,'half-1')
        fine=step(dt/2,middle,dt/2,'half-2')
        err, dominant=error_norm(state,full,fine,PROFILE)
        return dict(groups=groups, normalized_error=err, dominant=dominant)
    except InvalidStage as exc:
        return dict(groups=groups, error=str(exc), final_potential_state='Not evaluated: invalid RK stage')


def event_distances(model, angle):
    project=model.case.project_geometry
    intake=intake_results(project.intake,project.stroke_mm,project.rod_length_mm)
    events=[('intake-open',intake.opening),('intake-close',intake.closing),
            ('heat-start',model.case.heat_start_deg),('heat-end',(model.case.heat_start_deg+model.case.heat_duration_deg)%360)]
    for p in project.ports:
        values=port_results(p,project.stroke_mm,project.rod_length_mm)
        events.extend(((p.name+'-open',values.opening),(p.name+'-close',values.closing)))
    return [dict(name=name,phase_deg=phase,distance_deg=abs((angle-phase+180)%360-180)) for name,phase in events]


def negative_analysis(model, failure):
    ctx=failure['context']; advance,r=ctx['advance'],ctx['rk4']
    # Todas las negativas observadas en el cilindro se detectan en K4.
    if not ('k3' in r and 'k4' not in r): raise ValueError('Subetapa no prevista; revisar explícitamente.')
    y,dt=r['y'],r['dt']
    stage3=model.analytic(advance['angle']+(r['t']+dt/2)*model.rate,
        [v+dt/2*k for v,k in zip(y,r['k2'])],advance['heat'])
    snap=snapshot(model,advance['angle']+(r['t']+dt/2)*model.rate,stage3,advance['heat'])
    balance_links=[]
    for link in snap['links']:
        if 'C' not in (link['left'],link['right']): continue
        sign=1 if link['right']=='C' else -1
        balance_links.append(dict(link, signed_fresh_into_cylinder_kg_s=sign*link['fresh_kg_s']))
    rate=sum(l['signed_fresh_into_cylinder_kg_s'] for l in balance_links)
    f0,candidate=y[8],failure['state'][8]
    safe=PROFILE.atol_mass  # Escala diagnóstica explícita, nunca floor del estado.
    internal_sum=[0.,0.,0.,0.]
    for j,(left,right) in enumerate(model.layout.ends):
        if left is not None and right is not None:
            fresh=r['k3'][model.layout.physical+3*j+2]
            internal_sum[left]-=fresh;internal_sum[right]+=fresh
    return dict(cycle=ctx['cycle'],angle_deg=failure['angle_deg'],advance_angle_deg=advance['angle'],
        substage='K4',rk_branch='full' if dt==advance['dt'] else ('half-1' if r['t']==0 else 'half-2'),
        attempt_full_deg=advance['h'],attempt_full_dt_s=advance['dt'],
        rk_dt_s=dt,stage_offset_from_rk_base_s=dt,
        F_rk_base_kg=f0,F_previous_stage_K3_kg=stage3[8],
        F_increment_kg=dt*r['k3'][8],F_candidate_kg=candidate,
        candidate_m_C_kg=failure['state'][6],candidate_U_C_J=failure['state'][7],
        candidate_Y_C=candidate/failure['state'][6],negative_overshoot=abs(candidate)/max(abs(f0),safe),
        overshoot_reference='F at RK base',safe_scale_kg=safe,
        Bdot_kg_s=snap['Bdot_kg_s'],heat_active=advance['heat'] is not None,
        cylinder_links_at_K3=balance_links,stage3_snapshot=snap,
        stage3_fresh_rhs_kg_s=r['k3'][8],transport_sum_kg_s=rate,
        net_outflow_stage_increment_kg=-dt*rate,exceeds_rk_base_inventory=(-dt*rate>f0),
        exceeds_K3_inventory=(-dt*rate>stage3[8]),
        internal_global_fresh_rate_residual=sum(internal_sum),
        global_fresh_rate_residual=snap['global_fresh_derivative']-snap['boundary_fresh_net'],
        before_rejection_count=advance['failures'],
        only_F_invalid=all(m['m_kg']>0 and m['U_J']>0 and 100<=m['T_K']<=4000 and 1000<=m['p_Pa']<=2e7
                          for m in thermo(model,failure['angle_deg'],failure['state'])['cv'].values()),
        final_potential_state='Indeterminate under production contract: K4 RHS is forbidden for F<0.',
        replay=replay_attempt(model,advance))


def analyze(folder):
    base,_=build_project_case(example_project('2t-reference'),rpm=3000)
    for rpm in (1000,1500,1750):
        model=Model(replace(base,rpm=rpm),external_band_pa=BAND_PA)
        observation=json.loads((folder/f'{rpm}-observation.json').read_text(encoding='utf-8'))
        rejection=observation['rejections'][-1]; ctx=rejection['context']['advance']
        report=dict(rejection=rejection,base_snapshot=snapshot(model,ctx['angle'],ctx['state'],ctx['heat']),
            events=event_distances(model,ctx['angle']),dt_current_s=ctx['dt'],
            dt_requested_full_s=rejection['next_requested_full_deg']/model.rate,
            dt_requested_half_s=rejection['next_requested_half_deg']/model.rate,
            replay=replay_attempt(model,ctx))
        write_json(folder/f'{rpm}-diagnostic.json',report)
    model=Model(replace(base,rpm=2000),external_band_pa=BAND_PA)
    observation=json.loads((folder/'2000-observation.json').read_text(encoding='utf-8'))
    negatives=[r for r in observation['physical_failures'] if r['state'][8]<0]
    first,last=negatives[0],negatives[-1]
    report=dict(first_negative=negative_analysis(model,first),terminal_negative=negative_analysis(model,last),
        terminal_attempts=observation['tail'][-8:],negative_C_stage_count=len(negatives),
        reduction_next_full_deg=last['context']['advance']['h']*.5,
        reduction_next_half_deg=last['context']['advance']['h']*.25,
        reduction_executed=False,final_step_evaluated_after_negative=False)
    write_json(folder/'2000-diagnostic.json',report)


def markdown_table(headers, rows):
    def cell(v):
        if v is None: return '—'
        if isinstance(v,float): return f'{v:.10g}'
        return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',
                      *('| '+' | '.join(map(cell,row))+' |' for row in rows)])+'\n'


def reports(folder):
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8'))
    d=read('1000-diagnostic.json'); r=d['rejection']; snap=d['base_snapshot']
    content=['# Diagnóstico 1000 rpm — observación, sin corrección',
        'Ciclo 1. Último rechazo por error local antes de la parada por mínimo de paso. '
        'No existe ciclo completo ni W_C/pmax aceptados.',
        markdown_table(['Ángulo °','h actual °','medio paso actual °','dt completo s','dt solicitado completo s','dt solicitado medio s','error normalizado'],
            [[r['angle_deg'],r['proposed_deg'],r['substep_deg'],d['dt_current_s'],d['dt_requested_full_s'],d['dt_requested_half_s'],r['error']]]),
        'La propuesta siguiente es h=0,00141225378068°, medio paso=0,000706126890342° <0,001°. '
        'El intento actual sí respetaba el mínimo. Componente dominante C.F: diferencia entre '
        'paso completo y dos medios, dividida por15 y por la escala contractual. '
        'La reproducción offline a idéntico h devuelve exactamente el error observado.',
        '## Error por componente',
        markdown_table(['Componente','Estado inicial','Completo','Dos medios','Estimación absoluta','Escala','Error normalizado'],
            [[e[k] for k in ('component','start','full','fine','absolute_estimate','scale','normalized')] for e in r['component_errors']]),
        '## Estado al comienzo del intento',
        markdown_table(['CV','p Pa','T K','m kg','F kg','Y','U J'],
            [[cv,*[v[k] for k in ('p_Pa','T_K','m_kg','F_kg','Y','U_J')]] for cv,v in snap['cv'].items()]),
        markdown_table(['CV','dm/dt kg/s','dU/dt W','dF/dt kg/s'],[[cv,*v.values()] for cv,v in snap['derivatives'].items()]),
        '## Enlaces y geometría',
        markdown_table(['Enlace','Área m²','Caudal kg/s','Fresca kg/s','Δp izquierda−derecha Pa','Donante','Retorno'],
            [[str(l['index'])+': '+l['left']+'→'+l['right'],l['area_m2'],l['mass_kg_s'],l['fresh_kg_s'],l['dp_left_minus_right_Pa'],l['donor'],l['backflow']] for l in snap['links']]),
        'Todos los caudales, entalpías, estados de cada etapa y derivadas están en1000-diagnostic.json. '
        'Admisión I–K cerrada; transferencias y escape abiertos. Aporte térmico inactivo.',
        markdown_table(['Evento','Fase °','Distancia angular °'],[[e['name'],e['phase_deg'],e['distance_deg']] for e in d['events']]),
        'No coincide con apertura/cierre ni inicio/fin del calor. Las áreas permanecen constantes '
        'en este intento. El cambio relevante es de donante en ambas transferencias K↔C: '
        'Δp pasa de−7,65759 a+5,58971Pa entre K1 yK4 del paso completo. La trayectoria '
        'de dos medios resuelve la entrada de fresca en otras subetapas. Con F_C inicial=0, '
        'el error C.F domina aunque los errores de m/U son <1.',
        '**Mecanismo probable: F (cambio de sentido/donante en enlaces internos no regularizados cerca de Δp=0), '
        'con E (F_C=0).** No hay evidencia de evento geométrico A ni error de implementación '
        'del estimador D. La regularización exterior C no actúa sobre los enlaces2/3. '
        'No se ha realizado análisis espectral que permita afirmar rigidez temporal B. '
        'El coeficiente1/15 se aplica correctamente; su hipótesis de suavidad puede perder '
        'calidad al cruzar el cambio de donante, sin que eso constituya un bug demostrado.',
        'No se calcula una continuación por debajo del mínimo ni se cambia ninguna ley.']
    (folder/'diagnostico-1000.md').write_text('\n\n'.join(content)+'\n',encoding='utf-8')
    d=read('2000-diagnostic.json'); entries=[('Primera negativa observada',d['first_negative']),('Negativa terminal',d['terminal_negative'])]
    content=['# Diagnóstico 2000 rpm — positividad de etapas RK4',
        'La primera negativa ocurre en el ciclo1 y se recupera con rechazos/reducción. '
        'La negativa terminal ocurre en el ciclo6. Se conservan cinco ciclos completos '
        'como diagnóstico; no son una ejecución convergida.']
    for title,e in entries:
        content += ['## '+title,
            markdown_table(['Campo','Valor'],[[k,e[k]] for k in ('cycle','advance_angle_deg','angle_deg','substage','rk_branch','attempt_full_deg',
                'attempt_full_dt_s','rk_dt_s','F_rk_base_kg','F_previous_stage_K3_kg','F_increment_kg','F_candidate_kg','candidate_m_C_kg',
                'candidate_U_C_J','candidate_Y_C','negative_overshoot','safe_scale_kg','Bdot_kg_s','heat_active','before_rejection_count')]),
            'Los flujos siguientes se evalúan en el estado físico K3 que construye el candidato K4; '
            'no se evalúa RHS sobre el candidato negativo.',
            markdown_table(['Enlace','Área m²','Fresca firmada hacia C kg/s','Donante','p arriba Pa','p abajo Pa','Retorno'],
                [[l['index'],l['area_m2'],l['signed_fresh_into_cylinder_kg_s'],l['donor'],l['upstream_p_Pa'],l['downstream_p_Pa'],l['backflow']] for l in e['cylinder_links_at_K3']]),
            markdown_table(['Balance de etapa','Valor'],[[k,e[k]] for k in ('net_outflow_stage_increment_kg','exceeds_rk_base_inventory',
                'exceeds_K3_inventory','internal_global_fresh_rate_residual','global_fresh_rate_residual','only_F_invalid')])]
    content += ['## Interpretación offline',
        'RK4 construye K4 como y_base+dt*k3, no como y_K3+dt*k3. En ambas negativas '
        'F_base=0: K2 había aportado fresca a K3; luego K3 prescribe salida y K4 '
        'resta esa salida del inventario base cero. El incremento excede F_base, '
        'pero no F_K3. Esto identifica pérdida de positividad de una subetapa, '
        'no agotamiento físico demostrado del inventario que produjo el caudal.',
        'En la negativa terminal el escape cambia de C→E (K1, Δp=+1,19879Pa) a '
        'E→C (K2,−0,305042Pa) y vuelve a C→E (K3,+0,141702Pa). '
        'El donante de masa/entalpía/fresca es consistente con cada signo de presión. '
        'Transferencias cerradas, escape abierto, Bdot=0 y calor inactivo. '
        'La primera negativa en cambio incluye retorno C→K en las transferencias y salida C→E.',
        'Los transportes internos se suman con signos opuestos: residuo global de fresca '
        '0 en el episodio terminal;7,516e-23kg/s en el primero, redondeo flotante. '
        'No se observa pérdida global ni incoherencia de donante. m/U/T/p permanecen '
        'en dominio; la violación observada es del marcador F.',
        'negative_overshoot=abs(F_candidate)/max(abs(F_base),3e-13kg). La escala '
        '3e-13kg es atol_mass del perfil B, exclusivamente para diagnóstico. '
        'No es un floor ni permiso para aceptar valores negativos.',
        'La secuencia terminal contiene seis rechazos por error local y dos por '
        'estado no físico. Corrige la descripción abreviada anterior de “ocho '
        'rechazos no físicos”: el límite cuenta todos los motivos consecutivos.',
        markdown_table(['h intento °','Motivo','Error normalizado','Rechazo consecutivo'],
            [[r['proposed_deg'],r['cause'],r['error'],r['consecutive_rejections']] for r in d['terminal_attempts']]),
        'El rechazo7 se produce en half-1 de h=0,0206882929494°; el8 repite '
        'exactamente esa trayectoria como paso completo de h=0,0103441464747°. '
        'Esa reducción no evita la violación. La siguiente reducción algebraica '
        f"sería h={d['reduction_next_full_deg']:.12g}°, medio={d['reduction_next_half_deg']:.12g}°: "
        'aún por encima del mínimo, pero no autorizada por el límite de ocho rechazos. '
        'No se ejecutó. No puede afirmarse que evitaría la violación.',
        'El paso final potencial queda **indeterminado**: producirlo requeriría '
        'evaluar k4 en un estado prohibido, lo cual no se hizo. La evidencia sí '
        'localiza el fallo antes del estado final. No se aplicó clipping, floor, '
        'renormalización, limiter ni sustitución de integrador.',
        '**Mecanismo identificado:** positividad de etapas explícitas con F_base=0 '
        'y cambio de donante en una restricción interna no regularizada. '
        'Causa de parada adicional: presupuesto de rechazos consumido también por error local.']
    (folder/'diagnostico-2000.md').write_text('\n\n'.join(content)+'\n',encoding='utf-8')
    campaign=read('campaign.json')
    rows=[r for r in campaign['rows'] if r['rpm'] in campaign['boundary_rpms']]
    conclusion=dict(decision='LOW_RPM_FAILURE_MECHANISM_IDENTIFIED',
        lowest_observed_pass_rpm=min(r['rpm'] for r in rows if r['converged']),
        highest_observed_failure_rpm=max(r['rpm'] for r in rows if not r['converged']),
        observed_transition='monotonic in sampled terminal states; no inference between samples',
        candidate_boundary='>2000 and <=2250 rpm; refinement not performed',
        public_domain_unchanged=[2500,3500],production_changes=False,
        integration_seconds_total=sum(r['integration_seconds'] for r in campaign['rows']),
        integration_seconds_boundary=sum(r['integration_seconds'] for r in rows),
        campaign_wall_seconds=campaign['wall_seconds'],
        scientific_regression_exact_rpms=[1000,2000,3000],
        no_new_high_rpm_campaign=True,no_4t_campaign=True,no_candidate=True,
        limitations=['Potential final RK result not evaluated through invalid stage.',
                    'Next smaller step not integrated; avoidance of violation not established.',
                    'No experimental validation or general-domain proof.'])
    write_json(folder/'evidence.json',conclusion)
    text=['# Frontera baja 2T — 17/09/2026',
        '**LOW_RPM_FAILURE_MECHANISM_IDENTIFIED**. Ejemplo sintético Referencia, '
        'perfil B/100Pa, estado inicial independiente por RPM; sin warm-start ni '
        'cambios de solver. Dominio público 2500–3500 sin cambios.',
        '## Tabla de frontera',
        markdown_table(['RPM','Estado','Ciclos completos','Motivo terminal','dt mínimo aceptado °','Rechazos','W_C J','pmax Pa','Peor balance independiente %','Magnitudes'],
            [[r['rpm'],r['classification'],r['complete_cycles'],r['terminal_reason'],r['minimum_accepted_half_deg'],r['rejected_attempts'],
              r['last_complete_cycle']['W_C_J'] if r['last_complete_cycle'] else None,
              r['last_complete_cycle']['p_max_Pa'] if r['last_complete_cycle'] else None,
              r['worst_independent']*100 if r['worst_independent'] is not None else None,r['metrics_kind']] for r in rows]),
        'Magnitudes diagnostic_last_complete_cycle: no aceptadas. dt mínimo en grados '
        'es el mínimo medio paso **aceptado**, no la propuesta que provocó la parada. '
        'Sin ciclo completo se usa —; estados parciales y balances parciales quedan en los JSON.',
        markdown_table(['RPM','Integración s','Wall s','Medios pasos aceptados','dt mínimo s','Máximo rechazos consecutivos','P indicada W','T indicado N·m'],
            [[r['rpm'],r['integration_seconds'],r['wall_seconds'],r['accepted_half_steps'],r['minimum_accepted_dt_s'],r['max_consecutive_rejections'],
              r['indicated']['indicated_power_W'] if r['indicated'] else None,r['indicated']['indicated_torque_Nm'] if r['indicated'] else None] for r in rows]),
        'Wall por punto incluye preparación, integración y escritura de resultado/observación; '
        'no incluye escritura del índice campaign.json. Los tiempos incluyen observación '
        'y no constituyen un benchmark del solver sin instrumentación.',
        markdown_table(['RPM','Primera violación observada: ángulo °','Ubicación y motivo'],
            [[r['rpm'],r['first_physical_violation']['angle_deg'] if r['first_physical_violation'] else None,
              r['first_physical_violation']['error'] if r['first_physical_violation'] else None] for r in rows]),
        'Primera significa orden de intentos, no menor ángulo: un rechazo puede ocurrir '
        'en una etapa futura y reintentarse con un paso menor. Una violación rechazada '
        'no implica fallo terminal; también aparece en puntos PASS, que la recuperan.',
        '## Comparación de mecanismos',
        '- 1000: error local C.F al invertir donante en transferencias internas, F_C=0; siguiente medio paso0,000706127° bajo mínimo.\n'
        '- 1500: K4 da F_C=-1,168024e-15kg al mismo tipo de inversión K↔C; siguiente medio paso0,000747007° bajo mínimo.\n'
        '- 1750: durante calor prescrito del cilindro, el CV afectado es I; F_I excede m_I '
        'por6,776264e-21kg en el último intento (un ulp). Siguiente medio paso0,000815043° bajo mínimo. '
        'Es el límite superior F≤m, no fresca negativa en C.\n'
        '- 2000: primera negativa K4 a183°; negativa terminal K4 en ciclo6 al invertir C↔E '
        'con F_C base cero. Seis rechazos locales y dos físicos agotan el límite8.',
        '## Decisión y límites',
        'Menor RPM convergente ensayada:2250; mayor fallida:2000. Transición terminal '
        'monotónica en esta malla, mecanismos distintos. Frontera candidata >2000 y≤2250; '
        'no se han ensayado2050/2100/2150/2200 ni se infiere continuidad. 2500 sigue '
        'siendo un límite conservador razonable para este ejemplo/perfil: convergió de '
        'nuevo y deja margen respecto de2250, sin garantía para cualquier geometría.',
        'Hay base técnica para una fase correctiva separada: estudiar positividad '
        'conservativa de las etapas de transporte y el cambio de donante interno, '
        'incluyendo F=0 y F=m; distinguir error de discretización del redondeo en1750. '
        'No basta tratar todo como un único problema de mínimo de paso. Comparar estrategias '
        'solo con autorización nueva; no se recomienda clipping silencioso ni relajar límites.',
        f"Integración siete puntos={conclusion['integration_seconds_boundary']:.6f}s; "
        f"incluyendo1000={conclusion['integration_seconds_total']:.6f}s. Wall campaña={campaign['wall_seconds']:.6f}s. "
        'Los diagnósticos offline se ejecutaron después y no se suman como integración nueva.',
        '1000/2000/3000 reproducen exactamente los campos científicos completos de faseA, '
        'incluidas trayectorias, muestras, RHS, rechazos y paradas; solo difieren tiempos. '
        '3000 reproduce por transitividad y prueba histórica los resultados acreditados. '
        'No hay campaña alta/4T, UI, formatos, candidata ni aceptación manual nuevos.',
        'Detalles: [1000](diagnostico-1000.md), [2000](diagnostico-2000.md), '
        'JSON de observación, replay y resultados originales junto a este archivo.']
    (folder/'frontera.md').write_text('\n\n'.join(text)+'\n',encoding='utf-8')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    evidence=parser.parse_args().evidence
    analyze(evidence)
    reports(evidence)
