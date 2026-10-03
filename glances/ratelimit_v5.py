#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — rate limiting of the REST API and Web UI (architecture §4.5).

Two token buckets per client address, in one ASGI middleware that sits
between TrustedHost and CORS, so outside authentication:

- **General** — `[outputs] rate_limit_per_minute`, `rate_limit_burst`. Off by
  default (0): a WebUI tab polls ~30 times a minute and a `-c` client ~90, and
  several of them can share one address behind a NAT.
- **Failed authentication** — `[outputs] auth_fail_per_minute`, 10 by default.
  A request carrying credentials reserves a try on its way in and gets it back
  unless it ends in a 401; an address with no try left gets 429 before its
  credentials reach PBKDF2. Reserving up front is what keeps parallel guesses
  from all getting through while the first ones are still being checked. A
  request without credentials is a browser's first visit, not a guess: it is
  not counted. The try that locks an address out logs one WARNING naming it.

`/status` and `/healthz` are never limited. `/api/5/token` is: it is where a
password is guessed.

The client address is the one uvicorn reports, which already honours
`X-Forwarded-For` from a proxy on 127.0.0.1 (`--forwarded-allow-ips`); the
header itself is never read here. An IPv6 client is counted per /64, the
block one host is usually given, so rotating addresses inside it does not
reset its limit.
"""

from __future__ import annotations

import ipaddress
import logging
import math
import time
from typing import Any

from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Monotonic clock, a module attribute so tests can move it.
_now = time.monotonic

# Clients remembered at most. Past it, the least recently seen is forgotten,
# which hands it a full bucket again: the price of a bounded table.
_MAX_CLIENTS = 10_000

EXEMPT_PATHS: frozenset[str] = frozenset({"/status", "/healthz"})


def _client_key(scope: dict[str, Any]) -> str:
    """The client's address; an IPv6 one reduced to its /64."""
    client = scope.get("client")
    host = client[0] if client else ""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host
    if ip.version == 6:
        if ip.ipv4_mapped is not None:
            return str(ip.ipv4_mapped)
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


class Buckets:
    """One token bucket per client: `per_minute` tokens a minute, `capacity` at most."""

    def __init__(self, per_minute: int, capacity: int) -> None:
        self._rate = per_minute / 60.0
        self._capacity = float(capacity)
        # key -> (tokens, last update); kept in last-seen order.
        self._table: dict[str, tuple[float, float]] = {}

    def __len__(self) -> int:
        return len(self._table)

    def take(self, key: str) -> float:
        """Spend one token. Return 0 if it was there, else the seconds until it is."""
        now = _now()
        tokens = self._level(key, now)
        if tokens >= 1.0:
            self._store(key, tokens - 1.0, now)
            return 0.0
        self._store(key, tokens, now)
        return (1.0 - tokens) / self._rate

    def wait(self, key: str) -> float:
        """Seconds until `key` has a token, without spending or storing anything."""
        now = _now()
        tokens, last = self._table.get(key, (self._capacity, now))
        return max(0.0, 1.0 - min(self._capacity, tokens + (now - last) * self._rate)) / self._rate

    def give_back(self, key: str) -> None:
        now = _now()
        self._store(key, min(self._capacity, self._level(key, now) + 1.0), now)

    def _level(self, key: str, now: float) -> float:
        tokens, last = self._table.pop(key, (self._capacity, now))
        return min(self._capacity, tokens + (now - last) * self._rate)

    def _store(self, key: str, tokens: float, now: float) -> None:
        self._table[key] = (tokens, now)
        if len(self._table) > _MAX_CLIENTS:
            del self._table[next(iter(self._table))]


class RateLimitMiddleware:
    """Pure ASGI middleware: the general limit, then the failed-authentication one."""

    def __init__(self, app: Any, *, per_minute: int, burst: int, auth_fail_per_minute: int) -> None:
        self.app = app
        # A burst left at 0 is one minute's worth of requests.
        self._general = Buckets(per_minute, burst if burst > 0 else per_minute) if per_minute > 0 else None
        self._auth = Buckets(auth_fail_per_minute, auth_fail_per_minute) if auth_fail_per_minute > 0 else None

    def _reserve_auth_try(self, key: str) -> bool:
        return self._auth is None or self._auth.take(key) == 0.0

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        key = _client_key(scope)

        if self._general is not None:
            wait = self._general.take(key)
            if wait:
                await _too_many_requests(wait)(scope, receive, send)
                return

        if self._auth is None or not _has_credentials(scope):
            await self.app(scope, receive, send)
            return

        wait = self._auth.take(key)
        if wait:
            await _too_many_requests(wait)(scope, receive, send)
            return
        status: list[int] = []

        async def watch(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status.append(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, watch)
        finally:
            if status[:1] != [401]:
                self._auth.give_back(key)
            elif wait := self._auth.wait(key):
                # The try that emptied the bucket: once per lockout, naming the
                # address, so a log watcher (fail2ban) can act on it.
                logger.warning(
                    "Too many failed authentications from %s: refused for %d s", key, max(1, math.ceil(wait))
                )


def _has_credentials(scope: dict[str, Any]) -> bool:
    return any(name == b"authorization" and value for name, value in scope.get("headers", []))


def _too_many_requests(wait: float) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
        headers={"Retry-After": str(max(1, math.ceil(wait)))},
    )
