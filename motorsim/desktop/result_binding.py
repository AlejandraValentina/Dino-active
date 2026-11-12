"""Application-level binding through the public, verified result importer."""
import hashlib,json
from pathlib import Path


def verified_references(paths):
    from ..power_curve import import_curve_runs
    normalized=[Path(p).resolve() for p in paths]
    files=[p/'result.json' if p.is_dir() else p for p in normalized]
    snapshots={p:p.read_bytes() for p in files}
    # Full importer checks primary artifacts. Metadata alone never upgrades integrity.
    dataset=import_curve_runs([str(p.parent) for p in files])
    refs=[]
    for path,raw in snapshots.items():
        if path.read_bytes()!=raw:raise ValueError('El resultado cambió durante la verificación')
        result=json.loads(raw);binding=result.get('bindings',{})
        if not binding.get('identity_sha256') or not result.get('classification'):
            raise ValueError('Resultado sin identidad vinculable; conservá la apertura externa sin promoverlo')
        refs.append(dict(path=str(path),identity_sha256=binding['identity_sha256'],artifact_sha256=hashlib.sha256(raw).hexdigest(),classification=result['classification']))
    return refs,dataset
