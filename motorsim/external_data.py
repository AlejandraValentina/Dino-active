"""CSV declarativo por RPM y contraste descriptivo. Sin Qt ni cálculo del motor."""
import csv
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import io
import json
import math
from pathlib import Path
import re
import uuid

from .comparison import write_csv_files
from .prototype import write_json

PROVENANCES = ('No determinada', 'Medición declarada', 'Simulación externa', 'Ejemplo sintético')
WORK = 'Trabajo indicado del cilindro'
PRESSURE = 'Presión máxima absoluta del cilindro'
DEFINITIONS = {
    'W_C_J': 'Un cilindro 2T; integral p dV de la vuelta completa de 360°, incluido intercambio de gases; sin descontar trabajo del cárter ni pérdidas mecánicas.',
    'p_max_Pa': 'Presión máxima absoluta del cilindro; no presión manométrica ni potencia máxima.',
}
TITLES = {'W_C_J': WORK, 'p_max_Pa': PRESSURE}
CANONICAL = {'W_C_J': 'J/ciclo', 'p_max_Pa': 'Pa abs.'}
DEFINITIONS.update(W_C_4T_J='Un cilindro 4T; integral p dV del ciclo completo de 720°, incluido intercambio de gases; sin pérdidas mecánicas.',
    p_max_2T_Pa=DEFINITIONS['p_max_Pa']+' Ciclo 2T de 360° declarado.',
    p_max_4T_Pa=DEFINITIONS['p_max_Pa']+' Ciclo 4T de 720° declarado.')
TITLES.update(W_C_J=WORK+' · 2T / 360°',W_C_4T_J=WORK+' · 4T / 720°',
              p_max_2T_Pa=PRESSURE+' · 2T',p_max_4T_Pa=PRESSURE+' · 4T')
CANONICAL.update(W_C_4T_J='J/ciclo',p_max_2T_Pa='Pa abs.',p_max_4T_Pa='Pa abs.')
CYCLES={'W_C_J':'2T','W_C_4T_J':'4T','p_max_2T_Pa':'2T','p_max_4T_Pa':'4T','p_max_Pa':None}
SIM_KEYS={k:('W_C_J' if k.startswith('W_C') else 'p_max_Pa') for k in DEFINITIONS}
TEXT_FIELDS = ('name', 'source', 'engine', 'configuration', 'conditions', 'notes')
RULES = dict(encoding='UTF-8, BOM optional', delimiter=',', decimal='.', columns=['rpm','value'],
             rpm_matching='exact; no interpolation', bar_to_pa=100000)
LIMIT = 16*1024*1024
NUMBER = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z')


class ExternalDataError(ValueError):
    pass


def declarations(magnitude, unit, definition, provenance='No determinada', **texts):
    if magnitude not in DEFINITIONS or definition != DEFINITIONS[magnitude]:
        raise ExternalDataError('Magnitud/definición incompatible: declarala explícitamente antes de importar.')
    units = ('J/ciclo',) if SIM_KEYS[magnitude]=='W_C_J' else ('Pa','bar')
    if unit not in units:
        raise ExternalDataError('Unidad incompatible; solo J/ciclo o presión absoluta en Pa/bar según magnitud.')
    if provenance not in PROVENANCES:
        raise ExternalDataError('Procedencia desconocida: elegí una categoría admitida.')
    if set(texts)-set(TEXT_FIELDS):raise ExternalDataError('Metadatos no admitidos.')
    result=dict(magnitude=magnitude,original_unit=unit,canonical_unit=CANONICAL[magnitude],
                definition=definition,provenance=provenance)
    for key in TEXT_FIELDS:
        value=texts.get(key,'')
        if not isinstance(value,str) or len(value)>4096:raise ExternalDataError(f'Metadato {key}: texto de hasta 4096 caracteres.')
        result[key]=value.strip() or 'No informado'
    return result


def validate_declarations(data):
    if not isinstance(data,dict) or set(data)!=set(TEXT_FIELDS)|{'magnitude','original_unit','canonical_unit','definition','provenance'}:
        raise ExternalDataError('Metadatos incompletos o desconocidos.')
    expected=declarations(data['magnitude'],data['original_unit'],data['definition'],data['provenance'],
                          **{k:data[k] for k in TEXT_FIELDS})
    if data!=expected:raise ExternalDataError('Metadatos/unidades no corresponden a las reglas declaradas.')
    return expected


def _number(text,row,column):
    text=text.strip()
    if len(text)>80 or not NUMBER.fullmatch(text):
        raise ExternalDataError(f'Fila {row}, columna {column}: número decimal finito requerido (punto, sin miles).')
    try:
        number=Decimal(text)
        represented=float(number)
        if not number.is_finite() or not math.isfinite(represented) or (number!=0 and represented==0):
            raise ValueError()
    except (ValueError,InvalidOperation,OverflowError):
        raise ExternalDataError(f'Fila {row}, columna {column}: número fuera de representación finita.') from None
    return number


def parse_csv(raw,metadata):
    metadata=validate_declarations(metadata)
    if not isinstance(raw,bytes) or len(raw)>LIMIT:raise ExternalDataError('CSV: máximo 16 MiB.')
    try:text=raw.decode('utf-8-sig')
    except UnicodeError as exc:raise ExternalDataError('CSV: codificación UTF-8 inválida.') from exc
    reader=csv.reader(io.StringIO(text,newline=''),strict=True)
    rows=[];seen=set()
    try:
        header=next(reader,None)
        if header!=['rpm','value']:raise ExternalDataError('Fila 1, columnas: encabezado exacto requerido: rpm,value.')
        for cells in reader:
            line=reader.line_num
            if len(cells)!=2:raise ExternalDataError(f'Fila {line}, columnas: se requieren exactamente rpm,value.')
            rpm,value=(_number(cell,line,column) for cell,column in zip(cells,('rpm','value')))
            if rpm<=0:raise ExternalDataError(f'Fila {line}, columna rpm: debe ser positiva.')
            if rpm in seen:raise ExternalDataError(f'Fila {line}, columna rpm: régimen duplicado {rpm}.')
            seen.add(rpm)
            if SIM_KEYS[metadata['magnitude']]=='p_max_Pa' and value<=0:
                raise ExternalDataError(f'Fila {line}, columna value: presión absoluta estrictamente positiva.')
            with localcontext() as context:
                context.prec=800
                canonical=value*(100000 if metadata['original_unit']=='bar' else 1)
            if not math.isfinite(float(canonical)):
                raise ExternalDataError(f'Fila {line}, columna value: conversión fuera de representación finita.')
            rows.append(dict(rpm=rpm,original=value,value=canonical,source_row=line))
            if len(rows)>100000:raise ExternalDataError(f'Fila {line}, columnas: máximo 100000 puntos por CSV.')
    except csv.Error as exc:
        raise ExternalDataError(f'Fila {reader.line_num}, columnas: CSV inválido ({exc}).') from exc
    if not rows:raise ExternalDataError('Fila 2, columnas: falta al menos una fila de datos.')
    # Conservar raw y filas de origen; solo ordenar una copia para consulta.
    return sorted(rows,key=lambda row:row['rpm'])


def read_csv(path):
    try:
        with Path(path).open('rb') as stream:raw=stream.read(LIMIT+1)
        if len(raw)>LIMIT:raise ExternalDataError('CSV: máximo 16 MiB.')
        return raw
    except OSError as exc:raise ExternalDataError(f'No se pudo leer el CSV: {exc}') from exc


def prepare_import(raw,metadata):
    metadata=validate_declarations(metadata)
    return dict(raw=raw,metadata=metadata,rows=parse_csv(raw,metadata))


def save_import(folder,prepared):
    """Carpeta exclusiva, CSV original exacto; metadatos escritos al final."""
    prepared=prepare_import(prepared['raw'],prepared['metadata'])
    folder=Path(folder);created=[];owned=False
    manifest=dict(format='motorsim-external-rpm',version=1 if prepared['metadata']['magnitude'] in ('W_C_J','p_max_Pa') else 2,dataset_id=uuid.uuid4().hex,
        metadata=prepared['metadata'],rules=RULES,csv_file='original.csv',
        csv_sha256=hashlib.sha256(prepared['raw']).hexdigest())
    try:
        folder.mkdir(exist_ok=False);owned=True
        with (folder/'original.csv').open('xb') as stream:
            created.append(folder/'original.csv');stream.write(prepared['raw'])
        created.append(folder/'metadata.json');write_json(folder/'metadata.json',manifest)
        return load_import(folder/'metadata.json')
    except (OSError,ExternalDataError) as exc:
        cleanup=[]
        for path in created:
            try:path.unlink(missing_ok=True)
            except OSError as error:cleanup.append(str(error))
        if owned:
            try:folder.rmdir()
            except OSError as error:cleanup.append(str(error))
        detail=' Archivos incompletos en '+str(folder)+': '+'; '.join(cleanup) if cleanup else ''
        raise ExternalDataError(f'No se guardó la importación: {exc}.{detail}') from exc


def load_import(path):
    try:
        path=Path(path)
        if path.name!='metadata.json' or path.stat().st_size>128*1024:raise ExternalDataError('Elegí metadata.json de tamaño admitido.')
        manifest=json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(manifest,dict) or set(manifest)!={'format','version','dataset_id','metadata','rules','csv_file','csv_sha256'}
                or manifest['format']!='motorsim-external-rpm' or type(manifest['version']) is not int or manifest['version'] not in (1,2)
                or not isinstance(manifest['dataset_id'],str) or re.fullmatch('[0-9a-f]{32}',manifest['dataset_id']) is None
                or manifest['rules']!=RULES or manifest['csv_file']!='original.csv'):
            raise ExternalDataError('Formato, identidad o reglas no admitidos.')
        if manifest['version'] != (1 if manifest['metadata']['magnitude'] in ('W_C_J','p_max_Pa') else 2):
            raise ExternalDataError('Versión y definición de ciclo no corresponden.')
        source=(path.parent/'original.csv').resolve()
        if not source.is_relative_to(path.parent.resolve()):raise ExternalDataError('CSV externo a la carpeta de importación.')
        raw=read_csv(source)
        if hashlib.sha256(raw).hexdigest()!=manifest['csv_sha256']:raise ExternalDataError('CSV y metadatos no corresponden: hash distinto.')
        return dict(**prepare_import(raw,manifest['metadata']),manifest=manifest,path=path.resolve())
    except (OSError,ValueError,KeyError,TypeError,RecursionError) as exc:
        raise ExternalDataError(f'Importación ilegible: {exc}') from exc


def contrast(external,sweep):
    """Solo datos del lector de importación y load_sweep; nunca el editor."""
    metadata=validate_declarations(external['metadata'])
    cycle=CYCLES[metadata['magnitude']]
    actual=sweep['index']['common_inputs']['case']['project_geometry']['cycle']
    if cycle is None or cycle!=actual:
        raise ExternalDataError('Ciclo no declarado o incompatible: no se equiparan trabajo 360°/720° ni presiones de ciclos no declarados.')
    values={row['rpm']:row for row in external['rows']}
    simulated={Decimal(p['rpm']):(p,r) for p,r in zip(sweep['index']['points'],sweep['results'])}
    rows=[]
    with localcontext() as context:
        context.prec=800
        for rpm in sorted(values.keys()|simulated.keys()):
            ext=values.get(rpm);point,result=simulated.get(rpm,(None,None))
            accepted=point is not None and point['state']=='converged'
            sim=Decimal(str(result['result']['cycles'][-1][SIM_KEYS[metadata['magnitude']]])) if accepted else None
            ev=ext['value'] if ext else None
            difference=sim-ev if sim is not None and ev is not None else None
            relative=100*difference/abs(ev) if difference is not None and ev!=0 else None
            state=('coincidente' if accepted else 'simulación '+point['state']) if ext and point else ('solo externo' if ext else 'solo simulación: '+point['state'])
            rows.append(dict(rpm=rpm,external=ev,simulated=sim,difference=difference,relative_percent=relative,
                original_value=ext['original'] if ext else None,state=state,
                reason=point['reason'] if point else 'Sin RPM exactamente coincidentes en el barrido',
                run_id=point['run_id'] if point else None))
    return dict(rows=rows,magnitude=metadata['magnitude'],unit=metadata['canonical_unit'],
        external_count=len(values),simulated_count=len(simulated),
        matches=sum(row['difference'] is not None for row in rows),
        notice='Contraste descriptivo. Equivalencia de condiciones no acreditada.',
        dataset_id=external['manifest']['dataset_id'],series_id=sweep['index']['series_id'],metadata=metadata)


def export_contrast(folder,data):
    columns=['rpm','magnitude','canonical_unit','external','simulated','simulated_minus_external','relative_percent',
             'state','dataset_id','provenance','source','series_id','run_id','original_unit','original_value',
             'engine','configuration','conditions','definition','notice','reason']
    rows=[columns];meta=data['metadata']
    for row in data['rows']:
        rows.append([row['rpm'],data['magnitude'],data['unit'],row['external'],row['simulated'],row['difference'],
            row['relative_percent'],row['state'],data['dataset_id'],meta['provenance'],meta['source'],
            data['series_id'],row['run_id'],meta['original_unit'],row['original_value'],meta['engine'],
            meta['configuration'],meta['conditions'],meta['definition'],data['notice'],row['reason']])
    return write_csv_files(folder,[('contraste.csv',rows)])
