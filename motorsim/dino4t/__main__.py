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
    from .verification import run_suite
    report = run_suite(args.out, quick=args.quick)
    print(json.dumps({"passed": report["passed"], "failed": report["failed"]}, indent=2))
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
