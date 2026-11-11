"""Minimal Ed25519 verification/signing (RFC 8032) without external crypto deps.

The packaged application uses verification only. Signing is restricted to the
offline issuer tool; no private key is embedded in the application.
"""
from __future__ import annotations

import hashlib

P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
D = -121665 * pow(121666, P - 2, P) % P
I = pow(2, (P - 1) // 4, P)


def _sha512_int(data: bytes) -> int:
    return int.from_bytes(hashlib.sha512(data).digest(), "little")


def _inv(value: int) -> int:
    return pow(value, P - 2, P)


def _bit(value: bytes, index: int) -> int:
    return (value[index // 8] >> (index % 8)) & 1


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(D * y * y + 1) % P
    x = pow(xx, (P + 3) // 8, P)
    if (x * x - xx) % P:
        x = x * I % P
    if x & 1:
        x = P - x
    return x


BY = 4 * _inv(5) % P
BX = _xrecover(BY)
B = (BX % P, BY % P, 1, BX * BY % P)


def _edwards(left, right):
    x1, y1, z1, t1 = left
    x2, y2, z2, t2 = right
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = t1 * 2 * D * t2 % P
    dd = z1 * 2 * z2 % P
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _scalarmult(point, scalar: int):
    result = (0, 1, 1, 0)
    while scalar > 0:
        if scalar & 1:
            result = _edwards(result, point)
        point = _edwards(point, point)
        scalar >>= 1
    return result


def _encodepoint(point) -> bytes:
    x, y, z, _ = point
    zi = _inv(z)
    x, y = x * zi % P, y * zi % P
    bits = [(y >> index) & 1 for index in range(255)]
    bits.append(x & 1)
    return sum(bits[index] << index for index in range(256)).to_bytes(32, "little")


def _decodepoint(raw: bytes):
    if len(raw) != 32:
        raise ValueError("punto Ed25519 inválido")
    y = sum(2**index * _bit(raw, index) for index in range(255))
    x = _xrecover(y)
    if (x & 1) != _bit(raw, 255):
        x = P - x
    point = (x, y, 1, x * y % P)
    if (-x * x + y * y - 1 - D * x * x * y * y) % P:
        raise ValueError("punto Ed25519 fuera de curva")
    return point


def public_key(secret: bytes) -> bytes:
    if len(secret) != 32:
        raise ValueError("la clave privada Ed25519 debe tener 32 bytes")
    digest = hashlib.sha512(secret).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 1
    scalar &= ~7
    scalar |= 1 << 254
    return _encodepoint(_scalarmult(B, scalar))


def sign(secret: bytes, message: bytes) -> bytes:
    if len(secret) != 32:
        raise ValueError("la clave privada Ed25519 debe tener 32 bytes")
    digest = hashlib.sha512(secret).digest()
    scalar = int.from_bytes(digest[:32], "little")
    scalar &= (1 << 254) - 1
    scalar &= ~7
    scalar |= 1 << 254
    prefix = digest[32:]
    public = public_key(secret)
    nonce = _sha512_int(prefix + message) % Q
    encoded_r = _encodepoint(_scalarmult(B, nonce))
    challenge = _sha512_int(encoded_r + public + message) % Q
    scalar_s = (nonce + challenge * scalar) % Q
    return encoded_r + scalar_s.to_bytes(32, "little")


def verify(public: bytes, signature: bytes, message: bytes) -> bool:
    try:
        if len(public) != 32 or len(signature) != 64:
            return False
        point_a = _decodepoint(public)
        point_r = _decodepoint(signature[:32])
        scalar_s = int.from_bytes(signature[32:], "little")
        if scalar_s >= Q:
            return False
        challenge = _sha512_int(_encodepoint(point_r) + public + message) % Q
        return _encodepoint(_scalarmult(B, scalar_s)) == _encodepoint(
            _edwards(point_r, _scalarmult(point_a, challenge)))
    except (ValueError, TypeError, IndexError):
        return False
