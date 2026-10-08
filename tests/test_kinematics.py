import math
import unittest

from motorsim.kinematics import calculate_geometry, piston_position


class KinematicsTests(unittest.TestCase):
    def values(self, **changes):
        return dict(bore_mm=80, stroke_mm=90, rod_length_mm=150, compression_ratio=10, **changes)

    def test_dead_centers_and_periodicity(self):
        for angle in (0, 360, 720):
            self.assertEqual(piston_position(90, 150, angle), 0)
        for angle in (180, 540):
            self.assertEqual(piston_position(90, 150, angle), 90)
        for angle in (1, 45, 90, 179, 275):
            self.assertAlmostEqual(piston_position(90, 150, angle), piston_position(90, 150, angle+360))

    def test_independent_345_triangle(self):
        # A 90°, r=3 y L=5 forman triángulo 3-4-5: x=3+5-4=4 mm.
        self.assertAlmostEqual(piston_position(6, 5, 90), 4)
        # D=20: área=100*pi mm²; Vd=.6*pi cm³; C=3: Vc=.3*pi.
        data = calculate_geometry(dict(bore_mm=20, stroke_mm=6, rod_length_mm=5,
                                       compression_ratio=3), "2T")
        self.assertAlmostEqual(data.chamber, .3*math.pi)
        self.assertAlmostEqual(data.volumes[90], .7*math.pi)
        self.assertAlmostEqual(data.maximum, .9*math.pi)

    def test_volumes_and_range(self):
        data = calculate_geometry(self.values(), "4T")
        self.assertEqual(len(data.angles), 721)
        self.assertEqual(data.volumes[0], data.chamber)
        self.assertEqual(data.volumes[180], data.maximum)
        self.assertAlmostEqual(data.maximum-data.chamber, math.pi*80**2*90/4000)
        self.assertEqual(data.volumes[:361], data.volumes[360:])
        self.assertEqual(data.end_angle, 720)
        self.assertEqual(calculate_geometry(self.values(), "2T").end_angle, 360)

    def test_independent_dependencies(self):
        for field in ('bore_mm', 'compression_ratio'):
            values = self.values(); values[field] = None
            data = calculate_geometry(values, '2T')
            self.assertTrue(data.positions)
            self.assertFalse(data.volumes)
            self.assertIsNone(data.chamber)
            self.assertIn('Falta:', data.errors['volume'])
        for field in ('stroke_mm', 'rod_length_mm'):
            values = self.values(); values[field] = None
            data = calculate_geometry(values, '2T')
            self.assertFalse(data.positions)
            self.assertFalse(data.volumes)
            if field == 'rod_length_mm':
                self.assertIsNotNone(data.chamber)
        a = calculate_geometry(self.values(cylinder_count=1), '2T')
        b = calculate_geometry(self.values(cylinder_count=8), '2T')
        self.assertEqual(a.volumes, b.volumes)

    def test_incompatible_and_invalid_inputs(self):
        for rod in (45, 44, 0, math.nan, math.inf):
            values = self.values(); values['rod_length_mm'] = rod
            data = calculate_geometry(values, '2T')
            self.assertFalse(data.positions)
            self.assertFalse(data.volumes)
            self.assertTrue(data.errors['position'])
            self.assertIsNotNone(data.chamber)
        values = self.values()
        data = calculate_geometry(values, '2T', {'bore_mm': 'Entrada inválida'})
        self.assertTrue(data.positions)
        self.assertEqual(data.errors['volume'], 'Entrada inválida')

    def test_numeric_limits_are_explained(self):
        values = self.values(); values['bore_mm'] = 1e308
        data = calculate_geometry(values, '2T')
        self.assertFalse(data.volumes)
        self.assertIn('rango', data.errors['volume'])
        self.assertTrue(data.positions)

    def test_displacement_does_not_require_compression(self):
        for compression in (None, 1, 0, math.nan):
            values = self.values(); values['compression_ratio'] = compression
            data = calculate_geometry(values, '2T')
            self.assertAlmostEqual(data.displacement, math.pi*80**2*90/4000)
            self.assertIsNone(data.chamber)
            self.assertFalse(data.volumes)
            self.assertTrue(data.positions)
