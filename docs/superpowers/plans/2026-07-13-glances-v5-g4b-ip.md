# Glances v5 — ip plugin port + CVE-2026-35587 SSRF mitigation (G4B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `ip` scalar plugin to the v5 asyncio architecture (private-IP grab + in-model cadenced public-IP fetch + inline TUI renderer) while wiring the full CVE-2026-35587 SSRF mitigation (scheme allowlist + DNS-resolved internal-IP rejection + credential non-forwarding + opt-out key).

**Architecture:** A scalar `PluginModel(GlancesPluginBase[dict])` grabs the private IP via `get_ip_address()` in `asyncio.to_thread`, and — when public IP is enabled — performs a self-cadenced (`public_refresh_interval`, 300s) guarded fetch in `asyncio.to_thread`, replacing v4's standalone `threading.Thread`. A pure module-level helper `_public_api_allowed(url, allow_internal)` gates every fetch: only `http`/`https`, and only when *every* DNS-resolved address is non-internal (loopback/link-local/private/reserved), unless the new `public_api_allow_internal` key is set. A `render_curses_v5.render()` emits one inline `Row` (`IP <addr>/<cidr> [Pub <pub> {info}]`), masking the public address when the TUI `view["hide_public_info"]` flag is set (`--hide-public-info` parity).

**Tech Stack:** Python, psutil, urllib, socket, ipaddress, asyncio (to_thread), curses renderer v5, pytest

## Global Constraints

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **Reuse the v4 grabber** (`get_ip_address` from `glances.globals`) via `asyncio.to_thread` — no rewrite of the psutil interface walk.
- **Empty stats must stay valid**: no interface / no public IP yields a partial-or-empty scalar dict, never a crash.
- **No dead code**, no speculative config keys (only `public_api_allow_internal` is added), surgical edits.
- **Do NOT touch `NEWS.rst`** during development — the CVE changelog entry is maintainer/release-time only.
- **The new config key ships COMMENTED** in `conf/glances.conf` → behaviour unchanged for existing users (`allow_internal` defaults `False`, i.e. SSRF-safe).
- **No commits / push / PR** — stage only. Every task's final step is `git add <paths>` then STOP.
- Tests: `.venv/bin/python -m pytest`; lint `ruff check` + `ruff format`.

---

## File Structure

```
glances/plugins/ip/model_v5.py                      (NEW — PluginModel + _public_api_allowed + _ip_to_cidr)
glances/plugins/ip/render_curses_v5.py              (NEW — inline single-Row renderer)
tests/test_plugin_ip_v5.py                          (NEW — model + SSRF helper + cadence tests)
tests/test_plugin_ip_render_curses_v5.py            (NEW — renderer tests)
conf/glances.conf                                   (EDIT — add commented public_api_allow_internal in [ip])
glances/main_v5.py                                  (EDIT — add --hide-public-info CLI flag + wire into TuiV5)
glances/outputs/curses_renderer_v5.py               (EDIT — add `ip` to HEADER_SLOT between system and uptime)
glances/outputs/glances_curses_v5.py                (EDIT — `_paint_header` packs middle blocks + TuiV5 hide_public_info param + view seed)
docs/aoa/ip.rst                                     (NEW — plugin + SSRF hardening doc)
docs/aoa/index.rst                                  (EDIT — add `ip` to the toctree)
```

Reference plugins mirrored: **scalar** = `glances/plugins/system/model_v5.py` + `glances/plugins/system/render_curses_v5.py` (and `uptime`); **config/level/test idioms** = `glances/plugins/sensors/*` + `tests/test_plugin_sensors_v5.py`.

Discovery is automatic: `main_v5.discover_plugins` imports `glances.plugins.ip.model_v5.PluginModel`; the TUI auto-discovers `glances.plugins.ip.render_curses_v5.render`. No plugin/renderer *registration* edits needed. The only layout wiring is the slot placement (Task 5): `ip` is added to the `HEADER_SLOT` tuple so it lands on the header line instead of the LEFT sidebar.

**Slot placement (implemented — Task 5):** v4 paints `ip` on the *header* line between `system` and `uptime` (`glances_curses.py:696-721`: `system` flush-left, `ip` packed after it via `new_column()` with `space_between_column=3`, `uptime` flush-right). v5 mirrors this exactly. The routing hook is clean: `HEADER_SLOT` (`curses_renderer_v5.py:55`) is the single slot-ordering list, and `build_frame` already appends header blocks then sorts them by `HEADER_SLOT.index` (`curses_renderer_v5.py:806`). Adding `"ip"` between `"system"` and `"uptime"` in that tuple both routes `ip` to the header (`slot_for` returns `"header"` for any tuple member) AND orders `frame.header` as `[system, ip, uptime]` — no `slot_for` special-casing. The one real change is the shared painter `_paint_header` (`glances_curses_v5.py:657-679`), which today paints only `blocks[0]` (flush-left) and `blocks[-1]` (flush-right) and **skips middle blocks**; Task 5 generalizes it to also pack the middle block(s) left-to-right after the first block (generic, not `ip`-special-cased), and carries a regression guard because the painter is shared by every header plugin.

---

### Task 1: Model foundation: identity, fields, config parsing, private-IP grab

**Files:** `glances/plugins/ip/model_v5.py` (NEW), `tests/test_plugin_ip_v5.py` (NEW)

**Interfaces:**
- Consumes: `StatsStoreV5`, `GlancesConfigV5`, `glances.globals.get_ip_address`.
- Produces: `PluginModel` (scalar) with `plugin_name="ip"`, `IS_COLLECTION=False`, `EMITS_ALERTS=False`, `fields_description` (address, mask, mask_cidr, gateway, public_address, public_info_human), a synchronous `_grab_private()` and an `async _grab_stats()` that (this task) returns only the private-IP dict.

**Steps:**

- [ ] Write failing test `tests/test_plugin_ip_v5.py` with the sensors-style fixtures (`store`, `config`, and a `_cfg_with(tmp_path, monkeypatch, body)` helper mirroring `tests/test_plugin_sensors_v5.py`). Add:
  - `test_plugin_identity`: `p.plugin_name == "ip"`, `p.IS_COLLECTION is False`, `p._primary_key is None`, `p.EMITS_ALERTS is False`.
  - `test_fields_description`: keys `{address, mask, mask_cidr, gateway, public_address, public_info_human}` all present; `mask_cidr` unit is `"number"`; no field is `watched`.
  - `test_ip_to_cidr`: `_ip_to_cidr("255.255.255.0") == 24`; `_ip_to_cidr(None) == 0` (issue #1528 parity).
  - `test_grab_private_merges_address` (async): monkeypatch `glances.plugins.ip.model_v5.get_ip_address` to `lambda: ("192.168.1.10", "255.255.255.0")`; assert `await p._grab_stats()` yields `{"address": "192.168.1.10", "mask": "255.255.255.0", "mask_cidr": 24}` and `"gateway"` is absent (v4 declares but never populates it).
  - `test_grab_private_no_interface` (async): monkeypatch `get_ip_address` to `lambda: (None, None)`; assert result is `{"address": None, "mask": None, "mask_cidr": 0}` (no crash).
- [ ] Run (FAIL): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -v` (module import error / missing symbols).
- [ ] Write COMPLETE `glances/plugins/ip/model_v5.py`:

```python
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
        # Task 1 delivers the private-IP path only. Task 3 adds the public
        # fetch below this line.
        return await asyncio.to_thread(self._grab_private)
```

- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -v`
- [ ] Lint/format: `.venv/bin/python -m ruff check glances/plugins/ip/model_v5.py tests/test_plugin_ip_v5.py` and `.venv/bin/python -m ruff format glances/plugins/ip/model_v5.py tests/test_plugin_ip_v5.py`.
- [ ] `git add glances/plugins/ip/model_v5.py tests/test_plugin_ip_v5.py` then STOP (never `git commit`).

---

### Task 2: SSRF helper `_public_api_allowed` unit tests (CVE-2026-35587, critical)

The helper itself is already written in Task 1 (kept in the same module so it ships with the model). This task **locks its behaviour under test** — the security contract. Do NOT weaken the helper to make a test pass; fix the test.

**Files:** `tests/test_plugin_ip_v5.py` (EDIT — add an SSRF section)

**Interfaces:**
- Consumes: `glances.plugins.ip.model_v5._public_api_allowed`, mocked `socket.getaddrinfo`.
- Produces: full category coverage (scheme / loopback / link-local-metadata / private / reserved / public-allow / DNS-alias-reject / opt-in).

**Steps:**

- [ ] Add failing tests to `tests/test_plugin_ip_v5.py`. Import `_public_api_allowed` and add a `_getaddrinfo(*ips)` monkeypatch helper that returns `[(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (ip, 80)) for ip in ips]`:
  - `test_ssrf_scheme_rejected`: `_public_api_allowed("file:///etc/passwd", False) is False` (no getaddrinfo call needed).
  - `test_ssrf_loopback_rejected`: patch `socket.getaddrinfo` -> `127.0.0.1`; `_public_api_allowed("http://127.0.0.1/json", False) is False`.
  - `test_ssrf_metadata_rejected`: patch -> `169.254.169.254`; `_public_api_allowed("http://169.254.169.254/latest/meta-data/", False) is False` (link-local).
  - `test_ssrf_private_rejected`: patch -> `10.0.0.5`; result `False`.
  - `test_ssrf_reserved_rejected`: patch -> `240.0.0.1`; result `False`.
  - `test_ssrf_public_allowed`: patch -> `93.184.216.34`; `_public_api_allowed("http://example.com/json", False) is True`.
  - `test_ssrf_dns_alias_to_internal_rejected`: patch `socket.getaddrinfo` for host `evil.example.com` to resolve to `169.254.169.254`; `_public_api_allowed("http://evil.example.com/json", False) is False` (defeats DNS-based SSRF).
  - `test_ssrf_mixed_resolution_rejected`: patch -> `("93.184.216.34", "10.0.0.5")`; result `False` (ANY internal address rejects).
  - `test_ssrf_allow_internal_opt_in`: patch -> `127.0.0.1`; `_public_api_allowed("http://127.0.0.1/json", True) is True` (opt-in flips reject→allow; note: getaddrinfo is short-circuited before resolution when `allow_internal` is True).
  - `test_ssrf_unresolvable_fails_closed`: patch `socket.getaddrinfo` to raise `socket.gaierror`; result `False`.
- [ ] Run (FAIL first if any test is added before the helper exists in this worker's tree; otherwise this task is purely additive and should PASS immediately against the Task 1 helper): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -k ssrf -v`.
- [ ] If any test fails, correct the **test** to match the specified security semantics (the helper is the source of truth; only fix the helper if it genuinely deviates from §5).
- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -k ssrf -v`.
- [ ] Lint: `.venv/bin/python -m ruff check tests/test_plugin_ip_v5.py` + `ruff format`.
- [ ] `git add tests/test_plugin_ip_v5.py` then STOP.

---

### Task 3: Cadenced public-IP fetch (guarded, credential non-forwarding)

**Files:** `glances/plugins/ip/model_v5.py` (EDIT — add fetch/merge + extend `_grab_stats`), `tests/test_plugin_ip_v5.py` (EDIT)

**Interfaces:**
- Consumes: `_public_api_allowed`, `urlopen`/`Request`, `glances.globals.urlopen_auth`, `json_loads`, `self._monotonic`.
- Produces: `_grab_stats` that merges `public_address` + `public_info_human` into the scalar dict, refreshing at most every `public_refresh_interval` seconds; credentials attached only on the SSRF-passed path.

**Steps:**

- [ ] Add failing tests to `tests/test_plugin_ip_v5.py`:
  - `test_public_disabled_skips_fetch` (async): default config (no `[ip]`) → `public_disabled` True; monkeypatch `get_ip_address`; call `_grab_stats`; assert `"public_address"` absent and `_fetch_public_ip_info` never called (spy).
  - `test_public_fetch_merges` (async): `_cfg_with(... "[ip]\npublic_disabled=False\npublic_api=http://example.com/json\npublic_field=ip\npublic_template={country}\n")`; monkeypatch `get_ip_address`; monkeypatch `p._fetch_public_ip_info` -> `lambda: {"ip": "1.2.3.4", "country": "Wonderland"}`; assert result `public_address == "1.2.3.4"` and `public_info_human == "Wonderland"`.
  - `test_public_fetch_cadence_reuses_cache` (async): same config; replace `p._fetch_public_ip_info` with a call counter returning `{"ip": "1.2.3.4"}`; set `p._monotonic = lambda: 1000.0`; first `_grab_stats` → counter == 1; set `p._monotonic = lambda: 1000.0 + 10` (< 300) → second `_grab_stats` → counter still 1 and `public_address == "1.2.3.4"` (cache reused); set `p._monotonic = lambda: 1000.0 + 301` → third → counter == 2.
  - `test_public_info_human_bad_template` (async): template `"{missing}"`, info `{"ip": "1.2.3.4"}`; assert `public_info_human == ""` (KeyError guarded), `public_address == "1.2.3.4"`.
  - `test_credentials_never_sent_to_blocked_host`: config with `public_username`/`public_password` and `public_api=http://169.254.169.254/json`; monkeypatch `socket.getaddrinfo` -> `169.254.169.254`; spy-patch `glances.plugins.ip.model_v5.urlopen` and `.urlopen_auth` to record calls; call `p._fetch_public_ip_info()` directly; assert it returns `{}` and **neither** `urlopen` nor `urlopen_auth` was called (credentials never leave the process).
  - `test_fetch_uses_basic_auth_when_credentials_set`: config with creds + `public_api=http://example.com/json`; monkeypatch `socket.getaddrinfo` -> public IP; spy-patch `urlopen_auth` to return an object whose `.read()` yields `b'{"ip":"1.2.3.4"}'`; assert `_fetch_public_ip_info()` returns the parsed dict and `urlopen_auth` was called once, `urlopen` not called.
  - `test_fetch_network_error_keeps_last_good`: prime `p._public_cache = {"ip": "9.9.9.9"}`; monkeypatch `getaddrinfo` -> public IP; patch `urlopen` to raise `OSError`; assert `_fetch_public_ip_info()` returns `{"ip": "9.9.9.9"}` (last good preserved, v4 parity).
- [ ] Run (FAIL): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -k "public or credentials or fetch" -v`.
- [ ] Extend `glances/plugins/ip/model_v5.py`. Replace the Task-1 `_grab_stats` body and add the fetch/merge methods:

```python
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
```

- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -v` (whole model+SSRF suite).
- [ ] Lint/format the two files.
- [ ] `git add glances/plugins/ip/model_v5.py tests/test_plugin_ip_v5.py` then STOP.

---

### Task 4: TUI renderer (inline single Row) + `--hide-public-info` masking

**Files:** `glances/plugins/ip/render_curses_v5.py` (NEW), `tests/test_plugin_ip_render_curses_v5.py` (NEW)

**Interfaces:**
- Consumes: scalar payload `{address, mask_cidr, public_address, public_info_human, ...}`, optional `view` dict (`hide_public_info`).
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — one inline `Row`, or `[]` when empty.

**Layout (mirror v4 `msg_curse`):** `IP`(HEADER) + `<address>/<mask_cidr>` ; if `public_address`: `Pub`(HEADER) + `<public_address>` ; if `public_info_human`: `{info}`. The painter inserts a single space between cells, giving `IP 192.168.1.10/24 Pub 1.2.3.4 Wonderland`. The address and `/cidr` are combined into ONE cell so no space is inserted before the slash (v4 rendered them contiguous). Guard `UnicodeEncodeError/KeyError` around the public segment (issue #1469).

**Steps:**

- [ ] Write failing `tests/test_plugin_ip_render_curses_v5.py` (flat-text helper like the sensors render test):
  - `test_empty_returns_nothing`: `render({})` -> `[]`; `render({"address": None})` -> `[]` (no printable cell).
  - `test_private_only`: `render({"address": "192.168.1.10", "mask_cidr": 24})` -> flat contains `IP` and `192.168.1.10/24`; exactly one `Row`.
  - `test_private_no_cidr`: `render({"address": "10.0.0.2", "mask_cidr": 0})` still renders `10.0.0.2/0` (VPN/no-internet parity, issue #842 — `mask_cidr` present as 0).
  - `test_with_public`: payload adds `public_address="1.2.3.4"`; flat contains `Pub` and `1.2.3.4`.
  - `test_with_public_info_human`: adds `public_info_human="Wonderland"`; flat contains `Wonderland`.
  - `test_public_absent_no_pub_segment`: payload without `public_address` → flat has no `Pub`.
  - `test_hide_public_info_masks`: `render({..., "public_address": "1.2.3.4"}, None, view={"hide_public_info": True})` → flat contains `1.2.*.*` and NOT `1.2.3.4`.
  - `test_hide_public_info_off_shows_full`: same payload, `view={}` → flat contains `1.2.3.4`.
  - `test_header_cells_coloured`: the `IP` and `Pub` cells use `ColorRole.HEADER`.
- [ ] Run (FAIL): `.venv/bin/python -m pytest tests/test_plugin_ip_render_curses_v5.py -v`.
- [ ] Write COMPLETE `glances/plugins/ip/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI renderer for the ip plugin (inline single line).

Mirrors v4 `ip.msg_curse`: `IP <address>/<cidr>` and, when available,
` Pub <public_address> {public_info_human}`. Emitted as ONE Row; the
painter inserts a single space between cells. The `--hide-public-info`
CLI flag (surfaced via `view['hide_public_info']`, like `--fahrenheit`)
masks the public address `a.b.c.d` -> `a.b.*.*` at display time.

Note: v5 `Cell` has no per-segment `optional` flag (v4 used `optional=True`
to drop segments on narrow terminals); narrow-terminal handling is via
block clipping at paint time. Empty public fields are simply omitted.
"""

from __future__ import annotations

from typing import Any

from glances.outputs.curses_renderer_v5 import Cell, ColorRole, Row


def _hide_ip(ip: str) -> str:
    """Mask the last two octets of a dotted IPv4 address: a.b.c.d -> a.b.*.*"""
    return ".".join(ip.split(".")[0:2]) + ".*.*"


def render(payload: dict[str, Any], fields_desc: dict[str, dict[str, Any]] | None = None, view=None) -> list[Row]:
    if not isinstance(payload, dict) or not payload:
        return []
    view = view or {}
    hide_public = bool(view.get("hide_public_info"))

    cells: list[Cell] = []

    # Private IP (skip cleanly when no interface was found).
    address = payload.get("address")
    if address:
        cells.append(Cell(text="IP", color=ColorRole.HEADER))
        mask_cidr = payload.get("mask_cidr")
        text = f"{address}/{mask_cidr}" if mask_cidr is not None else str(address)
        cells.append(Cell(text=text))

    # Public IP (guarded — see issue #1469).
    try:
        public_address = payload.get("public_address") or ""
        if public_address:
            shown = _hide_ip(public_address) if hide_public else public_address
            cells.append(Cell(text="Pub", color=ColorRole.HEADER))
            cells.append(Cell(text=str(shown)))
            info = payload.get("public_info_human")
            if info:
                cells.append(Cell(text=str(info)))
    except (UnicodeEncodeError, KeyError):
        pass

    if not cells:
        return []
    return [Row(cells=cells)]
```

- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_plugin_ip_render_curses_v5.py -v`.
- [ ] Lint/format the two files.
- [ ] `git add glances/plugins/ip/render_curses_v5.py tests/test_plugin_ip_render_curses_v5.py` then STOP.

---

### Task 5: Header placement — route `ip` to the header line between `system` and `uptime`

Route the `ip` block onto the TUI header (v4 parity: `system … ip … uptime`) instead of the LEFT sidebar. Two edits: (1) add `"ip"` to the `HEADER_SLOT` tuple — a clean slot-ordering hook, no `slot_for` special-casing; (2) generalize the shared `_paint_header` to pack the middle block(s) between the flush-left first block and the flush-right last block. Because `_paint_header` is shared by *every* header plugin, this task carries an explicit regression guard on the existing header plugins (`system`, `uptime`, `now`, `core`, `version`).

**Files:** `glances/outputs/curses_renderer_v5.py` (EDIT), `glances/outputs/glances_curses_v5.py` (EDIT), `tests/test_curses_v5.py` (EDIT — header painter tests), `tests/test_curses_renderer_v5.py` (EDIT — HEADER_SLOT ordering test)

**Interfaces:**
- Consumes: `HEADER_SLOT`, `build_frame`'s header sort, `TuiV5._paint_header(stdscr, blocks, y0, max_x) -> int`.
- Produces: `frame.header == [system, ip, uptime]` (ordered) and a `_paint_header` that paints every block (first flush-left, middle packed after it, last flush-right).

**Steps:**

- [ ] Add a failing ordering test to `tests/test_curses_renderer_v5.py` (mirror the existing slot-ordering tests in that file):
  - `test_header_slot_orders_ip_between_system_and_uptime`: assert `HEADER_SLOT == ("system", "ip", "uptime")` and `slot_for("ip") == "header"`.
  - `test_build_frame_header_order_system_ip_uptime`: build a `registry=[("uptime", False), ("ip", False), ("system", False)]` (deliberately out of order) with minimal `store_snapshot`/`fields_by_plugin` so each renders one Row; call `build_frame(...)`; assert `[b.name for b in frame.header] == ["system", "ip", "uptime"]` (the `HEADER_SLOT.index` sort enforces order regardless of discovery order).
- [ ] Add a failing painter test to `tests/test_curses_v5.py` (mirror `test_paint_header_places_first_left_and_last_right`, ~line 1113):
  - `test_paint_header_packs_middle_block_between_first_and_last`: build three blocks — `system = PluginBlock(name="system", rows=[Row(cells=[Cell(text="myhost Ubuntu")])])`, `ip = PluginBlock(name="ip", rows=[Row(cells=[Cell(text="IP", color=ColorRole.HEADER), Cell(text="192.168.1.10/24")])])`, `uptime = PluginBlock(name="uptime", rows=[Row(cells=[Cell(text="Uptime: 3d04h")])])`; call `tui._paint_header(fake_stdscr, [system, ip, uptime], y0=0, max_x=120)`; collect `calls = [(c.args[0], c.args[1], c.args[2]) for c in fake_stdscr.addstr.call_args_list]`. Assert: `system` painted at `y==0, x==0`; the `ip` cells painted on `y==0` at some `x` with `system.width < x < uptime_x` (i.e. after the first block and before the flush-right block); `uptime` painted at `y==0, x == 120 - len("Uptime: 3d04h")`. Return value (height) `== 1`.
- [ ] REGRESSION-GUARD (add, must PASS before AND after the change): `test_paint_header_two_blocks_unchanged` — replicate `test_paint_header_places_first_left_and_last_right`'s exact assertions for the 2-block `[system, uptime]` case at `max_x=80` (first at x=0, last at `x == 80 - len("Uptime: 3d04h")`, height 1). This pins the existing `system`/`uptime`/`now`/`core`/`version` header behaviour (all header plugins funnel through the same first/last packing) against the painter edit.
- [ ] Run (FAIL): `.venv/bin/python -m pytest tests/test_curses_renderer_v5.py::test_header_slot_orders_ip_between_system_and_uptime tests/test_curses_renderer_v5.py::test_build_frame_header_order_system_ip_uptime tests/test_curses_v5.py::test_paint_header_packs_middle_block_between_first_and_last -v` (HEADER_SLOT lacks `ip`; middle block skipped).
- [ ] Edit `glances/outputs/curses_renderer_v5.py` line 55 — add `"ip"` between `"system"` and `"uptime"`:

```python
# BEFORE
HEADER_SLOT: tuple[str, ...] = ("system", "uptime")
# AFTER
HEADER_SLOT: tuple[str, ...] = ("system", "ip", "uptime")
```

- [ ] Edit `glances/outputs/glances_curses_v5.py` — generalize `_paint_header` (currently lines 657-679) to pack middle blocks. Add the `_HEADER_GAP` class constant next to the other header spacing constants and replace the whole method body:

```python
# BEFORE (lines 657-679)
    def _paint_header(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint the header line (v4 parity): first block flush-left, last
        block flush-right. Returns the header height (0 when empty, else the
        tallest block painted — normally 1).

        Only the first and last blocks are positioned explicitly; the header
        is expected to hold at most two blocks (system + uptime). Any middle
        block (not expected in v5) is skipped rather than overlapped.
        """
        if not blocks:
            return 0
        height = 0
        first = blocks[0]
        self._paint_block(stdscr, first, y0, 0, max_x, fit_to_term=False)
        height = max(height, first.height)
        if len(blocks) > 1:
            last = blocks[-1]
            # Flush-right, but never overlap the flush-left block.
            x = max(first.width + 1, max_x - last.width)
            if x < max_x:
                self._paint_block(stdscr, last, y0, x, max(1, max_x - x), fit_to_term=False)
                height = max(height, last.height)
        return height

# AFTER
    # Horizontal gap between header blocks packed on the left (v4 parity:
    # `space_between_column = 3` between the system and ip blocks).
    _HEADER_GAP = 3

    def _paint_header(self, stdscr, blocks: list[PluginBlock], y0: int, max_x: int) -> int:
        """Paint the header line (v4 parity): first block flush-left, last
        block flush-right, and any middle block(s) packed left-to-right after
        the first (v4 paints `system … ip … uptime` this way, `glances_curses.py`
        `__display_top`). Returns the header height (0 when empty, else the
        tallest block painted — normally 1).

        The middle-block packing is generic (not ip-specific): the header slot
        order is owned by `HEADER_SLOT`; this painter just lays out whatever
        blocks it is handed without overlapping them.
        """
        if not blocks:
            return 0
        height = 0
        first = blocks[0]
        self._paint_block(stdscr, first, y0, 0, max_x, fit_to_term=False)
        height = max(height, first.height)
        # Middle blocks (e.g. ip): packed after the first block, each separated
        # by `_HEADER_GAP`. Stop if we run past the right edge.
        x = first.width
        for block in blocks[1:-1]:
            x += self._HEADER_GAP
            if x >= max_x:
                break
            self._paint_block(stdscr, block, y0, x, max(1, max_x - x), fit_to_term=False)
            height = max(height, block.height)
            x += block.width
        if len(blocks) > 1:
            last = blocks[-1]
            # Flush-right, but never overlap the left-packed blocks.
            right_x = max(x + 1, max_x - last.width)
            if right_x < max_x:
                self._paint_block(stdscr, last, y0, right_x, max(1, max_x - right_x), fit_to_term=False)
                height = max(height, last.height)
        return height
```

  Note the 2-block path is byte-for-byte equivalent to the old code: with no middle block, `x` stays `first.width`, so `right_x = max(first.width + 1, max_x - last.width)` — identical to the old `x = max(first.width + 1, max_x - last.width)`. This is why the regression guard passes unchanged.
- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_curses_renderer_v5.py::test_header_slot_orders_ip_between_system_and_uptime tests/test_curses_renderer_v5.py::test_build_frame_header_order_system_ip_uptime tests/test_curses_v5.py::test_paint_header_packs_middle_block_between_first_and_last tests/test_curses_v5.py::test_paint_header_two_blocks_unchanged -v`.
- [ ] Regression guard (existing header + frame tests must all stay green after the shared-painter change): `.venv/bin/python -m pytest tests/test_curses_v5.py -k "header or paint or separator" tests/test_curses_renderer_v5.py -q`.
- [ ] Lint/format: `.venv/bin/python -m ruff check glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py tests/test_curses_v5.py tests/test_curses_renderer_v5.py` and `ruff format` the same paths.
- [ ] `git add glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py tests/test_curses_v5.py tests/test_curses_renderer_v5.py` then STOP (never `git commit`).

---

### Task 6: `--hide-public-info` CLI flag wiring (main_v5 + TuiV5 view)

The renderer already reads `view["hide_public_info"]` (Task 4). This task surfaces the CLI flag into that view, mirroring the proven `--fahrenheit` wiring exactly.

**Files:** `glances/main_v5.py` (EDIT), `glances/outputs/glances_curses_v5.py` (EDIT), `tests/test_plugin_ip_v5.py` (EDIT — a tiny arg-parse assertion)

**Interfaces:**
- Consumes: `argparse` flag `--hide-public-info` (dest `hide_public_info`).
- Produces: `view["hide_public_info"]` in `TuiV5._build_view`.

**Steps:**

- [ ] Add a failing test to `tests/test_plugin_ip_v5.py` (import the main_v5 parser builder — the function returning the parser at `glances/main_v5.py:183`; confirm its name during implementation, e.g. `build_parser`):
  - `test_hide_public_info_flag_parses`: `parser.parse_args([]).hide_public_info is False`; `parser.parse_args(["--hide-public-info"]).hide_public_info is True`.
- [ ] Run (FAIL): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -k hide_public_info_flag -v`.
- [ ] Edit `glances/main_v5.py`: add the argument immediately after the `--fahrenheit` block (after line 172), mirroring its style:

```python
    parser.add_argument(
        "--hide-public-info",
        dest="hide_public_info",
        action="store_true",
        default=False,
        help="Mask the last two octets of the public IP address in the TUI (a.b.c.d -> a.b.*.*).",
    )
```

- [ ] Edit `glances/main_v5.py` `assemble()` `_TuiV5(...)` construction (after line 421 `fahrenheit=...`): add `hide_public_info=getattr(args, "hide_public_info", False),`.
- [ ] Edit `glances/outputs/glances_curses_v5.py`:
  - Add `hide_public_info: bool = False,` to `TuiV5.__init__` params (after `fahrenheit: bool = False,`, line 166).
  - Add `self._hide_public_info = bool(hide_public_info)` next to `self._fahrenheit` (after line 201).
  - Add `view["hide_public_info"] = self._hide_public_info` in `_build_view` (next to `view["fahrenheit"] = self._fahrenheit`, ~line 592).
- [ ] Run (PASS): `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py -k hide_public_info_flag -v`.
- [ ] Regression guard: `.venv/bin/python -m pytest tests/ -k "curses_v5 or main_v5" -q` (TuiV5 constructor signature change must not break existing curses/main tests).
- [ ] Lint/format the three files.
- [ ] `git add glances/main_v5.py glances/outputs/glances_curses_v5.py tests/test_plugin_ip_v5.py` then STOP.

---

### Task 7: Ship `public_api_allow_internal` COMMENTED in conf/glances.conf

**Files:** `conf/glances.conf` (EDIT — `[ip]` section)

**Interfaces:** Consumes: the model's `self.config.get("ip", "public_api_allow_internal", False)`. Produces: an operator-visible, commented, default-off key (behaviour unchanged).

**Steps:**

- [ ] Edit the `[ip]` section of `conf/glances.conf` (lines 336-362). Extend the public-IP comment block to document the new key, and add it COMMENTED (so the effective default stays `False` = SSRF-safe). Insert after the existing `# - public_template: ...` comment line (line 349) and near the `public_field`/`public_template` values (~line 362), e.g.:

```ini
# - public_api_allow_internal: SECURITY (CVE-2026-35587). By default the
#   public IP API URL is rejected if its host resolves to a loopback,
#   link-local (e.g. 169.254.169.254 cloud metadata), private (RFC1918)
#   or reserved address, and no HTTP request is made (credentials are
#   never forwarded to an internal host). Set to True ONLY if you point
#   public_api at a self-hosted service on a private/loopback address.
#public_api_allow_internal=false
```

- [ ] Verify the key stays commented and the section still parses: `.venv/bin/python -c "from glances.config_v5 import GlancesConfigV5; c=GlancesConfigV5(cli_config_path='conf/glances.conf'); print(c.get('ip','public_api_allow_internal', False))"` prints `False`.
- [ ] `git add conf/glances.conf` then STOP.

---

### Task 8: Documentation: create docs/aoa/ip.rst + register in the toctree

**Files:** `docs/aoa/ip.rst` (NEW), `docs/aoa/index.rst` (EDIT)

**Interfaces:** Produces: an `.rst` page (mirroring `docs/aoa/wifi.rst` style) documenting the ip plugin, the `[ip]` keys, and a dedicated SSRF-hardening section for `public_api_allow_internal`.

**Steps:**

- [ ] Create `docs/aoa/ip.rst` (mirror the small-plugin style of `docs/aoa/wifi.rst` — label, title, short intro, a `.. code-block:: ini` config sample, and a dedicated security subsection):

```rst
.. _ip:

IP
==

*Availability: all (private IP); public IP requires outbound network access*

Glances displays the private (LAN) IP address and, optionally, the public
(WAN) IP address queried from an online service.

Configuration (``[ip]`` section):

.. code-block:: ini

    [ip]
    disable=False
    refresh=60
    public_disabled=True
    public_refresh_interval=300
    public_api=https://ipv4.ipleak.net/json/
    public_field=ip
    public_template={continent_name}/{country_name}/{city_name}
    #public_username=<myname>
    #public_password=<mysecret>
    #public_api_allow_internal=false

- ``public_disabled`` — set to ``True`` on offline hosts (no public IP query).
- ``public_refresh_interval`` — seconds between public-IP refreshes (default 300).
- ``public_api`` — URL of a JSON service returning the public IP.
- ``public_field`` — JSON field holding the address (default ``ip``).
- ``public_template`` — human-readable summary built from the JSON fields.
- ``public_username`` / ``public_password`` — optional HTTP Basic Auth.

Hiding the public IP
--------------------

The ``--hide-public-info`` command-line flag masks the last two octets of
the public IP address in the interface (``a.b.c.d`` becomes ``a.b.*.*``).

SSRF hardening (``public_api_allow_internal``)
----------------------------------------------

``public_api`` is a fully operator-controlled URL, and
``public_username`` / ``public_password`` are attached to whatever host it
targets. To prevent Server-Side Request Forgery (CVE-2026-35587), Glances
enforces, on **every** refresh:

- **Scheme allowlist** — only ``http://`` and ``https://`` are accepted.
- **Internal-IP rejection (with DNS resolution)** — the URL host is
  resolved, and if **any** resolved address is loopback, link-local
  (including the cloud-metadata address ``169.254.169.254``), private
  (RFC1918) or reserved, the request is **skipped** — so credentials are
  never sent to an internal host. Resolving on each refresh also defeats
  DNS-alias / rebinding tricks that point a public hostname at an internal
  address.

This protection is **on by default** and safe for the common case (public
services such as ipleak). If you deliberately run your own public-IP
service on a private or loopback address, opt out with:

.. code-block:: ini

    [ip]
    public_api_allow_internal=true

You can disable the whole plugin with ``--disable-plugin ip`` or the ``I``
key in the interface.
```

- [ ] Edit `docs/aoa/index.rst`: add `ip` to the toctree (line ~32-33) between `connections` and `wifi` (logical: after network/connections, before wifi). The block becomes:

```rst
   network
   connections
   ip
   wifi
```

- [ ] Verify the doc is valid reST (no build required for the plan): confirm the new file appears exactly once in the toctree and the underline lengths match their titles.
- [ ] `git add docs/aoa/ip.rst docs/aoa/index.rst` then STOP.

---

### Task 9: Full-suite + lint gate

**Files:** none (verification only).

**Steps:**

- [ ] Run the ip suite: `.venv/bin/python -m pytest tests/test_plugin_ip_v5.py tests/test_plugin_ip_render_curses_v5.py -v` (all green).
- [ ] Run the full suite to catch cross-module regressions (TuiV5 signature, discovery): `.venv/bin/python -m pytest -q`.
- [ ] Lint gate: `.venv/bin/python -m ruff check glances/plugins/ip/ glances/main_v5.py glances/outputs/curses_renderer_v5.py glances/outputs/glances_curses_v5.py tests/test_plugin_ip_v5.py tests/test_plugin_ip_render_curses_v5.py tests/test_curses_v5.py tests/test_curses_renderer_v5.py` and `.venv/bin/python -m ruff format --check` on the same paths.
- [ ] `git add -A` (only the files listed in File Structure will have changed) then STOP. Do NOT commit — the maintainer commits/pushes/opens the PR personally.

---

## Final self-check (maps every §4.4 + §5 bullet to a task)

| Spec bullet | Task |
| --- | --- |
| §4.4 private grabber (`get_ip_address` + `_ip_to_cidr`, `to_thread`, `gateway` unpopulated) | 1 |
| §4.4 in-model cadenced public fetch (no thread, `monotonic`, cache reuse) | 3 |
| §4.4 fields_description (address/mask/mask_cidr/gateway/public_address/public_info_human, scalar) | 1 |
| §4.4 inline renderer + guard | 4 |
| §4.4 header placement (`system … ip … uptime`, v4 parity) — `HEADER_SLOT` + `_paint_header` middle-block packing + regression guard | 5 |
| §4.4 `--hide-public-info` masking (maintainer decision: TUI-only; REST `public_address` stays unmasked — deliberate, closed) | 4 (mask) + 6 (CLI→view wiring) |
| §4.4 config keys incl. new `public_api_allow_internal` | 1 (read) + 7 (conf) |
| §5 control 1 scheme allowlist | 1 (init check) + 1/2 (helper) |
| §5 control 2 DNS-resolved internal-IP rejection | 1 (helper) + 2 (tests) |
| §5 control 3 credential non-forwarding | 3 (only-on-allowed path) + 3 test |
| §5 new key commented in conf | 7 |
| §5 rebinding note = flagged follow-up (no pinned opener) | documented here (§ note above), not implemented |
| §5 SSRF helper + unit tests as a dedicated task | 2 |
| Docs: create ip.rst + edit index.rst | 8 |
