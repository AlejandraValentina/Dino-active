import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from dev_orchestrator.contracts import BASE, read_json


def command(root,*args):
    return subprocess.run(['git',*args],cwd=root,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=10)


def repository(test):
    tmp=tempfile.TemporaryDirectory(prefix='motorsim-orchestrator-test-')
    test.addCleanup(tmp.cleanup)
    root=Path(tmp.name)
    shutil.copytree(BASE,root/'dev_orchestrator',ignore=shutil.ignore_patterns('runs','__pycache__','examples'))
    (root/'.gitignore').write_text('/dev_orchestrator/runs/\n__pycache__/\n',encoding='utf-8')
    (root/'motorsim').mkdir(); (root/'motorsim/sentinel.txt').write_text('product',encoding='utf-8')
    (root/'user.txt').write_text('baseline',encoding='utf-8')
    command(root,'init','-q'); command(root,'add','.')
    command(root,'-c','user.name=Infrastructure test','-c','user.email=test@example.invalid','commit','-qm','test baseline')
    return root


def save(path,data): path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def alter(root,**values):
    path=root/'dev_orchestrator/phases/dummy.json'; phase=read_json(path); phase.update(values); save(path,phase)
    roadmap_path=root/'dev_orchestrator/roadmap/gasdynamic.json'; roadmap=read_json(roadmap_path)
    entry=next(e for e in roadmap['phases'] if e['id']=='dummy')
    for a,b in (('depends_on','depends_on'),('allowed_paths','allowed_paths'),('forbidden_paths','forbidden_paths'),
                ('max_repair_attempts','max_repair_attempts'),('requires_human_approval','human_gate'),('required_checks','required_checks')):
        entry[a]=phase[b]
    save(roadmap_path,roadmap)
    return phase
