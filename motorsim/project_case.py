"""Adaptación acotada de geometría v5 al escenario de referencia, sin ecuaciones nuevas."""
from dataclasses import asdict, replace
import hashlib
import json
import math

from .project import Project, ProjectError, NUMERIC_FIELDS, PORT_FIELDS, INTAKE_FIELDS, DUCT_FIELDS, validate_number
from .ports import port_results
from .intake import intake_results
from .ducts import route_geometry
from .kinematics import piston_position
from .simulation import Model
from .simulation_case import SyntheticCase
from .rpm_domain import validate_rpm

SCENARIO_ID = 'S2T-0D-01-reference-conditions-v1'
RPM_SCENARIO_ID = 'S2T-0D-reference-recipe-variable-rpm-v1'


class ProjectCase(SyntheticCase):
    def manifest(self):
        data = super().manifest()
        data.pop('synthetic_not_experimental')
        data.update(scenario_identifier=SCENARIO_ID, reference_conditions=True,
                    geometry_provenance='not specified')
        return data


class RpmProjectCase(ProjectCase):
    def manifest(self):
        return {**super().manifest(), 'scenario_identifier': RPM_SCENARIO_ID}


def execution_errors(project):
    if project.cycle=='4T':
        from .four_stroke import execution_errors as four_errors
        return four_errors(project)
    errors = []
    try:
        project.validate()
    except ProjectError as exc:
        errors.append(str(exc))
    if project.cycle != '2T':
        errors.append('Tipo de motor: este modelo requiere 2T.')
    if type(project.cylinder_count) is not int or project.cylinder_count != 1:
        errors.append('Número de cilindros: se requiere exactamente uno.')
    for key, label in {**NUMERIC_FIELDS, 'crankcase_volume_bdc_cm3': 'Volumen libre del cárter en PMI'}.items():
        if getattr(project, key) is None:
            errors.append(f'Falta: {label}.')
        else:
            try:
                validate_number(getattr(project, key), key)
            except ProjectError as exc:
                errors.append(str(exc))
    mechanism_ok = project.stroke_mm is not None and project.rod_length_mm is not None
    if mechanism_ok:
        try:
            piston_position(project.stroke_mm, project.rod_length_mm, 90)
        except (ValueError, OverflowError) as exc:
            errors.append(f'Carrera / biela: {exc}')
            mechanism_ok = False
    if project.intake.mode != 'piston_port':
        errors.append('Admisión: configurar control por falda.')
    for key, label in INTAKE_FIELDS.items():
        if getattr(project.intake, key) is None:
            errors.append(f'Admisión: falta {label}.')
    if mechanism_ok:
        intake = intake_results(project.intake, project.stroke_mm, project.rod_length_mm)
        for message in (intake.event_error, intake.area_error):
            if message:
                errors.append('Admisión: '+message)
        if intake.never_opens:
            errors.append('Admisión: no tiene apertura efectiva.')
    functions = [p.function for p in project.ports]
    if len(functions) != 3 or functions.count('escape') != 1 or functions.count('transfer') != 2:
        errors.append('Lumbreras: se requiere exactamente una de Escape y dos de Transferencia, sin filas extra.')
    scenario = SyntheticCase()
    start, end = scenario.heat_start_deg, scenario.heat_start_deg+scenario.heat_duration_deg
    for index, port in enumerate(project.ports, 1):
        label = f'Lumbrera {index} ({port.name or "sin nombre"})'
        if port.function not in ('escape', 'transfer'):
            errors.append(f'{label}: falta función Escape o Transferencia.')
        for key, title in PORT_FIELDS.items():
            if getattr(port, key) is None:
                errors.append(f'{label}: falta {title}.')
        if mechanism_ok:
            result = port_results(port, project.stroke_mm, project.rod_length_mm)
            for message in (result.event_error, result.area_error):
                if message:
                    errors.append(f'{label}: {message}')
            if result.never_opens or result.maximum == 0:
                errors.append(f'{label}: no tiene apertura efectiva.')
            if result.opening is not None and result.closing is not None:
                # Intersección de intervalos abiertos entre eventos, incluido 360°.
                # En el evento mismo el área es cero; no decidir desde una gráfica.
                for turn in range(math.floor(start/360)-1, math.floor(end/360)+1):
                    if max(start, result.opening+360*turn) < min(end, result.closing+360*turn):
                        errors.append(f'{label}: cilindro abierto durante el aporte de {start:g} a {end:g}°.')
                        break
    for label, segments in (('Conducto de admisión', project.ducts.intake), ('Conducto de escape', project.ducts.exhaust)):
        if not segments:
            errors.append(label+': falta al menos un tramo.')
        for index, segment in enumerate(segments, 1):
            for key, title in DUCT_FIELDS.items():
                if getattr(segment, key) is None:
                    errors.append(f'{label}, tramo {index}: falta {title}.')
        geometry = route_geometry(segments)
        errors.extend(f'{label}: {m}' for m in geometry.errors.values())
        if any(j is False for j in geometry.joints):
            errors.append(label+': los diámetros de las uniones no son continuos.')
    return list(dict.fromkeys(errors))


def canonical_ports(project):
    # Nombres/posición visual no eligen función ni orden de enlaces.
    escape = [(i, p) for i, p in enumerate(project.ports) if p.function == 'escape']
    transfers = sorted(((i, p) for i, p in enumerate(project.ports) if p.function == 'transfer'),
                       key=lambda item: (item[1].top_mm, item[1].height_mm, item[1].width_mm))
    return escape+transfers


def build_project_case(project, *, rpm=None):
    if project.cycle=='4T':
        from .four_stroke import build_project_case as build_four
        return build_four(project,3000 if rpm is None else rpm)
    if rpm is not None:
        validate_rpm(rpm, project.cycle)
    errors = execution_errors(project)
    if errors:
        raise ProjectError('\n'.join(errors))
    ordered = canonical_ports(project)
    canonical = replace(project, ports=tuple(p for _, p in ordered))
    physics = canonical.to_dict()
    physics.pop('four_stroke')
    physics['format_version'] = 5
    for key in ('name', 'manufacturer', 'model', 'notes'):
        physics.pop(key)
    for port in physics['ports']:
        port.pop('name')
    for route in ('intake', 'exhaust'):
        for segment in physics['ducts'][route]:
            segment.pop('name')
    identity = hashlib.sha256(json.dumps(physics, sort_keys=True).encode()).hexdigest()[:16]
    case = (ProjectCase(identifier='PROJECT-0D-'+identity, project_geometry=canonical) if rpm is None else
            RpmProjectCase(identifier='PROJECT-0D-'+identity, project_geometry=canonical, rpm=rpm))
    mapping = [dict(link_index=link, model_port_index=index, source_row=row+1,
                    function=p.function, name=p.name, dimensions={k:getattr(p,k) for k in PORT_FIELDS})
               for index, ((row,p),link) in enumerate(zip(ordered, (4,2,3)))]
    try:
        model = Model(case, external_band_pa=100)
        # También comprobar representación numérica de volúmenes/inventarios, sin integrar.
        model.evaluate(case.initial_angle_deg, model.initial_state())
    except (ValueError, ArithmeticError, RuntimeError) as exc:
        raise ProjectError(f'Geometría fuera del dominio numérico del modelo: {exc}') from exc
    return case, mapping


def configuration_key(project):
    """Comparación independiente del orden visual, incluyendo identificación capturada."""
    data = project.to_dict()
    if project.cycle=='4T':
        for key in ('ports','intake','ducts','crankcase_volume_bdc_cm3'):data.pop(key)
        return json.dumps(data,sort_keys=True)
    data.pop('four_stroke')
    data['ports'] = sorted(data['ports'], key=lambda p: json.dumps(p, sort_keys=True))
    return json.dumps(data, sort_keys=True)
