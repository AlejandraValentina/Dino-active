"""Interfaz neutral, de solo lectura; sin proveedores ni modelos externos."""
from ..contracts import validate_named


def not_run():
    return dict(status='NOT_RUN',findings=[],blocking_findings=[],scientific_change_required=False,
                notes='Revisión no ejecutada.',kind='none')


def run_review(*, phase, diff, evidence, required_checks):
    # Stub solo valida el cableado de dummy. No acredita revisión independiente científica.
    if phase['phase']!='dummy':
        return dict(status='BLOCKED',findings=['No hay reviewer independiente conectado.'],
            blocking_findings=['reviewer_unavailable'],scientific_change_required=False,
            notes='No se llamó a ningún proveedor externo.',kind='none')
    findings=['scope_violation'] if evidence['scope_violations'] else []
    result=dict(status='BLOCKED' if findings else 'PASS',findings=findings,blocking_findings=findings,
        scientific_change_required=False,kind='dummy_stub',
        notes='Stub local de infraestructura; NO es revisión independiente de MotorSim ni revisión científica.')
    validate_named(result,'review')
    return result
