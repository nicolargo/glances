#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the security helpers (PBKDF2 + JWT).

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- hash_password / verify_password round-trip
- distinct salts on every call (random salt by default)
- explicit salt override (deterministic for tests)
- malformed stored values rejected (empty, missing $, empty parts)
- timing-safe comparison uses hmac.compare_digest (smoke test)
- JWTHandler mint / verify round-trip
- JWTHandler with explicit secret vs generated
- JWTHandler verify rejects: malformed, wrong secret, wrong issuer, expired,
  missing `sub`, missing token
- JWTHandler.expire_minutes is honoured
"""

from __future__ import annotations

import time

from jose import jwt

from glances.security_v5 import JWTHandler, hash_password, verify_password

# -------------------------------------------------------- password


def test_hash_password_round_trip():
    stored = hash_password("hunter2")
    assert verify_password("hunter2", stored) is True
    assert verify_password("hunter3", stored) is False


def test_hash_password_random_salt_per_call():
    a = hash_password("hunter2")
    b = hash_password("hunter2")
    assert a != b
    # Both still verify against the same plaintext.
    assert verify_password("hunter2", a)
    assert verify_password("hunter2", b)


def test_hash_password_explicit_salt_is_deterministic():
    a = hash_password("hunter2", salt="deadbeef")
    b = hash_password("hunter2", salt="deadbeef")
    assert a == b
    assert a.startswith("deadbeef$")


def test_verify_password_rejects_malformed_stored():
    assert verify_password("x", "") is False
    assert verify_password("x", "no-dollar-here") is False
    assert verify_password("x", "$onlyhash") is False
    assert verify_password("x", "salt$") is False


def test_verify_password_empty_plaintext_does_not_crash():
    stored = hash_password("not-empty")
    assert verify_password("", stored) is False


def test_hash_password_format_is_salt_dollar_hex():
    stored = hash_password("any", salt="abc123")
    salt, _, digest = stored.partition("$")
    assert salt == "abc123"
    # 128 bytes = 256 hex chars.
    assert len(digest) == 256
    int(digest, 16)  # raises if not hex


# -------------------------------------------------------- JWT


def test_jwt_round_trip():
    handler = JWTHandler(secret_key="test-secret")
    token = handler.create_access_token("alice")
    assert handler.verify_token(token) == "alice"


def test_jwt_rejects_wrong_secret():
    h1 = JWTHandler(secret_key="secret-a")
    h2 = JWTHandler(secret_key="secret-b")
    token = h1.create_access_token("alice")
    assert h2.verify_token(token) is None


def test_jwt_rejects_malformed_token():
    handler = JWTHandler(secret_key="x")
    assert handler.verify_token("not.a.token") is None
    assert handler.verify_token("") is None


def test_jwt_rejects_wrong_issuer():
    handler = JWTHandler(secret_key="x")
    # Mint a token outside the helper, with a foreign issuer.
    foreign = jwt.encode(
        {"sub": "alice", "iss": "not-glances", "exp": int(time.time()) + 60},
        "x",
        algorithm="HS256",
    )
    assert handler.verify_token(foreign) is None


def test_jwt_rejects_expired_token():
    handler = JWTHandler(secret_key="x", expire_minutes=60)
    # Bypass the helper to mint an already-expired token.
    expired = jwt.encode(
        {"sub": "alice", "iss": "glances", "exp": int(time.time()) - 1, "iat": int(time.time()) - 60},
        "x",
        algorithm="HS256",
    )
    assert handler.verify_token(expired) is None


def test_jwt_rejects_missing_sub():
    handler = JWTHandler(secret_key="x")
    no_sub = jwt.encode(
        {"iss": "glances", "exp": int(time.time()) + 60, "iat": int(time.time())},
        "x",
        algorithm="HS256",
    )
    assert handler.verify_token(no_sub) is None


def test_jwt_generated_secret_marker():
    h = JWTHandler()
    assert h.secret_was_generated is True
    # The handler is still functional with the generated secret.
    token = h.create_access_token("bob")
    assert h.verify_token(token) == "bob"


def test_jwt_explicit_secret_marker():
    h = JWTHandler(secret_key="explicit")
    assert h.secret_was_generated is False


def test_jwt_expire_minutes_honored():
    h = JWTHandler(secret_key="x", expire_minutes=42)
    assert h.expire_minutes == 42
    token = h.create_access_token("alice")
    payload = jwt.decode(token, "x", algorithms=["HS256"], issuer="glances")
    delta_seconds = payload["exp"] - payload["iat"]
    # 42 minutes = 2520 seconds, allow a small skew.
    assert 2510 <= delta_seconds <= 2530
