"""MULTICORE_EXECUTION_V1 — scheduler paralelo a nivel de trabajo.

Fase A: solo dev_orchestrator, sin UI. Usa ProcessPoolExecutor, aislamiento
científico, evidencia aislada, cancelación, memory guard y warm-start chains.
No activa parallel=True en Numba ni comparte arrays.
"""
import os
import time
import hashlib
import json
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, List, Dict, Optional, Tuple
try:
    import psutil  # type: ignore
except ImportError:
    psutil = None  # type: ignore

# --------------------------------------------------------------------
# 4. Detección automática — política contractual
# --------------------------------------------------------------------
def detect_physical_cores() -> int:
    """Intenta detectar físicos; fallback conservador."""
    if psutil is not None:
        try:
            phys = psutil.cpu_count(logical=False)
            if phys and phys > 0:
                return int(phys)
        except Exception:
            pass
    # fallback: logical //2 si hyperthreading, else logical
    logical = os.cpu_count() or 4
    # heurística: si logical es par y >2, asumir 2x hyperthreading
    if logical % 2 == 0 and logical > 2:
        est = logical // 2
        # para i5-10400: 12//2=6 correcto
        return est
    return logical

def suggest_workers(physical_cores: int) -> int:
    if physical_cores <= 2:
        return 1
    if 3 <= physical_cores <= 4:
        return 2
    if 5 <= physical_cores <= 6:
        return 3
    if 7 <= physical_cores <= 8:
        return 4
    if 9 <= physical_cores <= 12:
        return 6
    return min(8, physical_cores // 2)

def resolve_workers(workers: Any, physical: Optional[int] = None) -> int:
    """workers: 'auto'|'Automatic'|None → auto, int → manual 1..N."""
    if workers in (None, "auto", "Auto", "Automatic", "AUTOMATIC"):
        phys = physical if physical is not None else detect_physical_cores()
        return suggest_workers(phys)
    try:
        w = int(workers)
        if w < 1:
            return 1
        # limitar a físico razonable, pero permitir manual hasta físico
        phys = physical if physical is not None else detect_physical_cores()
        # para i5-10400: permitir 1..6 aunque auto sea 3
        return max(1, min(w, 64))
    except Exception:
        return suggest_workers(detect_physical_cores())

# --------------------------------------------------------------------
# 11. Memory guard
# --------------------------------------------------------------------
def system_memory_mb() -> Tuple[float, float]:
    """Retorna (total_mb, available_mb)."""
    if psutil is not None:
        try:
            vm = psutil.virtual_memory()
            return vm.total / (1024*1024), vm.available / (1024*1024)
        except Exception:
            pass
    # fallback sin psutil: asumir 20GB total, 10GB available
    return 20*1024, 10*1024

def can_launch_workers(worker_count: int, estimated_per_job_mb: float, reserve_percent: float = 25.0) -> Tuple[bool, str]:
    total, available = system_memory_mb()
    reserve_mb = total * reserve_percent / 100.0
    needed = worker_count * estimated_per_job_mb
    # available debe cubrir needed + reserva? Política conservadora: needed + reserve ≤ total
    if needed + reserve_mb > total:
        return False, f"needed {needed:.0f}MB + reserve {reserve_mb:.0f}MB > total {total:.0f}MB"
    if needed > available:
        return False, f"needed {needed:.0f}MB > available {available:.0f}MB"
    return True, "ok"

# --------------------------------------------------------------------
# 7. Determinismo — Job
# --------------------------------------------------------------------
@dataclass
class Job:
    job_id: str
    func: Callable[..., Any]  # será serializable via pickle (top-level)
    args: Tuple[Any, ...] = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    job_type: str = "INDEPENDENT"  # o DEPENDENT_CHAIN
    chain_id: Optional[str] = None
    estimated_memory_mb: float = 500.0
    config_hash: str = ""
    input_hash: str = ""
    backend: str = "unknown"
    # resultados (llenados por scheduler)
    status: str = "PENDING"
    worker_id: Optional[int] = None
    start_ts: Optional[float] = None
    end_ts: Optional[float] = None
    runtime: Optional[float] = None
    result: Any = None
    error: Optional[str] = None

    def deterministic_id(self) -> str:
        return self.job_id

def hash_config(obj: Any) -> str:
    try:
        s = json.dumps(obj, sort_keys=True, default=str)
        return hashlib.sha256(s.encode()).hexdigest()[:12]
    except Exception:
        return hashlib.sha256(str(obj).encode()).hexdigest()[:12]

# --------------------------------------------------------------------
# Helpers para ejecución en proceso hijo
# --------------------------------------------------------------------
def _job_wrapper(job_dict: Dict[str, Any], campaign_dir: str, worker_id: int) -> Dict[str, Any]:
    """Ejecuta un Job en proceso aislado, escribe evidencia aislada."""
    import os
    # P4-PERF-01 oversubscription audit: limit BLAS/OMP threads to 1 per worker for predictability
    for _var in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMBA_NUM_THREADS"):
        os.environ[_var] = "1"
    import time, traceback, json, hashlib
    from pathlib import Path
    job_id = job_dict["job_id"]
    # reconstruir job
    # func se pasa como importable: "module.func"
    func_path = job_dict["func_path"]
    module_name, func_name = func_path.rsplit(".", 1)
    mod = __import__(module_name, fromlist=[func_name])
    func = getattr(mod, func_name)
    args = job_dict["args"]
    kwargs = job_dict["kwargs"]
    job_dir = Path(campaign_dir) / "jobs" / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    start_ts = time.time()
    status = "PASS"
    result = None
    error = None
    try:
        # Cada worker ve su propio job_dir
        result = func(job_id=job_id, job_dir=str(job_dir), worker_id=worker_id, *args, **kwargs)
    except Exception as e:
        status = "FAILED"
        error = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        result = None
    end = time.perf_counter()
    end_ts = time.time()
    runtime = end - start
    # escribir evidencia aislada
    meta = {
        "job_id": job_id,
        "worker_id": worker_id,
        "func": func_path,
        "status": status,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "runtime": runtime,
        "error": error,
        "config_hash": job_dict.get("config_hash",""),
        "input_hash": job_dict.get("input_hash",""),
        "backend": job_dict.get("backend",""),
    }
    # resultado científico (lo que devuelva func) se guarda separado
    try:
        (job_dir / "result.json").write_text(json.dumps({"result": result, "meta": meta}, indent=2), encoding="utf-8")
        (job_dir / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    except Exception as e:
        status = "FAILED"
        error = (error or "") + f"\nwrite error: {e}"
    return {"job_id": job_id, "status": status, "runtime": runtime, "worker_id": worker_id, "start_ts": start_ts, "end_ts": end_ts, "error": error, "result": result, "meta": meta}

# --------------------------------------------------------------------
# Campaign
# --------------------------------------------------------------------
@dataclass
class CampaignResult:
    campaign_dir: Path
    worker_count: int
    jobs: List[Job]
    wall_seconds: float
    sequential_estimated_seconds: float
    speedup: float
    efficiency: float
    # estados
    passed: int
    failed: int
    cancelled: int
    blocked: int

class Campaign:
    def __init__(self, campaign_dir: Path, workers: Any = "auto", estimated_per_job_mb: float = 500.0, reserve_percent: float = 25.0):
        self.campaign_dir = Path(campaign_dir)
        self.campaign_dir.mkdir(parents=True, exist_ok=True)
        (self.campaign_dir / "jobs").mkdir(parents=True, exist_ok=True)
        self.workers_param = workers
        self.estimated_per_job_mb = estimated_per_job_mb
        self.reserve_percent = reserve_percent
        self.jobs: List[Job] = []
        self.workers = resolve_workers(workers)
        self._futures: Dict[str, Future] = {}
        self._executor: Optional[ProcessPoolExecutor] = None

    def add_job(self, job: Job):
        # asegurar ID determinista único
        if any(j.job_id == job.job_id for j in self.jobs):
            raise ValueError(f"job_id duplicado: {job.job_id}")
        self.jobs.append(job)

    def add_jobs(self, jobs: List[Job]):
        for j in jobs:
            self.add_job(j)

    def add_chain(self, chain: List[Job], chain_id: str):
        """Chain secuencial internamente, chains en paralelo."""
        for idx, job in enumerate(chain):
            job.job_type = "DEPENDENT_CHAIN"
            job.chain_id = chain_id
            # Para warm-start, el siguiente job depende del anterior; lo modelamos como chain_id + orden
            # El scheduler ejecutará la chain completa en un solo worker como una unidad
            self.jobs.append(job)
        # Marcar chain: en realidad vamos a agrupar por chain_id para ejecución
        # Para simplificar, el scheduler tratará cada chain como un único Job que ejecuta la secuencia
        # Pero para mantener granularidad, guardamos chain_id

    def _check_memory(self) -> Tuple[bool, str]:
        return can_launch_workers(self.workers, self.estimated_per_job_mb, self.reserve_percent)

    def run(self, timeout: Optional[float] = None) -> CampaignResult:
        # memory guard
        ok, msg = self._check_memory()
        if not ok:
            # No lanzar, marcar todos como BLOCKED por memoria
            for j in self.jobs:
                j.status = "BLOCKED"
                j.error = f"memory guard: {msg}"
            return self._finalize(0.0)

        # Determinar si hay chains
        # Agrupar por chain_id: cada chain se ejecuta como una unidad secuencial en un worker
        # Para INDEPENDENT, cada job es independiente
        # Para DEPENDENT_CHAIN, agrupamos
        groups: Dict[str, List[Job]] = {}
        independent: List[Job] = []
        for j in self.jobs:
            if j.job_type == "DEPENDENT_CHAIN" and j.chain_id:
                groups.setdefault(j.chain_id, []).append(j)
            else:
                independent.append(j)

        # Construir unidades de trabajo: cada independent es una unidad, cada chain es una unidad
        units: List[Dict[str, Any]] = []
        # Para independent, cada job es una unidad
        for job in independent:
            job.status = "PENDING"
            units.append({"type": "single", "jobs": [job]})
        # Para chains, cada chain es una unidad que ejecutará sus jobs secuencialmente en el mismo worker
        for cid, chain_jobs in groups.items():
            # ordenar por job_id (determinista) o por orden de agregado
            # Asumimos orden de lista es el orden deseado (ej. RPM ascendente)
            for j in chain_jobs:
                j.status = "PENDING"
            units.append({"type": "chain", "chain_id": cid, "jobs": chain_jobs})

        # Si no hay jobs, retornar
        if not units:
            return self._finalize(0.0)

        # Preparar serialización para procesos hijos: cada job necesita func_path
        def job_to_dict(job: Job) -> Dict[str, Any]:
            # func debe ser top-level importable; guardamos como "module.qualname"
            func_path = f"{job.func.__module__}.{job.func.__qualname__}"
            return {
                "job_id": job.job_id,
                "func_path": func_path,
                "args": job.args,
                "kwargs": job.kwargs,
                "config_hash": job.config_hash,
                "input_hash": job.input_hash,
                "backend": job.backend,
            }

        wall_start = time.perf_counter()
        # Usar ProcessPoolExecutor
        # Necesitamos función wrapper para chain: ejecuta jobs secuencialmente
        def chain_wrapper(chain_dict: Dict[str, Any], campaign_dir: str, worker_id: int):
            # chain_dict contiene lista de job_dicts
            results = []
            for jd in chain_dict["jobs"]:
                # cada job dentro de la chain escribe en su propio job_dir, pero comparten worker
                # El runtime de la chain es suma, pero cada job tiene su propio meta
                res = _job_wrapper(jd, campaign_dir, worker_id)
                results.append(res)
                if res["status"] != "PASS":
                    # fallo en chain: los siguientes jobs de la chain se marcan como BLOCKED (dependencia)
                    # No ejecutamos más jobs de esta chain
                    remaining = chain_dict["jobs"][len(results):]
                    for rjd in remaining:
                        # escribir meta CANCELLED/BLOCKED para los no ejecutados
                        from pathlib import Path as _P
                        jd2 = _P(campaign_dir) / "jobs" / rjd["job_id"]
                        jd2.mkdir(parents=True, exist_ok=True)
                        meta = {"job_id": rjd["job_id"], "worker_id": worker_id, "status": "BLOCKED", "error": f"chain blocked due to previous failure {res['job_id']}"}
                        (_P(campaign_dir) / "jobs" / rjd["job_id"] / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
                        results.append({"job_id": rjd["job_id"], "status": "BLOCKED", "runtime": 0, "worker_id": worker_id, "error": "chain blocked"})
                    break
            return results

        # Para simplificar, no usamos chain_wrapper separado sino que submitimos cada unit como función que puede ser single o chain
        # Vamos a submitir units directamente: cada unit se ejecuta en un worker y dentro itera
        # Necesitamos una función top-level para pickle
        # Definimos helpers top-level para single y chain
        # Usaremos _job_wrapper para single, y _chain_wrapper para chain — deben ser top-level

        # Mapear futures a unidades
        from concurrent.futures import ProcessPoolExecutor

        # Preparar executor
        self._executor = ProcessPoolExecutor(max_workers=self.workers)
        future_to_unit = {}
        # Para cada unit, submit
        # Necesitamos identificar worker_id: ProcessPoolExecutor no expone worker_id directamente, pero _job_wrapper recibe worker_id como arg; usamos un contador incremental como worker_id lógico (0..workers-1) no es el PID real, pero suficiente para evidencia
        # En realidad, el worker_id real debería ser el PID o índice del proceso; usaremos un simple contador round-robin para trazar que cada unit va a un worker distinto
        # Para determinismo, asignamos worker_id = hash(job_id) % workers, pero para simplicidad usamos índice de submit

        # Guardar para cancelación
        all_futures: List[Future] = []

        # Función para ejecutar una unidad (single o chain) en un worker
        # Creamos dos wrappers top-level ya definidos fuera: _single_unit_wrapper y _chain_unit_wrapper
        # Pero para evitar complejidad de pickle de closures, definimos funciones top-level en este módulo

        # Submit
        for idx, unit in enumerate(units):
            worker_id = idx % self.workers
            if unit["type"] == "single":
                job = unit["jobs"][0]
                job.status = "RUNNING"
                jd = job_to_dict(job)
                fut = self._executor.submit(_job_wrapper, jd, str(self.campaign_dir), worker_id)
                future_to_unit[fut] = unit
                all_futures.append(fut)
            else:
                # chain
                chain_jobs = unit["jobs"]
                # convertir cada job a dict
                chain_dict = {"chain_id": unit["chain_id"], "jobs": [job_to_dict(j) for j in chain_jobs]}
                # marcar todos como RUNNING (aunque secuenciales, el primero corre, los demás PENDING hasta que les toque)
                for j in chain_jobs:
                    j.status = "RUNNING" if j == chain_jobs[0] else "PENDING"
                fut = self._executor.submit(_chain_wrapper, chain_dict, str(self.campaign_dir), worker_id)
                future_to_unit[fut] = unit
                all_futures.append(fut)

        # Esperar con timeout
        completed = 0
        wall_end = None
        try:
            for fut in as_completed(all_futures, timeout=timeout):
                unit = future_to_unit[fut]
                try:
                    res = fut.result()
                    # res es para single: dict, para chain: list[dict]
                    if unit["type"] == "single":
                        # actualizar Job
                        job = unit["jobs"][0]
                        job.status = res["status"]
                        job.runtime = res["runtime"]
                        job.worker_id = res["worker_id"]
                        job.start_ts = res["start_ts"]
                        job.end_ts = res["end_ts"]
                        job.error = res["error"]
                        job.result = res["result"]
                    else:
                        # chain: res es lista
                        for j, r in zip(unit["jobs"], res):
                            j.status = r["status"]
                            j.runtime = r.get("runtime", 0)
                            j.worker_id = r.get("worker_id")
                            j.start_ts = r.get("start_ts")
                            j.end_ts = r.get("end_ts")
                            j.error = r.get("error")
                            j.result = r.get("result")
                except Exception as e:
                    # fallo de infraestructura
                    if unit["type"] == "single":
                        job = unit["jobs"][0]
                        job.status = "FAILED"
                        job.error = f"executor error: {e}"
                    else:
                        for j in unit["jobs"]:
                            j.status = "FAILED"
                            j.error = f"executor error: {e}"
                completed += 1
        except Exception as e:
            # timeout o cancel
            pass
        finally:
            # shutdown
            if self._executor:
                self._executor.shutdown(wait=True, cancel_futures=False)
                self._executor = None

        wall_end = time.perf_counter()
        wall_seconds = wall_end - wall_start
        return self._finalize(wall_seconds)

    def _finalize(self, wall_seconds: float) -> CampaignResult:
        # Calcular sequential estimado como suma de runtimes de jobs PASS/FAILED (no CANCELLED/BLOCKED)
        seq = sum(j.runtime for j in self.jobs if j.runtime and j.status in ("PASS","FAILED"))
        # speedup
        speedup = seq / wall_seconds if wall_seconds > 0 else 0
        eff = speedup / self.workers if self.workers else 0
        passed = sum(1 for j in self.jobs if j.status == "PASS")
        failed = sum(1 for j in self.jobs if j.status == "FAILED")
        cancelled = sum(1 for j in self.jobs if j.status == "CANCELLED")
        blocked = sum(1 for j in self.jobs if j.status == "BLOCKED")
        # Escribir resumen de campaña (solo metadatos, no sobreescribir jobs)
        jobs_ser = []
        for j in self.jobs:
            d = asdict(j)
            # func no es JSON serializable, convertir a path
            try:
                d["func"] = f"{j.func.__module__}.{j.func.__qualname__}" if j.func else None
            except Exception:
                d["func"] = str(d.get("func"))
            jobs_ser.append(d)
        summary = {
            "campaign_dir": str(self.campaign_dir),
            "workers": self.workers,
            "workers_param": self.workers_param,
            "wall_seconds": wall_seconds,
            "sequential_estimated_seconds": seq,
            "speedup": speedup,
            "efficiency": eff,
            "jobs": jobs_ser,
            "passed": passed,
            "failed": failed,
            "cancelled": cancelled,
            "blocked": blocked,
        }
        try:
            (self.campaign_dir / "campaign_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        except Exception as e:
            # Debug: no silenciar completamente en dev
            try:
                (self.campaign_dir / "campaign_error.log").write_text(str(e), encoding="utf-8")
            except Exception:
                pass
        return CampaignResult(
            campaign_dir=self.campaign_dir,
            worker_count=self.workers,
            jobs=self.jobs,
            wall_seconds=wall_seconds,
            sequential_estimated_seconds=seq,
            speedup=speedup,
            efficiency=eff,
            passed=passed,
            failed=failed,
            cancelled=cancelled,
            blocked=blocked,
        )

    # 9. Cancelación
    def cancel_pending(self):
        # Marcar PENDING como CANCELLED, no afecta RUNNING/PASS
        for j in self.jobs:
            if j.status == "PENDING":
                j.status = "CANCELLED"
                j.error = "cancelled pending"

    def cancel_all(self):
        # Cancelar PENDING y intentar cancelar futures si existen
        self.cancel_pending()
        if self._executor:
            # no hay API directa para matar procesos hijos, pero cancel_futures en shutdown
            pass
        # Los RUNNING se dejan terminar; al finalizar se preservan

    def cancel_job(self, job_id: str):
        for j in self.jobs:
            if j.job_id == job_id and j.status in ("PENDING","RUNNING"):
                if j.status == "PENDING":
                    j.status = "CANCELLED"
                    j.error = "cancelled individual"
                # si RUNNING, no podemos matar sin perder resultado; lo dejamos terminar pero lo marcaremos como CANCELLED después si hace falta
                break

# Wrappers top-level para pickle
def _chain_wrapper(chain_dict: Dict[str, Any], campaign_dir: str, worker_id: int):
    import os
    for _var in ("OMP_NUM_THREADS","MKL_NUM_THREADS","OPENBLAS_NUM_THREADS","NUMEXPR_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMBA_NUM_THREADS"):
        os.environ[_var] = "1"
    # chain_dict: {"chain_id": str, "jobs": [job_dict,...]}
    results = []
    for jd in chain_dict["jobs"]:
        res = _job_wrapper(jd, campaign_dir, worker_id)
        results.append(res)
        if res["status"] != "PASS":
            # bloquear restantes
            remaining = chain_dict["jobs"][len(results):]
            for rjd in remaining:
                # escribir meta bloqueada
                from pathlib import Path as _P
                import json as _js
                p = _P(campaign_dir) / "jobs" / rjd["job_id"]
                p.mkdir(parents=True, exist_ok=True)
                meta = {"job_id": rjd["job_id"], "worker_id": worker_id, "status": "BLOCKED", "error": f"chain blocked due to {res['job_id']} failure"}
                (p / "meta.json").write_text(_js.dumps(meta, indent=2), encoding="utf-8")
                results.append({"job_id": rjd["job_id"], "status": "BLOCKED", "runtime": 0, "worker_id": worker_id, "error": "chain blocked", "result": None, "meta": meta})
            break
    return results

# --------------------------------------------------------------------
# 13. RPM sweeps — construcción de chains
# --------------------------------------------------------------------
def build_rpm_chains(rpms: List[int], workers: int) -> List[List[int]]:
    """Divide rpms sorted en workers chunks contiguos para warm-start."""
    rpms_sorted = sorted(rpms)
    n = len(rpms_sorted)
    if workers <= 0:
        workers = 1
    # chunk size ceil
    chunk = (n + workers - 1) // workers
    chains = []
    for i in range(0, n, chunk):
        chains.append(rpms_sorted[i:i+chunk])
        if len(chains) >= workers:
            # si sobran, distribuir resto en últimos chains (ya lo hace chunk)
            pass
    # asegurar exactamente workers chains (puede haber menos si n<workers)
    # rellenar vacíos no, solo devolver los que tienen datos
    return chains

def build_rpm_jobs(rpms: List[int], workers: int, job_func: Callable, campaign_dir: Path, **kwargs) -> List[Job]:
    """Crea jobs INDEPENDENT si no se usa warm-start, o chains si se usa."""
    # Para warm-start, usar chains
    chains = build_rpm_chains(rpms, workers)
    jobs = []
    for chain_idx, chain_rpms in enumerate(chains):
        chain_id = f"chain_{chain_idx}"
        for rpm in chain_rpms:
            job_id = f"RPM_{rpm}"
            # config hash determinista
            cfg = {"rpm": rpm, "chain": chain_id}
            jobs.append(Job(job_id=job_id, func=job_func, args=(), kwargs={"rpm": rpm, **kwargs}, job_type="DEPENDENT_CHAIN", chain_id=chain_id, config_hash=hash_config(cfg), input_hash=hash_config(rpm), backend="multicore"))
    return jobs

# --------------------------------------------------------------------
# 14. Benchmark
# --------------------------------------------------------------------
def benchmark_scheduler(job_func: Callable, rpms: List[int], campaign_base: Path, repeats: int = 1) -> Dict[str, Any]:
    """Benchmark 1-4 workers en i5-10400 con trabajos idénticos."""
    results = {}
    for w in [1,2,3,4]:
        # cada benchmark usa campaign independiente
        camp_dir = campaign_base / f"bench_{w}workers"
        camp = Campaign(camp_dir, workers=w)
        # crear jobs independientes idénticos (no warm-start para benchmark puro)
        for rpm in rpms:
            camp.add_job(Job(job_id=f"RPM_{rpm}", func=job_func, kwargs={"rpm": rpm}, estimated_memory_mb=200))
        start = time.perf_counter()
        res = camp.run()
        wall = res.wall_seconds
        # sequential estimado es suma de runtimes
        results[w] = {"wall": wall, "sequential": res.sequential_estimated_seconds, "speedup": res.speedup, "efficiency": res.efficiency, "passed": res.passed}
        print(f"workers {w}: wall {wall:.2f} seq {res.sequential_estimated_seconds:.2f} speedup {res.speedup:.2f} eff {res.efficiency:.2f}")
    # elegir AUTO por throughput total (menor wall)
    best = min(results, key=lambda k: results[k]["wall"])
    return {"benchmark": results, "best_workers": best, "suggested_auto": best}

# --------------------------------------------------------------------
# Utilidades para UI futura (solo datos, no widgets)
# --------------------------------------------------------------------
def ui_config_text(workers: Any) -> str:
    phys = detect_physical_cores()
    auto = suggest_workers(phys)
    if workers in (None, "auto", "Automatic"):
        return f"Automático ({auto})"
    return str(workers)
