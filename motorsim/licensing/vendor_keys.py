"""Public verification keys shipped with the application.

Private keys are never embedded. The offline issuer tool holds the private key
outside the repository and signs license payloads with Ed25519.
"""
from __future__ import annotations

VENDOR_PUBLIC_KEYS = {
    "vendor-2026-01": bytes.fromhex(
        "81c0857287f7f7aa217b1d270ca95cee9364d2f0f0f59960a39343352bd5dfc8"
    ),
}
