"""Fail-closed disk-space checks for package builds and RPM campaigns.

No directory is created by this module. Callers must run the check before the
first write to their output or work roots.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
from typing import Iterable

GIB = 1024 ** 3


class InsufficientStorageError(RuntimeError):
    """Raised before work starts when a target volume lacks safe headroom."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(json.dumps(report, ensure_ascii=False, sort_keys=True))


def default_artifact_root() -> Path:
    """Use an explicit artifact root, otherwise a user-owned home directory."""
    configured = os.environ.get("DINO_ARTIFACT_ROOT")
    return Path(configured).expanduser() if configured else Path.home() / "Dino-artifacts"


def default_reserve_bytes() -> int:
    raw = os.environ.get("DINO_STORAGE_RESERVE_GIB", "2")
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError("DINO_STORAGE_RESERVE_GIB must be a nonnegative number") from exc
    if not math.isfinite(value) or value < 0:
        raise ValueError("DINO_STORAGE_RESERVE_GIB must be a nonnegative number")
    return int(value * GIB)


def _existing_probe_path(path: Path) -> Path:
    candidate = path.expanduser().resolve(strict=False)
    while not candidate.exists():
        parent = candidate.parent
        if parent == candidate:
            raise FileNotFoundError(f"cannot locate existing volume for storage target: {path}")
        candidate = parent
    return candidate if candidate.is_dir() else candidate.parent


def _volume_key(path: Path) -> str:
    if os.name == "nt":
        return path.anchor.casefold()
    return str(os.stat(path).st_dev)


def check_storage_requirements(
    requirements: Iterable[tuple[str | Path, int]],
    *, reserve_bytes: int | None = None,
) -> dict:
    """Check aggregated estimated writes by volume, without making directories.

    ``requirements`` contains (target root, estimated bytes written there).
    Requirements on the same volume are summed, then a single safety reserve
    is added. This avoids requiring the reserve twice when work and output are
    on one disk.
    """
    reserve = default_reserve_bytes() if reserve_bytes is None else int(reserve_bytes)
    if reserve < 0:
        raise ValueError("reserve_bytes must be nonnegative")
    volumes: dict[str, dict] = {}
    targets = []
    for target_value, estimate_value in requirements:
        target = Path(target_value).expanduser().resolve(strict=False)
        estimate = int(estimate_value)
        if estimate < 0:
            raise ValueError("estimated write bytes must be nonnegative")
        probe = _existing_probe_path(target)
        key = _volume_key(probe)
        usage = shutil.disk_usage(probe)
        volume = volumes.setdefault(key, {
            "volume": target.anchor or str(probe),
            "free_bytes": int(usage.free),
            "reserve_bytes": reserve,
            "estimated_write_bytes": 0,
            "targets": [],
        })
        volume["estimated_write_bytes"] += estimate
        volume["targets"].append({"path": str(target), "estimated_write_bytes": estimate})
        targets.append(str(target))

    for volume in volumes.values():
        volume["required_free_bytes"] = (
            volume["estimated_write_bytes"] + volume["reserve_bytes"]
        )
        volume["headroom_after_estimate_bytes"] = (
            volume["free_bytes"] - volume["estimated_write_bytes"]
        )
        volume["status"] = (
            "PASS" if volume["free_bytes"] >= volume["required_free_bytes"]
            else "BLOCKED_INSUFFICIENT_SPACE"
        )
    report = {
        "schema": "DINO_STORAGE_PREFLIGHT_V1",
        "status": "PASS" if all(v["status"] == "PASS" for v in volumes.values()) else
                  "BLOCKED_INSUFFICIENT_SPACE",
        "targets": targets,
        "volumes": list(volumes.values()),
    }
    if report["status"] != "PASS":
        raise InsufficientStorageError(report)
    return report


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
