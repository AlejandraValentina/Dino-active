"""Command line: ``python -m motorsim.dino4t run CONFIG --out DIR [--rpm N] [--cycles K]``
and ``python -m motorsim.dino4t verify --out DIR [--quick]``."""
from __future__ import annotations

import argparse
import json
import sys

from .config import load


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m motorsim.dino4t")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="simulate one operating point to periodicity")
    run.add_argument("config")
    run.add_argument("--out", required=True)
    run.add_argument("--rpm", type=float)
    run.add_argument("--phi", type=float, help="equivalence ratio override")
    run.add_argument("--cycles", type=int, help="maximum cycles")
    run.add_argument("--dx-mm", type=float)
    sweep = sub.add_parser("sweep", help="parameter sweep with continuation (Cartesian product of --param)")
    sweep.add_argument("config")
    sweep.add_argument("--out", required=True)
    sweep.add_argument("--param", action="append", required=True,
                       help="dotted.path=start:stop:n  or  dotted.path=v1,v2,...  (repeatable)")
    sweep.add_argument("--dx-mm", type=float)
    sweep.add_argument("--max-cycles", type=int, default=14)
    sens = sub.add_parser("sensitivity", help="local central-difference sensitivities (elasticities)")
    sens.add_argument("config")
    sens.add_argument("--out", required=True)
    sens.add_argument("--rel-step", type=float, default=0.05)
    sens.add_argument("--params", help="comma list; default all physical parameters")
    sens.add_argument("--dx-mm", type=float)
    sens.add_argument("--max-cycles", type=int, default=14)
    verify = sub.add_parser("verify", help="run the numerical verification suite")
    verify.add_argument("--out", required=True)
    verify.add_argument("--quick", action="store_true", help="skip the engine mesh-convergence study")
    args = parser.parse_args(argv)

    if args.command == "run":
        from .runner import run_operating_point
        overrides = {}
        if args.rpm is not None or args.phi is not None:
            overrides["operating_point"] = {k: v for k, v in (("rpm", args.rpm), ("equivalence_ratio", args.phi))
                                            if v is not None}
        if args.dx_mm is not None:
            overrides["numerics"] = {"dx_mm": args.dx_mm}

        def progress(record):
            print(f"cycle {record.index + 1}: W={record.work_net:.2f} J  p_max={record.p_max / 1e5:.2f} bar",
                  file=sys.stderr, flush=True)

        out = run_operating_point(load(args.config), out_dir=args.out, overrides=overrides or None,
                                  max_cycles=args.cycles, progress=progress)
        s = out["summary"]
        f = s["final_cycle"] or {}
        print(json.dumps({"status": s["status"], "periodicity": s["periodicity"]["status"],
                          "cycles": s["cycles_run"], "imep_net_bar": f.get("imep_net_bar"),
                          "bmep_bar": f.get("bmep_bar"), "brake_power_kW": f.get("brake_power_kW"),
                          "volumetric_efficiency": f.get("volumetric_efficiency_intake_valve"),
                          "max_closure": s["conservation"]["max_relative_closure"],
                          "claims": s["claims"]}, indent=2))
        return 0 if s["status"] == "completed" else 1
    if args.command == "sweep":
        import itertools
        from . import studies
        axes = []
        for spec in args.param:
            path, values = spec.split("=", 1)
            if ":" in values:
                a, b, n = values.split(":")
                axes.append([(path, p[path]) for p in studies.linspace_points(path, float(a), float(b), int(n))])
            else:
                axes.append([(path, float(x)) for x in values.split(",")])
        points = [dict(combo) for combo in itertools.product(*axes)]
        base = {"numerics": {"dx_mm": args.dx_mm}} if args.dx_mm else None
        rows = studies.sweep(load(args.config), points, out_dir=args.out, max_cycles=args.max_cycles, base_overrides=base,
                             progress=lambda r: print(json.dumps({k: r[k] for k in ("overrides", "status", "cycles", "imep_net_bar",
                                                    "volumetric_efficiency_intake_valve")}, default=float), file=sys.stderr, flush=True))
        return 0 if all(r["status"] == "completed" for r in rows) else 1
    if args.command == "sensitivity":
        from . import studies
        base = {"numerics": {"dx_mm": args.dx_mm}} if args.dx_mm else None
        res = studies.sensitivity(load(args.config), parameters=args.params.split(",") if args.params else None,
                                  rel_step=args.rel_step, max_cycles=args.max_cycles, out_dir=args.out, base_overrides=base,
                                  progress=lambda n, e: print(n, file=sys.stderr, flush=True))
        print(json.dumps({"parameters": list(res["parameters"])}, indent=1))
        return 0
    from .verification import run_suite
    report = run_suite(args.out, quick=args.quick)
    print(json.dumps({"passed": report["passed"], "failed": report["failed"]}, indent=2))
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
