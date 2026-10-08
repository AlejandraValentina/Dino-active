"""Dominios públicos por ciclo; la campaña candidata no habilita la interfaz."""
from .project import ProjectError

PUBLIC_DOMAINS = {'2T': (2500, 15000), '4T': (2500, 3500)}
CANDIDATE_2T_DOMAIN = (1000, 15000)


def validate_rpm(rpm, cycle='2T'):
    if cycle not in PUBLIC_DOMAINS:
        raise ProjectError('Ciclo de motor inválido.')
    low, high = PUBLIC_DOMAINS[cycle]
    if type(rpm) is not int or not low <= rpm <= high:
        raise ProjectError(f'Régimen {cycle}: debe ser un entero entre {low} y {high} rpm.')
    return rpm


def validate_candidate_2t_rpm(rpm):
    """Solo campaña de dominio; no usar para solicitudes de la aplicación."""
    low, high = CANDIDATE_2T_DOMAIN
    if type(rpm) is not int or not low <= rpm <= high:
        raise ProjectError(f'Campaña candidata 2T: entero entre {low} y {high} rpm requerido.')
    return rpm
