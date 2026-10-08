"""Validación del subconjunto cerrado de JSON Schema usado por estos contratos.

No es un validador JSON Schema general. Rechaza keywords desconocidas en lugar
de ignorarlas. Los schemas publicados también sirven para validadores externos.
"""
import json
import math
from pathlib import Path, PurePosixPath
import re

TERMINAL_STATES = ('PASS', 'BLOCKED', 'SCIENTIFIC_CHANGE_REQUIRED', 'FAILED_INFRASTRUCTURE')
BASE = Path(__file__).resolve().parent


class ContractError(ValueError):
    pass


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ContractError('Clave duplicada: '+key)
            result[key] = value
        return result
    def constant(value): raise ContractError('Número JSON no finito: '+value)
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream, object_pairs_hook=pairs, parse_constant=constant)


def validate(value, schema, path='$'):
    supported = {'$schema', '$id', 'title', 'description', 'type', 'enum', 'properties',
        'required', 'additionalProperties', 'items', 'minItems', 'maxItems', 'uniqueItems',
        'minimum', 'maximum', 'minLength', 'pattern'}
    if set(schema)-supported: raise ContractError('Keyword no soportada: '+str(set(schema)-supported))
    types = dict(object=lambda v:isinstance(v,dict), array=lambda v:isinstance(v,list),
        string=lambda v:isinstance(v,str), boolean=lambda v:type(v) is bool,
        integer=lambda v:type(v) is int,
        number=lambda v:type(v) in (int,float) and math.isfinite(v), null=lambda v:v is None)
    expected = schema.get('type')
    if expected:
        alternatives = expected if isinstance(expected,list) else [expected]
        if not any(types[t](value) for t in alternatives): raise ContractError(f'{path}: tipo {expected} requerido')
    if 'enum' in schema and value not in schema['enum']: raise ContractError(f'{path}: valor no admitido')
    if isinstance(value,dict):
        missing = set(schema.get('required',[]))-value.keys()
        if missing: raise ContractError(f'{path}: faltan {sorted(missing)}')
        properties = schema.get('properties',{})
        for key,item in value.items():
            if key in properties: validate(item,properties[key],path+'.'+key)
            elif schema.get('additionalProperties') is False: raise ContractError(f'{path}: campo desconocido {key}')
            elif isinstance(schema.get('additionalProperties'),dict): validate(item,schema['additionalProperties'],path+'.'+key)
    if isinstance(value,list):
        if not schema.get('minItems',0)<=len(value)<=schema.get('maxItems',float('inf')): raise ContractError(path+': longitud inválida')
        if schema.get('uniqueItems') and len({json.dumps(x,sort_keys=True) for x in value})!=len(value): raise ContractError(path+': elementos duplicados')
        for index,item in enumerate(value): validate(item,schema.get('items',{}),f'{path}[{index}]')
    if isinstance(value,str):
        if len(value)<schema.get('minLength',0): raise ContractError(path+': cadena vacía')
        if 'pattern' in schema and re.search(schema['pattern'],value) is None: raise ContractError(path+': patrón inválido')
    if type(value) in (int,float):
        if not math.isfinite(value) or not schema.get('minimum',-math.inf)<=value<=schema.get('maximum',math.inf): raise ContractError(path+': número fuera de rango')
    return value


def validate_named(value, name):
    return validate(value,read_json(BASE/'schemas'/f'{name}.schema.json'))


def relative_path(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value:
        raise ContractError('Ruta relativa POSIX requerida: '+str(value))
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or value.startswith('./') or '*' in value:
        raise ContractError('Ruta fuera del contrato: '+value)
    if str(path)=='.': raise ContractError('No se permite la raíz como alcance')
    return value


def inside(root, value):
    relative_path(value)
    root = Path(root).resolve()
    target = (root/value).resolve()
    if not target.is_relative_to(root): raise ContractError('Ruta resuelta fuera de raíz: '+value)
    return target


def load_phase(root, phase_id, config):
    if re.fullmatch(r'[A-Za-z0-9_-]+',phase_id) is None: raise ContractError('Identificador de fase inválido')
    roadmap = validate_named(read_json(root/'dev_orchestrator/roadmap/gasdynamic.json'),'roadmap')
    entries = roadmap['phases']
    if len({p['id'] for p in entries}) != len(entries): raise ContractError('Fase duplicada en roadmap')
    entry = next((p for p in entries if p['id']==phase_id),None)
    if entry is None: raise ContractError('Fase ausente del roadmap: '+phase_id)
    phase = read_json(root/'dev_orchestrator/phases'/f'{phase_id}.json')
    phase.setdefault('max_repair_attempts',config['default_max_repair_attempts'])
    phase.setdefault('timeout',config['default_phase_timeout'])
    validate_named(phase,'phase')
    for a,b in (('id','phase'),('depends_on','depends_on'),('allowed_paths','allowed_paths'),
                ('forbidden_paths','forbidden_paths'),('max_repair_attempts','max_repair_attempts'),
                ('requires_human_approval','human_gate'),('gate_policy','gate')):
        if entry[a]!=phase[b]: raise ContractError('Roadmap/fase contradictorios: '+a)
    if entry['required_checks']!=phase['required_checks']: raise ContractError('Checks de roadmap contradictorios')
    if phase['phase']!=phase_id: raise ContractError('Identidad de fase contradictoria')
    ids=[c['id'] for c in phase['commands']]
    if len(set(ids))!=len(ids): raise ContractError('Comando duplicado')
    if not set(phase['required_tests']) <= {c['id'] for c in phase['commands'] if c['kind']=='test'}:
        raise ContractError('Test requerido sin comando')
    for value in phase['allowed_paths']+phase['forbidden_paths']+phase['required_evidence']:
        relative_path(value)
    for command in phase['commands']:
        if command.get('result_file'): relative_path(command['result_file'])
    return roadmap,phase
