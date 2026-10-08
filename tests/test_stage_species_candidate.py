"""Pruebas focales del candidato opt-in; no cambia expected históricos."""
import json
import math
from pathlib import Path
import unittest
from motorsim.simulation import TWO_LAYOUT as L, InvalidStage, rk4
from tools.stage_species_candidate import (LimiterDiagnostics, fresh_derivatives,
    limit_stage_species_fluxes, candidate_rk4)

ROOT = Path(__file__).resolve().parents[1]


def state(fresh):
    y = [0.]*L.size
    for i,f in enumerate(fresh): y[3*i:3*i+3] = [1.,100.,f]
    return y


def attempt(y, transfers, dt=1.):
    raw=y.copy()
    df, ledger=fresh_derivatives(transfers,L)
    dm=[0.]*4
    for j,q,f in transfers:
        a,b=L.ends[j]
        if a is not None: dm[a]-=q
        if b is not None: dm[b]+=q
    for i in range(4):
        raw[3*i]+=dt*dm[i]; raw[3*i+2]+=dt*df[i]
    diag=LimiterDiagnostics()
    fixed, flows=limit_stage_species_fluxes(y,raw,transfers,dt,diag)
    return raw,fixed,flows,diag


class SpeciesLimiterTests(unittest.TestCase):
    def test_scientific_comparison_normalizes_only_json_representation(self):
        from tools.verify_species_positivity import scientific_equal
        self.assertTrue(scientific_equal({'samples':[(1.,2.)],'seconds':1},
                                         {'samples':[[1.,2.]],'seconds':2}))
        self.assertFalse(scientific_equal({'samples':[(1.,2.)]}, {'samples':[[1.,2.000001]]}))

    def assert_conserved(self,y,raw,fixed,flows,dt=1.):
        for i in range(4):
            self.assertEqual(raw[3*i:3*i+2],fixed[3*i:3*i+2])
            self.assertLessEqual(0,fixed[3*i+2]); self.assertLessEqual(fixed[3*i+2],fixed[3*i])
        exterior=0.
        for j,q,f in flows:
            self.assertLessEqual(abs(f),abs(q))
            self.assertGreaterEqual(q*f,0)
            a,b=L.ends[j]
            if a is None: exterior+=dt*f
            if b is None: exterior-=dt*f
        residual=math.fsum(fixed[3*i+2]-y[3*i+2] for i in range(4))-exterior
        bound=8*math.ulp(max(1e-300,math.fsum(abs(v) for v in y[2:12:3])+abs(exterior)))
        self.assertLessEqual(abs(residual),bound)

    def check(self,y,flows,dt=1.):
        raw,fixed,limited,diag=attempt(y,flows,dt)
        self.assert_conserved(y,raw,fixed,limited,dt)
        return fixed,limited,diag

    def test_zero_fresh_requested_out(self):
        fixed,flows,d=self.check(state([0,0,0,0]),[(1,.2,.1)])
        self.assertEqual(flows[0][2],0); self.assertEqual(d.min_alpha,0)

    def test_tiny_fresh(self):
        _,flows,d=self.check(state([1e-20,0,0,0]),[(1,.2,.1)])
        self.assertLessEqual(flows[0][2],1e-20); self.assertEqual(d.activation_count,1)

    def test_competing_outlets_and_multiple_receivers(self):
        _,flows,d=self.check(state([0,.1,0,0]),[(1,-.3,-.2),(2,.3,.2),(3,.3,.2)])
        self.assertLessEqual(sum(abs(f) for j,q,f in flows),.1)
        self.assertEqual(abs(flows[0][2]),flows[1][2]); self.assertEqual(flows[1][2],flows[2][2])

    def test_backflow(self):
        _,flows,_=self.check(state([0,.01,0,0]),[(1,-.2,-.1)])
        self.assertLess(flows[0][2],0)

    def test_pure_donor_f_equals_m_y_one(self):
        _,flows,d=self.check(state([1,0,0,0]),[(1,.2,.2)])
        self.assertEqual(d.min_alpha,1); self.assertEqual(flows[0][2],.2)

    def test_y_zero(self):
        _,_,d=self.check(state([0,0,0,0]),[(1,.2,0)])
        self.assertEqual(d.activation_count,0)

    def test_receiver_without_fresh(self):
        fixed,_,_=self.check(state([.5,0,0,0]),[(1,.2,.1)])
        self.assertEqual(fixed[5],.1)

    def test_receiver_upper_limit(self):
        # base I puro; entrada pura .1 y salida evaluada .1 con Y=.5.
        fixed,_,d=self.check(state([1,0,0,0]),[(0,.1,.1),(1,.1,.05)])
        self.assertLessEqual(fixed[2],fixed[0]); self.assertEqual(d.activation_count,1)

    def test_upper_bound_infeasible_is_not_clipped(self):
        with self.assertRaisesRegex(InvalidStage,'sin solución'):
            attempt(state([1,0,0,0]),[(1,.1,.05)])

    def test_no_intervention_is_exact(self):
        y=state([.5,.5,.5,.5]); flows=[(1,.1,.05)]
        raw,fixed,limited,d=attempt(y,flows)
        self.assertIs(raw,fixed); self.assertIs(limited,flows); self.assertEqual(d.min_alpha,1)

    def test_rk4_exact_when_inactive(self):
        y=state([.5,.5,.5,.5])
        def rhs(t,v):
            k=[0.]*L.size
            k[0]=-.1;k[3]=.1;k[2]=-.05;k[5]=.05;k[15]=.1;k[17]=.05
            return k
        d=LimiterDiagnostics()
        self.assertEqual(rk4(0,y,.1,rhs),candidate_rk4(d,lambda t:t)(0,y,.1,rhs))
        self.assertEqual(d.activation_count,0)

    def test_rk4_donor_switch_all_evaluated_stages_and_conservation(self):
        y=state([0,.5,0,0])
        evaluated=[]
        def rhs(t,v):
            evaluated.append(v.copy())
            q=.1 if t<.25 else -.1
            donor=1 if q>0 else 2
            f=q*v[3*donor+2]/v[3*donor]
            k=[0.]*L.size
            k[3]=-q;k[6]=q;k[5]=-f;k[8]=f;k[18]=q;k[20]=f
            return k
        raw=rk4(0,y,1.,rhs)
        self.assertTrue(any(v[8]<0 for v in evaluated))
        evaluated.clear(); diag=LimiterDiagnostics()
        fixed=candidate_rk4(diag,lambda t:180+t)(0,y,1.,rhs)
        self.assertTrue(all(0<=v[3*i+2]<=v[3*i] for v in evaluated for i in range(4)))
        self.assertGreater(diag.activation_count,0)
        self.assertEqual(math.fsum(fixed[2:12:3]),.5)
        for i in range(4): self.assertEqual(raw[3*i:3*i+2],fixed[3*i:3*i+2])

    def replay_micro(self,rpm):
        p=ROOT/f'results/frontera-baja-2t-20260917/{rpm}-observation.json'
        rows=json.loads(p.read_text(encoding='utf-8'))['physical_failures']
        rows=[r for r in rows if (r['state'][8]<0 if rpm==2000 else r['state'][2]>r['state'][0])]
        c=rows[-1]['context']['rk4']; y,k,dt=c['y'],c['k3'],c['dt']
        raw=[v+dt*d for v,d in zip(y,k)]
        flows=[(j,k[12+3*j],k[14+3*j]) for j in range(6)]
        diag=LimiterDiagnostics(rpm)
        fixed,limited=limit_stage_species_fluxes(y,raw,flows,dt,diag)
        self.assert_conserved(y,raw,fixed,limited,dt)
        return y,raw,fixed,diag

    def test_real_2000_zero_base_microstate(self):
        y,raw,fixed,d=self.replay_micro(2000)
        self.assertEqual(y[8],0); self.assertLess(raw[8],0); self.assertEqual(fixed[8],0)
        self.assertAlmostEqual(d.total_corrected,9.523239929231602e-18,delta=1e-32)

    def test_real_1750_upper_one_ulp_microstate(self):
        y,raw,fixed,d=self.replay_micro(1750)
        self.assertEqual(y[0],y[2]); self.assertEqual(raw[2]-raw[0],math.ulp(raw[0]))
        self.assertLessEqual(fixed[2],fixed[0]); self.assertLess(d.total_corrected,math.ulp(raw[0]))

    def test_final_combination_checked_and_direction_not_averaged(self):
        y=state([.01,0,0,0]); flows=[(1,.2,.1),(1,-.1,0.)]
        _,limited,_=self.check(y,flows)
        self.assertEqual(limited[0][1],.2); self.assertEqual(limited[1][1],-.1)


if __name__=='__main__': unittest.main()
