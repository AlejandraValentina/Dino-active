"""S4T-0D-01: tres volúmenes reales, distribución prescrita, sin Qt."""
from dataclasses import asdict, dataclass, field, replace
import hashlib
import json
import math
from .project import FOUR_DUCT_REFERENCE, Project, FourStroke, Valve, Ducts, DuctSegment
from .simulation import Model, FOUR_LAYOUT
from .ducts import route_geometry
from .kinematics import piston_position
from .valves import area, errors, closed_during_heat


def geometry():
    return Project(name='S4T-0D-01 — EJEMPLO SINTÉTICO, NO MEDIDO', cycle='4T',
        cylinder_count=1, bore_mm=54, stroke_mm=56, rod_length_mm=100, compression_ratio=8,
        four_stroke=FourStroke(Valve(24,20,5,5,0,220), Valve(20,18,5,5,500,220),
            Ducts((DuctSegment('Tubo I',100,20,20),),
                  (DuctSegment('Tubo E',100,20,20), DuctSegment('Cono E',100,20,40)), reference=FOUR_DUCT_REFERENCE)))


@dataclass(frozen=True)
class FourStrokeCase:
    identifier: str = 'S4T-0D-01'
    model: str = 'three-cv-0d-prescribed-heat-720-v1'
    project_geometry: Project = field(default_factory=geometry)
    rpm: float = 3000
    gas_r: float = 287
    gamma: float = 1.35
    initial_pty: tuple = ((100000,300,1), (100000,500,0), (100000,500,0))
    reservoirs_pty: tuple = ((100000,300,1), (100000,500,0))
    discharge_coefficients: tuple = (.8,.7,.7,.8)
    initial_angle_deg: float = 0
    heat_start_deg: float = 350
    heat_duration_deg: float = 40
    fresh_energy_j_kg: float = 800000

    def manifest(self):
        return {**asdict(self), 'synthetic_not_experimental': True, 'cycle': '4T',
                'period_deg': 720, 'cv_order': ['I','C','E'],
                'link_order': ['exterior-I','I-C','C-E','E-exterior'],
                'units': 'SI en estados; geometría mm y cm3 según nombres',
                'assumptions': ['mezcla homogénea', 'gas caloríficamente perfecto',
                    'paredes adiabáticas', 'sin pérdidas mecánicas',
                    'sin inercia, ondas ni sintonía', 'alzada seno cuadrado idealizada',
                    'cortina cilíndrica limitada por garganta anular, no medida',
                    'energía y conversión de marcador prescritas, no química']}


def execution_errors(project):
    messages = []
    try: project.validate()
    except ValueError as exc: return [str(exc)]
    if project.cycle != '4T' or project.cylinder_count != 1:
        messages.append('El modelo 4T requiere un cilindro.')
    for key in ('bore_mm','stroke_mm','rod_length_mm','compression_ratio'):
        if getattr(project,key) is None: messages.append('Falta '+key)
    if project.rod_length_mm is not None and project.stroke_mm is not None:
        if project.rod_length_mm <= project.stroke_mm/2: messages.append('Biela incompatible.')
    for name in ('intake','exhaust'):
        valve = getattr(project.four_stroke,name)
        issues = errors(valve); messages += [name+': '+v for v in issues]
        if not issues and not closed_during_heat(valve):
            messages.append(name+': cilindro abierto durante aporte 350–390°.')
        result = route_geometry(getattr(project.four_stroke.ducts,name))
        if result.errors or not result.segments or not all(result.joints):
            messages.append(name+': requiere conducto completo y continuo.')
    return messages


class FourStrokeModel(Model):
    layout = FOUR_LAYOUT

    def __init__(self, case=None, *, external_band_pa=100):
        if external_band_pa not in (50,100): raise ValueError('Banda 50/100 Pa requerida.')
        self.case = case or FourStrokeCase(); self.external_band_pa = external_band_pa
        p = self.case.project_geometry
        issues = execution_errors(p)
        if issues: raise ValueError('\n'.join(issues))
        self.rate = 6*self.case.rpm; self.cv = self.case.gas_r/(self.case.gamma-1)
        self.ap = math.pi*(p.bore_mm*.001)**2/4
        self.clearance = self.ap*p.stroke_mm*.001/(p.compression_ratio-1)
        self.duct_volumes, self.throats = [], []
        for route in (p.four_stroke.ducts.intake,p.four_stroke.ducts.exhaust):
            g = route_geometry(route)
            self.duct_volumes.append(float(g.volume)*1e-6)
            self.throats.append(float(min(min(s.start_area,s.end_area) for s in g.segments))*1e-6)
        phases = {0.,180.,350.,360.,390.,540.}
        for valve in (p.four_stroke.intake,p.four_stroke.exhaust):
            phases.update((valve.opening_deg,(valve.opening_deg+valve.duration_deg)%720,
                           (valve.opening_deg+valve.duration_deg/2)%720))
        self.events = sorted(phases)

    def geometry(self, angle):
        p = self.case.project_geometry
        x = piston_position(p.stroke_mm,p.rod_length_mm,angle)
        theta = math.radians(angle%360); r, rod = p.stroke_mm*.0005,p.rod_length_mm*.001
        sine, cosine = math.sin(theta),math.cos(theta)
        dx = r*sine+r*r*sine*cosine/math.sqrt(rod*rod-r*r*sine*sine)
        dv = self.ap*dx*self.rate*math.pi/180
        return ((self.duct_volumes[0],self.clearance+self.ap*x*.001,self.duct_volumes[1]),
                (0.,dv,0.), (self.throats[0],area(p.four_stroke.intake,angle)*1e-6,
                            area(p.four_stroke.exhaust,angle)*1e-6,self.throats[1]))


SCENARIO_4T = 'S4T-0D-reference-recipe-variable-rpm-v1'

class FourStrokeProjectCase(FourStrokeCase):
    def manifest(self):
        data=super().manifest();data.pop('synthetic_not_experimental')
        return dict(data,reference_conditions=True,scenario_identifier=SCENARIO_4T,
                    geometry_provenance='not specified')


def build_project_case(project, rpm=3000):
    from .project import Intake, ProjectError
    from .project_case import validate_rpm
    validate_rpm(rpm, '4T')
    issues=execution_errors(project)
    if issues:raise ProjectError('\n'.join(issues))
    canonical=replace(project,ports=(),intake=Intake(),ducts=Ducts(),crankcase_volume_bdc_cm3=None)
    data=canonical.to_dict()
    for key in ('name','manufacturer','model','notes'):data.pop(key)
    for route in ('intake','exhaust'):
        for piece in data['four_stroke']['ducts'][route]:piece.pop('name')
    identity=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:16]
    case=FourStrokeProjectCase(identifier='PROJECT-4T-'+identity,project_geometry=canonical,rpm=rpm)
    try:
        model=FourStrokeModel(case);model.evaluate(0,model.initial_state())
    except (ValueError,ArithmeticError,RuntimeError) as exc:
        raise ProjectError('Geometría 4T fuera del dominio numérico: '+str(exc)) from exc
    return case,[dict(link_index=i,role=role,dimensions=asdict(getattr(canonical.four_stroke,role)))
                 for i,role in ((1,'intake'),(2,'exhaust'))]
