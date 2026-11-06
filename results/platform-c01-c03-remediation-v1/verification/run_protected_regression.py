"""Read-only protected regression using explicit historical artifact context."""
import json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
# Repository is resolved from this new receipt's location, never from historical cwd.
sys.path.insert(0,str(ROOT))
modules=json.loads((ROOT/'results/platform-integration-audit-v1/checks/contract/contract-integrity.json').read_text())['selected_modules']
context=Path(sys.argv[1]).resolve()
assert (context/'results/p4-g2-v2-20260929/checkpoint_cycle031.json.gz').is_file()
print('PINNED_SOURCE_ROOT',ROOT,flush=True)
print('HISTORICAL_ARTIFACT_CWD',context,flush=True)
print('EXTERNAL_ARTIFACT_ROOT',os.environ.get('DINO_ARTIFACT_ROOT'),flush=True)
os.chdir(context)
import motorsim.artifact_store
assert Path(motorsim.artifact_store.__file__).is_relative_to(ROOT)
import pytest
raise SystemExit(pytest.main([*[str(ROOT/Path(p.replace('\\','/'))) for p in modules],'-q','-p','no:cacheprovider']))
