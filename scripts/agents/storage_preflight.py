"""CLI wrapper for the shared MotorSim storage preflight implementation."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from motorsim.storage_preflight import (
    GIB, InsufficientStorageError, check_storage_requirements,
    default_artifact_root, default_reserve_bytes,
)


def _parse_requirement(value: str) -> tuple[Path, int]:
    try:
        raw_path, raw_gib = value.rsplit("=", 1)
        estimate = float(raw_gib)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use PATH=GiB, for example C:/artifacts=9") from exc
    if not raw_path or not math.isfinite(estimate) or estimate < 0:
        raise argparse.ArgumentTypeError("path must be nonempty and GiB nonnegative")
    return Path(raw_path), int(estimate * GIB)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-gib", action="append", type=_parse_requirement,
                        required=True, metavar="PATH=GiB",
                        help="estimated write volume; repeat for distinct roots")
    parser.add_argument("--reserve-gib", type=float, default=None,
                        help="minimum free-space reserve per volume (default: 2 GiB or DINO_STORAGE_RESERVE_GIB)")
    args = parser.parse_args(argv)
    try:
        reserve = (default_reserve_bytes() if args.reserve_gib is None
                   else int(args.reserve_gib * GIB))
        report = check_storage_requirements(args.require_gib, reserve_bytes=reserve)
    except InsufficientStorageError as exc:
        print(json.dumps(exc.report, ensure_ascii=False, indent=2))
        return 2
    except (OSError, ValueError) as exc:
        print(f"storage preflight error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
