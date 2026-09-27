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
- The alert block mirrors the server's (``/api/5/alert`` and
  ``/api/5/alert/incidents``, same cycle): the client runs no alert engine,
  so no alert actions either; the server is the one that acts.
- ``--export`` works under ``-c`` (issue #1527): a ``RemotePlugin`` per server
  plugin, built from the server's schema, answers ``get_export()`` from the
  local store.
- A disconnected client keeps showing the last values it received, with
  the time they were received (maintainer, 2026-09-27): the store is never
  cleared.
- Authentication: one token per connection (``POST /api/5/token``), not Basic
  credentials on every poll, because the server checks a password with PBKDF2,
  which is slow by design. Credentials never go into a URL.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import time
from typing import Any
from urllib.parse import urlsplit

import requests

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.processlist.model_v5 import PluginModel as _Processlist

logger = logging.getLogger(__name__)

DEFAULT_PORT = 61208
DEFAULT_TIMEOUT = 3.0


class RemoteError(Exception):
    """The server could not be read (unreachable, timeout, unexpected answer)."""


class AuthError(RemoteError):
    """The server refused the credentials, or wants some and got none."""


class NotAGlancesV5Server(RemoteError):
    """Something answered, but not the Glances v5 API."""


class NotFound(RemoteError):
    """The server answered 404: a route it does not serve (alerts disabled, unknown pid)."""


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
        return self._request("get", path)

    def post_json(self, path: str) -> Any:
        """`POST base_url + path`, no body, as JSON: the server's pin routes."""
        return self._request("post", path)

    def _request(self, method: str, path: str) -> Any:
        if self._password and not self._auth_checked:
            self._authenticate()
        send = getattr(self._session, method)
        for attempt in (1, 2):
            headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
            try:
                response = send(f"{self.base_url}{path}", headers=headers, timeout=self._timeout)
            except requests.RequestException as e:
                raise RemoteError(f"{self.base_url}: {e}") from e
            if response.status_code == 401:
                if self._password and attempt == 1:
                    self._authenticate()  # the token may have expired: one new one, then give up
                    continue
                raise AuthError(f"{self.base_url} requires a password: use --password, or [passwords] in glances.conf")
            if response.status_code == 404:
                raise NotFound(f"{self.base_url}{path} answered HTTP 404")
            if not response.ok:
                raise RemoteError(f"{self.base_url}{path} answered HTTP {response.status_code}")
            try:
                return response.json()
            except ValueError as e:
                raise NotAGlancesV5Server(f"{self.base_url}{path} did not answer JSON") from e
        raise AuthError(f"{self.base_url} refused the new token")  # pragma: no cover -- loop always returns or raises


class RemoteAlerts:
    """The server's alert engine, read-only: the methods the TUI calls on `GlancesAlerts`.

    Built from `/api/5/alert` (the transition log) and `/api/5/alert/incidents`.
    The incidents' ongoing rows give back the engine's `ongoing`, `since` and
    `top` maps, so the TUI derives exactly the incidents the server does.
    Each `update` replaces whole objects: the TUI thread never sees a half.
    """

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []
        self._initializing = False
        self._ongoing: dict[tuple[str, Any, str], str] = {}
        self._since: dict[tuple[str, Any, str], str] = {}
        self._top: dict[tuple[str, Any, str], dict[str, Any]] = {}

    def update(self, history: Any, incidents: Any) -> None:
        if not isinstance(history, list) or not isinstance(incidents, dict):
            raise NotAGlancesV5Server("the alert routes did not answer as Glances v5 does")
        ongoing, since, top = {}, {}, {}
        for incident in incidents.get("incidents") or []:
            if not isinstance(incident, dict) or not incident.get("ongoing"):
                continue
            state_key = (str(incident.get("plugin", "")), incident.get("key"), str(incident.get("field", "")))
            ongoing[state_key] = str(incident.get("level", ""))
            if incident.get("begin") and not incident.get("partial"):
                since[state_key] = incident["begin"]
            top[state_key] = {"top": list(incident.get("top") or []), "top_sort": incident.get("top_sort")}
        self._history, self._ongoing, self._since, self._top = history, ongoing, since, top
        self._initializing = bool(incidents.get("is_initializing"))

    def clear(self) -> None:
        """The server runs no alert engine: nothing to mirror."""
        self.update([], {})

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def is_initializing(self) -> bool:
        return self._initializing

    def get_ongoing(self) -> dict[tuple[str, Any, str], str]:
        return dict(self._ongoing)

    def get_ongoing_since(self) -> dict[tuple[str, Any, str], str]:
        return dict(self._since)

    def get_ongoing_top(self) -> dict[tuple[str, Any, str], dict[str, Any]]:
        return dict(self._top)


class RemotePlugin(GlancesPluginBase):
    """A server's plugin, for the exporters: `get_export()` from the local store.

    Built from the server's `fields_description` (`remote_plugins`), never
    from the local plugin class: some do real work in `__init__` (`ports`
    starts a scan thread), and a newer client must export an older server's
    fields as the server has them. It never collects.
    """

    # `[processlist] export` (or `--export-process-filter`) applies here as
    # on a server: by default no process is exported (v4 #794).
    _PROCESS_LISTS = ("processlist", "programlist")

    def __init__(self, store: Any, config: Any) -> None:
        super().__init__(store, config)
        self._export_patterns = (
            self._compile_filter("export", section="processlist") if self.plugin_name in self._PROCESS_LISTS else []
        )

    async def _grab_stats(self) -> Any:  # pragma: no cover -- never scheduled
        raise RuntimeError("a remote plugin never collects")

    def get_export(self) -> dict[str, Any] | list[dict[str, Any]]:
        export = super().get_export()
        if self.plugin_name not in self._PROCESS_LISTS:
            return export
        if not self._export_patterns:
            return []
        # The processlist model's own rule, not a copy: it reads `_export_patterns` only.
        return [item for item in export if _Processlist._matches_export(self, item)]  # type: ignore[arg-type]


def remote_plugins(schema: dict[str, Any], store: Any, config: Any, not_exportable: set[str]) -> list[RemotePlugin]:
    """One `RemotePlugin` per plugin of the server's schema (`/api/5/all/info`), for the exporters."""
    plugins = []
    for name, fields in schema.items():
        if name in not_exportable or not isinstance(fields, dict):
            continue
        is_collection = any(isinstance(f, dict) and f.get("primary_key") for f in fields.values())
        cls = type(
            f"Remote_{name}",
            (RemotePlugin,),
            {"plugin_name": name, "fields_description": fields, "IS_COLLECTION": is_collection},
        )
        plugins.append(cls(store, config))
    return plugins


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
    ) -> None:
        self.connection = connection
        self.store = store
        self.host = host
        self.registry: list[tuple[str, bool]] = [("system", False)]
        self.fields_by_plugin: dict[str, dict[str, Any]] = {"system": {}}
        # Every plugin's schema, hidden ones included: what the exporters get.
        self.schema: dict[str, Any] = {}
        self._hidden = hidden_plugins or set()
        self.alerts = RemoteAlerts()
        self._schema_loaded = False
        self._last_error: str | None = None
        self.connected = False
        # The pid this client pinned on the server (`e`), None otherwise.
        self.pinned: int | None = None
        # When the values in the store were received (epoch seconds), None
        # before the first. Shown in the header while disconnected.
        self.last_update: float | None = None

    def status(self) -> tuple[str, str, float | None]:
        """`("connected" | "disconnected", host, last_update)`, for the TUI's header."""
        return ("connected" if self.connected else "disconnected", self.host, self.last_update)

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
        self.schema = info
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
            await asyncio.to_thread(self._poll_alerts)
        except RemoteError as e:
            # The store keeps the last values: the TUI goes on showing them.
            self._failed(str(e))
            return
        if not self.connected and self._last_error:
            logger.info("Reconnected to %s", self.connection.base_url)
        self.connected = True
        self.last_update = time.time()
        self._last_error = None

    def _poll_alerts(self) -> None:
        try:
            history = self.connection.get_json("/api/5/alert")
            incidents = self.connection.get_json("/api/5/alert/incidents")
        except NotFound:
            self.alerts.clear()
            return
        self.alerts.update(history, incidents)

    def _failed(self, error: str) -> None:
        self.connected = False
        if error != self._last_error:
            # Once per distinct error, not once per cycle.
            logger.warning("Cannot read %s: %s", self.connection.base_url, error)
            self._last_error = error

    def pin_extended(self, pid: int | None) -> None:
        """Pin `pid` for extended stats on the SERVER, or unpin (None). Synchronous.

        The pin is global to the server, as the Web UI's is: the server
        collects one pinned process' extended stats and publishes them in
        `processlist`'s `extended`. Raises `RemoteError`.
        """
        self.connection.post_json(
            "/api/5/processes/extended/disable" if pid is None else f"/api/5/processes/extended/{pid}"
        )
        self.pinned = pid

    def unpin_on_exit(self) -> None:
        """Leaving the client: drop the pin it set, or the server keeps paying for it. Never raises."""
        if self.pinned is None:
            return
        try:
            self.pin_extended(None)
        except RemoteError as e:
            logger.warning("Cannot unpin pid %s on %s: %s", self.pinned, self.connection.base_url, e)

    async def run_forever(self, refresh: float) -> None:
        """Poll every `refresh` seconds, the client's own cadence, until cancelled."""
        while True:
            await self.poll_once()
            await asyncio.sleep(refresh)
