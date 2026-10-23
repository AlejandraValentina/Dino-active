"""Packaged path/identity safeguards; physical execution is tested in the EXE."""
import json
from pathlib import Path

import pytest

from motorsim import engineering_point as point
from motorsim.engine_project import load_project, save_project
from motorsim.desktop.services import new_project


def test_packaged_commit_never_launches_git(tmp_path, monkeypatch):
    (tmp_path/'motorsim').mkdir()
    manifest=tmp_path/'motorsim/build.json'
    manifest.write_text(json.dumps({'source_commit':'a'*40}))
    monkeypatch.setattr(point,'ROOT',tmp_path)
    monkeypatch.setattr(point.sys,'frozen',True,raising=False)
    monkeypatch.setattr(point.subprocess,'check_output',lambda *a,**k:pytest.fail('Git called'))
    assert point._producer_head()=='a'*40
    manifest.write_text(json.dumps({'source_commit':'unknown'}))
    with pytest.raises(ValueError,match='packaged source commit'):point._producer_head()


def test_portable_project_references_and_legacy_semantics(tmp_path, monkeypatch):
    project=new_project('portable-test')
    project['result_references']=[dict(path=p,identity_sha256='a'*64,artifact_sha256='b'*64,classification='EXPLORATORY')
                                  for p in ['./Datos/run/result.json','legacy/run/result.json']]
    path=tmp_path/'project.dino.json';save_project(path,project)
    monkeypatch.chdir(tmp_path.parent)
    loaded=load_project(path)
    assert loaded['result_references'][0]['path']==str(tmp_path/'Datos/run/result.json')
    assert loaded['result_references'][1]['path']=='legacy/run/result.json'
    assert json.loads(path.read_text())['result_references']==project['result_references']
