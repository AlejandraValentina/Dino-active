"""Offline perpetual licensing with signed files and a local TRIAL fallback.

Product licensing is deliberately separate from software version and from the
scientific validation status. Licensing errors never delete or block access to
user projects/results; they only change the visible commercial status.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile

from .ed25519 import sign, verify
from .vendor_keys import VENDOR_PUBLIC_KEYS

LICENSE_SCHEMA = "DINO_SIGNED_LICENSE_V1"
PAYLOAD_SCHEMA = "DINO_LICENSE_V1"
STATUS_SCHEMA = "DINO_LICENSE_STATUS_V1"
PRODUCT = "Dino Desktop"
LICENSE_TYPE = "PERPETUAL"
DEFAULT_TRIAL_DAYS = 30
TRIAL_DAYS_ENV = "DINO_TRIAL_DAYS"
TRIAL_POLICY = "PENDING_COMMERCIAL_DECISION"


class LicenseError(ValueError):
    pass


def _now(now=None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_iso(value) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise LicenseError("fecha de licencia inválida")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise LicenseError("fecha de licencia inválida") from exc
    return _now(parsed)


def _canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _inside_repository(path: Path) -> bool:
    for parent in (path, *path.parents):
        if (parent / ".git").exists():
            return True
    return False


def license_root(root=None) -> Path:
    if root is not None:
        candidate = Path(root).expanduser()
    elif os.environ.get("DINO_LICENSE_ROOT"):
        candidate = Path(os.environ["DINO_LICENSE_ROOT"]).expanduser()
    elif os.environ.get("DINO_ARTIFACT_ROOT"):
        candidate = Path(os.environ["DINO_ARTIFACT_ROOT"]).expanduser() / "licensing"
    else:
        candidate = Path.home() / "Dino-artifacts" / "licensing"
    candidate = candidate.resolve()
    if root is not None and _inside_repository(candidate):
        raise LicenseError("la raíz de licencia no puede estar dentro del repositorio")
    if _inside_repository(candidate):
        candidate = (Path.home() / "Dino-artifacts" / "licensing").resolve()
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def validate_payload(payload: dict) -> dict:
    if not isinstance(payload, dict) or payload.get("schema") != PAYLOAD_SCHEMA:
        raise LicenseError("payload de licencia no reconocido")
    if payload.get("product") != PRODUCT:
        raise LicenseError("la licencia no corresponde a Dino Desktop")
    if payload.get("license_type") != LICENSE_TYPE:
        raise LicenseError("sólo se admite licencia perpetua")
    if payload.get("activation") != "OFFLINE":
        raise LicenseError("la licencia debe ser de activación offline")
    if not isinstance(payload.get("license_id"), str) or not payload["license_id"].strip():
        raise LicenseError("license_id inválido")
    _parse_iso(payload.get("issued_at"))
    if "expires_at" in payload or "expiry" in payload:
        raise LicenseError("la licencia perpetua no admite vencimiento")
    return dict(payload)


def sign_license(payload: dict, secret: bytes, key_id: str) -> dict:
    validate_payload(payload)
    signature = base64.b64encode(sign(secret, _canonical(payload))).decode("ascii")
    return {"schema": LICENSE_SCHEMA, "payload": payload,
            "signature": {"algorithm": "Ed25519", "key_id": key_id,
                          "value": signature}}


def verify_license(document: dict, public_keys=None) -> dict:
    keys = dict(public_keys or VENDOR_PUBLIC_KEYS)
    if not isinstance(document, dict) or document.get("schema") != LICENSE_SCHEMA:
        raise LicenseError("archivo de licencia no reconocido")
    signature = document.get("signature")
    if not isinstance(signature, dict) or signature.get("algorithm") != "Ed25519":
        raise LicenseError("firma de licencia no admitida")
    key_id = signature.get("key_id")
    public = keys.get(key_id)
    if public is None:
        raise LicenseError("clave de firma desconocida")
    try:
        raw_signature = base64.b64decode(signature.get("value", ""), validate=True)
    except (ValueError, TypeError) as exc:
        raise LicenseError("firma de licencia inválida") from exc
    payload = validate_payload(document.get("payload"))
    if not verify(public, raw_signature, _canonical(payload)):
        raise LicenseError("firma de licencia no coincide")
    return payload


def activate_license(path, *, root=None, public_keys=None, now=None) -> dict:
    source = Path(path)
    try:
        document = json.loads(source.read_text(encoding="utf-8"))
        payload = verify_license(document, public_keys)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise LicenseError(f"licencia rechazada: {exc}") from exc
    target = license_root(root) / "license.json"
    raw = (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n").encode("utf-8")
    _atomic_write(target, raw)
    return license_status(root=root, public_keys=public_keys, now=now)


def _trial_days(value=None) -> int:
    if value is None:
        value = os.environ.get(TRIAL_DAYS_ENV, DEFAULT_TRIAL_DAYS)
    try:
        days = int(value)
    except (TypeError, ValueError) as exc:
        raise LicenseError("duración TRIAL inválida") from exc
    if not 1 <= days <= 3650:
        raise LicenseError("duración TRIAL fuera de rango")
    return days


def _trial_state(root: Path, now: datetime, trial_days=None) -> dict:
    days = _trial_days(trial_days)
    path = root / "trial.json"
    state = None
    error = None
    try:
        if path.is_file():
            state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        error = str(exc)
    if not isinstance(state, dict) or state.get("schema") != "DINO_TRIAL_STATE_V1":
        state = {"schema": "DINO_TRIAL_STATE_V1", "started_at": _iso(now),
                 "last_seen_at": _iso(now), "trial_days": days,
                 "reset_reason": "MISSING_OR_CORRUPT" if error else "FIRST_RUN"}
    try:
        started = _parse_iso(state.get("started_at"))
        last_seen = _parse_iso(state.get("last_seen_at"))
    except LicenseError:
        started = last_seen = now
        state["reset_reason"] = "CORRUPT_DATES"
    clock_rollback = now < last_seen - timedelta(minutes=5)
    effective = max(now, last_seen)
    state["last_seen_at"] = _iso(effective)
    state["trial_days"] = days
    try:
        _atomic_write(path, (json.dumps(state, sort_keys=True, indent=2,
                                        ensure_ascii=False) + "\n").encode("utf-8"))
    except OSError as exc:
        error = str(exc)
    expires = started + timedelta(days=days)
    remaining = max(0.0, (expires - effective).total_seconds() / 86400.0)
    return {"started_at": _iso(started), "last_seen_at": _iso(effective),
            "trial_days": days, "days_remaining": round(remaining, 2),
            "expired": effective >= expires, "clock_rollback": clock_rollback,
            "storage_error": error, "path": str(path)}


def _label(state: str, trial=None) -> str:
    if state == "LICENSED":
        return "LICENCIA PERPETUA ACTIVA"
    if state == "TRIAL":
        days = trial.get("days_remaining") if trial else None
        return f"TRIAL · {days:g} días" if isinstance(days, (int, float)) else "TRIAL"
    if state == "TRIAL_EXPIRED":
        return "TRIAL VENCIDO · acceso a proyectos conservado"
    if state == "INVALID_LICENSE":
        return "LICENCIA INVÁLIDA · modo TRIAL"
    return "SIN LICENCIA"


def license_status(*, root=None, public_keys=None, now=None, trial_days=None,
                   _trial=None) -> dict:
    current = _now(now)
    try:
        base = license_root(root)
        license_path = base / "license.json"
    except (OSError, LicenseError) as exc:
        return {"schema": STATUS_SCHEMA, "state": "UNLICENSED",
                "label": "SIN LICENCIA", "product": PRODUCT,
                "license_id": None, "customer": None, "issued_at": None,
                "commercial_use": False, "core_access_allowed": True,
                "license_scope": "PRODUCT_ONLY", "error": str(exc)}
    error = None
    if license_path.is_file():
        try:
            payload = verify_license(json.loads(license_path.read_text(encoding="utf-8")),
                                     public_keys)
            return {"schema": STATUS_SCHEMA, "state": "LICENSED",
                    "label": _label("LICENSED"), "product": PRODUCT,
                    "license_id": payload["license_id"],
                    "customer": payload.get("customer"), "issued_at": payload["issued_at"],
                    "license_type": payload["license_type"],
                    "commercial_use": True, "core_access_allowed": True,
                    "license_scope": "PRODUCT_ONLY", "error": None,
                    "license_path": str(license_path)}
        except (OSError, ValueError, TypeError, LicenseError) as exc:
            error = str(exc)
    trial = _trial_state(base, current, trial_days)
    state = "TRIAL_EXPIRED" if trial["expired"] else "TRIAL"
    if error:
        state = "INVALID_LICENSE"
    return {"schema": STATUS_SCHEMA, "state": state, "label": _label(state, trial),
            "product": PRODUCT, "license_id": None, "customer": None, "issued_at": None,
            "commercial_use": False, "core_access_allowed": True,
            "license_scope": "PRODUCT_ONLY", "trial": trial, "error": error,
            "license_path": str(license_path)}
