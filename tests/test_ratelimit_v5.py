#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — rate limiting (architecture §4.5).

Two limits, per client address:
- the general one, `[outputs] rate_limit_per_minute` / `rate_limit_burst`,
  off by default;
- failed authentication, `[outputs] auth_fail_per_minute` (10 by default):
  a request carrying credentials that ends in a 401 spends one token, and an
  address with none left gets 429 before its credentials are checked.
"""

from __future__ import annotations

import base64
import os

import pytest
from fastapi.testclient import TestClient

from glances import ratelimit_v5, webserver_v5
from glances.config_v5 import GlancesConfigV5
from glances.security_v5 import hash_password
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import build_app

PASSWORD_HASH = hash_password("hunter2")


@pytest.fixture
def config_factory(tmp_path, monkeypatch):
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for env_key in list(os.environ):
        if env_key.startswith("GLANCES_"):
            monkeypatch.delenv(env_key, raising=False)

    def make(**outputs) -> GlancesConfigV5:
        for key, value in outputs.items():
            monkeypatch.setenv(f"GLANCES_OUTPUTS__{key.upper()}", str(value))
        return GlancesConfigV5()

    return make


@pytest.fixture
def clock(monkeypatch):
    """A frozen monotonic clock the test moves by hand."""
    now = [1000.0]
    monkeypatch.setattr(ratelimit_v5, "_now", lambda: now[0])
    return now


@pytest.fixture
def pbkdf2_calls(monkeypatch):
    """Count the password checks the auth middleware runs."""
    calls = []
    real = webserver_v5.verify_password

    def counting(password, password_hash):
        calls.append(password)
        return real(password, password_hash)

    monkeypatch.setattr(webserver_v5, "verify_password", counting)
    return calls


def _client(config, ip="192.0.2.1") -> TestClient:
    return TestClient(build_app(config=config, store=StatsStoreV5()), client=(ip, 50000))


def _basic(user: str, password: str) -> dict[str, str]:
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


# ----------------------------------------------------------- general limit


def test_the_general_limit_is_off_by_default(config_factory, clock):
    client = _client(config_factory())
    assert {client.get("/api/5/pluginslist").status_code for _ in range(200)} == {200}


def test_the_general_limit_answers_429_past_the_burst(config_factory, clock):
    client = _client(config_factory(rate_limit_per_minute=60, rate_limit_burst=3))
    assert [client.get("/api/5/pluginslist").status_code for _ in range(4)] == [200, 200, 200, 429]
    refused = client.get("/api/5/pluginslist")
    assert refused.status_code == 429
    assert refused.headers["Retry-After"] == "1"
    assert refused.json() == {"detail": "Too many requests"}


def test_the_bucket_refills_at_the_configured_rate(config_factory, clock):
    client = _client(config_factory(rate_limit_per_minute=60, rate_limit_burst=1))
    assert client.get("/api/5/pluginslist").status_code == 200
    assert client.get("/api/5/pluginslist").status_code == 429
    clock[0] += 1.0  # 60 per minute: one token a second
    assert client.get("/api/5/pluginslist").status_code == 200


def test_a_zero_burst_means_one_minute_of_requests(config_factory, clock):
    client = _client(config_factory(rate_limit_per_minute=5))
    assert [client.get("/api/5/pluginslist").status_code for _ in range(6)] == [200] * 5 + [429]


def test_the_probes_are_never_limited(config_factory, clock):
    client = _client(config_factory(rate_limit_per_minute=60, rate_limit_burst=1))
    client.get("/api/5/pluginslist")
    assert {client.get(path).status_code for path in ["/status", "/healthz"] * 5} == {200}


def test_the_token_route_is_limited(config_factory, clock):
    client = _client(config_factory(password=PASSWORD_HASH, rate_limit_per_minute=60, rate_limit_burst=1))
    client.get("/status")
    client.post("/api/5/token", headers=_basic("glances", "hunter2"))
    assert client.post("/api/5/token", headers=_basic("glances", "hunter2")).status_code == 429


def test_each_address_has_its_own_bucket(config_factory, clock):
    config = config_factory(rate_limit_per_minute=60, rate_limit_burst=1)
    app = build_app(config=config, store=StatsStoreV5())
    first = TestClient(app, client=("192.0.2.1", 50000))
    second = TestClient(app, client=("192.0.2.2", 50000))
    assert first.get("/api/5/pluginslist").status_code == 200
    assert first.get("/api/5/pluginslist").status_code == 429
    assert second.get("/api/5/pluginslist").status_code == 200


def test_an_ipv6_slash_64_shares_one_bucket(config_factory, clock):
    """One host owns a whole /64: rotating inside it must not reset the limit."""
    config = config_factory(rate_limit_per_minute=60, rate_limit_burst=1)
    app = build_app(config=config, store=StatsStoreV5())
    assert TestClient(app, client=("2001:db8::1", 50000)).get("/api/5/pluginslist").status_code == 200
    assert TestClient(app, client=("2001:db8::2", 50000)).get("/api/5/pluginslist").status_code == 429
    assert TestClient(app, client=("2001:db8:0:1::1", 50000)).get("/api/5/pluginslist").status_code == 200


# --------------------------------------------------- failed authentication


def test_failed_logins_are_cut_off_before_the_password_check(config_factory, clock, pbkdf2_calls):
    client = _client(config_factory(password=PASSWORD_HASH))
    codes = [client.get("/api/5/pluginslist", headers=_basic("glances", "guess")).status_code for _ in range(11)]
    assert codes == [401] * 10 + [429]
    assert len(pbkdf2_calls) == 10, "the 11th guess must not reach PBKDF2"
    # Even the right password waits: the address is out of tries.
    assert client.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 429


def test_failed_logins_on_the_token_route_count_too(config_factory, clock):
    client = _client(config_factory(password=PASSWORD_HASH, auth_fail_per_minute=2))
    codes = [client.post("/api/5/token", headers=_basic("glances", "guess")).status_code for _ in range(3)]
    assert codes == [401, 401, 429]


def test_a_request_without_credentials_is_not_a_failed_login(config_factory, clock):
    """A browser's first request carries no credentials and gets the 401 challenge."""
    client = _client(config_factory(password=PASSWORD_HASH, auth_fail_per_minute=2))
    assert {client.get("/api/5/pluginslist").status_code for _ in range(10)} == {401}
    assert client.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 200


def test_successful_logins_spend_nothing(config_factory, clock):
    client = _client(config_factory(password=PASSWORD_HASH, auth_fail_per_minute=2))
    for _ in range(10):
        assert client.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 200
    assert client.get("/api/5/pluginslist", headers=_basic("glances", "guess")).status_code == 401


def test_the_failed_login_tries_come_back(config_factory, clock):
    client = _client(config_factory(password=PASSWORD_HASH, auth_fail_per_minute=2))
    for _ in range(2):
        client.get("/api/5/pluginslist", headers=_basic("glances", "guess"))
    assert client.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 429
    clock[0] += 30.0  # 2 per minute: one try back every 30 s
    assert client.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 200


def test_the_failed_login_limit_can_be_turned_off(config_factory, clock):
    client = _client(config_factory(password=PASSWORD_HASH, auth_fail_per_minute=0))
    assert {client.get("/api/5/pluginslist", headers=_basic("glances", "guess")).status_code for _ in range(15)} == {
        401
    }


def test_another_address_is_not_locked_out(config_factory, clock):
    config = config_factory(password=PASSWORD_HASH, auth_fail_per_minute=1)
    app = build_app(config=config, store=StatsStoreV5())
    attacker = TestClient(app, client=("192.0.2.66", 50000))
    for _ in range(3):
        attacker.get("/api/5/pluginslist", headers=_basic("glances", "guess"))
    user = TestClient(app, client=("192.0.2.1", 50000))
    assert user.get("/api/5/pluginslist", headers=_basic("glances", "hunter2")).status_code == 200


# ------------------------------------------------------------------ table


async def test_concurrent_guesses_cannot_overspend(clock):
    """A try is reserved on the way in, so parallel guesses cannot all slip through."""
    seen = []

    async def app(scope, receive, send):
        seen.append(scope["path"])
        await send({"type": "http.response.start", "status": 401, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    limiter = ratelimit_v5.RateLimitMiddleware(app, per_minute=0, burst=0, auth_fail_per_minute=2)
    scope = {
        "type": "http",
        "path": "/api/5/cpu",
        "client": ("192.0.2.1", 1),
        "headers": [(b"authorization", b"Basic eDp5")],
    }
    sent = []

    async def send(message):
        sent.append(message)

    async def receive():
        return {"type": "http.request"}

    # Reserve two tries without letting either finish, then a third arrives.
    assert limiter._reserve_auth_try(ratelimit_v5._client_key(scope))
    assert limiter._reserve_auth_try(ratelimit_v5._client_key(scope))
    await limiter(scope, receive, send)
    assert sent[0]["status"] == 429
    assert seen == []


def test_the_table_stays_bounded(clock, monkeypatch):
    monkeypatch.setattr(ratelimit_v5, "_MAX_CLIENTS", 3)
    buckets = ratelimit_v5.Buckets(per_minute=60, capacity=1)
    for i in range(10):
        buckets.take(f"192.0.2.{i}")
    assert len(buckets) <= 3
