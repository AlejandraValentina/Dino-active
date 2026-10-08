import unittest, tempfile, json, gzip, os
from pathlib import Path
import numpy as np
from motorsim.checkpoint import (
    make_summary, save_summary, load_summary,
    save_restart, load_restart, load_restart_legacy_json_gz,
    save_full_debug, load_full_debug,
    should_write_restart, assert_decision_size, _atomic_write_text
)
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_fast import run_cycle
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas

class PerfCheckpointTests(unittest.TestCase):
    def test_summary_serialization_small(self):
        # Create dummy row with history like real
        row = dict(
            begin=180, end=540, complete=True, reason='final_time',
            work_indicated_J=12.3, power_indicated_W=615, torque_indicated_Nm=0.1,
            global_balance=[1e-14]*3, initial_inventory=[1,1,1], final_inventory=[1,1,1],
            port_integral=[0,0,0], external=[0,0,0], cycle_wall_seconds=19, solver_seconds=17,
            segments=[dict(result=dict(counts=dict(rhs=30000, HLLC=7000000)))],
            history=[dict(angle=180+i, p_cyl=1e5, T_cyl=300, m_cyl=0.001, Y_cyl=0.2,
                          sensors_p_u_M_Y=[(1e5,10,0.3,0.2)]*3, p_port=1e5, Mach_port=0.1,
                          mass_flux_port=0, energy_flux_port=0, species_flux_port=0) for i in range(1000)],
            state=[0]*9, cells=[[0]*4]*10
        )
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"summary.json"
            summ, sz = save_summary(row, p)
            # Should be small <50KB
            self.assertLess(sz, 50*1024)
            loaded = load_summary(p)
            self.assertEqual(loaded['work_indicated_J'], 12.3)
            self.assertEqual(loaded['history_len'], 1000)
            # No large history in summary
            self.assertNotIn('history_decimated', loaded)

    def test_restart_roundtrip(self):
        state = np.random.rand(9).astype(np.float64)
        cells = np.random.rand(250,4).astype(np.float64)
        config = dict(dx_target=0.003, backend='NUMBA_FUSED', cfl=0.4, config_hash='abc')
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"restart"
            meta, raw, sz = save_restart(state, cells, cycle=5, angle=540, config=config, out_dir=out, compressed=False)
            meta2, s2, c2 = load_restart(out)
            self.assertTrue(np.allclose(state, s2))
            self.assertTrue(np.allclose(cells, c2))
            self.assertEqual(s2.dtype, np.float64)
            self.assertEqual(c2.dtype, np.float64)
            self.assertEqual(meta['n'], 250)

    def test_restart_next_cycle_equivalence(self):
        # Use real motor cycle for exact equivalence
        model = LegacySources()
        mesh = exhaust_mesh(segments('straight'), 0.003)
        p,T,Y = model.case.initial_pty[3]
        eos = IdealGas()
        U = eos.conservative((p/(eos.R*T),0.,p,Y))
        pipe = [tuple(v*u for u in U) for v in mesh.volumes]
        state = model.initial_state()[:9]
        # warm JIT
        _ = run_cycle(mesh, pipe, state, 180., backend='NUMBA_FUSED', cfl=0.4)
        # First cycle
        row1 = run_cycle(mesh, pipe, state, 180., backend='NUMBA_FUSED', cfl=0.4)
        s1 = row1['state']
        c1 = row1['cells']
        angle1 = row1['end']
        # Path A
        rowA = run_cycle(mesh, c1, s1, angle1, backend='NUMBA_FUSED', cfl=0.4)
        # Path B via restart
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"restart"
            config = dict(dx_target=0.003, backend='NUMBA_FUSED', cfl=0.4)
            save_restart(s1, c1, cycle=1, angle=angle1, config=config, out_dir=out, compressed=False)
            meta, s1b, c1b = load_restart(out)
            rowB = run_cycle(mesh, c1b.tolist(), s1b.tolist(), angle1, backend='NUMBA_FUSED', cfl=0.4)
            self.assertEqual(rowA['work_indicated_J'], rowB['work_indicated_J'])
            self.assertEqual(rowA['state'], rowB['state'])
            self.assertEqual(rowA['cells'], rowB['cells'])

    def test_atomic_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"atomic.json"
            # Write 100 times, check no partial
            for i in range(20):
                _atomic_write_text(p, json.dumps({"i": i}))
                data = json.loads(p.read_text())
                self.assertEqual(data["i"], i)
            # Check that tmp file not left
            self.assertFalse((p.parent / (p.name + ".tmp")).exists())

    def test_restart_every_policy(self):
        self.assertTrue(should_write_restart(1, 1))
        self.assertTrue(should_write_restart(5, 5))
        self.assertFalse(should_write_restart(1, 5))
        self.assertFalse(should_write_restart(2, 5))
        self.assertTrue(should_write_restart(5, 5))
        self.assertTrue(should_write_restart(3, 5, is_final=True))
        self.assertTrue(should_write_restart(2, 5, is_cancelled=True))
        self.assertTrue(should_write_restart(2, 5, is_failed=True))

    def test_full_debug_compatibility(self):
        row = dict(state=[1,2,3], cells=[[1,2,3,4]]*5, history=[], work_indicated_J=1, begin=180, end=540)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"full.json.gz"
            raw, gz = save_full_debug(row, p)
            loaded = load_full_debug(p)
            self.assertEqual(loaded, row)
            self.assertLess(gz, raw*1.5) # gz smaller or similar

    def test_binary_float64_preservation(self):
        # Ensure float64 exact, not float32
        state = np.array([1.123456789012345, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0], dtype=np.float64)
        cells = np.array([[1.123456789012345]*4]*10, dtype=np.float64)
        config = dict(dx_target=0.003)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"restart"
            save_restart(state, cells, cycle=1, angle=180, config=config, out_dir=out, compressed=False)
            meta, s2, c2 = load_restart(out)
            self.assertEqual(s2.dtype, np.float64)
            self.assertEqual(c2.dtype, np.float64)
            self.assertEqual(s2[0], state[0])
            self.assertEqual(c2[0,0], cells[0,0])

    def test_no_aliasing(self):
        # Test that reused buffers don't alias input (fused path already tested elsewhere)
        # Here test that save_restart does not modify input arrays
        state = np.array([1.,2.,3.,4.,5.,6.,7.,8.,9.], dtype=np.float64)
        cells = np.array([[1.,2.,3.,4.]]*10, dtype=np.float64)
        state_copy = state.copy()
        cells_copy = cells.copy()
        config = dict(dx_target=0.003)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)/"restart"
            save_restart(state, cells, cycle=1, angle=180, config=config, out_dir=out, compressed=False)
            # Ensure original not modified
            self.assertTrue(np.allclose(state, state_copy))
            self.assertTrue(np.allclose(cells, cells_copy))
            # Also test that load does not alias
            meta, s2, c2 = load_restart(out)
            s2[0] = 999
            c2[0,0] = 999
            self.assertNotEqual(state[0], 999)
            self.assertNotEqual(cells[0,0], 999)

    def test_decision_compact(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"decision.json"
            # Small should pass
            p.write_text(json.dumps({"phase":"P4-PERF-01", "gate":"PASS"}))
            assert_decision_size(p, max_kb=100)
            # Large should fail
            p.write_text("x"*200*1024)
            with self.assertRaises(ValueError):
                assert_decision_size(p, max_kb=100)

    def test_backward_legacy(self):
        # Create legacy json.gz and read via checkpoint
        row = dict(state=[1,2,3], cells=[[1,2,3,4]], work_indicated_J=1, begin=180, end=540)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/"legacy.json.gz"
            p.write_bytes(gzip.compress(json.dumps(row).encode()))
            loaded = load_restart_legacy_json_gz(p)
            self.assertEqual(loaded['state'], [1,2,3])
            self.assertEqual(loaded['work_indicated_J'], 1)

    def test_thread_limits_in_multicore(self):
        # Check that _job_wrapper sets env to 1
        import dev_orchestrator.multicore as mc
        import inspect
        src = inspect.getsource(mc._job_wrapper)
        self.assertIn('OMP_NUM_THREADS', src)
        self.assertIn('\"1\"', src)

if __name__ == "__main__":
    unittest.main()
