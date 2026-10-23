#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Zeroconf: servers announce themselves, the browser lists them.

Design: ``docs/superpowers/specs/2026-09-27-glances-v5-phase3-design.md`` §4.6
(chantier P3-5). v4: ``glances/servers_list_dynamic.py``.

- **Server** (``-s``): announces ``_glances._tcp.local.`` with a TXT record
  ``api=5``, unless ``--disable-autodiscover``. ``protocol=rest`` is kept in
  the record for v4 browsers, which read it.
- **Browser** (``--browser``): adds the announcements carrying ``api=5`` to
  the server list, as ``source="zeroconf"``. A v4 server is left out: the
  client could not talk to it.
- **A discovered server is untrusted** (CVE-2026-32634): anyone can announce
  under any name. Its entry connects to the address it was seen at, never
  to the name it claims, and it is sent no configured credential
  (``ServersPoller.password_for``); the user types one when opening it.
- ``zeroconf`` is an optional extra (``browser``). Without it, both sides
  say so at INFO and go on: the browser with its static list alone.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any

from glances import __apiversion__
from glances.servers_list import ServerEntry

try:
    from zeroconf import IPVersion, ServiceBrowser, ServiceInfo, ServiceStateChange, Zeroconf
except ImportError:  # the `browser` extra is not installed
    Zeroconf = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

SERVICE_TYPE = "_glances._tcp.local."
API_VERSION = __apiversion__.encode()
# An announced name is shown in the TUI and served by /api/5/serverslist:
# printable characters only, and not a screenful.
_ALIAS_MAX = 64
# Discovered entries are polled, and `/api/5/serverslist` serves what they
# answer: a LAN that announces thousands of them is not followed beyond this
# (static entries have `servers_list.MAX_SERVERS`).
MAX_DISCOVERED = 256


def available() -> bool:
    if Zeroconf is None:
        logger.info("Zeroconf is not installed (pip install glances[browser]): no autodiscovery")
        return False
    return True


def _announced_address(bind: str) -> str | None:
    """The IPv4 address to announce for a server bound to `bind`; None when the LAN cannot reach it."""
    try:
        address = ipaddress.ip_address(socket.gethostbyname(bind or "0.0.0.0"))
    except (OSError, ValueError):
        return None
    if address.is_loopback:
        return None
    if address.is_unspecified:
        from glances.globals import get_ip_address

        found = get_ip_address()[0]
        return str(found) if found else None
    return str(address)


class Announcer:
    """`-s`: this server, announced on the LAN until `close()`."""

    def __init__(self) -> None:
        self._zeroconf: Any = None
        self._info: Any = None

    def start(self, bind: str, port: int, hostname: str | None = None) -> bool:
        if not available():
            return False
        address = _announced_address(bind)
        if address is None:
            logger.info("Zeroconf: bound to %s, which the LAN cannot reach: nothing to announce", bind)
            return False
        hostname = hostname or socket.gethostname()
        self._info = ServiceInfo(
            SERVICE_TYPE,
            f"{hostname}:{port}.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(address)],
            port=port,
            properties={"api": API_VERSION, "protocol": b"rest"},
            server=f"{hostname}.local.",
        )
        try:
            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._zeroconf.register_service(self._info)
        except Exception as e:  # noqa: BLE001 -- the network layer raises widely; never cost the server
            logger.warning("Zeroconf: cannot announce this server (%s)", e)
            self.close()
            return False
        logger.info("Zeroconf: announced as %s on %s:%d", hostname, address, port)
        return True

    def close(self) -> None:
        if self._zeroconf is None:
            return
        try:
            if self._info is not None:
                self._zeroconf.unregister_service(self._info)
            self._zeroconf.close()
        except Exception as e:  # noqa: BLE001
            logger.debug("Zeroconf: close failed (%s)", e)
        self._zeroconf = None


def _alias(service_name: str) -> str:
    """`myhost:61208._glances._tcp.local.` -> `myhost`, printable characters only."""
    name = service_name.removesuffix(f".{SERVICE_TYPE}").rsplit(":", 1)[0]
    return "".join(ch for ch in name if ch.isprintable())[:_ALIAS_MAX] or "?"


def _is_routable(address: str) -> bool:
    """A unicast address the browser may poll: an announcement is not trusted to
    point it at loopback, link-local (169.254.169.254), multicast, 0.0.0.0,
    broadcast or a reserved range (security audit 2026-10-17, B-19)."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return not (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
        or ip == ipaddress.IPv4Address("255.255.255.255")
    )


class Discovery:
    """`--browser`: adds the v5 servers announced on the LAN to `servers`, and removes them when they leave.

    `servers` is the poller's list. Entries are appended and removed whole,
    so the poller and the TUI, which iterate copies, never see half of one.
    """

    def __init__(self, servers: list[ServerEntry]) -> None:
        self.servers = servers
        self._zeroconf: Any = None
        self._browser: Any = None
        # Zeroconf service name -> the entry it added.
        self._found: dict[str, ServerEntry] = {}
        self._cap_warned = False

    def start(self) -> bool:
        if not available():
            return False
        try:
            self._zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
            self._browser = ServiceBrowser(self._zeroconf, SERVICE_TYPE, handlers=[self._on_change])
        except Exception as e:  # noqa: BLE001
            logger.warning("Zeroconf: cannot browse the LAN (%s)", e)
            self.close()
            return False
        return True

    def _on_change(self, zeroconf: Any, service_type: str, name: str, state_change: Any) -> None:
        if state_change is ServiceStateChange.Removed:
            self.remove(name)
            return
        info = zeroconf.get_service_info(service_type, name, timeout=3000)
        if info is None:
            logger.debug("Zeroconf: no details for %s", name)
            return
        addresses = info.parsed_addresses(IPVersion.V4Only)
        self.add(name, addresses[0] if addresses else None, info.port, info.properties or {})

    def add(self, name: str, address: str | None, port: int | None, properties: dict[bytes, Any]) -> None:
        """One announcement. Kept only when it is a v5 server with an address and a port."""
        if properties.get(b"api") != API_VERSION:
            logger.debug("Zeroconf: %s is not a Glances v5 server, left out", name)
            return
        if not address or not port:
            return
        if not _is_routable(address):
            logger.debug("Zeroconf: %s announces %s, which is not a LAN address, left out", name, address)
            return
        alias = _alias(name)
        # A discovered server showing under a configured server's name would
        # be opened, and given a typed password, as that server (audit A7).
        known = {n.casefold() for s in self.servers if s.source == "static" for n in (s.name, s.alias) if n}
        if alias.casefold() in known:
            logger.warning("Zeroconf: %s at %s refused: a [serverlist] server has that name", alias, address)
            return
        if name not in self._found and len(self._found) >= MAX_DISCOVERED:
            if not self._cap_warned:
                logger.warning("Zeroconf: more than %d servers announced, the others are ignored", MAX_DISCOVERED)
                self._cap_warned = True
            return
        # Connect to where the announcement came from, never to the name it
        # claims (CVE-2026-32634): the name is shown, not trusted.
        entry = ServerEntry(name=address, port=int(port), alias=alias, source="zeroconf")
        previous = self._found.get(name)
        if previous is not None and previous.target == entry.target:
            return
        if previous is not None:
            self.remove(name)
        self._found[name] = entry
        self.servers.append(entry)
        logger.info("Zeroconf: found %s at %s", entry.alias, entry.target)

    def remove(self, name: str) -> None:
        entry = self._found.pop(name, None)
        if entry is not None and entry in self.servers:
            self.servers.remove(entry)
            logger.info("Zeroconf: %s left", entry.alias)

    def close(self) -> None:
        if self._zeroconf is None:
            return
        try:
            if self._browser is not None:
                self._browser.cancel()
            self._zeroconf.close()
        except Exception as e:  # noqa: BLE001
            logger.debug("Zeroconf: close failed (%s)", e)
        self._zeroconf = None
