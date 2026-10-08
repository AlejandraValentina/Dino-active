"""Comparación de resultados ya validados y CSV; sin integración ni Qt."""
import csv
from pathlib import Path

from .project import NUMERIC_FIELDS, VALVE_FIELDS, PORT_FIELDS, INTAKE_FIELDS, DUCT_FIELDS
from .reference_results import validated_model
from .performance import result_metrics


class ComparisonError(ValueError):
    pass


CONDITIONS = {
    'model': 'Modelo físico', 'rpm': 'Régimen', 'gas_r': 'Constante del gas',
    'gamma': 'Relación de calores específicos', 'reservoirs_pty': 'Contornos p/T/Y',
    'initial_pty': 'Receta inicial p/T/Y', 'discharge_coefficients': 'Coeficientes de descarga',
    'heat_start_deg': 'Inicio del aporte', 'heat_duration_deg': 'Duración del aporte',
    'fresh_energy_j_kg': 'Energía prescrita por carga fresca', 'initial_angle_deg': 'Referencia angular inicial',
    'cv_order': 'Volúmenes del modelo', 'link_order': 'Topología de enlaces', 'assumptions': 'Hipótesis físicas',
}
STATES = dict(converged='Convergido', cancelled='Cancelado', not_converged='No convergido', error='Error')


def compatibility_errors(a, b):
    errors = []
    for label, result in (('A', a), ('B', b)):
        if result.get('status') != 'converged':
            errors.append(f'{label}: {STATES.get(result.get("status"), "estado desconocido")}; no es una configuración evaluada correctamente.')
        cycles = result.get('result', {}).get('cycles', [])
        if not cycles or not all(c.get('balances_passed') is True for c in cycles[-3:]):
            errors.append(f'{label}: faltan balances finales aprobados.')
    for key, label in (('model_version', 'Versión del modelo'), ('variant', 'Variante de regularización'), ('profile', 'Perfil numérico')):
        for side, result in (('A', a), ('B', b)):
            if key not in result['inputs']:
                errors.append(f'{side}: falta {label}; no puede acreditarse compatibilidad.')
        if key in a['inputs'] and key in b['inputs'] and a['inputs'][key] != b['inputs'][key]:
            errors.append(f'{label}: las configuraciones difieren.')
    for key, label in CONDITIONS.items():
        left, right = a['inputs'].get('case', {}), b['inputs'].get('case', {})
        if key not in left or key not in right:
            errors.append(f'Falta {label}; no puede acreditarse compatibilidad.')
        elif left[key] != right[key]:
            errors.append(f'{label}: A={left[key]}, B={right[key]}.')
    # Configuración física admitida, separada de dimensiones e inventarios derivados.
    for key in ('cycle', 'cylinder_count'):
        left = a['inputs'].get('case', {}).get('project_geometry', {})
        right = b['inputs'].get('case', {}).get('project_geometry', {})
        if key not in left or key not in right:
            errors.append(f'Falta configuración física: {key}.')
        elif left[key] != right[key]:
            errors.append(f'Configuración física: {key} difiere.')
    return errors


def geometry_fields(result):
    """Interpretación canónica del contrato existente, sin otro lector."""
    model, _ = validated_model(result['inputs'])
    project = model.case.project_geometry
    physical, descriptive = {}, {}
    def field(section, title, unit, value):
        physical[(section, title, unit)] = value
    for key, title in NUMERIC_FIELDS.items():
        field('Ficha', title, 'cil.' if key == 'cylinder_count' else (':1' if key == 'compression_ratio' else 'mm'), getattr(project,key))
    if project.cycle=='4T':
        for role,title in (('intake','Válvula admisión'),('exhaust','Válvula escape')):
            for key,caption in VALVE_FIELDS.items():
                field(title,caption,'°' if key.endswith('_deg') else 'mm',getattr(getattr(project.four_stroke,role),key))
    else:
        field('Cárter', 'Volumen libre en PMI', 'cm³', project.crankcase_volume_bdc_cm3)
        field('Admisión', 'Modalidad', '', project.intake.mode)
        field('Admisión', 'Referencia', '', project.intake.reference)
        for key, title in INTAKE_FIELDS.items():field('Admisión',title,'mm',getattr(project.intake,key))
        # El adaptador ya asigna escape/transferencias por función, no por fila/nombre.
        # Desempate nominal solo para descripciones de transferencias geométricamente idénticas.
        ports = sorted(project.ports, key=lambda p:(p.function,p.top_mm,p.height_mm,p.width_mm,p.name))
        counts = {}
        for port in ports:
            counts[port.function] = counts.get(port.function,0)+1
            section = f'{"Escape" if port.function == "escape" else "Transferencia"} {counts[port.function]}'
            for key,title in PORT_FIELDS.items():field(section,title,'mm',getattr(port,key))
            descriptive[(section,'Nombre','')] = port.name
    for route,title in (('intake','Conducto admisión'),('exhaust','Conducto escape')):
        for index,segment in enumerate(getattr(project.four_stroke.ducts if project.cycle=='4T' else project.ducts,route),1):
            section=f'{title} · tramo {index}'
            for key,caption in DUCT_FIELDS.items():field(section,caption,'mm',getattr(segment,key))
            descriptive[(section,'Nombre','')]=segment.name
    for key,title in (('name','Proyecto'),('manufacturer','Fabricante'),('model','Modelo'),('notes','Observaciones')):
        descriptive[('Descripción',title,'')]=getattr(project,key)
    return physical,descriptive


def input_differences(a,b):
    fields_a,fields_b=geometry_fields(a),geometry_fields(b)
    groups=[]
    for left,right in zip(fields_a,fields_b):
        groups.append([dict(section=key[0],field=key[1],unit=key[2],a=left.get(key),b=right.get(key))
            for key in dict.fromkeys((*left,*right)) if left.get(key)!=right.get(key)])
    return dict(geometry=groups[0],descriptive=groups[1])


def aligned_curve(result):
    cycle=result['result']['cycles'][-1]['cycle']
    four=result['inputs']['case']['project_geometry']['cycle']=='4T'
    period,ci=(720,1) if four else (360,2)
    return [dict(angle_cycle_deg=row['angle_deg']-period*(cycle-1),angle_original_deg=row['angle_deg'],
                 pressure_absolute_Pa=row['p_T_Y'][ci][0],volume_m3=row['V_m3'][ci])
            for row in result['samples']['cycles'][-1]]


def compare_results(a,b):
    """Los llamadores cargan cada selección con reference_results.load_result."""
    errors=compatibility_errors(a,b)
    if errors:raise ComparisonError('\n'.join(errors))
    differences=input_differences(a,b)
    left,right=(r['result']['cycles'][-1] for r in (a,b))
    metrics=[]
    four=a['inputs']['case']['project_geometry']['cycle']=='4T'
    for key,title,unit in (('W_C_J','Trabajo indicado del cilindro','J/ciclo'),
                            ('W_K_J','Trabajo del cárter (separado)','J/ciclo'),
                            ('p_max_Pa','Presión máxima del cilindro','Pa abs.')):
        if key=='W_K_J' and a['inputs']['case']['project_geometry']['cycle']=='4T':continue
        if four and key=='W_C_J':unit='J/720°'
        av,bv=left[key],right[key]
        metrics.append(dict(magnitude=key,title=title,unit=unit,a=av,b=bv,difference=bv-av,
                            relative_percent=100*(bv-av)/abs(av) if av!=0 else None))
    for i,cv in enumerate(('I','C','E') if a['inputs']['case']['project_geometry']['cycle']=='4T' else ('I','K','C','E')):
        av,bv=left['Y'][i],right['Y'][i]
        metrics.append(dict(magnitude='Y_'+cv,title='Fracción fresca '+cv,unit='1',a=av,b=bv,
                            difference=bv-av,relative_percent=None))
    derived_a,derived_b=result_metrics(a),result_metrics(b)
    for key,title,unit in (('indicated_power_W','Potencia indicada','W'),
                           ('indicated_torque_Nm','Par indicado equivalente','N·m')):
        av,bv=derived_a[key],derived_b[key]
        metrics.append(dict(magnitude=key,title=title,unit=unit,a=av,b=bv,difference=bv-av,
                            relative_percent=100*(bv-av)/abs(av) if av!=0 else None))
    return dict(metrics=metrics,differences=differences,curves=[aligned_curve(a),aligned_curve(b)],
                run_ids=[r['manifest']['run_id'] for r in (a,b)])


def export_csv(folder, comparison):
    summary=[['magnitude','unit','run_id_A','run_id_B','value_A','value_B',
              'difference_B_minus_A','relative_difference_percent']]
    summary.extend([r['magnitude'],r['unit'],*comparison['run_ids'],r['a'],r['b'],
                    r['difference'],r['relative_percent']] for r in comparison['metrics'])
    columns=['angle_cycle_deg','angle_original_deg','pressure_absolute_Pa','volume_m3']
    curves=[['configuration','run_id','sample_index',*columns]]
    for label,run_id,rows in zip(('A','B'),comparison['run_ids'],comparison['curves']):
        curves.extend([label,run_id,i,*[row[k] for k in columns]] for i,row in enumerate(rows))
    return write_csv_files(folder, [('resumen.csv',summary),('curvas.csv',curves)])


def write_csv_files(folder, files):
    """Carpeta exclusiva. Ante error retirar solo lo creado, nunca las fuentes."""
    folder=Path(folder)
    created=[]
    owned=False
    try:
        folder.mkdir(exist_ok=False)
        owned=True
        for name, rows in files:
            path=folder/name
            with path.open('x',encoding='utf-8',newline='') as stream:
                created.append(path)
                csv.writer(stream).writerows(rows)
    except (OSError,ValueError,csv.Error) as exc:
        cleanup=[]
        for path in created:
            try:path.unlink()
            except OSError as error:cleanup.append(str(error))
        if owned:
            try:folder.rmdir()
            except OSError as error:cleanup.append(str(error))
        detail=(' Quedaron archivos incompletos en '+str(folder)+': '+'; '.join(cleanup)) if cleanup else ''
        raise ComparisonError(f'No se exportó la comparación: {exc}.{detail}') from exc
    return tuple(created)
