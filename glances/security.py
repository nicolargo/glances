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
- ``KnownCredentials`` — the ``Authorization`` values already proven good,
  which the rate limiter lets through and the auth middleware does not
  re-check with PBKDF2.

The v4 modules are intentionally not imported — v5 keeps a clean boundary.
Stored password hashes are *not* byte-compatible across v4 ↔ v5 because v4
applied an extra ``pbkdf2(..., salt='')`` pre-hash. v5 drops that pre-hash;
migrating users must regenerate the stored hash via the v5 CLI (Phase 1.7).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import anyio
from jose import JWTError, jwt

logger = logging.getLogger(__name__)

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


# PBKDF2 is ~50-250 ms of CPU per check. Two at a time, process-wide: a flood
# of unseen Basic headers (one per address, past the failed-login limiter)
# can no longer fill the thread pool and the host's cores (security audit
# 2026-10-17, A1 / W-2). Good credentials are checked once, then remembered
# (`KnownCredentials`), so this never queues the users already logged in.
_VERIFY_LIMITER = anyio.CapacityLimiter(2)


async def verify_password_in_thread(plaintext: str, stored: str) -> bool:
    """`verify_password` off the event loop, at most two checks at a time."""
    return await anyio.to_thread.run_sync(verify_password, plaintext, stored, limiter=_VERIFY_LIMITER)


# ----------------------------------------------------- JWT bearer tokens

_JWT_ALG = "HS256"
_JWT_ISSUER = "glances"
_DEFAULT_EXPIRE_MINUTES = 60
# A configured key shorter than this, or the example shipped in glances.conf,
# is refused: anyone could mint a token (security audit 2026-10-17, A2).
_MIN_SECRET_BYTES = 32
_EXAMPLE_SECRET = "your-secure-secret-key-here"
_MAX_EXPIRE_MINUTES = 24 * 60


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

    def __init__(
        self,
        secret_key: str | None = None,
        expire_minutes: int = _DEFAULT_EXPIRE_MINUTES,
        username: str | None = None,
    ) -> None:
        if secret_key and (secret_key == _EXAMPLE_SECRET or len(secret_key.encode()) < _MIN_SECRET_BYTES):
            logger.warning(
                "[outputs] jwt_secret_key is the example value or shorter than %d bytes: ignored, "
                "using an ephemeral key (tokens become invalid on every restart)",
                _MIN_SECRET_BYTES,
            )
            secret_key = None
        self._secret_was_generated = not secret_key
        self._secret_key = secret_key or secrets.token_urlsafe(32)
        expire_minutes = int(expire_minutes)
        if expire_minutes > _MAX_EXPIRE_MINUTES:
            logger.warning("[outputs] jwt_expire_minutes=%d capped to %d", expire_minutes, _MAX_EXPIRE_MINUTES)
            expire_minutes = _MAX_EXPIRE_MINUTES
        self._expire_minutes = expire_minutes
        # When set, a token is only valid for this user (the one who can mint them).
        self._username = username

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
                options={"require_exp": True, "require_iat": True},
            )
        except JWTError:
            return None
        sub = payload.get("sub")
        if not isinstance(sub, str):
            return None
        if self._username is not None and not hmac.compare_digest(sub.encode(), self._username.encode()):
            return None
        return sub


# ----------------------------------------------------- known credentials

# Basic headers remembered at most. One password gives one good header per
# username spelling, so a handful is plenty; the bound only caps memory.
_MAX_KNOWN_BASIC = 64


class KnownCredentials:
    """The ``Authorization`` values already proven good (security audit 2026-10-04, M3).

    The failed-login limiter runs before authentication, so on its own it
    refuses the right password too while an address is locked out, and every
    client behind one proxy or NAT shares that address. With this, a request
    whose credentials are known good spends no try and is never refused:

    - a Bearer token is known good when it verifies (an HMAC, no PBKDF2);
    - a Basic header is known good once it has passed PBKDF2. Only an HMAC of
      it, under a key drawn per process, is kept, so the plain password never
      stays in memory; the set is lost on restart, as is the config it was
      checked against.

    A request with credentials never seen before still spends a try.
    """

    def __init__(self, jwt_handler: JWTHandler) -> None:
        self._jwt_handler = jwt_handler
        self._key = secrets.token_bytes(32)
        self._basic: dict[bytes, None] = {}

    def is_known(self, authorization: str) -> bool:
        if authorization.startswith("Bearer "):
            return self._jwt_handler.verify_token(authorization[len("Bearer ") :].strip()) is not None
        return self._digest(authorization) in self._basic

    def remember(self, authorization: str) -> None:
        """Record a Basic header that has just passed the password check."""
        self._basic[self._digest(authorization)] = None
        if len(self._basic) > _MAX_KNOWN_BASIC:
            del self._basic[next(iter(self._basic))]

    def _digest(self, authorization: str) -> bytes:
        return hmac.new(self._key, authorization.encode(), hashlib.sha256).digest()
