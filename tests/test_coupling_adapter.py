import unittest
from dataclasses import replace
from motorsim.coupling_adapter import chamber_from_model, state_with_chamber
from motorsim.coupling import interface_flux
from motorsim.simulation import Model
from motorsim.four_stroke import FourStrokeModel


class AdapterTests(unittest.TestCase):
    def test_existing_two_and_four_stroke_states_roundtrip(self):
        for model in (Model(),FourStrokeModel()):
            angle=model.case.initial_angle_deg;state=model.initial_state();original=state.copy()
            for index,node in enumerate(model.layout.cv):
                with self.subTest(cycle=model.layout.period,node=node):
                    chamber,eos=chamber_from_model(model,angle,state,node)
                    rho,p,t,y=chamber.thermodynamics(eos)
                    expected=model.case.initial_pty[index]
                    for a,b in zip((p,t,y),expected):self.assertAlmostEqual(a,b)
                    self.assertEqual(state_with_chamber(model,angle,state,node,chamber),state)
                    flux=interface_flux(chamber,(rho,0.,p,y),.001,-1,eos=eos)
                    self.assertEqual([flux.outward[k] for k in (0,2,3)],[0.,0.,0.])
                    changed=replace(chamber,internal_energy=chamber.internal_energy*1.001)
                    result=state_with_chamber(model,angle,state,node,changed)
                    self.assertNotEqual(result[3*index+1],state[3*index+1])
                    self.assertEqual(result[:3*index],state[:3*index])
                    self.assertEqual(result[3*index+3:],state[3*index+3:])
            self.assertEqual(state,original)

    def test_invalid_mapping_rejected(self):
        model=Model();state=model.initial_state();angle=model.case.initial_angle_deg
        chamber,_=chamber_from_model(model,angle,state,'C')
        for invalid in (replace(chamber,volume=chamber.volume*2),replace(chamber,fresh_mass=chamber.mass*2)):
            with self.assertRaises(ValueError):state_with_chamber(model,angle,state,'C',invalid)
        with self.assertRaises(ValueError):chamber_from_model(model,angle,state[:-1],'C')
        with self.assertRaises(ValueError):chamber_from_model(model,angle,state,'unknown')
