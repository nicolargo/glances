#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the remote client: a local store filled from a v5 server.

Design: ``docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md`` §4.1
to §4.4 (chantier P3-1).

- One ``GET /api/5/all`` per cycle, written to the local store as is,
  ``_levels`` included: the TUI shows the server's thresholds, as v4's client
  did. The server's schema (``/api/5/all/info``) drives the display, so a newer
  client shows an older server faithfully.
- The client polls at its own ``[global] refresh``. A server that collects less
  often answers with the same data until it has new data; that is not a
  failure, only a failed request counts toward ``DISCONNECTED``.
- Authentication: one token per connection (``POST /api/5/token``), not Basic
  credentials on every poll, because the server checks a password with PBKDF2,
  which is slow by design. Credentials never go into a URL.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any
from urllib.parse import urlsplit

import requests

logger = logging.getLogger(__name__)

DEFAULT_PORT = 61208
DEFAULT_TIMEOUT = 3.0
DEFAULT_STALE_MAX_CYCLES = 3


class RemoteError(Exception):
    """The server could not be read (unreachable, timeout, unexpected answer)."""


class AuthError(RemoteError):
    """The server refused the credentials, or wants some and got none."""


class NotAGlancesV5Server(RemoteError):
    """Something answered, but not the Glances v5 API."""


def parse_target(target: str) -> tuple[str, str]:
    """`host`, `host:port`, `[v6]:port` or an `http(s)://` URL -> (base URL, host)."""
    if "://" not in target:
        target = f"http://{target}"
    parts = urlsplit(target)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError(f"not a server address: {target!r}")
    host = parts.hostname
    port = parts.port or DEFAULT_PORT
    netloc = f"[{host}]:{port}" if ":" in host else f"{host}:{port}"
    return f"{parts.scheme}://{netloc}{parts.path.rstrip('/')}", host


def _is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class RemoteConnection:
    """One `requests` session to one server, with its token. Synchronous: callers use `to_thread`."""

    def __init__(
        self,
        base_url: str,
        username: str = "glances",
        password: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        verify: bool | str = True,
    ) -> None:
        self.base_url = base_url
        self._username = username
        self._password = password
        self._timeout = timeout
        self._session = requests.Session()
        self._session.verify = verify
        self._token: str | None = None
        self._auth_checked = False
        plain_http = base_url.startswith("http://")
        if password and plain_http and not _is_loopback(urlsplit(base_url).hostname or ""):
            logger.warning(
                "Sending credentials to %s over plain HTTP: use an https:// URL behind a TLS proxy", base_url
            )

    def _authenticate(self) -> None:
        """Trade the password for a token, once. A server without auth answers 404: go on without."""
        self._auth_checked = True
        try:
            response = self._session.post(
                f"{self.base_url}/api/5/token", auth=(self._username, self._password or ""), timeout=self._timeout
            )
        except requests.RequestException as e:
            self._auth_checked = False
            raise RemoteError(f"{self.base_url}: {e}") from e
        if response.status_code == 404:
            self._token = None
        elif response.status_code == 401:
            raise AuthError(f"{self.base_url} refused the username or password")
        elif response.ok:
            self._token = response.json().get("access_token")
        else:
            raise RemoteError(f"{self.base_url}/api/5/token answered HTTP {response.status_code}")

    def get_json(self, path: str) -> Any:
        """`GET base_url + path` as JSON. Takes a token first if a password is set."""
        if self._password and not self._auth_checked:
            self._authenticate()
        for attempt in (1, 2):
            headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
            try:
                response = self._session.get(f"{self.base_url}{path}", headers=headers, timeout=self._timeout)
            except requests.RequestException as e:
                raise RemoteError(f"{self.base_url}: {e}") from e
            if response.status_code == 401:
                if self._password and attempt == 1:
                    self._authenticate()  # the token may have expired: one new one, then give up
                    continue
                raise AuthError(f"{self.base_url} requires a password: use --password, or [passwords] in glances.conf")
            if not response.ok:
                raise RemoteError(f"{self.base_url}{path} answered HTTP {response.status_code}")
            try:
                return response.json()
            except ValueError as e:
                raise NotAGlancesV5Server(f"{self.base_url}{path} did not answer JSON") from e
        raise AuthError(f"{self.base_url} refused the new token")  # pragma: no cover -- loop always returns or raises


class RemoteSource:
    """Fills a store from one server, and tells the TUI what to show.

    `registry` and `fields_by_plugin` are the objects the TUI reads. They are
    filled in place on the first successful connection, so a TUI started while
    the server was unreachable shows the server's blocks once it answers.
    Until then the registry holds `system` alone: its renderer draws the
    "Disconnected from <host>" line with no payload at all.
    """

    def __init__(
        self,
        connection: RemoteConnection,
        store: Any,
        host: str,
        hidden_plugins: set[str] | None = None,
        stale_max_cycles: int = DEFAULT_STALE_MAX_CYCLES,
    ) -> None:
        self.connection = connection
        self.store = store
        self.host = host
        self.registry: list[tuple[str, bool]] = [("system", False)]
        self.fields_by_plugin: dict[str, dict[str, Any]] = {"system": {}}
        self._hidden = hidden_plugins or set()
        self._stale_max_cycles = stale_max_cycles
        self._schema_loaded = False
        self._failures = 0
        self._cleared = False
        self._last_error: str | None = None
        self.connected = False

    def status(self) -> tuple[str, str]:
        """`("connected" | "disconnected", host)`, for the TUI's header."""
        return ("connected" if self.connected else "disconnected", self.host)

    def connect(self) -> None:
        """Check the server speaks API 5, then load its schema. Synchronous."""
        status = self.connection.get_json("/status")
        if not isinstance(status, dict) or str(status.get("version")) != "5":
            raise NotAGlancesV5Server(
                f"{self.connection.base_url} is not a Glances v5 server (its /status says {status!r})"
            )
        info = self.connection.get_json("/api/5/all/info")
        if not isinstance(info, dict):
            raise NotAGlancesV5Server(f"{self.connection.base_url}/api/5/all/info is not a schema")
        registry = []
        for name, fields in info.items():
            if not isinstance(fields, dict) or name in self._hidden:
                continue
            is_collection = any(isinstance(f, dict) and f.get("primary_key") for f in fields.values())
            registry.append((name, is_collection))
            self.fields_by_plugin[name] = fields
        if "system" not in info:
            # The header line carries the connection status: keep it.
            registry.insert(0, ("system", False))
        # One assignment, so the TUI thread never reads a half-built list.
        self.registry[:] = registry
        self._schema_loaded = True
        # The server answered: that is "Connected to", even before the first
        # /api/5/all has landed.
        self.connected = True

    async def poll_once(self) -> None:
        """One cycle: connect if needed, read `/api/5/all`, publish it. Never raises."""
        try:
            if not self._schema_loaded:
                await asyncio.to_thread(self.connect)
            payloads = await asyncio.to_thread(self.connection.get_json, "/api/5/all")
            if not isinstance(payloads, dict):
                raise NotAGlancesV5Server(f"{self.connection.base_url}/api/5/all is not a dict")
            for name, payload in payloads.items():
                if isinstance(payload, (dict, list)):
                    await self.store.set(name, payload)
        except RemoteError as e:
            self._failed(str(e))
            await self._clear_if_stale()
            return
        if not self.connected and self._last_error:
            logger.info("Reconnected to %s", self.connection.base_url)
        self.connected = True
        self._failures = 0
        self._cleared = False
        self._last_error = None

    def _failed(self, error: str) -> None:
        self._failures += 1
        self.connected = False
        if error != self._last_error:
            # Once per distinct error, not once per cycle.
            logger.warning("Cannot read %s: %s", self.connection.base_url, error)
            self._last_error = error

    async def _clear_if_stale(self) -> None:
        """After `stale_max_cycles` failed cycles, stop showing the last known values (§6)."""
        if self._cleared or self._failures < self._stale_max_cycles:
            return
        for name in self.store.keys():
            await self.store.set(name, {})
        self._cleared = True

    async def run_forever(self, refresh: float) -> None:
        """Poll every `refresh` seconds, the client's own cadence, until cancelled."""
        while True:
            await self.poll_once()
            await asyncio.sleep(refresh)
