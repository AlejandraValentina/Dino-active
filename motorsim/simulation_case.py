"""S2T-0D-01: definición sintética, separada del formato de proyectos."""
from dataclasses import asdict, dataclass, field

from .project import Project, Port, Intake, Ducts, DuctSegment


def geometry():
    return Project(
        name='S2T-0D-01 — CASO SINTÉTICO, NO MEDIDO', cycle='2T',
        cylinder_count=1, bore_mm=54, stroke_mm=56, rod_length_mm=100,
        compression_ratio=8, crankcase_volume_bdc_cm3=250,
        ports=(Port('Escape', 'escape', 32, 10, 20),
               Port('Transferencia 1', 'transfer', 44, 10, 12),
               Port('Transferencia 2', 'transfer', 44, 10, 12)),
        intake=Intake('piston_port', 64, 10, 20, 42),
        ducts=Ducts((DuctSegment('Tubo I', 100, 20, 20),),
                    (DuctSegment('Tubo E', 100, 20, 20),
                     DuctSegment('Cono E', 100, 20, 40))))


@dataclass(frozen=True)
class SyntheticCase:
    identifier: str = 'S2T-0D-01'
    model: str = 'four-cv-0d-prescribed-heat-v1'
    project_geometry: Project = field(default_factory=geometry)
    rpm: float = 3000
    gas_r: float = 287
    gamma: float = 1.35
    # Orden de CV: I, K, C, E. Tuplas p [Pa absolutos], T [K], Y [-].
    initial_pty: tuple = ((100000, 300, 1), (120000, 330, 1),
                          (140000, 700, 0), (100000, 500, 0))
    reservoirs_pty: tuple = ((100000, 300, 1), (100000, 500, 0))
    # Enlaces: exterior-I, I-K, K-C1, K-C2, C-E, E-exterior.
    discharge_coefficients: tuple = (.8, .7, .65, .65, .7, .8)
    initial_angle_deg: float = 180
    heat_start_deg: float = 350
    heat_duration_deg: float = 40
    fresh_energy_j_kg: float = 800000

    def manifest(self):
        data = asdict(self)
        data['project_geometry'].pop('four_stroke')
        return {**data, 'synthetic_not_experimental': True,
                'units': 'SI en estados; geometría mm y cm3 según nombres',
                'cv_order': ['I', 'K', 'C', 'E'],
                'link_order': ['exterior-I', 'I-K', 'K-C1', 'K-C2', 'C-E', 'E-exterior'],
                'assumptions': ['mezcla homogénea', 'gas caloríficamente perfecto',
                    'paredes adiabáticas', 'sin pérdidas mecánicas',
                    'sin inercia, ondas ni sintonía', 'transferencias sin almacenamiento',
                    'energía y conversión de marcador prescritas, no química']}
