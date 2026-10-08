import copy
import unittest
from motorsim.four_stroke_acceptance import evaluate_r2


def fixture(offsets):
    runs=[]
    for offset in offsets:
        pressure=100000+offset
        balances={k:dict(normalized_m_u_f=[0.,0.,0.],residual_kg_j_kg=[0.,0.,0.]) for k in ('I','C','E','global')}
        cycles=[dict(cycle=i,state=[.001,100.,.0005]*3,Y=[.5]*3,net_link_mass_kg=[1e-4]*4,
            W_C_J=10.,p_max_Pa=pressure,Q_J=1.,F_s_kg=.0001,discrete=balances,independent=balances,
            convergence=dict(passed=True,m_relative=0.,U_relative=0.,Y_absolute=0.,W_relative=0.,p_curve_relative=0.)) for i in range(1,8)]
        rows=[[dict(angle_deg=720*(i-1)+j*.5,p_T_Y=[[pressure,300,.5]]*3) for j in range(1441)] for i in (6,7)]
        runs.append(dict(converged=True,cycles=cycles,last_two_cycles=rows,seconds=1.,peak_MiB=20.,rhs_evaluations=100))
    return copy.deepcopy(runs)


class AcceptanceTests(unittest.TestCase):
    def test_normal(self):
        result=evaluate_r2(fixture((0,100,110)))
        self.assertTrue(result['passed']);self.assertEqual(result['route'],'normal')
    def test_practical_not_monotonic(self):
        result=evaluate_r2(fixture((0,.1,1)))
        self.assertTrue(result['passed']);self.assertEqual(result['route'],'practical')
        self.assertFalse(result['original_R1']['decreasing_discrepancy'])
        self.assertAlmostEqual(result['spread']['p_max_Pa'],1/100001)
    def test_outside_practical(self):
        self.assertFalse(evaluate_r2(fixture((0,1,100)))['passed'])
    def test_balances_and_convergence_block(self):
        for kind in ('convergence','balance'):
            runs=fixture((0,.1,1))
            if kind=='convergence':runs[0]['converged']=False
            else:runs[0]['cycles'][-1]['independent']['C']['normalized_m_u_f'][0]=.002
            self.assertFalse(evaluate_r2(runs)['passed'])
    def test_missing_blocks(self):
        for key in ('cycles','seconds','last_two_cycles'):
            runs=fixture((0,.1,1));del runs[1][key]
            self.assertFalse(evaluate_r2(runs)['passed'])

    def test_nonfinite_or_incoherent_physics_blocks(self):
        for key,value in (('Q_J',float('nan')),('F_s_kg',float('inf')),('Y',[2,2,2]),('Y',[.6,.6,.6])):
            runs=fixture((0,.1,1))
            for r in runs:r['cycles'][-1][key]=value
            self.assertFalse(evaluate_r2(runs)['passed'],key)
        runs=fixture((0,.1,1));runs[0]['last_two_cycles'][0].pop()
        self.assertFalse(evaluate_r2(runs)['passed'])


if __name__=='__main__':unittest.main()
