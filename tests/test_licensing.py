"""CP2 offline licensing: signatures, trial, tamper, reinstall and no blocking."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import base64
import json
import os
from pathlib import Path

import pytest

from motorsim.licensing import ed25519
from motorsim.licensing.license import (DEFAULT_TRIAL_DAYS, LicenseError,
                                        activate_license, license_status,
                                        sign_license, verify_license)


def test_ed25519_rfc8032_vector():
    secret = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    public = ed25519.public_key(secret)
    signature = ed25519.sign(secret, b"")
    assert public.hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    assert signature.hex() == (
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert ed25519.verify(public, signature, b"")
    assert not ed25519.verify(public, signature, b"tampered")


def payload(**changes):
    data = {"schema": "DINO_LICENSE_V1", "product": "Dino Desktop",
            "license_type": "PERPETUAL", "activation": "OFFLINE",
            "license_id": "lic-test-001", "customer": "Synthetic Customer",
            "issued_at": "2026-11-11T12:00:00+00:00"}
    data.update(changes); return data


def signed(tmp_path, secret, *, key_id="test-key", changes=None):
    public = ed25519.public_key(secret)
    document = sign_license(payload(**(changes or {})), secret, key_id)
    path = tmp_path / "customer.dinolicense"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, document, {key_id: public}


def test_signed_license_verifies_and_is_perpetual(tmp_path):
    secret = os.urandom(32)
    path, document, keys = signed(tmp_path, secret)
    assert verify_license(document, keys)["license_id"] == "lic-test-001"
    root = tmp_path / "license-root"
    status = activate_license(path, root=root, public_keys=keys,
                              now=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert status["state"] == "LICENSED"
    assert status["commercial_use"] is True and status["core_access_allowed"] is True
    future = datetime(2099, 1, 1, tzinfo=timezone.utc)
    assert license_status(root=root, public_keys=keys, now=future)["state"] == "LICENSED"


def test_tampered_payload_or_signature_is_rejected(tmp_path):
    secret = os.urandom(32)
    path, document, keys = signed(tmp_path, secret)
    document["payload"]["customer"] = "Changed"
    with pytest.raises(LicenseError):
        verify_license(document, keys)
    document = sign_license(payload(), secret, "test-key")
    document["signature"]["value"] = base64.b64encode(b"x" * 64).decode()
    with pytest.raises(LicenseError):
        verify_license(document, keys)


def test_invalid_license_never_blocks_core_access_and_falls_back_to_trial(tmp_path):
    root = tmp_path / "license-root"; root.mkdir()
    (root / "license.json").write_text('{"schema":"broken"}', encoding="utf-8")
    status = license_status(root=root, now=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert status["state"] == "INVALID_LICENSE"
    assert status["core_access_allowed"] is True
    assert status["commercial_use"] is False
    assert status["error"]


def test_trial_is_configurable_expires_and_detects_clock_rollback(tmp_path):
    root = tmp_path / "license-root"
    start = datetime(2026, 11, 1, tzinfo=timezone.utc)
    first = license_status(root=root, now=start, trial_days=2)
    assert first["state"] == "TRIAL" and first["trial"]["days_remaining"] == 2.0
    later = license_status(root=root, now=start + timedelta(days=3), trial_days=2)
    assert later["state"] == "TRIAL_EXPIRED"
    assert later["core_access_allowed"] is True
    rollback = license_status(root=root, now=start - timedelta(days=1), trial_days=2)
    assert rollback["trial"]["clock_rollback"] is True
    assert rollback["state"] == "TRIAL_EXPIRED"


def test_reinstall_reimports_the_same_signed_file(tmp_path):
    secret = os.urandom(32)
    path, _document, keys = signed(tmp_path, secret)
    root = tmp_path / "license-root"
    activate_license(path, root=root, public_keys=keys)
    (root / "license.json").unlink()
    assert license_status(root=root, public_keys=keys)["state"] in {"TRIAL", "TRIAL_EXPIRED"}
    status = activate_license(path, root=root, public_keys=keys)
    assert status["state"] == "LICENSED" and status["license_id"] == "lic-test-001"


def test_activation_works_with_network_disabled(tmp_path, monkeypatch):
    import socket
    secret = os.urandom(32)
    path, _document, keys = signed(tmp_path, secret)
    monkeypatch.setattr(socket, "socket", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network used")))
    status = activate_license(path, root=tmp_path / "license-root", public_keys=keys)
    assert status["state"] == "LICENSED"


def test_default_trial_policy_is_explicit_and_not_scientific(tmp_path):
    assert DEFAULT_TRIAL_DAYS == 30
    # Licensing does not expose or mutate scientific validation claims.
    status = license_status(root=tmp_path / "license-root", trial_days=1)
    assert "scientific" not in json.dumps(status).lower()
