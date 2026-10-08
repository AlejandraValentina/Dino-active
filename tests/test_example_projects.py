"""JSON públicos reales: identidad, equivalencia y persistencia; sin solver."""
import json
from dataclasses import replace
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from motorsim.project import ProjectError
from tools import generate_example_projects as generator
from motorsim.examples import PROJECT_FILES, example_file_project
from motorsim.simulation_case import geometry as geometry2
from motorsim.four_stroke import geometry as geometry4
from motorsim.project_case import execution_errors
from motorsim.storage import load_project, save_project

ROOT = Path(__file__).resolve().parents[1]


class PhysicalExampleTests(unittest.TestCase):
    def test_files_canonical_fields_and_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            for key, filename in PROJECT_FILES.items():
                with self.subTest(key=key):
                    path=ROOT/'examples/projects'/filename
                    raw=json.loads(path.read_text(encoding='utf-8'))
                    self.assertEqual(raw['format_version'],6)
                    project=load_project(path);project.validate()
                    canonical=(geometry2 if key.startswith('2t') else geometry4)()
                    self.assertEqual(replace(project,name=canonical.name,notes=canonical.notes,
                        compression_ratio=canonical.compression_ratio),canonical)
                    self.assertEqual(project,example_file_project(key))
                    self.assertEqual(project.name,f'EJEMPLO SINTÉTICO {canonical.cycle} — REFERENCIA')
                    self.assertIn('NO MEDIDO',project.notes)
                    self.assertEqual(execution_errors(project),[])
                    copy=Path(tmp)/filename;save_project(copy,project)
                    self.assertEqual(load_project(copy),project)
                    self.assertEqual(json.loads(copy.read_text(encoding='utf-8')),raw)
    def test_only_compression_differs(self):
        for cycle in ('2t','4t'):
            a=load_project(ROOT/'examples/projects'/PROJECT_FILES[cycle+'-reference']).to_dict()
            b=load_project(ROOT/'examples/projects'/PROJECT_FILES[cycle+'-compression']).to_dict()
            self.assertEqual([k for k in a if a[k]!=b[k]],['compression_ratio'])
            self.assertEqual(a['compression_ratio'],8.0);self.assertEqual(b['compression_ratio'],8.2)
    def test_generator_is_deterministic_from_another_directory(self):
        files=[ROOT/'examples/projects'/name for name in PROJECT_FILES.values()]
        before={path:path.read_bytes() for path in files}
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            temporary_root=Path(tmp)/'temporary-repository'
            alternate_cwd=Path(tmp)/'different-working-directory'
            alternate_cwd.mkdir()
            with patch.object(generator,'ROOT',temporary_root):
                previous=os.getcwd()
                try:
                    os.chdir(alternate_cwd)
                    generator.generate()
                    generated={p.name:p.read_bytes() for p in
                               (temporary_root/'examples/projects').iterdir()}
                    generator.generate()
                    self.assertEqual(generated,{p.name:p.read_bytes() for p in
                                                (temporary_root/'examples/projects').iterdir()})
                finally:
                    os.chdir(previous)
        self.assertEqual(before,{path:path.read_bytes() for path in files})
    def test_generator_preserves_other_files_and_rejects_invalid_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(generator,'ROOT',Path(tmp)), redirect_stdout(StringIO()):
            folder=Path(tmp)/'examples/projects';folder.mkdir(parents=True)
            other=folder/'personal.json';other.write_bytes(b'preservar')
            generator.generate()
            before={p.name:p.read_bytes() for p in folder.iterdir()}
            self.assertEqual(set(before),set(PROJECT_FILES.values())|{'personal.json'})
            def invalid(key):
                p=example_file_project(key)
                return replace(p,compression_ratio=0) if key=='4t-compression' else p
            with patch.object(generator,'example_file_project',side_effect=invalid),self.assertRaises(ProjectError):
                generator.generate()
            self.assertEqual(before,{p.name:p.read_bytes() for p in folder.iterdir()})


if __name__=='__main__':unittest.main()
