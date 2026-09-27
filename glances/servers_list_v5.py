#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the browser's server list and its poller.

Design: ``docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md`` §4.5
(chantier P3-4). v4: ``servers_list.py``, ``servers_list_static.py``.

- **Sources**: ``[serverlist]`` (static). Zeroconf comes with P3-5.
- **Polling**: one thread, the servers one after the other (one connection
  at a time, Phase 3 decision 2), each with ``GET /status`` then one
  ``GET /api/5/<plugin>`` per plugin named in ``[serverlist] columns``.
- **Credentials never sit in a ``ServerEntry``** (CVE-2026-32633): v4 put the
  password hash in each server's ``uri``, which ``/api/4/serverslist``
  served. Here the passwords live in the poller's connections only, and an
  entry has no field that could carry one.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from glances.client_v5 import (
    DEFAULT_PORT,
    DEFAULT_TIMEOUT,
    AuthError,
    NotAGlancesV5Server,
    NotFound,
    RemoteConnection,
    RemoteError,
    parse_target,
)

logger = logging.getLogger(__name__)

SECTION = "serverlist"
DEFAULT_COLUMNS = "system:hr_name,load:min5,cpu:total,mem:percent"
# v4's list, bounded the same way.
MAX_SERVERS = 256

# v4's statuses, minus SNMP (dropped), plus UNSUPPORTED: something answers
# on the port, but not the Glances v5 API (a v4 server, for one).
UNKNOWN = "UNKNOWN"
ONLINE = "ONLINE"
OFFLINE = "OFFLINE"
PROTECTED = "PROTECTED"
UNSUPPORTED = "UNSUPPORTED"


@dataclass(frozen=True)
class Column:
    """One `[serverlist] columns` entry: `plugin:field` or `plugin:field:key`."""

    plugin: str
    field: str
    key: str | None = None

    @property
    def label(self) -> str:
        return ":".join(p for p in (self.plugin, self.field, self.key) if p)


def parse_columns(text: str) -> list[Column]:
    """`system:hr_name,sensors:value:Ambient` -> columns. A malformed entry is skipped with a warning."""
    columns = []
    for raw in text.split(","):
        parts = [p.strip() for p in raw.split(":")]
        if len(parts) not in (2, 3) or not all(parts):
            logger.warning("[%s] columns: %r is not plugin:field[:key], skipped", SECTION, raw.strip())
            continue
        columns.append(Column(*parts))
    return columns


@dataclass
class ServerEntry:
    """One server of the list, as the TUI and `/api/5/serverslist` show it. No credential field."""

    name: str
    port: int
    alias: str | None = None
    source: str = "static"
    status: str = UNKNOWN
    # `Column.label` -> {"value": ..., "level": "ok" | ... | None}. Replaced
    # whole by the poller, so a reader never sees half a round.
    columns: dict[str, dict[str, Any]] = field(default_factory=dict)

    @property
    def target(self) -> str:
        """What `-c` would take: `host:port`, or the configured URL."""
        return self.name if "://" in self.name else f"{self.name}:{self.port}"

    @property
    def key(self) -> str:
        """The poller's key for its connection, and so its credentials: per source,
        so a discovered server announcing a static one's address never shares its password."""
        return f"{self.source}:{self.target}"

    def as_dict(self) -> dict[str, Any]:
        """The `/api/5/serverslist` item: built field by field, never from `vars()`."""
        return {
            "name": self.name,
            "alias": self.alias,
            "port": self.port,
            "status": self.status,
            "source": self.source,
            "columns": {label: dict(cell) for label, cell in self.columns.items()},
        }


def load_static_servers(config: Any) -> list[ServerEntry]:
    """`[serverlist] server_N_name/port/alias`, N from 1 to 256 (v4's layout)."""
    servers = []
    for n in range(1, MAX_SERVERS + 1):
        name = str(config.get(SECTION, f"server_{n}_name", "") or "").strip()
        if not name:
            continue
        if config.get_value(SECTION, f"server_{n}_protocol") is not None:
            # v4 had `rpc` and `rest`; v5 speaks REST only.
            logger.warning("[%s] server_%d_protocol is ignored: v5 servers speak REST only", SECTION, n)
        raw_port = str(config.get(SECTION, f"server_{n}_port", "") or "").strip()
        try:
            port = int(raw_port) if raw_port else DEFAULT_PORT
            parse_target(name if "://" in name else f"{name}:{port}")
        except ValueError as e:
            logger.warning("[%s] server_%d skipped: %s", SECTION, n, e)
            continue
        alias = str(config.get(SECTION, f"server_{n}_alias", "") or "").strip() or None
        servers.append(ServerEntry(name=name, port=port, alias=alias))
    logger.info("%d server(s) loaded from [%s]", len(servers), SECTION)
    return servers


def _cell(payload: Any, column: Column) -> dict[str, Any] | None:
    """The column's value and level in a `/api/5/<plugin>` payload, or None if it has none."""
    if not isinstance(payload, dict):
        return None
    levels = payload.get("_levels") or {}
    if column.key is None:
        if column.field not in payload:
            return None
        level = (levels.get(column.field) or {}).get("level")
        return {"value": payload[column.field], "level": level}
    primary_key = payload.get("_key")
    for item in payload.get("data") or []:
        # Case-insensitive, as v4 matches the key.
        if isinstance(item, dict) and str(item.get(primary_key, "")).lower() == column.key.lower():
            if column.field not in item:
                return None
            item_levels = levels.get(str(item.get(primary_key))) or {}
            return {"value": item[column.field], "level": (item_levels.get(column.field) or {}).get("level")}
    return None


class ServersPoller:
    """Polls every server of the list, one after the other, in its own thread.

    Holds the connections, and so the credentials: `[passwords] <name>`, then
    `[passwords] default`, for static servers only (P3-5 keeps Zeroconf
    servers away from them, CVE-2026-32634), or what the user typed.
    """

    def __init__(self, servers: list[ServerEntry], config: Any, columns: list[Column]) -> None:
        self.servers = servers
        self.columns = columns
        self._config = config
        self._timeout = float(config.get("client", "timeout", DEFAULT_TIMEOUT))
        self._connections: dict[str, RemoteConnection] = {}
        self._passwords: dict[str, str] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def password_for(self, server: ServerEntry) -> str | None:
        """The password to open `server` with, if one is known."""
        if server.key in self._passwords:
            return self._passwords[server.key]
        if server.source != "static":
            return None
        host = parse_target(server.target)[1]
        return self._config.get_value("passwords", host) or self._config.get_value("passwords", "default") or None

    def set_password(self, server: ServerEntry, password: str) -> None:
        """A password the user typed for `server`: used from the next round on."""
        self._passwords[server.key] = password
        self._connections.pop(server.key, None)

    def _connection(self, server: ServerEntry) -> RemoteConnection:
        conn = self._connections.get(server.key)
        if conn is None:
            base_url = parse_target(server.target)[0]
            conn = RemoteConnection(base_url, password=self.password_for(server), timeout=self._timeout)
            self._connections[server.key] = conn
        return conn

    def poll_server(self, server: ServerEntry) -> None:
        """One server: its status, then its columns. Never raises."""
        conn = self._connection(server)
        try:
            status = conn.get_json("/status")
            if not isinstance(status, dict) or str(status.get("version")) != "5":
                raise NotAGlancesV5Server(f"{server.target} is not a Glances v5 server")
            cells: dict[str, dict[str, Any]] = {}
            for plugin in dict.fromkeys(c.plugin for c in self.columns):
                try:
                    payload = conn.get_json(f"/api/5/{plugin}")
                except NotFound:
                    continue  # plugin disabled on that server: its columns stay empty
                for column in self.columns:
                    if column.plugin == plugin and (cell := _cell(payload, column)) is not None:
                        cells[column.label] = cell
        except AuthError:
            server.status = PROTECTED
            return
        except (NotAGlancesV5Server, NotFound):
            # Columns answer 404 inside the loop above: a 404 here is `/status`,
            # which every v5 server serves (a v4 server does not).
            server.status = UNSUPPORTED
            return
        except RemoteError as e:
            logger.debug("Browser: %s is offline (%s)", server.target, e)
            server.status = OFFLINE
            return
        server.columns = cells
        server.status = ONLINE

    def poll_round(self) -> None:
        for server in list(self.servers):
            if self._stop.is_set():
                return
            self.poll_server(server)

    def start(self, interval: float) -> None:
        """Poll round after round, `interval` seconds apart, until `stop()`."""

        def loop() -> None:
            while not self._stop.is_set():
                try:
                    self.poll_round()
                except Exception:
                    # A thread that dies says nothing: the list would freeze at UNKNOWN.
                    logger.exception("Browser: a polling round failed")
                self._stop.wait(interval)

        self._thread = threading.Thread(target=loop, name="glances-browser-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()


def build_poller(config: Any) -> ServersPoller:
    """The static list of `[serverlist]` and its `columns`, ready to `start()`."""
    columns = parse_columns(str(config.get(SECTION, "columns", "") or DEFAULT_COLUMNS))
    return ServersPoller(load_static_servers(config), config, columns)
