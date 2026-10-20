"""ISV1 A3b -- preregistered CFL/spatial sensitivity matrix driver.

The protocol is frozen in
``results/integrated-solver-verification-v1/a3b-preregistration-v2.json``.
This driver implements the matrix *without executing it*: real runs require a
separate owner execution confirmation and an ``a3b-execution-addendum.json``
that binds this driver's SHA-256.

Subcommands
-----------
``preflight``   Build every configured mesh/CFL level and run the zero-solver-
                step preflight.  No budget is consumed.
``run-config``  Run one config invocation.  Requires the frozen protocol, the
                execution addendum, an owner authorization file and the global
                run lock.  Uses a shared checkpoint and a durable time ledger.
``freeze-atol`` Derive the numeric ``atol_obs`` table from T1-A after that
                config is complete.  Writes ``a3b-analysis-freeze.json`` once.
``analyze``     Produce the per-observable sensitivity table and bounded
                statement.  Refuses to compare before the freeze exists.
``addendum``    Write the execution addendum after tests/preflight, binding the
                current LF-normalized driver SHA-256.

The driver never edits ``motorsim/``.  It imports the same primitives used by
the exploratory workflow and the A3a profile driver.
"""
from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import math
import os
import shutil
import statistics
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.engine_configuration import (
    resolve_for_operating_point,
    sha256 as engine_configuration_sha256,
)
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration
from motorsim.exploratory_workflow import (
    MAX_RUN_ARTIFACT_BYTES,
    RunCancelled,
    RunDeadline,
    _advance_cycle,
    _atomic_write,
    _json_bytes,
    _periodicity_source_sha256,
    _prepare_engineering_output_record,
    _rss_bytes,
    _sha,
    preflight,
)
from motorsim.integrated_2t import (
    IntegratedEngine2T,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
    make_integrated_engineering_output,
)
from motorsim.mechanical import MechanicalLossModel
from motorsim.reference_harness.convergence import (
    CONTRACT as CYCLE_PRIMARY_CONTRACT,
    CONTRACT_V2 as PERIODICITY_CONTRACT_V2,
    THRESHOLDS as PERIODICITY_THRESHOLDS_V2,
    PeriodicDetectorV2,
)
from motorsim import exploratory_workflow as exploratory_workflow_module

PROTOCOL = ROOT / "results/integrated-solver-verification-v1/a3b-preregistration-v2.json"
ADDENDUM = ROOT / "results/integrated-solver-verification-v1/a3b-execution-addendum.json"
ANALYSIS_FREEZE = ROOT / "results/integrated-solver-verification-v1/a3b-analysis-freeze.json"
REPORT = ROOT / "results/integrated-solver-verification-v1/a3b-sensitivity-report.json"
RECEIPT = ROOT / "results/integrated-solver-verification-v1/a3b-analysis-receipt.json"
PROJECT = ROOT / "examples/projects/dino-2t-exhaust-comparison.dino2t.json"
VARIANT = "Escape original"
RPM = 3000
MAX_CYCLES = 3
MEMORY_LIMIT_MIB = 3072
PREFLIGHT_BUDGET_SECONDS = 600
PER_INVOCATION_CAP_SECONDS = 600.0
INTERNAL_INVOCATION_DEADLINE_SECONDS = 595.0
GLOBAL_CAP_SECONDS = 4320.0
PROTOCOL_SHA256 = "c8ab07daeeccfaf00ee27c0bedbd4ddb25334384438b29e875d8ac04827c45ed"

RUN_SCHEMA = "DINO_ISV1_A3B_RUN_V1"
INVOCATION_SCHEMA = "DINO_ISV1_A3B_INVOCATION_V1"
CHECKPOINT_SCHEMA = "DINO_ISV1_A3B_CHECKPOINT_V1"
PREFLIGHT_SCHEMA = "DINO_ISV1_A3B_PREFLIGHT_V1"
RESULT_SCHEMA = "DINO_ISV1_A3B_CONFIG_RESULT_V1"
LEDGER_SCHEMA = "DINO_ISV1_A3B_BUDGET_LEDGER_V1"
FREEZE_SCHEMA = "DINO_ISV1_A3B_ANALYSIS_FREEZE_V1"
REPORT_SCHEMA = "DINO_ISV1_A3B_SENSITIVITY_REPORT_V1"
RECEIPT_SCHEMA = "DINO_ISV1_A3B_ANALYSIS_RECEIPT_V1"
ADDENDUM_SCHEMA = "DINO_ISV1_A3B_EXECUTION_ADDENDUM_V1"

CONFIG_SPECS: dict[str, dict[str, Any]] = {
    "T1-A": {"cells": 48, "per_section": 8, "max_cfl": 0.4, "cap_seconds": 525.0,
             "role": "temporal_base", "linear_seconds_per_cycle": 144.55},
    "T1-B": {"cells": 48, "per_section": 8, "max_cfl": 0.2, "cap_seconds": 1050.0,
             "role": "temporal_mid", "linear_seconds_per_cycle": 289.10},
    "T1-C": {"cells": 48, "per_section": 8, "max_cfl": 0.1, "cap_seconds": 2100.0,
             "role": "temporal_fine", "linear_seconds_per_cycle": 578.20},
    "T1-D": {"cells": 28, "per_section": 4, "max_cfl": 0.4, "cap_seconds": 310.0,
             "role": "spatial_mid", "linear_seconds_per_cycle": 84.32},
    "T1-E": {"cells": 18, "per_section": 2, "max_cfl": 0.4, "cap_seconds": 210.0,
             "role": "spatial_coarse", "linear_seconds_per_cycle": 54.21},
}
INVOCATION_PLAN: dict[str, list[int]] = {
    "T1-A": [3], "T1-B": [2, 1], "T1-C": [1, 1, 1],
    "T1-D": [3], "T1-E": [3],
}
OBSERVABLES = (
    "indicated_power_w",
    "indicated_torque_nm",
    "imep_pa",
    "brake_work_j",
    "brake_power_w",
    "brake_torque_nm",
    "bmep_pa",
    "fmep_pa",
    "net_piston_mep_pa",
    "crankcase_gas_work_J",
    "crankcase.mass_kg",
)
WORK_FLOOR_J = 5e-12
MASS_FLOOR_KG = 1.2891841457210451e-18
TIMER_KEYS = (
    "integration_physical_seconds",
    "audit_reconstruction_make_seconds",
    "audit_reconstruction_audit_seconds",
    "serialization_io_seconds",
    "state_snapshot_orchestration_seconds",
    "engineering_output_seconds",
    "periodicity_detector_seconds",
    "dispatch_overhead_seconds",
)


class Refused(RuntimeError):
    """A precondition refused the operation before a run started."""


class BudgetExhausted(RuntimeError):
    """The durable time ledger would exceed a cap."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _display_path(path: Path) -> str:
    candidate = Path(path).resolve()
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return str(candidate)


def _file_sha(path: Path) -> str:
    """SHA-256 with CRLF normalized to LF (stage1 convention)."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _file_sha_raw(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    if not Path(path).is_file():
        raise Refused(f"required file is missing: {path}")
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Refused(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise Refused(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: Any) -> None:
    _atomic_write(Path(path), _json_bytes(value))


def _load_protocol() -> dict[str, Any]:
    if not PROTOCOL.is_file():
        raise Refused(f"frozen protocol is missing: {PROTOCOL}")
    actual = _file_sha_raw(PROTOCOL)
    if actual != PROTOCOL_SHA256:
        raise Refused(
            f"protocol SHA-256 mismatch: expected {PROTOCOL_SHA256}, found {actual}")
    protocol = _load_json(PROTOCOL)
    if protocol.get("status") != "FROZEN_PROTOCOL_EXECUTION_NOT_AUTHORIZED":
        raise Refused(f"unexpected protocol status: {protocol.get('status')!r}")
    configs = protocol.get("scope", {}).get("configuration_set", [])
    ids = [row.get("id") for row in configs if isinstance(row, dict)]
    if ids != list(CONFIG_SPECS):
        raise Refused(f"protocol configuration order/ids changed: {ids!r}")
    for row in configs:
        spec = CONFIG_SPECS[row["id"]]
        try:
            cells = int(row["cells"])
            max_cfl = float(row["max_cfl"])
            cap_seconds = float(row["cost_cap_seconds"])
        except (KeyError, TypeError, ValueError) as exc:
            raise Refused(f"protocol configuration row is incomplete: {row!r}") from exc
        if (cells != int(spec["cells"]) or max_cfl != float(spec["max_cfl"])
                or cap_seconds != float(spec["cap_seconds"])):
            raise Refused(
                f"protocol configuration {row['id']} does not match the driver: "
                f"cells={cells}/{spec['cells']}, max_cfl={max_cfl}/{spec['max_cfl']}, "
                f"cap={cap_seconds}/{spec['cap_seconds']}")
    budget = protocol.get("budget", {})
    try:
        hard_cap = float(budget["hard_cap_seconds"])
        invocation_cap = float(budget["per_invocation_cap_seconds"])
        memory_mib = int(budget["per_process_memory_limit_mib"])
        protocol_caps = {
            str(key): float(value)
            for key, value in budget["per_configuration_caps_seconds"].items()}
        protocol_plan = {
            str(row["id"]): (int(row["invocations"]),
                             [int(value) for value in row["cycles_per_invocation"]])
            for row in budget["invocation_plan"]}
    except (KeyError, TypeError, ValueError) as exc:
        raise Refused("protocol budget block is incomplete") from exc
    if hard_cap != GLOBAL_CAP_SECONDS:
        raise Refused(f"protocol hard cap changed: {hard_cap}")
    if invocation_cap != PER_INVOCATION_CAP_SECONDS:
        raise Refused(f"protocol invocation cap changed: {invocation_cap}")
    if memory_mib != MEMORY_LIMIT_MIB:
        raise Refused(f"protocol memory limit changed: {memory_mib}")
    driver_caps = {key: float(spec["cap_seconds"])
                   for key, spec in CONFIG_SPECS.items()}
    if protocol_caps != driver_caps:
        raise Refused(f"protocol per-config caps changed: {protocol_caps!r}")
    driver_plan = {key: (len(plan), list(plan))
                   for key, plan in INVOCATION_PLAN.items()}
    if protocol_plan != driver_plan:
        raise Refused(f"protocol invocation plan changed: {protocol_plan!r}")
    return protocol


def _load_addendum() -> dict[str, Any]:
    addendum = _load_json(ADDENDUM)
    if addendum.get("schema") != ADDENDUM_SCHEMA:
        raise Refused("execution addendum schema mismatch")
    if addendum.get("protocol", {}).get("sha256") != PROTOCOL_SHA256:
        raise Refused("execution addendum does not bind the frozen v2 protocol")
    current = _file_sha(Path(__file__))
    bound = addendum.get("driver", {}).get("sha256_lf")
    if bound != current:
        raise Refused(
            "execution addendum driver SHA-256 does not match this driver; "
            "regenerate the addendum after any driver edit")
    return addendum


def _load_authorization(path: Path) -> dict[str, Any]:
    value = _load_json(Path(path))
    if value.get("protocol_sha256") != PROTOCOL_SHA256:
        raise Refused("owner authorization does not quote the frozen v2 protocol SHA-256")
    confirmation = value.get("owner_confirmation")
    if not isinstance(confirmation, str) or not confirmation.strip():
        raise Refused("owner authorization lacks the owner confirmation text")
    try:
        cap = float(value.get("global_cap_seconds"))
    except (TypeError, ValueError) as exc:
        raise Refused("owner authorization lacks a numeric global_cap_seconds") from exc
    if cap != GLOBAL_CAP_SECONDS:
        raise Refused(
            f"owner authorization global cap {cap!r} differs from {GLOBAL_CAP_SECONDS}")
    return value


def _artifact_root() -> Path:
    base = Path(os.environ.get("DINO_ARTIFACT_ROOT", str(Path.home() / "Dino-artifacts")))
    root = (base.expanduser() / "integrated-solver-verification-v1" / "a3b").resolve()
    enclosing = repository_root_containing(root)
    if enclosing is not None:
        raise Refused(
            f"artifact root must be outside the repository; {root} is inside {enclosing}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sections(variant: dict[str, Any]) -> list[dict[str, Any]]:
    sections = (variant.get("native_configuration", {})
                .get("geometry_identity", {})
                .get("chamber", {})
                .get("sections"))
    if not isinstance(sections, list) or not sections:
        raise Refused("variant has no exhaust sections")
    return sections


def _build_configuration(config_id: str) -> dict[str, Any]:
    if config_id not in CONFIG_SPECS:
        raise Refused(f"unknown config: {config_id}")
    spec = CONFIG_SPECS[config_id]
    project = load_project(PROJECT)
    try:
        source = project["variants"][VARIANT]
    except KeyError as exc:
        raise Refused(f"project lacks variant {VARIANT!r}") from exc
    section_count = len(_sections(source))
    if section_count != 5:
        raise Refused(f"expected five exhaust sections, found {section_count}")
    refined = refine_exhaust_configuration(source, [1] * section_count)
    refined = refine_exhaust_configuration(refined, [spec["per_section"]] * section_count)
    native = refined.get("native_configuration")
    if not isinstance(native, dict):
        raise Refused("refined variant has no native_configuration")
    native["max_cfl"] = float(spec["max_cfl"])
    refined["native_configuration_sha256"] = engine_configuration_sha256(native)
    effective = resolve_for_operating_point(refined, rpm=RPM)
    check = preflight(
        refined,
        rpm=RPM,
        max_cycles=MAX_CYCLES,
        budget_seconds=PREFLIGHT_BUDGET_SECONDS,
        memory_limit_mib=MEMORY_LIMIT_MIB,
    )
    if check.get("status") != "PASS" or check.get("solver_steps") != 0:
        raise Refused(f"preflight did not pass without solver steps for {config_id}")
    if int(check.get("total_finite_volume_cells", -1)) != int(spec["cells"]):
        raise Refused(
            f"{config_id} cell count {check.get('total_finite_volume_cells')} "
            f"!= {spec['cells']}")
    if effective.get("native_configuration_sha256") != check.get("configuration_sha256"):
        raise Refused(f"{config_id} configuration hash mismatch between resolve/preflight")
    return {
        "config_id": config_id,
        "spec": spec,
        "project": project,
        "variant": refined,
        "effective": effective,
        "preflight": check,
    }


def _validate_identity(protocol: dict[str, Any], built: dict[str, Any]) -> None:
    invariants = protocol.get("scope", {}).get("identity_invariants", {})
    check = built["preflight"]
    config_id = built["config_id"]
    if _file_sha_raw(PROJECT) != invariants.get("project_sha256"):
        raise Refused("project file SHA-256 differs from the frozen v2 protocol")
    if check.get("periodicity_thresholds_sha256") != invariants.get("periodicity_thresholds_sha256"):
        raise Refused("periodicity thresholds differ from the frozen v2 protocol")
    if check.get("mechanical_loss_model_sha256") != invariants.get("mechanical_loss_model_sha256"):
        raise Refused("mechanical loss model differs from the frozen v2 protocol")
    if check.get("fuel_id") != invariants.get("fuel_id"):
        raise Refused("fuel identity differs from the frozen v2 protocol")
    if config_id == "T1-A" and check.get("identity_sha256") != invariants.get("identity_sha256"):
        raise Refused("T1-A identity differs from the frozen A3a identity")
    # The preflight identity includes the selected mesh/CFL, so every non-base
    # configuration has its own identity_sha256.  It is recorded, not compared
    # to the T1-A base value.


def _binding(built: dict[str, Any]) -> dict[str, Any]:
    check = built["preflight"]
    effective = built["effective"]
    return {
        "config_id": built["config_id"],
        "protocol_sha256": PROTOCOL_SHA256,
        "driver_sha256": _file_sha(Path(__file__)),
        "project_sha256": _file_sha_raw(PROJECT),
        "configuration_sha256": check["configuration_sha256"],
        "identity_sha256": check["identity_sha256"],
        "mechanical_loss_model_sha256": check["mechanical_loss_model_sha256"],
        "fuel_id": check["fuel_id"],
        "periodicity_contract": check["periodicity_contract"],
        "cycle_primary_contract": check["cycle_primary_contract"],
        "periodicity_source_sha256": check["periodicity_source_sha256"],
        "periodicity_thresholds_sha256": check["periodicity_thresholds_sha256"],
        "exploratory_workflow_source_sha256": _file_sha(
            Path(exploratory_workflow_module.__file__)),
        "solver_source_hashes": effective["source_hashes"],
    }


def _protocol_preflight_receipt(config_ids: list[str]) -> dict[str, Any]:
    _load_protocol()
    configs = []
    for config_id in config_ids:
        built = _build_configuration(config_id)
        _validate_identity(_load_protocol(), built)
        check = built["preflight"]
        configs.append({
            "config_id": config_id,
            "cells": CONFIG_SPECS[config_id]["cells"],
            "max_cfl": CONFIG_SPECS[config_id]["max_cfl"],
            "configuration_sha256": check["configuration_sha256"],
            "identity_sha256": check["identity_sha256"],
            "total_finite_volume_cells": check["total_finite_volume_cells"],
            "solver_steps": check["solver_steps"],
            "status": check["status"],
            "mechanical_loss_model_sha256": check["mechanical_loss_model_sha256"],
            "fuel_id": check["fuel_id"],
            "periodicity_thresholds_sha256": check["periodicity_thresholds_sha256"],
        })
    return {
        "schema": PREFLIGHT_SCHEMA,
        "status": "PASS",
        "created_utc": _now_iso(),
        "protocol": {"path": _display_path(PROTOCOL), "sha256": PROTOCOL_SHA256},
        "driver_sha256_lf": _file_sha(Path(__file__)),
        "driver_sha256_raw": _file_sha_raw(Path(__file__)),
        "configs": configs,
        "no_solver_steps": True,
        "caps": {
            "per_invocation_seconds": PER_INVOCATION_CAP_SECONDS,
            "global_seconds": GLOBAL_CAP_SECONDS,
            "memory_limit_mib": MEMORY_LIMIT_MIB,
        },
        "invocation_plan": INVOCATION_PLAN,
    }


# ---------------------------------------------------------------------------
# Durable budget ledger
# ---------------------------------------------------------------------------

def _entry_charge(entry: dict[str, Any]) -> float:
    try:
        elapsed = float(entry.get("elapsed_seconds", 0.0))
    except (TypeError, ValueError):
        elapsed = 0.0
    try:
        reserved = float(entry.get("reserved_seconds", 0.0))
    except (TypeError, ValueError):
        reserved = 0.0
    return max(0.0, elapsed, reserved)


def _ledger_spent(ledger: dict[str, Any]) -> float:
    return sum(_entry_charge(row) for row in ledger.get("entries", []))


def _ledger_config_spent(ledger: dict[str, Any], config_id: str) -> float:
    return sum(_entry_charge(row) for row in ledger.get("entries", [])
               if row.get("config_id") == config_id)


def _load_ledger(root: Path) -> dict[str, Any]:
    path = root / "a3b-budget-ledger.json"
    if not path.is_file():
        return {"schema": LEDGER_SCHEMA, "protocol_sha256": PROTOCOL_SHA256,
                "created_utc": _now_iso(), "updated_utc": _now_iso(), "entries": []}
    ledger = _load_json(path)
    if ledger.get("schema") != LEDGER_SCHEMA:
        raise Refused("budget ledger schema mismatch")
    if ledger.get("protocol_sha256") != PROTOCOL_SHA256:
        raise Refused("budget ledger belongs to a different protocol")
    if not isinstance(ledger.get("entries"), list):
        raise Refused("budget ledger entries are malformed")
    return ledger


def _save_ledger(root: Path, ledger: dict[str, Any]) -> None:
    ledger["updated_utc"] = _now_iso()
    _write_json(root / "a3b-budget-ledger.json", ledger)


def _close_stale_entries(ledger: dict[str, Any]) -> None:
    for entry in ledger.get("entries", []):
        if entry.get("status") == "RUNNING" or float(entry.get("reserved_seconds", 0.0)) > 0.0:
            charge = _entry_charge(entry)
            entry["elapsed_seconds"] = charge
            entry["reserved_seconds"] = 0.0
            entry["status"] = "INTERRUPTED_ACCOUNTED"
            entry["closed_utc"] = _now_iso()
            entry["close_reason"] = "stale reservation charged as elapsed time"


@contextlib.contextmanager
def _exclusive_run_lock(root: Path):
    path = root / ".a3b.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise Refused("another A3b invocation holds the global run lock") from exc
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise Refused("another A3b invocation holds the global run lock") from exc
        acquired = True
        yield
    finally:
        if acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _reserve_next_cycle(ledger: dict[str, Any], entry: dict[str, Any],
                        config_id: str, invocation_elapsed: float) -> float:
    spec = CONFIG_SPECS[config_id]
    base = max(0.0, float(entry.get("elapsed_seconds", 0.0)), invocation_elapsed)
    reserve = float(spec["linear_seconds_per_cycle"]) * 1.10 + 5.0
    remaining_invocation = max(0.0, PER_INVOCATION_CAP_SECONDS - base)
    if remaining_invocation < 30.0:
        raise BudgetExhausted(
            f"per-invocation cap leaves only {remaining_invocation:.3f} s")
    reserve = min(reserve, remaining_invocation)
    entry["reserved_seconds"] = base + reserve
    spent = _ledger_spent(ledger)
    config_spent = _ledger_config_spent(ledger, config_id)
    if spent > GLOBAL_CAP_SECONDS:
        entry["reserved_seconds"] = base
        raise BudgetExhausted(
            f"global cap exceeded: projected {spent:.3f} s > {GLOBAL_CAP_SECONDS:.0f} s")
    if config_spent > float(spec["cap_seconds"]):
        entry["reserved_seconds"] = base
        raise BudgetExhausted(
            f"{config_id} cap exceeded: projected {config_spent:.3f} s "
            f"> {spec['cap_seconds']:.0f} s")
    return reserve


def _reset_stats(stats: dict[str, Any]) -> None:
    stats["attempted"] = 0
    stats["accepted"] = 0
    stats["rejected"] = 0
    stats["dt_accepted"] = []
    stats["cfl_stage_values"] = []
    stats["cfl_step_max"] = []
    stats["cfl_rejected"] = []


@contextlib.contextmanager
def _instrumented_engine():
    """Count step attempts and capture accepted dt / effective CFL."""
    stats: dict[str, Any] = {}
    _reset_stats(stats)
    stats["cfl_active"] = False
    stats["current_cfl"] = []
    integration = {"seconds": 0.0, "calls": 0}
    original_step = IntegratedEngine2T.step
    original_cfl = IntegratedEngine2T._cfl

    def timed_step(self, *args, **kwargs):
        dt_s = args[0] if args else kwargs.get("dt_s")
        stats["attempted"] += 1
        stats["current_cfl"] = []
        stats["cfl_active"] = True
        mark = time.perf_counter()
        try:
            result = original_step(self, *args, **kwargs)
        except ValueError:
            stats["rejected"] += 1
            stats["cfl_rejected"].extend(stats["current_cfl"])
            raise
        finally:
            integration["seconds"] += time.perf_counter() - mark
            integration["calls"] += 1
            stats["cfl_active"] = False
        stats["accepted"] += 1
        if isinstance(dt_s, (int, float)) and math.isfinite(float(dt_s)):
            stats["dt_accepted"].append(float(dt_s))
        stats["cfl_stage_values"].extend(stats["current_cfl"])
        if stats["current_cfl"]:
            stats["cfl_step_max"].append(max(stats["current_cfl"]))
        return result

    def timed_cfl(self, *args, **kwargs):
        value = original_cfl(self, *args, **kwargs)
        if stats["cfl_active"]:
            stats["current_cfl"].append(float(value))
        return value

    IntegratedEngine2T.step = timed_step
    IntegratedEngine2T._cfl = timed_cfl
    try:
        yield stats, integration
    finally:
        IntegratedEngine2T.step = original_step
        IntegratedEngine2T._cfl = original_cfl


def _stats_summary(stats: dict[str, Any]) -> dict[str, Any]:
    def _spread(values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0, "min": None, "median": None, "max": None}
        return {"count": len(values), "min": min(values),
                "median": statistics.median(values), "max": max(values)}

    return {
        "attempted": stats["attempted"],
        "accepted": stats["accepted"],
        "rejected": stats["rejected"],
        "dt_accepted_s": _spread(stats["dt_accepted"]),
        "effective_cfl_step_max": _spread(stats["cfl_step_max"]),
        "stage_cfl": _spread(stats["cfl_stage_values"]),
        "rejected_cfl": _spread(stats["cfl_rejected"]),
    }


# ---------------------------------------------------------------------------
# Observable extraction and result artifacts
# ---------------------------------------------------------------------------

def _observable_record(primary: dict[str, Any], metrics: dict[str, Any],
                       name: str) -> dict[str, Any]:
    if name == "crankcase.mass_kg":
        try:
            value = primary["observables"]["chambers"]["crankcase"]["mass_kg"]
        except (KeyError, TypeError):
            return {"value": None, "status": "UNDEFINED",
                    "source": "primary.observables.chambers.crankcase.mass_kg",
                    "reason": "crankcase terminal mass is unavailable"}
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return {"value": float(value), "status": "DEFINED",
                    "source": "primary.observables.chambers.crankcase.mass_kg",
                    "reason": None}
        return {"value": None, "status": "UNDEFINED",
                "source": "primary.observables.chambers.crankcase.mass_kg",
                "reason": "crankcase terminal mass is nonfinite"}
    if name == "crankcase_gas_work_J":
        try:
            value = primary["observables"]["crankcase_gas_work_J"]
        except (KeyError, TypeError):
            return {"value": None, "status": "UNDEFINED",
                    "source": "primary.observables.crankcase_gas_work_J",
                    "reason": "crankcase gas work is unavailable"}
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return {"value": float(value), "status": "DEFINED",
                    "source": "primary.observables.crankcase_gas_work_J",
                    "reason": None}
        return {"value": None, "status": "UNDEFINED",
                "source": "primary.observables.crankcase_gas_work_J",
                "reason": "crankcase gas work is nonfinite"}
    record = metrics.get(name)
    if not isinstance(record, dict):
        return {"value": None, "status": "UNDEFINED",
                "source": f"engineering.cycle_metrics.{name}",
                "reason": "metric is absent from the engineering output"}
    status = record.get("status")
    value = record.get("value")
    if status == "DEFINED" and isinstance(value, (int, float)) and math.isfinite(float(value)):
        return {"value": float(value), "status": "DEFINED",
                "source": f"engineering.cycle_metrics.{name}",
                "reason": None}
    return {"value": None, "status": "UNDEFINED",
            "source": f"engineering.cycle_metrics.{name}",
            "reason": record.get("reason") or "metric is not DEFINED"}


def _selected_primary_observables(primary: dict[str, Any]) -> dict[str, Any]:
    observables = primary.get("observables", {})
    crankcase = (observables.get("chambers", {}).get("crankcase", {})
                 if isinstance(observables.get("chambers"), dict) else {})
    selected = {
        "work_J": observables.get("work_J"),
        "crankcase_gas_work_J": observables.get("crankcase_gas_work_J"),
        "net_piston_gas_work_J": observables.get("net_piston_gas_work_J"),
        "crankcase_mass_kg": crankcase.get("mass_kg"),
    }
    return {key: (float(value) if isinstance(value, (int, float)) else None)
            for key, value in selected.items()}


def _aggregate_timers(records: list[dict[str, Any]]) -> dict[str, float]:
    result = {key: 0.0 for key in TIMER_KEYS}
    result["cycle_wall_seconds"] = 0.0
    for record in records:
        timers = record.get("timers", {})
        if isinstance(timers, dict):
            for key in TIMER_KEYS:
                value = timers.get(key, 0.0)
                if isinstance(value, (int, float)) and math.isfinite(float(value)):
                    result[key] += float(value)
        wall = record.get("wall_seconds", 0.0)
        if isinstance(wall, (int, float)) and math.isfinite(float(wall)):
            result["cycle_wall_seconds"] += float(wall)
    return result


def _config_ledger_summaries(ledger: dict[str, Any], config_id: str) -> list[dict[str, Any]]:
    rows = []
    for entry in ledger.get("entries", []):
        if entry.get("config_id") != config_id:
            continue
        rows.append({
            "invocation_id": entry.get("invocation_id"),
            "invocation_index": entry.get("invocation_index"),
            "status": entry.get("status"),
            "elapsed_seconds": entry.get("elapsed_seconds"),
            "reserved_seconds": entry.get("reserved_seconds"),
            "cycles_completed": entry.get("cycles_completed"),
            "cycle_indices": entry.get("cycle_indices", []),
            "checkpoint_next_cycle": entry.get("checkpoint_next_cycle"),
            "started_utc": entry.get("started_utc"),
            "finished_utc": entry.get("finished_utc"),
            "failure": entry.get("failure"),
        })
    return rows


def _write_config_result(root: Path, built: dict[str, Any], binding: dict[str, Any],
                         records: list[dict[str, Any]], status: str,
                         failure: str | None,
                         invocations: list[dict[str, Any]]) -> Path:
    ordered = sorted(records, key=lambda row: int(row["cycle"]))
    payload = {
        "schema": RESULT_SCHEMA,
        "config_id": built["config_id"],
        "status": status,
        "failure": failure,
        "created_utc": _now_iso(),
        "protocol_sha256": PROTOCOL_SHA256,
        "spec": built["spec"],
        "bindings": binding,
        "preflight": built["preflight"],
        "observables": list(OBSERVABLES),
        "records": ordered,
        "cycles_completed": len(ordered),
        "cycle_indices": [row["cycle"] for row in ordered],
        "timers": _aggregate_timers(ordered),
        "invocations": invocations,
        "claims": {
            "periodicity": "NOT_EVALUATED_HORIZON_INSUFFICIENT",
            "convergence": "NOT_EVALUATED",
            "predictive_validation": "NOT_CLAIMED",
            "experimental_validation": "NOT_PERFORMED",
        },
        "no_motorsim_changes": True,
    }
    path = root / built["config_id"] / "result.json"
    _write_json(path, payload)
    return path


def _load_checkpoint(path: Path, binding: dict[str, Any]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    checkpoint = _load_json(path)
    if checkpoint.get("schema") != CHECKPOINT_SCHEMA:
        raise Refused("checkpoint schema mismatch")
    if checkpoint.get("bindings") != binding:
        raise Refused(
            "checkpoint bindings differ from the current protocol/driver/configuration; "
            "refusing to resume")
    next_cycle = checkpoint.get("next_cycle")
    if type(next_cycle) is not int or not 1 <= next_cycle <= MAX_CYCLES + 1:
        raise Refused(f"checkpoint next_cycle is invalid: {next_cycle!r}")
    records = checkpoint.get("records")
    if not isinstance(records, list):
        raise Refused("checkpoint records are malformed")
    if len(records) != next_cycle - 1:
        raise Refused(
            f"checkpoint has {len(records)} records for next_cycle {next_cycle}")
    expected = list(range(1, next_cycle))
    seen = [row.get("cycle") for row in records if isinstance(row, dict)]
    if seen != expected:
        raise Refused(f"checkpoint cycle indices are not contiguous: {seen!r}")
    if not isinstance(checkpoint.get("engine_snapshot"), dict):
        raise Refused("checkpoint engine snapshot is missing")
    if not isinstance(checkpoint.get("periodicity_snapshot"), dict):
        raise Refused("checkpoint periodicity snapshot is missing")
    return checkpoint


def _write_invocation(path: Path, payload: dict[str, Any]) -> None:
    _write_json(path / "invocation.json", payload)


def _disk_bytes(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _run_config(config_id: str, invocation_index: int, authorization_path: Path) -> int:
    run_started = time.monotonic()
    protocol = _load_protocol()
    addendum = _load_addendum()
    authorization = _load_authorization(authorization_path)
    built = _build_configuration(config_id)
    _validate_identity(protocol, built)
    binding = _binding(built)
    spec = CONFIG_SPECS[config_id]
    plan = INVOCATION_PLAN[config_id]
    root = _artifact_root()
    if shutil.disk_usage(root).free < MAX_RUN_ARTIFACT_BYTES:
        raise Refused("artifact root has less free space than the bounded artifact budget")

    with _exclusive_run_lock(root):
        ledger = _load_ledger(root)
        _close_stale_entries(ledger)
        _save_ledger(root, ledger)

        config_dir = root / config_id
        config_dir.mkdir(parents=True, exist_ok=True)
        result_path = config_dir / "result.json"
        if result_path.is_file():
            existing = _load_json(result_path)
            if (existing.get("status") == "COMPLETE"
                    and int(existing.get("cycles_completed", 0)) >= MAX_CYCLES):
                print(json.dumps({
                    "config": config_id,
                    "status": "COMPLETE",
                    "cycles_completed": int(existing.get("cycles_completed", 0)),
                    "message": "evidence already complete; not rewriting result",
                }, sort_keys=True))
                return 0
        checkpoint_path = config_dir / "checkpoint.json"
        checkpoint = _load_checkpoint(checkpoint_path, binding)
        start_cycle = int(checkpoint["next_cycle"]) if checkpoint else 1

        if start_cycle > MAX_CYCLES:
            records = list(checkpoint.get("records", [])) if checkpoint else []
            _write_config_result(root, built, binding, records, "COMPLETE", None,
                                 _config_ledger_summaries(ledger, config_id))
            print(json.dumps({"config": config_id, "status": "COMPLETE",
                              "cycles_completed": len(records),
                              "message": "config already complete"}, sort_keys=True))
            return 0

        if _ledger_spent(ledger) >= GLOBAL_CAP_SECONDS:
            raise BudgetExhausted(
                f"global cap already reached: {_ledger_spent(ledger):.3f} s")
        if _ledger_config_spent(ledger, config_id) >= float(spec["cap_seconds"]):
            raise BudgetExhausted(
                f"{config_id} cap already reached: "
                f"{_ledger_config_spent(ledger, config_id):.3f} s")

        if invocation_index < 1:
            raise Refused("invocation index must be positive")
        planned_cycles = (plan[invocation_index - 1]
                          if invocation_index <= len(plan) else 1)
        max_cycles_this = min(int(planned_cycles), MAX_CYCLES - start_cycle + 1)
        if max_cycles_this <= 0:
            raise Refused("invocation has no remaining cycles")

        engine = IntegratedEngine2T.from_configuration_dict(
            built["effective"]["native_configuration"])
        detector = PeriodicDetectorV2()
        records: list[dict[str, Any]] = []
        if checkpoint is not None:
            try:
                engine.restore(checkpoint["engine_snapshot"])
                detector.restore(checkpoint["periodicity_snapshot"])
            except Exception as exc:
                raise Refused(f"cannot restore checkpoint: {exc}") from exc
            records = list(checkpoint["records"])
        loss = MechanicalLossModel.from_dict(built["effective"]["mechanical_loss_model"])
        load = float(built["effective"]["operating_conditions"]["load"])

        invocation_id = f"{config_id}-inv{invocation_index:02d}-{uuid.uuid4().hex[:10]}"
        invocation_dir = config_dir / f"inv{invocation_index:02d}-{uuid.uuid4().hex[:10]}"
        invocation_dir.mkdir(parents=True, exist_ok=False)
        _write_json(invocation_dir / "configuration.json", built["effective"])
        _write_json(invocation_dir / "binding.json", binding)
        _write_json(invocation_dir / "preflight.json", built["preflight"])

        entry = {
            "invocation_id": invocation_id,
            "config_id": config_id,
            "invocation_index": invocation_index,
            "started_utc": _now_iso(),
            "started_monotonic": run_started,
            "elapsed_seconds": 0.0,
            "reserved_seconds": 0.0,
            "cycles_completed": 0,
            "cycle_indices": [],
            "checkpoint_next_cycle": start_cycle,
            "status": "RUNNING",
            "failure": None,
            "pid": os.getpid(),
        }
        ledger["entries"].append(entry)
        _save_ledger(root, ledger)

        timers = {key: 0.0 for key in TIMER_KEYS}
        rss_start = _rss_bytes()
        rss_peak = {"bytes": rss_start}
        sampler_stop = threading.Event()

        def _sample_rss() -> None:
            while not sampler_stop.wait(0.2):
                try:
                    value = _rss_bytes()
                except OSError:
                    return
                if value > rss_peak["bytes"]:
                    rss_peak["bytes"] = value

        sampler = threading.Thread(target=_sample_rss, daemon=True)
        sampler.start()
        status = "RUNNING"
        failure = None
        invocation_started = run_started
        deadline = invocation_started + INTERNAL_INVOCATION_DEADLINE_SECONDS

        def _progress(info: dict[str, Any]) -> None:
            print(json.dumps({
                "config": config_id,
                "invocation": invocation_index,
                "cycle": info.get("cycle"),
                "angle_deg": round(float(info.get("angle_deg", 0.0)), 3),
                "cycles_completed": info.get("cycles_completed"),
                "rss_bytes": info.get("rss_bytes"),
            }, sort_keys=True), flush=True)

        try:
            with _instrumented_engine() as (stats, integration):
                for cycle in range(start_cycle, start_cycle + max_cycles_this):
                    if time.monotonic() >= deadline:
                        status = "INTERRUPTED_CHECKPOINTED"
                        failure = "TIMEOUT"
                        break
                    invocation_elapsed = time.monotonic() - invocation_started
                    try:
                        _reserve_next_cycle(ledger, entry, config_id, invocation_elapsed)
                    except BudgetExhausted as exc:
                        status = "PARTIAL_BUDGET"
                        failure = str(exc)
                        _save_ledger(root, ledger)
                        break
                    _save_ledger(root, ledger)
                    _reset_stats(stats)
                    cycle_wall_mark = time.perf_counter()
                    cycle_timers = {key: 0.0 for key in TIMER_KEYS}
                    state_mark = time.perf_counter()
                    cycle_start = engine.snapshot()
                    cycle_timers["state_snapshot_orchestration_seconds"] += (
                        time.perf_counter() - state_mark)
                    integration_base = integration["seconds"]
                    calls_base = integration["calls"]
                    advance_mark = time.perf_counter()
                    try:
                        rejected = _advance_cycle(
                            engine, cycle, deadline=deadline, cancel_event=None,
                            progress=_progress, memory_limit_mib=MEMORY_LIMIT_MIB)
                    except (RunCancelled, RunDeadline) as exc:
                        restore_mark = time.perf_counter()
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        cycle_timers["state_snapshot_orchestration_seconds"] += (
                            time.perf_counter() - restore_mark)
                        status = "INTERRUPTED_CHECKPOINTED"
                        failure = ("CANCELLED" if isinstance(exc, RunCancelled)
                                   else "TIMEOUT")
                        break
                    except MemoryError as exc:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = f"RESOURCE_LIMIT_EXCEEDED: {exc}"
                        break
                    except Exception as exc:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = f"{type(exc).__name__}: {exc}"
                        break
                    advance_seconds = time.perf_counter() - advance_mark
                    step_seconds = integration["seconds"] - integration_base
                    cycle_timers["integration_physical_seconds"] += step_seconds
                    cycle_timers["dispatch_overhead_seconds"] += (
                        advance_seconds - step_seconds)

                    state_mark = time.perf_counter()
                    end = engine.snapshot()
                    cycle_timers["state_snapshot_orchestration_seconds"] += (
                        time.perf_counter() - state_mark)
                    make_mark = time.perf_counter()
                    try:
                        primary = make_integrated_cycle_primary(
                            engine, cycle_start, end, cycle,
                            rejected_trials=rejected,
                            runner_sha256=binding["driver_sha256"])
                    except Exception as exc:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = f"PRIMARY_RECONSTRUCTION_FAILED: {type(exc).__name__}: {exc}"
                        break
                    cycle_timers["audit_reconstruction_make_seconds"] += (
                        time.perf_counter() - make_mark)
                    audit_mark = time.perf_counter()
                    audit = audit_integrated_cycle_primary(
                        primary, preserve_precycle_p7_baseline=True)
                    cycle_timers["audit_reconstruction_audit_seconds"] += (
                        time.perf_counter() - audit_mark)
                    if audit.get("recomputed") is not True or primary.get("admissible") is not True:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = "PRIMARY_AUDIT_FAIL"
                        break
                    if primary.get("configuration_hash") != binding["configuration_sha256"]:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = "PRIMARY_CONFIGURATION_HASH_MISMATCH"
                        break

                    detector_mark = time.perf_counter()
                    try:
                        update = detector.update({
                            "cycle_index": cycle,
                            "configuration_hash": primary["configuration_hash"],
                            "contract": CYCLE_PRIMARY_CONTRACT,
                            "observables": primary["observables"],
                        })
                    except Exception as exc:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = f"PERIODICITY_DETECTOR_FAILED: {type(exc).__name__}: {exc}"
                        break
                    cycle_timers["periodicity_detector_seconds"] += (
                        time.perf_counter() - detector_mark)
                    periodicity_evidence = None
                    if detector.classification is not None:
                        periodicity_evidence = {
                            "status": detector.classification,
                            "configuration_hash": primary["configuration_hash"],
                            "terminal_cycle": cycle,
                            "detector_sha256": _sha(_json_bytes(detector.snapshot())),
                        }

                    serialization_mark = time.perf_counter()
                    primary_payload = _json_bytes(primary)
                    primary_sha = _sha(primary_payload)
                    compressed_primary = gzip.compress(
                        primary_payload, compresslevel=6, mtime=0)
                    committed_bytes = _disk_bytes(invocation_dir)
                    if committed_bytes + len(compressed_primary) > MAX_RUN_ARTIFACT_BYTES:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = "ARTIFACT_BUDGET_EXCEEDED"
                        break
                    artifact_rel = f"cycle-{cycle:04d}.json.gz"
                    _atomic_write(invocation_dir / artifact_rel, compressed_primary)
                    cycle_timers["serialization_io_seconds"] += (
                        time.perf_counter() - serialization_mark)

                    engineering_mark = time.perf_counter()
                    try:
                        engineering = make_integrated_engineering_output(
                            _prepare_engineering_output_record(
                                primary, periodicity_evidence),
                            displacement_m3=primary.get("swept_displacement_m3"),
                            mechanical_loss_model=loss,
                            load=load,
                            periodicity_status=detector.classification or "NOT_EVALUATED")
                    except Exception as exc:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = f"ENGINEERING_OUTPUT_FAILED: {type(exc).__name__}: {exc}"
                        break
                    cycle_timers["engineering_output_seconds"] += (
                        time.perf_counter() - engineering_mark)
                    if engineering.get("configuration_sha256") != binding["configuration_sha256"]:
                        try:
                            engine.restore(cycle_start)
                        except Exception:
                            pass
                        status = "FAILED_CLOSED"
                        failure = "ENGINEERING_CONFIGURATION_HASH_MISMATCH"
                        break

                    observables = {
                        name: _observable_record(primary, engineering["cycle_metrics"], name)
                        for name in OBSERVABLES
                    }
                    cycle_timers["cycle_wall_seconds"] = time.perf_counter() - cycle_wall_mark
                    record = {
                        "cycle": cycle,
                        "artifact": artifact_rel,
                        "primary_sha256": primary_sha,
                        "configuration_hash": primary["configuration_hash"],
                        "audit": audit,
                        "audit_method": "INTEGRATED_CYCLE_REPLAY_V2_PRE_CYCLE_P7_BASELINE",
                        "periodicity_update": update,
                        "periodicity": detector.classification or "NOT_EVALUATED",
                        "periodicity_evidence": periodicity_evidence,
                        "conservation": primary["conservation"],
                        "primary_observables": _selected_primary_observables(primary),
                        "observables": observables,
                        "engineering_schema": engineering["schema"],
                        "engineering_claims": engineering["claims"],
                        "rejected_step_count": len(rejected),
                        "cfl_stats": _stats_summary(stats),
                        "cfl_primary": primary.get("CFL"),
                        "timers": cycle_timers,
                        "wall_seconds": cycle_timers["cycle_wall_seconds"],
                        "rss_bytes_at_cycle_end": _rss_bytes(),
                    }
                    records.append(record)

                    state_mark = time.perf_counter()
                    engine.compact_cycle_trace()
                    checkpoint_payload = {
                        "schema": CHECKPOINT_SCHEMA,
                        "bindings": binding,
                        "next_cycle": cycle + 1,
                        "records": records,
                        "engine_snapshot": engine.snapshot(),
                        "periodicity_snapshot": detector.snapshot(),
                    }
                    _write_json(checkpoint_path, checkpoint_payload)
                    cycle_timers["state_snapshot_orchestration_seconds"] += (
                        time.perf_counter() - state_mark)
                    cycle_timers["cycle_wall_seconds"] = time.perf_counter() - cycle_wall_mark
                    record["wall_seconds"] = cycle_timers["cycle_wall_seconds"]
                    for key in TIMER_KEYS:
                        timers[key] += cycle_timers.get(key, 0.0)
                    entry["elapsed_seconds"] = time.monotonic() - invocation_started
                    entry["reserved_seconds"] = 0.0
                    entry["cycles_completed"] = len(records) - (start_cycle - 1)
                    entry["cycle_indices"].append(cycle)
                    entry["checkpoint_next_cycle"] = cycle + 1
                    entry["status"] = "RUNNING"
                    _save_ledger(root, ledger)
                    _write_config_result(
                        root, built, binding, records, "RUNNING", None,
                        _config_ledger_summaries(ledger, config_id))
                    if cycle == MAX_CYCLES:
                        status = "COMPLETE"
                        break
        except Exception as exc:
            if status == "RUNNING":
                status = "FAILED_CLOSED"
            if failure is None:
                failure = f"{type(exc).__name__}: {exc}"
        finally:
            sampler_stop.set()
            sampler.join(timeout=2.0)
            entry["elapsed_seconds"] = time.monotonic() - invocation_started
            entry["reserved_seconds"] = 0.0
            entry["cycles_completed"] = len(records) - (start_cycle - 1)
            entry["checkpoint_next_cycle"] = (records[-1]["cycle"] + 1
                                              if records else start_cycle)
            entry["status"] = status
            entry["failure"] = failure
            entry["finished_utc"] = _now_iso()
            _save_ledger(root, ledger)
            if status == "RUNNING":
                status = ("COMPLETE" if len(records) >= MAX_CYCLES
                          else "INVOCATION_COMPLETE_CHECKPOINTED")
                entry["status"] = status
                _save_ledger(root, ledger)
            invocation_payload = {
                "schema": INVOCATION_SCHEMA,
                "invocation_id": invocation_id,
                "config_id": config_id,
                "invocation_index": invocation_index,
                "status": status,
                "failure": failure,
                "started_utc": entry["started_utc"],
                "finished_utc": entry["finished_utc"],
                "cycles_run": entry["cycle_indices"],
                "cycles_completed_total": len(records),
                "checkpoint_next_cycle": entry["checkpoint_next_cycle"],
                "preflight": built["preflight"],
                "bindings": binding,
                "addendum_sha256": _file_sha_raw(ADDENDUM),
                "authorization_sha256": _file_sha_raw(Path(authorization_path)),
                "owner_confirmation": authorization.get("owner_confirmation"),
                "rss_start_bytes": rss_start,
                "rss_peak_bytes": rss_peak["bytes"],
                "rss_end_bytes": _rss_bytes(),
                "ledger_entry": entry,
            }
            _write_invocation(invocation_dir, invocation_payload)
            try:
                _write_config_result(
                    root, built, binding, records, status, failure,
                    _config_ledger_summaries(ledger, config_id))
            except Exception as exc:
                print(json.dumps({"config": config_id, "warning":
                                  f"could not write final config result: {exc}"}),
                      file=sys.stderr)
            print(json.dumps({
                "config": config_id,
                "invocation": invocation_index,
                "status": status,
                "failure": failure,
                "cycles_completed_total": len(records),
                "elapsed_seconds": round(entry["elapsed_seconds"], 3),
                "global_spent_seconds": round(_ledger_spent(ledger), 3),
                "config_spent_seconds": round(
                    _ledger_config_spent(ledger, config_id), 3),
            }, sort_keys=True), flush=True)

    return 1 if status == "FAILED_CLOSED" else 0


# ---------------------------------------------------------------------------
# Numeric atol freeze and sensitivity analysis
# ---------------------------------------------------------------------------

def _load_config_result(root: Path, config_id: str) -> dict[str, Any]:
    path = root / config_id / "result.json"
    result = _load_json(path)
    if result.get("schema") != RESULT_SCHEMA:
        raise Refused(f"{config_id} result schema mismatch")
    if result.get("config_id") != config_id:
        raise Refused(f"{config_id} result identifies itself as {result.get('config_id')!r}")
    if result.get("protocol_sha256") != PROTOCOL_SHA256:
        raise Refused(f"{config_id} result belongs to a different protocol")
    bindings = result.get("bindings")
    if not isinstance(bindings, dict):
        raise Refused(f"{config_id} result has no bindings")
    if bindings.get("protocol_sha256") != PROTOCOL_SHA256:
        raise Refused(f"{config_id} result binding does not quote the frozen protocol")
    if bindings.get("driver_sha256") != _file_sha(Path(__file__)):
        raise Refused(
            f"{config_id} result was produced by a different driver revision")
    records = result.get("records")
    if not isinstance(records, list):
        raise Refused(f"{config_id} result records are malformed")
    cycles = [row.get("cycle") for row in records if isinstance(row, dict)]
    if cycles != [1, 2, 3]:
        raise Refused(f"{config_id} does not have exactly cycles 1,2,3: {cycles!r}")
    if result.get("status") != "COMPLETE":
        raise Refused(f"{config_id} is not COMPLETE: {result.get('status')!r}")
    return result


def _cycle_record(result: dict[str, Any], cycle: int) -> dict[str, Any]:
    for record in result.get("records", []):
        if record.get("cycle") == cycle:
            return record
    raise Refused(f"cycle {cycle} is missing from {result.get('config_id')}")


def _cycle_observable(result: dict[str, Any], cycle: int, name: str) -> float | None:
    record = _cycle_record(result, cycle)
    observable = record.get("observables", {}).get(name)
    if not isinstance(observable, dict) or observable.get("status") != "DEFINED":
        return None
    value = observable.get("value")
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return float(value)
    return None


def _mass_resolution(result: dict[str, Any]) -> float:
    worst = 0.0
    for record in result.get("records", []):
        conservation = record.get("conservation", {})
        value = conservation.get("mass_residual_kg") if isinstance(conservation, dict) else None
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            worst = max(worst, abs(float(value)))
    return max(MASS_FLOOR_KG, worst)


def _resolution_for(name: str, result: dict[str, Any]) -> float:
    if name == "crankcase.mass_kg":
        return _mass_resolution(result)
    if name in {"brake_work_j", "crankcase_gas_work_J"}:
        return WORK_FLOOR_J
    return 0.0


def _freeze_atol() -> dict[str, Any]:
    if ANALYSIS_FREEZE.exists():
        raise Refused(
            f"analysis freeze already exists and is immutable: {ANALYSIS_FREEZE}")
    _load_addendum()
    root = _artifact_root()
    t1a_path = root / "T1-A" / "result.json"
    t1a_sha_before = _file_sha_raw(t1a_path)
    t1a = _load_config_result(root, "T1-A")
    if _file_sha_raw(t1a_path) != t1a_sha_before:
        raise Refused("T1-A result changed while the analysis freeze was being built")
    resolutions = {name: _resolution_for(name, t1a) for name in OBSERVABLES}
    table: dict[str, dict[str, Any]] = {}
    for name in OBSERVABLES:
        table[name] = {}
        for cycle in (1, 2, 3):
            value = _cycle_observable(t1a, cycle, name)
            if value is None:
                table[name][f"cycle_{cycle}"] = {
                    "x_base": None,
                    "atol_obs": None,
                    "resolution": resolutions[name],
                    "status": "NOT_EVALUATED",
                }
                continue
            table[name][f"cycle_{cycle}"] = {
                "x_base": value,
                "atol_obs": max(0.05 * abs(value), resolutions[name]),
                "resolution": resolutions[name],
                "status": "DEFINED",
            }
    payload = {
        "schema": FREEZE_SCHEMA,
        "status": "FROZEN_BEFORE_COMPARISON",
        "created_utc": _now_iso(),
        "protocol_sha256": PROTOCOL_SHA256,
        "t1a_result_sha256": _file_sha_raw(t1a_path),
        "t1a_configuration_sha256": t1a["bindings"]["configuration_sha256"],
        "t1a_identity_sha256": t1a["bindings"]["identity_sha256"],
        "observables": table,
        "resolutions": resolutions,
        "immutability": (
            "This table is written once from T1-A before any cross-config "
            "comparison.  Any change requires a new preregistration."),
        "no_post_hoc_adjustment": True,
        "claim_scope": "TRANSIENT_CYCLES_1_TO_3_ONLY",
    }
    _write_json(ANALYSIS_FREEZE, payload)
    print(json.dumps({
        "status": payload["status"],
        "path": _display_path(ANALYSIS_FREEZE),
        "t1a_result_sha256": payload["t1a_result_sha256"],
        "observables": len(table),
    }, sort_keys=True))
    return payload


def _pair_rows(coarse: dict[str, Any], fine: dict[str, Any], name: str,
               freeze: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for cycle in (1, 2, 3):
        x_coarse = _cycle_observable(coarse, cycle, name)
        x_fine = _cycle_observable(fine, cycle, name)
        frozen = freeze.get("observables", {}).get(name, {}).get(f"cycle_{cycle}", {})
        atol = frozen.get("atol_obs")
        row: dict[str, Any] = {
            "cycle": cycle,
            "coarse_config": coarse["config_id"],
            "fine_config": fine["config_id"],
            "x_coarse": x_coarse,
            "x_fine": x_fine,
            "atol_obs": atol,
        }
        if (x_coarse is None or x_fine is None or
                not isinstance(atol, (int, float)) or not math.isfinite(float(atol))):
            row.update({"delta": None, "relative_to_fine": None,
                        "sign_crossing": None, "passes_tolerance": None,
                        "status": "NOT_EVALUATED"})
            rows.append(row)
            continue
        atol = float(atol)
        delta = x_fine - x_coarse
        sign_crossing = (x_coarse * x_fine < 0.0 and
                         max(abs(x_coarse), abs(x_fine)) > atol)
        passes = bool(abs(delta) <= max(0.05 * abs(x_fine), atol) and not sign_crossing)
        row.update({
            "delta": delta,
            "relative_to_fine": (abs(delta) / abs(x_fine) if x_fine != 0.0 else None),
            "sign_crossing": sign_crossing,
            "passes_tolerance": passes,
            "status": "PASS" if passes else "FAIL",
        })
        rows.append(row)
    return rows


def _classify_pair_rows(rows1: list[dict[str, Any]],
                        rows2: list[dict[str, Any]]) -> list[str]:
    results = []
    for row1, row2 in zip(rows1, rows2):
        if row1["status"] == "NOT_EVALUATED" or row2["status"] == "NOT_EVALUATED":
            results.append("NOT_EVALUATED")
            continue
        if row1["sign_crossing"] or row2["sign_crossing"]:
            results.append("NOT_CONVERGED")
            continue
        d1 = abs(float(row1["delta"]))
        d2 = abs(float(row2["delta"]))
        monotone = (d2 < d1) or (d1 == 0.0 and d2 == 0.0)
        if not monotone:
            results.append("NON_MONOTONE")
        elif row2["passes_tolerance"]:
            results.append("CONVERGING_MONOTONE")
        else:
            results.append("NOT_CONVERGED")
    return results


def _p_diagnostic(rows1: list[dict[str, Any]],
                  rows2: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values = []
    for row1, row2 in zip(rows1, rows2):
        if row1["status"] == "NOT_EVALUATED" or row2["status"] == "NOT_EVALUATED":
            values.append({"cycle": row1["cycle"], "p": None,
                           "status": "NOT_EVALUATED"})
            continue
        d1 = abs(float(row1["delta"]))
        d2 = abs(float(row2["delta"]))
        if d1 > 0.0 and d2 > 0.0 and row1["status"] == "PASS" and row2["status"] == "PASS":
            p = math.log(d1 / d2) / math.log(2.0)
            values.append({"cycle": row1["cycle"], "p": p,
                           "status": "DIAGNOSTIC_ONLY",
                           "consistent_with_first_order": 0.5 <= p <= 1.5})
        else:
            values.append({"cycle": row1["cycle"], "p": None,
                           "status": "NOT_COMPUTED",
                           "reason": "requires positive deltas and passing pairs"})
    return values


def _summarize_classifications(classifications: list[str]) -> str:
    if not classifications:
        return "NOT_EVALUATED"
    if any(value == "NOT_CONVERGED" for value in classifications):
        return "NOT_CONVERGED"
    if any(value == "NON_MONOTONE" for value in classifications):
        return "NON_MONOTONE"
    if all(value == "CONVERGING_MONOTONE" for value in classifications):
        return "CONVERGING_MONOTONE"
    return "NOT_EVALUATED"


def _analyze() -> int:
    _load_addendum()
    freeze = _load_json(ANALYSIS_FREEZE)
    if freeze.get("schema") != FREEZE_SCHEMA:
        raise Refused("analysis freeze schema mismatch")
    if freeze.get("protocol_sha256") != PROTOCOL_SHA256:
        raise Refused("analysis freeze belongs to a different protocol")
    root = _artifact_root()
    t1a_path = root / "T1-A" / "result.json"
    if _file_sha_raw(t1a_path) != freeze.get("t1a_result_sha256"):
        raise Refused("T1-A result changed after the analysis freeze")

    results: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for config_id in CONFIG_SPECS:
        try:
            results[config_id] = _load_config_result(root, config_id)
        except Refused as exc:
            missing.append(f"{config_id}: {exc}")

    base_header = {
        "schema": REPORT_SCHEMA,
        "created_utc": _now_iso(),
        "protocol_sha256": PROTOCOL_SHA256,
        "driver_sha256_lf": _file_sha(Path(__file__)),
        "analysis_freeze_sha256": _file_sha_raw(ANALYSIS_FREEZE),
        "inputs": {
            config_id: _file_sha_raw(root / config_id / "result.json")
            for config_id in CONFIG_SPECS if config_id in results
        },
        "claim_scope": {
            "periodicity": "NOT_EVALUATED_HORIZON_INSUFFICIENT",
            "global_convergence": "NO_GLOBAL_VERDICT",
            "predictive_validation": "NOT_CLAIMED",
            "experimental_validation": "NOT_PERFORMED",
        },
    }
    if missing:
        report = {
            **base_header,
            "status": "INCOMPLETE_MATRIX",
            "missing": missing,
            "overall_output": "INCOMPLETE_MATRIX",
            "bounded_statement": (
                "The matrix is incomplete; no convergence statement is made."),
        }
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "status": "INCOMPLETE_MATRIX",
            "created_utc": report["created_utc"],
            "protocol_sha256": PROTOCOL_SHA256,
            "analysis_freeze_sha256": report["analysis_freeze_sha256"],
            "missing": missing,
            "no_global_verdict": True,
        }
        _write_json(REPORT, report)
        _write_json(RECEIPT, receipt)
        print(json.dumps({"status": "INCOMPLETE_MATRIX", "missing": missing},
                         sort_keys=True), file=sys.stderr)
        return 1

    temporal = (("T1-A", "T1-B"), ("T1-B", "T1-C"))
    spatial = (("T1-E", "T1-D"), ("T1-D", "T1-A"))
    observables: dict[str, Any] = {}
    for name in OBSERVABLES:
        temporal_rows = [_pair_rows(results[a], results[b], name, freeze)
                         for a, b in temporal]
        spatial_rows = [_pair_rows(results[a], results[b], name, freeze)
                        for a, b in spatial]
        temporal_classes = _classify_pair_rows(*temporal_rows)
        spatial_classes = _classify_pair_rows(*spatial_rows)
        p_values = _p_diagnostic(*temporal_rows)
        spatial_p = [{"cycle": cycle, "p": None, "status": "NOT_COMPUTED",
                      "reason": "spatial levels do not have a uniform refinement ratio"}
                     for cycle in (1, 2, 3)]
        temporal_summary = _summarize_classifications(temporal_classes)
        spatial_summary = _summarize_classifications(spatial_classes)
        combined = _summarize_classifications(
            temporal_classes + spatial_classes)
        observables[name] = {
            "temporal": {
                "pairs": [
                    {"coarse": temporal[0][0], "fine": temporal[0][1],
                     "rows": temporal_rows[0]},
                    {"coarse": temporal[1][0], "fine": temporal[1][1],
                     "rows": temporal_rows[1]},
                ],
                "per_cycle_classification": [
                    {"cycle": cycle, "classification": temporal_classes[cycle - 1]}
                    for cycle in (1, 2, 3)
                ],
                "p_diagnostic": p_values,
                "summary": temporal_summary,
            },
            "spatial": {
                "pairs": [
                    {"coarse": spatial[0][0], "fine": spatial[0][1],
                     "rows": spatial_rows[0]},
                    {"coarse": spatial[1][0], "fine": spatial[1][1],
                     "rows": spatial_rows[1]},
                ],
                "per_cycle_classification": [
                    {"cycle": cycle, "classification": spatial_classes[cycle - 1]}
                    for cycle in (1, 2, 3)
                ],
                "p_diagnostic": spatial_p,
                "summary": spatial_summary,
            },
            "summary": combined,
        }

    all_converging = all(row["summary"] == "CONVERGING_MONOTONE"
                         for row in observables.values())
    any_not_converged = any(row["summary"] == "NOT_CONVERGED"
                            for row in observables.values())
    if all_converging:
        statement = (
            "Within the studied transient cycles 1-3, all audited observables "
            "meet the preregistered tolerance at the finest temporal and spatial "
            "levels. This supports numerical sensitivity only; it does not "
            "establish periodicity, predictive accuracy, or experimental validation.")
    elif any_not_converged:
        statement = (
            "At least one audited observable does not meet the preregistered "
            "tolerance; numerical error is not bounded for the studied domain. "
            "The result supports exploratory use only, not predictive power curves.")
    else:
        statement = (
            "The matrix is complete, but at least one audited observable is "
            "non-monotone or not evaluated. No convergence statement is made "
            "beyond the per-observable table.")

    cost_rows = {}
    for config_id, result in results.items():
        timers = result.get("timers", {})
        wall = float(timers.get("cycle_wall_seconds", 0.0) or 0.0)
        shares = {
            key: (float(value) / wall if wall > 0.0 else None)
            for key, value in timers.items()
            if key != "cycle_wall_seconds"
            and isinstance(value, (int, float))
        }
        cost_rows[config_id] = {
            "status": result.get("status"),
            "cycles": result.get("cycle_indices"),
            "wall_seconds": wall,
            "exclusive_timers_seconds": {
                key: value for key, value in timers.items()
                if key != "cycle_wall_seconds"
            },
            "shares_of_wall": shares,
            "single_sample": True,
        }

    report = {
        **base_header,
        "status": "COMPLETE",
        "configs": {
            config_id: {
                "cells": CONFIG_SPECS[config_id]["cells"],
                "max_cfl": CONFIG_SPECS[config_id]["max_cfl"],
                "configuration_sha256": result["bindings"]["configuration_sha256"],
                "identity_sha256": result["bindings"]["identity_sha256"],
            }
            for config_id, result in results.items()
        },
        "observables": observables,
        "per_observable_classifications": {
            name: row["summary"] for name, row in observables.items()
        },
        "cost": cost_rows,
        "overall_output": "NO_GLOBAL_CONVERGENCE_VERDICT",
        "bounded_statement": statement,
        "no_global_verdict": True,
        "no_predictive_claim": True,
    }
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "status": "COMPLETE",
        "created_utc": report["created_utc"],
        "protocol_sha256": PROTOCOL_SHA256,
        "analysis_freeze_sha256": report["analysis_freeze_sha256"],
        "inputs": report["inputs"],
        "per_observable_classifications": report["per_observable_classifications"],
        "overall_output": report["overall_output"],
        "bounded_statement": statement,
        "no_global_verdict": True,
        "no_predictive_claim": True,
        "claim_scope": report["claim_scope"],
    }
    _write_json(REPORT, report)
    _write_json(RECEIPT, receipt)
    print(json.dumps({
        "status": "COMPLETE",
        "report": _display_path(REPORT),
        "receipt": _display_path(RECEIPT),
        "classifications": report["per_observable_classifications"],
        "bounded_statement": statement,
    }, sort_keys=True))
    return 0


# ---------------------------------------------------------------------------
# Execution addendum
# ---------------------------------------------------------------------------

def _write_addendum(preflight_receipt_path: Path, tests_status: str) -> dict[str, Any]:
    if ADDENDUM.exists():
        raise Refused(f"execution addendum already exists: {ADDENDUM}")
    if tests_status != "PASS":
        raise Refused("execution addendum requires tests_status=PASS")
    protocol = _load_protocol()
    receipt = _load_json(preflight_receipt_path)
    if receipt.get("schema") != PREFLIGHT_SCHEMA or receipt.get("status") != "PASS":
        raise Refused("preflight receipt is not a PASS receipt")
    if receipt.get("protocol", {}).get("sha256") != PROTOCOL_SHA256:
        raise Refused("preflight receipt does not bind the frozen v2 protocol")
    current_driver = _file_sha(Path(__file__))
    if receipt.get("driver_sha256_lf") != current_driver:
        raise Refused("preflight receipt was produced by a different driver")
    configs = receipt.get("configs")
    if not isinstance(configs, list) or len(configs) != len(CONFIG_SPECS):
        raise Refused("preflight receipt does not cover all five configurations")
    seen: set[str] = set()
    for row in configs:
        config_id = row.get("config_id")
        if config_id not in CONFIG_SPECS:
            raise Refused(f"preflight receipt has unknown config: {config_id!r}")
        if config_id in seen:
            raise Refused(f"preflight receipt repeats config: {config_id}")
        seen.add(config_id)
        if int(row.get("total_finite_volume_cells", -1)) != CONFIG_SPECS[config_id]["cells"]:
            raise Refused(f"preflight receipt cell count mismatch for {config_id}")
        if float(row.get("max_cfl", -1.0)) != float(CONFIG_SPECS[config_id]["max_cfl"]):
            raise Refused(f"preflight receipt max_cfl mismatch for {config_id}")
        if row.get("solver_steps") != 0:
            raise Refused(f"preflight receipt is not zero-step for {config_id}")
    if seen != set(CONFIG_SPECS):
        raise Refused(f"preflight receipt config set is incomplete: {sorted(seen)}")
    payload = {
        "schema": ADDENDUM_SCHEMA,
        "created_utc": _now_iso(),
        "protocol": {
            "path": _display_path(PROTOCOL),
            "sha256": PROTOCOL_SHA256,
            "status": protocol.get("status"),
        },
        "driver": {
            "path": _display_path(Path(__file__)),
            "sha256_lf": current_driver,
            "sha256_raw": _file_sha_raw(Path(__file__)),
        },
        "tests": {
            "command": "python -m pytest tests/test_integrated_solver_verification_a3b.py -q",
            "status": tests_status,
        },
        "preflight": {
            "receipt": _display_path(Path(preflight_receipt_path)),
            "sha256": _file_sha_raw(Path(preflight_receipt_path)),
            "status": "PASS",
            "no_solver_steps": True,
        },
        "configs": configs,
        "caps": {
            "per_invocation_seconds": PER_INVOCATION_CAP_SECONDS,
            "global_seconds": GLOBAL_CAP_SECONDS,
            "memory_limit_mib": MEMORY_LIMIT_MIB,
            "config_caps_seconds": {
                config_id: CONFIG_SPECS[config_id]["cap_seconds"]
                for config_id in CONFIG_SPECS
            },
        },
        "invocation_plan": INVOCATION_PLAN,
        "commands": {
            "preflight": "python scripts/diagnostics/integrated_solver_verification_a3b.py preflight",
            "run_config": (
                "python scripts/diagnostics/integrated_solver_verification_a3b.py "
                "run-config --config T1-A --invocation 1 --authorization <owner-confirmation.json>"),
            "freeze_atol": (
                "python scripts/diagnostics/integrated_solver_verification_a3b.py freeze-atol"),
            "analyze": (
                "python scripts/diagnostics/integrated_solver_verification_a3b.py analyze"),
        },
        "authorization": {
            "required": True,
            "status": "NOT_GRANTED",
            "owner_confirmation_reference": (
                "results/integrated-solver-verification-v1/"
                "a3b-owner-execution-confirmation.json"),
        },
        "claim_scope": {
            "periodicity": "NOT_EVALUATED_HORIZON_INSUFFICIENT",
            "global_convergence": "NO_GLOBAL_VERDICT",
            "predictive_validation": "NOT_CLAIMED",
            "experimental_validation": "NOT_PERFORMED",
        },
        "no_motorsim_changes": True,
    }
    _write_json(ADDENDUM, payload)
    print(json.dumps({
        "status": "WRITTEN",
        "path": _display_path(ADDENDUM),
        "driver_sha256_lf": current_driver,
    }, sort_keys=True))
    return payload


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ISV1 A3b preregistered sensitivity matrix driver")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="zero-solver-step preflight")
    pre.add_argument("--config", choices=list(CONFIG_SPECS), default=None)
    pre.add_argument("--receipt", type=Path, default=None)

    run = sub.add_parser("run-config", help="run one config invocation")
    run.add_argument("--config", required=True, choices=list(CONFIG_SPECS))
    run.add_argument("--invocation", required=True, type=int)
    run.add_argument("--authorization", required=True, type=Path)

    sub.add_parser("freeze-atol", help="freeze numeric atol from T1-A")
    sub.add_parser("analyze", help="build sensitivity report and receipt")

    add = sub.add_parser("addendum", help="write the execution addendum")
    add.add_argument("--preflight-receipt", required=True, type=Path)
    add.add_argument("--tests-status", required=True, choices=("PASS", "FAIL", "PENDING"))

    args = parser.parse_args(argv)
    try:
        if args.command == "preflight":
            config_ids = [args.config] if args.config else list(CONFIG_SPECS)
            payload = _protocol_preflight_receipt(config_ids)
            if args.receipt is not None:
                _write_json(args.receipt, payload)
            print(json.dumps(payload, sort_keys=True))
            return 0
        if args.command == "run-config":
            return _run_config(args.config, args.invocation, args.authorization)
        if args.command == "freeze-atol":
            _freeze_atol()
            return 0
        if args.command == "analyze":
            return _analyze()
        if args.command == "addendum":
            _write_addendum(args.preflight_receipt, args.tests_status)
            return 0
        raise Refused(f"unknown command: {args.command}")
    except Refused as exc:
        print(json.dumps({"status": "REFUSED", "error": str(exc)}, sort_keys=True),
              file=sys.stderr)
        return 2
    except BudgetExhausted as exc:
        print(json.dumps({"status": "BUDGET_EXHAUSTED", "error": str(exc)},
                         sort_keys=True), file=sys.stderr)
        return 1
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error": f"{type(exc).__name__}: {exc}"},
                         sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
