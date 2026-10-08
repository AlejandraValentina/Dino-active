"""Evidencia pequeña con referencias a logs separados, sin secretos ni entorno completo."""
import hashlib
import json
from pathlib import Path

from ..contracts import inside, validate_named


def artifacts(run_dir, paths):
    records=[]
    for value in paths:
        path=inside(run_dir,value)
        if not path.is_file(): raise FileNotFoundError('Evidencia requerida ausente: '+value)
        records.append(dict(path=value,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size))
    return records


def build_report(run_dir, evidence):
    validate_named(evidence,'evidence')
    run_dir=Path(run_dir)
    path=run_dir/'evidence.json'
    temporary=run_dir/'evidence.tmp'
    temporary.write_text(json.dumps(evidence,ensure_ascii=False,allow_nan=False,indent=2)+'\n',encoding='utf-8')
    temporary.replace(path)
    lines=[f"# {evidence['phase_id']} · {evidence['gate']}",
        f"Run: `{evidence['run_id']}`",f"Estado de ejecución: {evidence['execution_status']}",
        f"Git: `{evidence['git_commit']}` · dirty inicial: {evidence['git_dirty']}",
        f"Inicio: {evidence['started_at']} · Fin: {evidence['finished_at']}",
        'Motivos: '+', '.join(evidence['gate_reasons']),
        '## Checks','| Check | Resultado | Motivo |','| --- | --- | --- |']
    lines.extend(f"| {c['id']} | {'PASS' if c['passed'] else 'FAIL'} | {c.get('reason','')} |" for c in evidence['checks'])
    lines += ['', '## Intentos']
    lines.extend(f"- {a['number']}: {a['kind']} → {a['state']} ({a['cause']})" for a in evidence['attempts'])
    lines += ['', '## Revisión',evidence['review']['notes'],
        '## Alcance',f"Cambios de la fase: {evidence['files_changed']}",
        f"Violaciones: {evidence['scope_violations']}",
        f"Cambios previos conservados: {evidence['preexisting_changes']}",
        '## Evidencia','Logs separados en logs/; métricas, hashes y metadatos en [evidence.json](evidence.json).',
        'La ejecución se detiene aquí. No encadena fases ni acredita aceptación humana.']
    # Espaciado uniforme; datos sin copiar logs enormes al resumen.
    output=[]
    for line in lines:
        if output and not (line.startswith('|') and output[-1].startswith('|')):
            output.append('')
        output.append(line)
    (run_dir/'summary.md').write_text('\n'.join(output)+'\n',encoding='utf-8')
    return path
