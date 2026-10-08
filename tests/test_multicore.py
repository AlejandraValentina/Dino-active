import unittest, tempfile, json, time
from pathlib import Path
from dev_orchestrator.multicore import (
    detect_physical_cores, suggest_workers, resolve_workers,
    Campaign, Job, build_rpm_chains, can_launch_workers, system_memory_mb
)

# Top-level job functions must be pickleable
def job_compute(job_id, job_dir, worker_id, rpm, sleep=0.01):
    import json, time
    from pathlib import Path
    time.sleep(sleep)
    result = {"rpm": rpm, "computed": rpm*2}
    Path(job_dir).joinpath("out.json").write_text(json.dumps(result))
    return result

def job_fail(job_id, job_dir, worker_id, **kwargs):
    raise RuntimeError("intentional fail")

class MulticoreTests(unittest.TestCase):
    def test_detect_and_policy(self):
        self.assertEqual(suggest_workers(1), 1)
        self.assertEqual(suggest_workers(2), 1)
        self.assertEqual(suggest_workers(3), 2)
        self.assertEqual(suggest_workers(4), 2)
        self.assertEqual(suggest_workers(5), 3)
        self.assertEqual(suggest_workers(6), 3)
        self.assertEqual(suggest_workers(7), 4)
        self.assertEqual(suggest_workers(8), 4)
        self.assertEqual(suggest_workers(9), 6)
        self.assertEqual(suggest_workers(12), 6)
        self.assertEqual(suggest_workers(13), 6)  # min(8,6) ->6
        self.assertEqual(suggest_workers(16), 8)
        self.assertEqual(suggest_workers(24), 8)
        # i5-10400 6 ->3
        self.assertEqual(resolve_workers("auto", 6), 3)
        self.assertEqual(resolve_workers("Automatic", 6), 3)
        self.assertEqual(resolve_workers(1, 6), 1)
        self.assertEqual(resolve_workers(6, 6), 6)

    def test_isolated_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            camp = Campaign(Path(tmp)/"camp", workers=2, estimated_per_job_mb=20)
            for rpm in [3000,3500]:
                camp.add_job(Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm, "sleep": 0.02}))
            res = camp.run()
            self.assertEqual(res.passed, 2)
            # cada job tiene su directorio
            for rpm in [3000,3500]:
                p = Path(tmp)/"camp"/"jobs"/f"RPM_{rpm}"/"result.json"
                self.assertTrue(p.exists())
                data = json.loads(p.read_text())
                self.assertEqual(data["result"]["rpm"], rpm)
            # no hay archivo común con escrituras concurrentes
            self.assertTrue((Path(tmp)/"camp"/"campaign_summary.json").exists())

    def test_determinism_and_equivalence(self):
        rpms = [3000,3500,4000]
        # workers=1
        with tempfile.TemporaryDirectory() as tmp1:
            c1 = Campaign(Path(tmp1)/"c1", workers=1, estimated_per_job_mb=20)
            for rpm in rpms:
                c1.add_job(Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm}))
            r1 = c1.run()
            results1 = {j.job_id: json.loads((Path(tmp1)/"c1"/"jobs"/j.job_id/"result.json").read_text())["result"] for j in c1.jobs}
        with tempfile.TemporaryDirectory() as tmp2:
            c2 = Campaign(Path(tmp2)/"c2", workers=3, estimated_per_job_mb=20)
            for rpm in rpms:
                c2.add_job(Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm}))
            r2 = c2.run()
            results2 = {j.job_id: json.loads((Path(tmp2)/"c2"/"jobs"/j.job_id/"result.json").read_text())["result"] for j in c2.jobs}
        self.assertEqual(results1, results2)
        # job_id determinista
        self.assertEqual(sorted(results1.keys()), ["RPM_3000","RPM_3500","RPM_4000"])

    def test_cancellation_preserves_completed(self):
        with tempfile.TemporaryDirectory() as tmp:
            camp = Campaign(Path(tmp)/"camp", workers=2, estimated_per_job_mb=20)
            for rpm in [3000,3500,4000]:
                camp.add_job(Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm, "sleep": 0.05}))
            # Simular cancel_pending antes de run
            camp.cancel_pending()
            self.assertTrue(all(j.status=="CANCELLED" for j in camp.jobs))
            # Ahora run con jobs ya cancelados no debe ejecutarlos (se quedan CANCELLED)
            # Para test de cancel_all durante run, usamos un camp con jobs y cancelamos a mitad
            # Simplificado: verificar que cancel_pending no afecta jobs ya completados en un run previo
            camp2 = Campaign(Path(tmp)/"camp2", workers=2, estimated_per_job_mb=20)
            for rpm in [3000,3500]:
                camp2.add_job(Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm, "sleep": 0.02}))
            res = camp2.run()
            self.assertEqual(res.passed, 2)
            # Ahora añadir un nuevo job pending y cancelarlo
            camp2.add_job(Job(job_id="RPM_4000", func=job_compute, kwargs={"rpm": 4000}))
            # El nuevo job está PENDING, cancelarlo
            camp2.cancel_pending()
            self.assertEqual(camp2.jobs[-1].status, "CANCELLED")
            # Los completados siguen PASS
            self.assertEqual(camp2.jobs[0].status, "PASS")

    def test_failure_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            camp = Campaign(Path(tmp)/"camp", workers=2, estimated_per_job_mb=20)
            camp.add_job(Job(job_id="RPM_3000", func=job_compute, kwargs={"rpm": 3000}))
            camp.add_job(Job(job_id="RPM_3500", func=job_fail))
            camp.add_job(Job(job_id="RPM_4000", func=job_compute, kwargs={"rpm": 4000}))
            res = camp.run()
            # 2 pass, 1 failed, no pérdida de los pass
            self.assertEqual(res.passed, 2)
            self.assertEqual(res.failed, 1)
            self.assertTrue((Path(tmp)/"camp"/"jobs"/"RPM_3000"/"result.json").exists())
            self.assertTrue((Path(tmp)/"camp"/"jobs"/"RPM_4000"/"result.json").exists())

    def test_memory_guard(self):
        ok, msg = can_launch_workers(1, 100)
        self.assertTrue(ok)
        ok2, msg2 = can_launch_workers(100, 5000)
        self.assertFalse(ok2)

    def test_warm_start_chains(self):
        rpms = [3000,3500,4000,4500,5000,5500,6000,6500,7000,7500,8000,8500]
        chains = build_rpm_chains(rpms, 3)
        self.assertEqual(chains, [[3000,3500,4000,4500],[5000,5500,6000,6500],[7000,7500,8000,8500]])
        # Ejecutar chains
        with tempfile.TemporaryDirectory() as tmp:
            camp = Campaign(Path(tmp)/"camp", workers=3, estimated_per_job_mb=20)
            for idx, chain_rpms in enumerate(chains):
                chain = [Job(job_id=f"RPM_{rpm}", func=job_compute, kwargs={"rpm": rpm}, chain_id=f"chain_{idx}", job_type="DEPENDENT_CHAIN") for rpm in chain_rpms]
                camp.add_chain(chain, chain_id=f"chain_{idx}")
            res = camp.run()
            self.assertEqual(res.passed, 12)
            # Verificar que cada chain se ejecutó secuencialmente (no hay paralelismo dentro de chain)
            # Cada job de una chain debe tener el mismo worker_id (porque chain se ejecuta en un worker)
            # Revisar que jobs de chain_0 tienen mismo worker_id
            chain0_workers = set(j.worker_id for j in camp.jobs if j.chain_id=="chain_0")
            self.assertEqual(len(chain0_workers), 1)

    def test_rpm_sweeps_proximity(self):
        # Verificar que chains preservan proximidad y son comparables a secuencial
        rpms = list(range(3000, 9000, 500))
        chains = build_rpm_chains(rpms, 3)
        # Cada chain debe ser contigua y ordenada
        flat = [rpm for chain in chains for rpm in chain]
        self.assertEqual(flat, sorted(rpms))
        # Cada chain interna ordenada
        for chain in chains:
            self.assertEqual(chain, sorted(chain))

    def test_no_solver_threads(self):
        # Verificar que exhaust_numba sigue con parallel=False
        import motorsim.exhaust_numba as nb
        self.assertFalse(nb.faces.targetoptions["parallel"])
        self.assertFalse(nb.fused_interior.targetoptions["parallel"])
        self.assertFalse(nb.fused_interior.targetoptions["fastmath"])

if __name__ == "__main__":
    unittest.main()
