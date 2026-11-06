"""Verify retained real producer output without executing either solver."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from motorsim.desktop.four_stroke_artifacts import require_verified_run
root=Path(__file__).resolve().parent
bundle=root/'native-producer-smoke'
receipt=json.loads((root/'native-producer-smoke-receipt.json').read_bytes())
for entry in receipt['raw_file_preimages']:
    raw=(bundle/entry['path']).read_bytes()
    assert len(raw)==entry['size_bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
ref=json.loads((bundle/'reference.json').read_bytes())
for key in ('path','run_manifest_path'):ref[key]=str((bundle/ref[key]).resolve())
run=require_verified_run(ref)
assert run.summary['cycles_run']==1 and run.summary['periodicity']['status']=='NOT_CONVERGED'
assert run.meta['source_qualification']=='COMPLETE_CLEAN_SOURCE_SNAPSHOT'
print(json.dumps({'classification':run.classification,'source':run.meta['source_qualification'],
    'cycles':1,'periodicity':'NOT_CONVERGED','new_solver_runs':0}))
