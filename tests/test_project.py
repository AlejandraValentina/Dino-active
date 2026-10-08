import unittest

from motorsim.project import Project, ProjectError


class ProjectTests(unittest.TestCase):
    def test_valid_names_and_cycles_are_preserved(self):
        for name in ("Motor", "Árbol de José", "  Motor  "):
            for cycle in ("2T", "4T"):
                with self.subTest(name=name, cycle=cycle):
                    project = Project(name, cycle)
                    self.assertEqual(Project.from_dict(project.to_dict()), project)
                    self.assertEqual(set(project.to_dict()), {"format_version", "two_stroke_reference", *Project.__dataclass_fields__})

    def test_invalid_names_and_cycles(self):
        for name in ("", " \t\n", None, 4, True, []):
            with self.subTest(name=name), self.assertRaises(ProjectError):
                Project(name, "2T").validate()
        for cycle in ("", "3T", "2t", 2, True, None, []):
            with self.subTest(cycle=cycle), self.assertRaises(ProjectError):
                Project("Motor", cycle).validate()

    def test_invalid_object_fields_and_versions(self):
        cases = [None, [], "texto", 1, {}, {"name": "Motor", "cycle": "2T"}]
        valid = Project().to_dict()
        for key in valid:
            cases.append({k: v for k, v in valid.items() if k != key})
        for version in (True, False, 1.0, "1", 0, 7, None):
            cases.append({**valid, "format_version": version})
        cases.extend([{**valid, "name": 1}, {**valid, "cycle": 4}])
        for data in cases:
            with self.subTest(data=data), self.assertRaises(ProjectError):
                Project.from_dict(data)
