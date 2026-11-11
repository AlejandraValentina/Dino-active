"""Offline license issuer tool. Never embed or ship private keys with the app."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.licensing.ed25519 import public_key  # noqa: E402
from motorsim.licensing.license import sign_license, verify_license  # noqa: E402


def _secret(path):
    raw = Path(path).read_text(encoding="ascii").strip()
    secret = bytes.fromhex(raw)
    if len(secret) != 32:
        raise ValueError("la clave privada debe ser 32 bytes hexadecimales")
    return secret


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate-key")
    generate.add_argument("--private-key-out", type=Path, required=True)
    generate.add_argument("--public-key-out", type=Path, required=True)
    generate.add_argument("--force", action="store_true")
    sign = sub.add_parser("sign")
    sign.add_argument("--private-key", type=Path, required=True)
    sign.add_argument("--key-id", default="vendor-2026-01")
    sign.add_argument("--payload", type=Path, required=True)
    sign.add_argument("--out", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--license", type=Path, required=True)
    verify.add_argument("--public-key", required=True, help="hex Ed25519 public key")
    verify.add_argument("--key-id", default="vendor-2026-01")
    args = parser.parse_args(argv)

    if args.command == "generate-key":
        if not args.force and (args.private_key_out.exists() or args.public_key_out.exists()):
            raise SystemExit("destino existente; use --force sólo si controla la custodia")
        secret = os.urandom(32)
        args.private_key_out.parent.mkdir(parents=True, exist_ok=True)
        args.public_key_out.parent.mkdir(parents=True, exist_ok=True)
        args.private_key_out.write_text(secret.hex() + "\n", encoding="ascii")
        args.public_key_out.write_text(public_key(secret).hex() + "\n", encoding="ascii")
        try:
            args.private_key_out.chmod(0o600)
        except OSError:
            pass
        print(json.dumps({"public_key": public_key(secret).hex(),
                          "private_key": str(args.private_key_out)}))
        return 0

    if args.command == "sign":
        payload = json.loads(args.payload.read_text(encoding="utf-8"))
        document = sign_license(payload, _secret(args.private_key), args.key_id)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(document, sort_keys=True, indent=2,
                                       ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"license": str(args.out), "license_id": payload.get("license_id")}))
        return 0

    document = json.loads(args.license.read_text(encoding="utf-8"))
    payload = verify_license(document, {args.key_id: bytes.fromhex(args.public_key)})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
