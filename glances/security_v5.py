#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 security helpers — password hashing + JWT.

Two primitives, both kept algorithmically equivalent to v4 (CVE-2026-32596
"Carry forward"):

- ``hash_password(plain)`` / ``verify_password(plain, stored)`` — PBKDF2-SHA256,
  100 000 iterations, ``dklen=128``, hex-encoded ``salt$hash`` storage. Salt is
  a UUID4 hex (matching v4 ``glances/password.py``).
- ``JWTHandler`` — HS256 JWT minting and verification, with ``sub`` / ``exp``
  / ``iat`` / ``iss`` claims. Same algorithm and claim shape as v4
  ``glances/jwt_utils.py``.

The v4 modules are intentionally not imported — v5 keeps a clean boundary.
Stored password hashes are *not* byte-compatible across v4 ↔ v5 because v4
applied an extra ``pbkdf2(..., salt='')`` pre-hash. v5 drops that pre-hash;
migrating users must regenerate the stored hash via the v5 CLI (Phase 1.7).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

# ----------------------------------------------------- password hashing

_PBKDF2_ITERATIONS = 100_000
_PBKDF2_HASH = "sha256"
_PBKDF2_DKLEN = 128


def hash_password(plaintext: str, *, salt: str | None = None) -> str:
    """Return ``salt$hex(pbkdf2)`` for ``plaintext``.

    The salt is a UUID4 hex string when not supplied. Use this function once
    to produce the value placed into ``[outputs] password=`` in
    ``glances.conf``. The plaintext itself is never stored.
    """
    if salt is None:
        salt = uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH,
        plaintext.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
        dklen=_PBKDF2_DKLEN,
    ).hex()
    return f"{salt}${digest}"


def verify_password(plaintext: str, stored: str) -> bool:
    """Constant-time comparison of ``plaintext`` against a ``salt$hex`` hash.

    Returns ``False`` on any structural problem (missing separator, invalid
    salt) rather than raising — callers should not branch on the failure
    mode, only on the boolean result.
    """
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    if not salt or not expected:
        return False
    candidate = hashlib.pbkdf2_hmac(
        _PBKDF2_HASH,
        plaintext.encode("utf-8"),
        salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
        dklen=_PBKDF2_DKLEN,
    ).hex()
    return hmac.compare_digest(candidate, expected)


# ----------------------------------------------------- JWT bearer tokens

_JWT_ALG = "HS256"
_JWT_ISSUER = "glances"
_DEFAULT_EXPIRE_MINUTES = 60


class JWTHandler:
    """Mint and verify HS256 JWTs for the Glances REST API.

    Mirrors v4 ``glances/jwt_utils.py``: same algorithm, same claim shape, so
    a JWT minted by a v4 server is decodable by a v5 server sharing the
    secret (and vice versa).

    A missing ``secret_key`` triggers generation of a per-process random key.
    Tokens minted against an ephemeral secret survive only until restart —
    a startup INFO is logged so operators know to set ``[outputs]
    jwt_secret_key`` in long-running deployments.
    """

    def __init__(self, secret_key: str | None = None, expire_minutes: int = _DEFAULT_EXPIRE_MINUTES) -> None:
        self._secret_was_generated = not secret_key
        self._secret_key = secret_key or secrets.token_urlsafe(32)
        self._expire_minutes = expire_minutes

    @property
    def expire_minutes(self) -> int:
        return self._expire_minutes

    @property
    def secret_was_generated(self) -> bool:
        return self._secret_was_generated

    def create_access_token(self, username: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": username,
            "exp": now + timedelta(minutes=self._expire_minutes),
            "iat": now,
            "iss": _JWT_ISSUER,
        }
        return jwt.encode(payload, self._secret_key, algorithm=_JWT_ALG)

    def verify_token(self, token: str) -> str | None:
        """Return the ``sub`` claim if ``token`` is valid, else ``None``."""
        if not token:
            return None
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[_JWT_ALG],
                issuer=_JWT_ISSUER,
            )
        except JWTError:
            return None
        sub = payload.get("sub")
        if not isinstance(sub, str):
            return None
        return sub
