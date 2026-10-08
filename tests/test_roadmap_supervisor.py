import json, os, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_status():
 r=subprocess.run([sys.executable,'dev_orchestrator/roadmap_supervisor.py','status'],cwd=ROOT,capture_output=True,text=True)
 assert r.returncode==0 and 'P5_B' in r.stdout
def test_configured_agent_command():
 cfg=json.loads((ROOT/'dev_orchestrator/roadmap_supervisor.json').read_text())
 assert cfg['agent_command'][0] == 'codex'
