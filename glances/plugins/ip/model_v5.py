#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — ip plugin (scalar private + public IP).

Migrated from `glances/plugins/ip/__init__.py`. The private IP is grabbed
via `get_ip_address()` (psutil, first up non-`lo` AF_INET interface). The
public IP is fetched by an **in-model cadenced** call (replacing v4's
standalone `threading.Thread`): every `public_refresh_interval` seconds a
GUARDED fetch runs in `asyncio.to_thread`; between refreshes the cached
value is reused. `gateway` is declared in the schema but never populated
(v4 parity). SNMP input is dropped (architecture §10).

CVE-2026-35587 SSRF mitigation is enforced by `_public_api_allowed`
(scheme allowlist + DNS-resolved internal-IP rejection); credentials are
attached only on the all-passed path (see Task 2 / Task 3).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
import time
from typing import Any, ClassVar
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from glances.config_v5 import GlancesConfigV5
from glances.globals import get_ip_address, json_loads, urlopen_auth
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5

logger = logging.getLogger(__name__)

_DEFAULT_PUBLIC_REFRESH_INTERVAL = 300
_FETCH_TIMEOUT = 2


def _ip_to_cidr(mask: str | None) -> int:
    """Convert a dotted netmask to its CIDR prefix length.

    Example: '255.255.255.0' -> 24. None -> 0 (issue #1528 parity).
    Ported from the v4 `IpPlugin.ip_to_cidr` staticmethod.
    """
    if not mask:
        return 0
    return sum(bin(int(octet)).count("1") for octet in mask.split("."))


def _public_api_allowed(url: str, allow_internal: bool) -> bool:
    """SSRF gate for the public-IP API URL (CVE-2026-35587).

    Three controls (§5 of the G4B design):
      1. Scheme allowlist — only http/https.
      2. DNS-resolved internal-IP rejection — resolve the host with
         `socket.getaddrinfo` and reject if ANY resolved address is
         loopback / link-local (covers 169.254.169.254 metadata) /
         private (RFC1918) / reserved. `allow_internal=True` opts out.
      3. Credential non-forwarding is enforced by the caller: a False
         return means no request is issued, so credentials never reach
         a blocked host.

    Pure (no logging, no I/O beyond getaddrinfo) so it is unit-testable in
    isolation. Fails closed on any resolution error.
    """
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    if allow_internal:
        return True
    host = parsed.hostname
    if not host:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return False  # cannot resolve -> fail closed
    for info in infos:
        raw_ip = info[4][0]
        try:
            addr = ipaddress.ip_address(raw_ip)
        except ValueError:
            return False
        if addr.is_loopback or addr.is_link_local or addr.is_private or addr.is_reserved:
            return False
    return True


class PluginModel(GlancesPluginBase[dict]):
    """IP plugin (scalar)."""

    plugin_name: ClassVar[str] = "ip"
    IS_COLLECTION: ClassVar[bool] = False
    # ip never raises alerts (v4 has no ip colouring/thresholds). No field
    # is watched, so `_levels` stays empty regardless — False documents intent.
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "address": {"description": "Private IP address.", "unit": "string"},
        "mask": {"description": "Private IP mask.", "unit": "string"},
        "mask_cidr": {"description": "Private IP mask in CIDR format.", "unit": "number"},
        "gateway": {"description": "Private IP gateway.", "unit": "string"},
        "public_address": {"description": "Public IP address.", "unit": "string"},
        "public_info_human": {"description": "Public IP information (human readable).", "unit": "string"},
    }

    def __init__(self, store: StatsStoreV5, config: GlancesConfigV5) -> None:
        super().__init__(store, config)

        # Public-IP configuration (see issue #2732). `get(...)` coerces to
        # type(default): "" -> str, [] -> comma list, 300 -> int, False -> bool.
        self.public_api = self.config.get("ip", "public_api", "")
        self.public_username = self.config.get("ip", "public_username", "")
        self.public_password = self.config.get("ip", "public_password", "")
        self.public_field = self.config.get("ip", "public_field", [])
        self.public_template = self.config.get("ip", "public_template", "")
        self.public_refresh_interval = self.config.get(
            "ip", "public_refresh_interval", _DEFAULT_PUBLIC_REFRESH_INTERVAL
        )
        # CVE-2026-35587 opt-out (default False = SSRF-safe).
        self.allow_internal = self.config.get("ip", "public_api_allow_internal", False)

        self.public_disabled = (
            self.config.get("ip", "public_disabled", False) or not self.public_api or not self.public_field
        )

        # Defence-in-depth (port of the v4 init scheme-check): reject a
        # forbidden scheme at construction with a clear one-time warning.
        if not self.public_disabled and urlparse(self.public_api).scheme not in ("http", "https"):
            logger.warning(
                "IP plugin - public_api uses a forbidden scheme "
                "(only http:// and https:// are allowed). Public IP disabled."
            )
            self.public_disabled = True

        # In-model cadence state (replaces the v4 ThreadPublicIpAddress).
        self._last_public_fetch_ts: float | None = None
        self._public_cache: dict[str, Any] = {}
        self._blocked_logged = False
        # Indirected clock so cadence is testable (tests set p._monotonic).
        self._monotonic = time.monotonic

    # ------------------------------------------------------------ private IP

    def _grab_private(self) -> dict[str, Any]:
        address, mask = get_ip_address()
        return {"address": address, "mask": mask, "mask_cidr": _ip_to_cidr(mask)}

    async def _grab_stats(self) -> dict:
        stats = await asyncio.to_thread(self._grab_private)
        if self.public_disabled:
            return stats
        now = self._monotonic()
        due = self._last_public_fetch_ts is None or (now - self._last_public_fetch_ts) >= self.public_refresh_interval
        if due:
            self._public_cache = await asyncio.to_thread(self._fetch_public_ip_info)
            self._last_public_fetch_ts = now
        self._merge_public(stats, self._public_cache)
        return stats

    # ------------------------------------------------------------- public IP

    def _fetch_public_ip_info(self) -> dict[str, Any]:
        """Fetch public-IP JSON from the configured API — SSRF-gated.

        Runs in a worker thread (getaddrinfo + urlopen are blocking). A
        blocked host returns {} (public IP left empty) and logs once; a
        network error keeps the last good cache (v4 parity).
        """
        if not _public_api_allowed(self.public_api, self.allow_internal):
            if not self._blocked_logged:
                logger.warning(
                    "IP plugin - public_api %s resolves to a forbidden internal/loopback address; "
                    "public IP disabled. Set [ip] public_api_allow_internal=true to override (see docs).",
                    self.public_api,
                )
                self._blocked_logged = True
            return {}
        try:
            if self.public_username and self.public_password:
                response = urlopen_auth(
                    self.public_api, self.public_username, self.public_password, _FETCH_TIMEOUT
                ).read()
            else:
                response = urlopen(Request(self.public_api), timeout=_FETCH_TIMEOUT).read()
            return json_loads(response)
        except Exception as e:  # noqa: BLE001 — network/parse failure must not crash the cycle
            logger.debug("IP plugin - cannot get public IP info from %s (%s)", self.public_api, e)
            return self._public_cache

    def _merge_public(self, stats: dict[str, Any], info: dict[str, Any]) -> None:
        """Merge the public-IP fields into the scalar stats dict.

        No masking here — the `--hide-public-info` flag is a TUI display
        preference applied by the renderer (see Task 5). The field carrying
        the address is the configured `public_field` (defaults to 'ip',
        matching the shipped conf and v4's literal extraction key).
        """
        if not info:
            return
        field = self.public_field[0] if self.public_field else "ip"
        address = info.get(field, "")
        if not address:
            return
        stats["public_address"] = address
        stats["public_info_human"] = self._public_info_for_human(info)

    def _public_info_for_human(self, info: dict[str, Any]) -> str:
        if not info or not self.public_template:
            return ""
        try:
            return self.public_template.format(**info)
        except (KeyError, IndexError):
            return ""
