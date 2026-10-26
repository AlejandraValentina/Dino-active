"""Bounded three-cycle Python-vs-Numba HLLC prototype for IntegratedEngine2T.

This diagnostic monkey-patches only the module-local HLLC callable. The product
path and default Python implementation remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=("python", "numba"), required=True)
    args = parser.parse_args()

    config = args.config.resolve()
    output = args.output.resolve()
    source_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(source_root))
    native = json.loads(config.read_text(encoding="utf-8"))
    if native.get("reference_rpm") != 9000:
        raise ValueError("V4 bounded diagnostic is restricted to existing 9000 RPM config")

    import motorsim.integrated_2t as integrated
    from motorsim.gas1d.eos import IdealGas, InvalidState
    from motorsim.gas1d.riemann import hllc_flux as reference_hllc
    compile_s = 0.0
    if args.backend == "numba":
        import numpy as np
        from motorsim.exhaust_numba import hllc_flux as compiled_hllc

        reason_names = {
            1: "degenerate_contact_denominator",
            2: "unordered_wave_speeds",
            3: "degenerate_star_denominator",
            4: "inadmissible_star",
        }

        def accelerated_hllc(left, right, eos):
            try:
                flux, waves, reason_code = compiled_hllc(
                    np.asarray(left, dtype=np.float64),
                    np.asarray(right, dtype=np.float64), eos.gamma, eos.R)
            except ValueError as exc:
                raise InvalidState(str(exc)) from exc
            reason = reason_names.get(int(reason_code))
            # The existing Numba prototype uses SM=0 on some fallback paths;
            # preserve the Python reference's undefined-contact marker.
            sm = float(waves[1])
            if reason and (not (float(waves[0]) < sm < float(waves[2]))):
                sm = None
            return tuple(float(x) for x in flux), (
                float(waves[0]), sm, float(waves[2])), reason

        # Separate first JIT compilation from steady simulation timing.
        left = np.asarray((1.18, 22.0, 101800.0, 0.96), dtype=np.float64)
        right = np.asarray((1.05, -4.0, 99500.0, 0.89), dtype=np.float64)
        started = time.perf_counter()
        compiled_hllc(left, right, IdealGas().gamma, IdealGas().R)
        compile_s = time.perf_counter() - started
        expected = reference_hllc(tuple(left), tuple(right), IdealGas())
        actual = accelerated_hllc(tuple(left), tuple(right), IdealGas())
        if actual != expected:
            raise AssertionError(f"HLLC smoke equivalence failed: {actual!r} != {expected!r}")
        integrated.hllc_flux = accelerated_hllc

    from motorsim import engineering_point as point
    limits = point.parser().parse_args([
        "--config", str(config), "--output", str(output), "--rpm", "9000",
        "--max-cycles", "3", "--wall-seconds", "180", "--memory-mib", "512",
        "--mechanical-loss", "standard-v1",
    ])
    start_wall, start_cpu = time.perf_counter(), time.process_time()
    code = point.run(limits)
    wall_s = time.perf_counter() - start_wall
    cpu_s = time.process_time() - start_cpu
    if code:
        raise RuntimeError("bounded point failed; preserve artifacts for diagnosis")
    manifest_path = output / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("cycles_completed") != 3 or manifest.get("failure"):
        raise RuntimeError("diagnostic did not complete exactly three cycles")
    report = {
        "schema": "DINO_INTEGRATED_NUMBA_V4_PILOT",
        "backend": args.backend,
        "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "compile_initial_s": compile_s,
        "wall_s_excluding_compile": wall_s,
        "wall_s_including_compile": wall_s + compile_s,
        "cpu_s": cpu_s,
        "solver_step_wall_s": manifest["solver_step_wall_s"],
        "cycles_completed": manifest["cycles_completed"],
        "status": manifest["status"],
        "peak_rss_mib": manifest["peak_rss_mib"],
        "final_conservation": manifest["final_conservation"],
        "cycle_diagnostics_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.glob("cycle-*-diagnostics.json"))
        },
        "checkpoint_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(output.glob("checkpoint-next-*.json"))
        },
    }
    output.joinpath("v4-benchmark.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "backend", "compile_initial_s", "wall_s_excluding_compile",
        "wall_s_including_compile", "solver_step_wall_s", "cycles_completed",
        "peak_rss_mib", "status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
