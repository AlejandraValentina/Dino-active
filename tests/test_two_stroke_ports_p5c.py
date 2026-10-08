import unittest

from motorsim.p5c import make_p5c_fixture
from motorsim.project import ProjectError
from motorsim.two_stroke_ports import (AreaKnot, DuctBinding, PortDefinition,
                                       TwoStrokePortSet)
from motorsim.two_stroke_ports_p5c import P5CGenericPortGeometry, P5CPathBinding


def port_fixture():
    return TwoStrokePortSet(
        56.0, 100.0,
        (DuctBinding("intake", "intake"),
         DuctBinding("primary", "transfer"),
         DuctBinding("secondary-and-boost", "transfer"),
         DuctBinding("exhaust", "exhaust")),
        (PortDefinition("piston-inlet", "Piston inlet", "intake", "piston_port",
                        "intake", "piston_port", 0.9, "SYNTHETIC_ASSUMPTION",
                        top_mm=64.0, height_mm=10.0, width_mm=20.0, skirt_mm=42.0),
         PortDefinition("primary-transfer", "Primary", "transfer", "primary",
                        "primary", "rectangular_window", 0.7, "SYNTHETIC_ASSUMPTION",
                        top_mm=32.0, height_mm=10.0, width_mm=20.0),
         PortDefinition("secondary-transfer", "Secondary", "transfer", "secondary",
                        "secondary-and-boost", "rectangular_window", 0.8,
                        "SYNTHETIC_ASSUMPTION", top_mm=34.0, height_mm=8.0, width_mm=12.0),
         PortDefinition("boost-transfer", "Boost", "transfer", "boost",
                        "secondary-and-boost", "rectangular_window", 0.6,
                        "SYNTHETIC_ASSUMPTION", top_mm=36.0, height_mm=7.0, width_mm=8.0),
         PortDefinition("main-exhaust", "Main exhaust", "exhaust", "main", "exhaust",
                        "rectangular_window", 0.9, "SYNTHETIC_ASSUMPTION",
                        top_mm=30.0, height_mm=10.0, width_mm=20.0),
         PortDefinition("aux-exhaust", "Auxiliary exhaust", "exhaust", "auxiliary",
                        "exhaust", "effective_profile", 0.5, "SYNTHETIC_ASSUMPTION",
                        area_profile=(AreaKnot(0.0, 0.0), AreaKnot(90.0, 30.0),
                                      AreaKnot(180.0, 60.0), AreaKnot(270.0, 30.0),
                                      AreaKnot(360.0, 0.0)))))


class GenericPortsP5CAdapterTests(unittest.TestCase):
    def setUp(self):
        self.ports = port_fixture()
        self.bindings = P5CPathBinding("intake", ("primary", "secondary-and-boost"),
                                       "exhaust")
        self.base = lambda angle: {"volumes": (1e-3, 1e-3, 1e-2),
                                   "volume_rates": (0.0, 0.0)}

    def test_individual_apertures_resolve_to_p5c_interface_areas(self):
        callback = P5CGenericPortGeometry(self.ports, self.bindings, self.base)
        result = callback(180.0)
        expected = tuple(self.ports.duct_area_at(duct, 180.0) * 1e-6
                         for duct in ("intake", "primary", "secondary-and-boost", "exhaust"))
        self.assertEqual(result["areas"], expected)
        # The opt-in adapter supplies actual stage geometry to the unchanged P5-B RHS.
        fixture = make_p5c_fixture(cells=2)
        fixture.core.geometry_callback = callback
        _, trace = fixture.core._rhs(fixture.core._state(), 180.0)
        self.assertEqual(trace["areas"], expected[:3])
        self.assertGreater(trace["areas"][1], 0.0)
        self.assertGreater(trace["areas"][2], 0.0)

    def test_adapter_rejects_a_third_transfer_duct_instead_of_dropping_it(self):
        from dataclasses import replace
        with self.assertRaisesRegex(ProjectError, "conductos adicionales"):
            extra = replace(self.ports,
                            ducts=(*self.ports.ducts,
                                   DuctBinding("boost-path", "transfer")))
            P5CGenericPortGeometry(extra, self.bindings, self.base)

    def test_adapter_rejects_bad_chamber_geometry(self):
        callback = P5CGenericPortGeometry(
            self.ports, self.bindings,
            lambda angle: {"volumes": (1e-3, 1e-3, 1e-2),
                           "volume_rates": (False, 0.0)})
        with self.assertRaisesRegex(ProjectError, "no finito"):
            callback(180.0)


if __name__ == "__main__":
    unittest.main()
