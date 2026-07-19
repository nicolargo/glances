# Glances v5 — ports plugin port (G6B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the v4 `ports` plugin to the Glances v5 asyncio collection architecture (LEFT sidebar), reusing `GlancesPortsList`, `GlancesWebList` and `ThreadScanner` **verbatim**, keeping the fetch path non-blocking, and computing the heterogeneous `status` levels with **bespoke logic inside the model** so that `glances/plugins/plugin/base_v5.py` is not modified.

**Architecture:** `PluginModel(GlancesPluginBase[list])`, `IS_COLLECTION=True`, `primary_key="indice"`, `EMITS_ALERTS=False`. `__init__` builds the scan list once (`GlancesPortsList(config=config).get_ports_list() + GlancesWebList(config=config).get_web_list()`), passing the `GlancesConfigV5` instance straight through. `_grab_stats()` relaunches `ThreadScanner` only when it is dead and returns a **copy** of the current scan list immediately — it never awaits a scan. `stop()` stops the scanner thread (called by `GlancesScheduler.stop()` via `asyncio.to_thread`). `_derived_parameters()` is overridden to compute `_levels` from `status`, branching on item kind (`url` → web, `host` → port). A dedicated `render_curses_v5.render` mirrors v4 `msg_curse()` — **no title row**, description left-aligned and truncated, status right-aligned on 9.

**Tech Stack:** Python, `threading` (v4 `ThreadScanner`), `requests` (optional, guarded in the v4 module), asyncio, curses renderer v5, pytest

## Cross-plan dependency — READ BEFORE STARTING

**This plan requires Task 1 of `docs/superpowers/plans/2026-07-18-glances-v5-g6b-folders.md` to have landed first.**

`GlancesPortsList.load()` calls `config.get_value(self._section, 'port_1_host')` with **two arguments**, and
`config.get_value(..., 'rtt_warning', default=None)`. The `GlancesConfigV5.get_value(section, option, default: T)`
that shipped before G6B **requires** the third argument and coerces the raw string via `type(default)` —
`type(None)` raises `TypeError: Unsupported config target type`. `folders`, `ports` and (in G6C) `amps` all hit
this, so the maintainer ruled for **one shared fix in `glances/config_v5.py`** rather than three per-plugin shims:
`default` becomes optional, and `default=None` returns the **raw, uncoerced** value (v4 `GlancesConfig.get_value`
semantics). That fix is Task 1 of the `folders` plan. **This plan does not modify `glances/config_v5.py`.**

Fail loudly if the plans are run out of order — run this gate first:

```bash
.venv/bin/python -c "import inspect; from glances.config_v5 import GlancesConfigV5; p = inspect.signature(GlancesConfigV5.get_value).parameters['default']; assert p.default is None, 'get_value(default=...) is still mandatory — run Task 1 of the folders plan first'; print('config_v5.get_value shared fix present — OK')"
```

Expected: prints `config_v5.get_value shared fix present — OK`. If it raises `AssertionError`, **stop** and run
the `folders` plan's Task 1 before continuing.

## Global Constraints

- **Mirror v4**: read the v4 `msg_curse()` + grabber before writing the renderer/model; divergent "clean generic" layouts are regressions.
- **Reuse the v4 engines VERBATIM.** `glances/ports_list.py`, `glances/web_list.py` and `ThreadScanner` (in `glances/plugins/ports/__init__.py`) are **NOT modified** by this plan.
- **`glances/plugins/plugin/base_v5.py` is NOT modified.** This is an explicit review criterion for G6B (spec §5.3 and §8). The bespoke `status` level logic lives in `glances/plugins/ports/model_v5.py`.
- `ports` renders in the **LEFT sidebar** (34-char budget). It is already in `LEFT_SLOT` in `curses_renderer_v5.py` — **no orchestrator/layout change**.
- **Plugin titles and column headers are ALWAYS `ColorRole.HEADER`** — never escalate a header's colour from `_levels`. (`ports` has no header row at all; see Task 4.)
- **Alerts fire on `warning`+ only**; `careful` is colour-only. `ports` sets `EMITS_ALERTS = False` — v4 runs `get_p_alert(log=False)` and never writes to the event history.
- **Empty configuration must stay valid**: no port and no web URL configured → empty payload, never a crash.
- **Accepted and deliberately NOT fixed** (spec §4): the hardcoded `time.sleep(1)` between ICMP scans; the unpooled `ThreadScanner`; the per-item `refresh` field being stored but unused as a per-item timer (only the global `[ports] refresh` drives the scheduler cadence).
- No dead code; no speculative config keys; surgical edits.
- **Do NOT touch `NEWS.rst`** (release-time only).
- **No commits / push / PR — stage only.** Every task ends at `git add`. **NEVER run `git commit`.** Never add a `Co-Authored-By` trailer.
- Tests via `.venv/bin/python -m pytest`; lint `.venv/bin/python -m ruff check` / `.venv/bin/python -m ruff format`.

---

## File Structure

- **Create** `glances/plugins/ports/model_v5.py` — the collection plugin: scan-list construction (Task 1), non-blocking fetch + `stop()` (Task 2), bespoke `_levels` (Task 3).
- **Create** `glances/plugins/ports/render_curses_v5.py` — the TUI renderer (Task 4).
- **Create** `tests/test_plugin_ports_v5.py` — model tests (Tasks 1–3).
- **Create** `tests/test_plugin_ports_render_curses_v5.py` — renderer tests (Task 4).
- **Modify** `docs/aoa/ports.rst` — v5 note (Task 5). `ports` is already in `docs/aoa/index.rst` — do NOT re-add.

**Unchanged and reused:** `glances/ports_list.py`, `glances/web_list.py`, `glances/plugins/ports/__init__.py` (for `ThreadScanner`), `glances/plugins/plugin/base_v5.py`, `glances/scheduler_v5.py`, `glances/outputs/curses_renderer_v5.py`.

### Reconciliation notes (v4 source vs. spec — baked into this plan)

1. **No per-plugin config shim.** The v4 list builders' `get_value` calling convention is served by the
   **shared** `glances/config_v5.py` fix delivered by the `folders` plan's Task 1 (see "Cross-plan
   dependency" above). The model passes its `GlancesConfigV5` instance straight to `GlancesPortsList`
   / `GlancesWebList` — no adapter, no wrapper, no duplicated shim.

2. **`_grab_stats()` returns COPIES.** `ThreadScanner` holds a live reference to the scan-list dicts and
   mutates `status` / `elapsed` from its own thread. The base pipeline's `_remove_parameters()` **replaces**
   each item dict with a filtered projection; if `_grab_stats()` returned the live dicts the base would
   hand filtered dicts back into the store while the scanner kept writing into the originals, and any future
   in-place transform would race the scanner. `_grab_stats()` therefore returns `[dict(item) for item in self._scan_list]`
   — a per-cycle snapshot. The scanner's list is never handed to the base.

3. **`proxies` and `ssl_verify` are deliberately NOT declared in `fields_description` — this is a
   credential-leak guard, not an oversight.** `web_x_http_proxy` / `web_x_https_proxy` may embed
   credentials inline (`http://user:pass@proxy:3128`). Every declared field is served verbatim by
   `/api/4/ports` and by every export module (InfluxDB, MongoDB, MQTT, …), and the project rule is
   that no credential is ever exposed through those surfaces. Undeclared fields are stripped by the
   base's `_remove_parameters()`, so they never reach the store, the REST API or an exporter. Locked
   by a test in Task 3 whose docstring states the reason, so nobody "completes" the field list later.

4. **Level precedence mirrors v4's `get_default_ret_value` (last-truthy-wins), with ONE deliberate
   deviation.** v4 builds `{'CAREFUL': …, 'CRITICAL': …, 'WARNING': …}` and takes the **last** truthy key,
   so WARNING outranks CRITICAL outranks CAREFUL. For **web** items that makes `status is None` resolve to
   **CRITICAL** (because `None not in [200, 301, 302]` is also true) — every configured URL is painted red
   for the whole first refresh window, before any scan has run. Spec §5.3 states web + `status is None` →
   **careful**, matching the `Scanning` string the renderer prints and matching the port branch. This plan
   implements the spec: `status is None` short-circuits to `careful` for **both** kinds. For non-`None`
   values the v4 last-wins order is preserved exactly (a 500 that is also slower than `rtt_warning`
   resolves to `warning`, not `critical`) and locked by a test.

5. **The 34-char budget vs. v4's `max_width - 7`.** v4 truncates the description to `max_width - 7` and then
   appends a 9-char right-aligned status, i.e. a block of `max_width + 2`. v5's painter hard-clips LEFT-sidebar
   blocks at 34 chars. The renderer therefore feeds the v4 formula the `max_width` whose +2 overshoot lands
   exactly on the budget: `_MAX_WIDTH = 32` → `_NAME_MAX_WIDTH = 32 - 7 = 25`, and `25 + 9 = 34`. The status
   cell carries `glue=True` so the painter inserts no separating space (v4 concatenates the two strings directly).

6. **No `__init__` prime and no `input_method` branch.** v4's `update()` has an SNMP branch setting
   `self.stats = None`; v5 has no SNMP input method, so the branch is dropped (dead code otherwise).

---

### Task 1: ports model — identity, fields, scan list

**Files:**
- Create: `glances/plugins/ports/model_v5.py`
- Create: `tests/test_plugin_ports_v5.py`

**Interfaces:**
- Consumes: `GlancesPluginBase` from `glances.plugins.plugin.base_v5`; `GlancesPortsList` from `glances.ports_list`; `GlancesWebList` from `glances.web_list`.
- Requires: the shared `GlancesConfigV5.get_value(section, option, default=None)` fix from the `folders` plan's Task 1 (see "Cross-plan dependency"). Run the gate command from that section before Step 1.
- Produces:
  - `PluginModel(store, config)` — `plugin_name = "ports"`, `IS_COLLECTION = True`, `EMITS_ALERTS = False`, `_primary_key == "indice"`, `fields_description` per below, and the instance attribute `self._scan_list: list[dict[str, Any]]`.
  - A placeholder `async _grab_stats(self) -> list` returning `[]` — replaced in Task 2.

- [ ] **Step 0: Gate — the shared `config_v5` fix must already be in place**

Run: `.venv/bin/python -c "import inspect; from glances.config_v5 import GlancesConfigV5; p = inspect.signature(GlancesConfigV5.get_value).parameters['default']; assert p.default is None, 'get_value(default=...) is still mandatory — run Task 1 of the folders plan first'; print('config_v5.get_value shared fix present — OK')"`
Expected: prints `config_v5.get_value shared fix present — OK`. On `AssertionError`, **stop** and run the `folders` plan's Task 1 first — this plan must not re-implement that fix.

- [ ] **Step 1: Write the failing identity / fields / scan-list tests**

Create `tests/test_plugin_ports_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 ports plugin model."""

from __future__ import annotations

from glances.plugins.ports.model_v5 import PluginModel

# A [ports] section with one TCP port, one ICMP port and one web URL.
_FULL_SECTION = {
    "refresh": "60",
    "timeout": "3",
    "port_default_gateway": "False",
    "port_1_host": "192.168.0.1",
    "port_1_port": "80",
    "port_1_description": "Home Box",
    "port_1_timeout": "1",
    "port_1_rtt_warning": "1000",
    "port_2_host": "www.google.com",
    "port_2_description": "Internet ICMP",
    "web_1_url": "https://blog.nicolargo.com",
    "web_1_description": "My Blog",
    "web_1_rtt_warning": "3000",
}


def _mk(store_with, config_with, section=None):
    return PluginModel(store_with(), config_with({"ports": section if section is not None else _FULL_SECTION}))


def test_identity(store_with, config_with):
    p = _mk(store_with, config_with)
    assert p.plugin_name == "ports"
    assert p.IS_COLLECTION is True
    assert p.EMITS_ALERTS is False
    assert p._primary_key == "indice"


def test_fields_present(store_with, config_with):
    p = _mk(store_with, config_with)
    fd = p.fields_description
    for key in ("indice", "description", "host", "port", "url", "status", "elapsed", "rtt_warning", "timeout", "refresh"):
        assert key in fd, key
    assert fd["indice"].get("primary_key") is True


def test_secrets_are_not_declared_fields(store_with, config_with):
    """`proxies` and `ssl_verify` must stay OUT of `fields_description`.

    WHY (do not "complete" the field list): `web_x_http_proxy` /
    `web_x_https_proxy` may embed credentials inline
    (`http://user:pass@proxy:3128`). Every DECLARED field is served verbatim by
    `/api/4/ports` — unauthenticated by default — and by every export module
    (InfluxDB, MongoDB, MQTT, ...). Declaring these two would leak the proxy
    credentials to both surfaces. Leaving them undeclared makes the base
    `_remove_parameters()` strip them from every payload; the scanner still
    reads them from its own live dicts, which never leave the process.
    """
    p = _mk(store_with, config_with)
    assert "proxies" not in p.fields_description
    assert "ssl_verify" not in p.fields_description


def test_scan_list_merges_ports_then_web(store_with, config_with):
    p = _mk(store_with, config_with)
    assert [i["indice"] for i in p._scan_list] == ["port_1", "port_2", "web_1"]
    # Port items carry host/port, web items carry url.
    assert p._scan_list[0]["host"] == "192.168.0.1"
    assert p._scan_list[0]["port"] == "80"
    assert p._scan_list[2]["url"] == "https://blog.nicolargo.com"
    assert "host" not in p._scan_list[2]


def test_rtt_warning_is_converted_to_seconds(store_with, config_with):
    p = _mk(store_with, config_with)
    # v4 converts the configured milliseconds to seconds.
    assert p._scan_list[0]["rtt_warning"] == 1.0
    assert p._scan_list[1]["rtt_warning"] is None
    assert p._scan_list[2]["rtt_warning"] == 3.0


def test_per_port_timeout_overrides_the_global_one(store_with, config_with):
    p = _mk(store_with, config_with)
    assert p._scan_list[0]["timeout"] == 1  # port_1_timeout=1
    assert p._scan_list[1]["timeout"] == 3  # falls back to [ports] timeout


def test_default_gateway_takes_indice_port_0(store_with, config_with, monkeypatch):
    import glances.ports_list

    monkeypatch.setattr(glances.ports_list, "get_default_gateway", lambda: "192.168.1.254")
    p = _mk(store_with, config_with, {"port_default_gateway": "True", "port_1_host": "www.free.fr"})
    assert [i["indice"] for i in p._scan_list] == ["port_0", "port_1"]
    gateway = p._scan_list[0]
    assert gateway["host"] == "192.168.1.254"
    assert gateway["port"] == 0  # 0 == ICMP
    assert gateway["description"] == "DefaultGateway"


def test_no_port_and_no_web_configured_yields_an_empty_scan_list(store_with, config_with):
    p = _mk(store_with, config_with, {"refresh": "60", "timeout": "3", "port_default_gateway": "False"})
    assert p._scan_list == []


def test_no_ports_section_at_all_does_not_crash(store_with, config_with):
    p = PluginModel(store_with(), config_with({"cpu": {"user_careful": "50"}}))
    assert p._scan_list == []
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.ports.model_v5'`.

- [ ] **Step 3: Create the model (fields + scan list, placeholder grab)**

Create `glances/plugins/ports/model_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — Ports plugin (collection, one item per scanned host/URL).

Port of ``glances/plugins/ports/__init__.py`` (v4). ``GlancesPortsList``,
``GlancesWebList`` and ``ThreadScanner`` are reused VERBATIM (design §4): the
scan list is built once at construction, a single background ``ThreadScanner``
sweeps it, and ``_grab_stats()`` only relaunches that thread when it is dead —
it never awaits a scan.

One list holds TWO item kinds:

- port-scan items — carry ``host`` + ``port`` (``port == 0`` means ICMP);
- web items       — carry ``url`` + ``elapsed``.

``status`` is therefore a heterogeneous union (``None`` while scanning, ``0``
or ``False`` on timeout, a float RTT in seconds, an HTTP status code, or the
string ``"Error"``), and its level depends on the value's *type* as much as its
magnitude. Neither the base's numeric ladder nor its categorical mapping
describes that, so ``_derived_parameters()`` is overridden here.
``glances/plugins/plugin/base_v5.py`` is deliberately NOT modified (design §5.3).

See docs/superpowers/specs/2026-07-18-glances-v5-g6b-design.md.
"""

from __future__ import annotations

import logging
from typing import Any, ClassVar

from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.ports_list import GlancesPortsList
from glances.web_list import GlancesWebList

logger = logging.getLogger(__name__)


class PluginModel(GlancesPluginBase[list]):
    """Ports/URL scanner plugin (collection, primary key ``indice``)."""

    plugin_name: ClassVar[str] = "ports"
    IS_COLLECTION: ClassVar[bool] = True
    # v4 runs `get_p_alert(log=False)`: the level colours the TUI cell but is
    # never written to the event history and never dispatches an action.
    EMITS_ALERTS: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        # `port_0` is reserved for the auto-added default-gateway ICMP entry;
        # configured entries are `port_1`.. and `web_1`...
        "indice": {"description": "Unique indice for the host/port.", "unit": "string", "primary_key": True},
        "description": {"description": "Human readable description for the host/port/URL.", "unit": "string"},
        "host": {"description": "Measurement is done on this host (or IP address).", "unit": "string"},
        "port": {"description": "Measurement is done on this port (0 for ICMP).", "unit": "number"},
        "url": {"description": "Measurement is done on this URL (HEAD request).", "unit": "string"},
        "status": {
            "description": "Measurement result: None while scanning, 0/False on timeout, "
            "the RTT in seconds for a port, or the HTTP status code for a URL.",
            "unit": "second",
        },
        "elapsed": {"description": "HTTP response time (URL items only).", "unit": "second"},
        "rtt_warning": {"description": "Warning threshold (in seconds) for the measurement.", "unit": "second"},
        "timeout": {"description": "Timeout (in seconds) for the measurement.", "unit": "second"},
        # Stored for API parity. NOT used as a per-item timer — the whole list
        # is swept on the global `[ports] refresh` cadence (v4 behaviour, design §4).
        "refresh": {"description": "Refresh time (in seconds) for this host/port.", "unit": "second"},
        # NOT declared on purpose: `proxies` (may embed credentials via
        # web_x_http_proxy) and `ssl_verify`. The base `_remove_parameters()`
        # strips every undeclared field, so they never reach the store/REST/export.
    }

    def __init__(self, store, config) -> None:
        super().__init__(store, config)

        # Build the scan list ONCE, exactly as v4's __init__ does. The v4
        # builders are reused verbatim (design §4) and read the config through
        # `get_value(section, option[, default])` — served natively by
        # `GlancesConfigV5` since the shared fix that also unblocks `folders`
        # and (G6C) `amps`: `default` is optional and `default=None` returns
        # the raw uncoerced value, v4 `GlancesConfig.get_value` semantics.
        self._scan_list: list[dict[str, Any]] = (
            GlancesPortsList(config=config).get_ports_list() + GlancesWebList(config=config).get_web_list()
        )

    async def _grab_stats(self) -> list:
        # Implemented in Task 2.
        return []
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py && .venv/bin/python -m ruff format glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`
Expected: `All checks passed!` then the reformat summary.
Then: `git add glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`

---

### Task 2: ports model — non-blocking fetch + `stop()`

**Files:**
- Modify: `glances/plugins/ports/model_v5.py`
- Modify: `tests/test_plugin_ports_v5.py`

**Interfaces:**
- Consumes: `ThreadScanner` from `glances.plugins.ports` (the v4 plugin module — reused verbatim); `PluginModel._scan_list` from Task 1.
- Produces on `PluginModel`:
  - `self._thread: ThreadScanner | None` (set in `__init__`, initially `None`).
  - `async _grab_stats(self) -> list[dict[str, Any]]` — relaunches the scanner **only when it is dead**, then returns `[dict(item) for item in self._scan_list]` **without awaiting the scan**.
  - `stop(self) -> None` — overrides the base no-op; stops the scanner thread. The base `stop()` is **synchronous**; `GlancesScheduler.stop()` offloads it via `asyncio.to_thread`, so a blocking teardown here cannot stall the event loop (containers precedent).

- [ ] **Step 1: Write the failing fetch / stop tests**

Append to `tests/test_plugin_ports_v5.py`:

```python
import threading
import time


class _FakeScanner:
    """Stand-in for ThreadScanner: records construction and start/stop, and
    stays 'alive' until released — no socket, no subprocess, no sleep(1)."""

    instances: list["_FakeScanner"] = []

    def __init__(self, stats):
        self.stats = stats
        self.started = False
        self.stopped = False
        self._alive = False
        _FakeScanner.instances.append(self)

    def start(self):
        self.started = True
        self._alive = True

    def is_alive(self):
        return self._alive

    def finish(self):
        """Simulate the scan completing."""
        self._alive = False

    def stop(self, timeout=None):
        self.stopped = True
        self._alive = False


def _patch_scanner(monkeypatch):
    import glances.plugins.ports.model_v5 as model_v5

    _FakeScanner.instances = []
    monkeypatch.setattr(model_v5, "ThreadScanner", _FakeScanner)
    return _FakeScanner


async def test_grab_starts_a_scanner_on_the_first_cycle(store_with, config_with, monkeypatch):
    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    out = await p._grab_stats()
    assert len(scanner.instances) == 1
    assert scanner.instances[0].started is True
    # The scanner sweeps the LIVE list, not the returned copies.
    assert scanner.instances[0].stats is p._scan_list
    assert [i["indice"] for i in out] == ["port_1", "port_2", "web_1"]


async def test_grab_returns_copies_not_the_live_scanner_dicts(store_with, config_with, monkeypatch):
    _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    out = await p._grab_stats()
    for returned, live in zip(out, p._scan_list):
        assert returned == live
        assert returned is not live
    # Mutating the returned snapshot must not corrupt the scanner's list.
    out[0]["status"] = 0.123
    assert p._scan_list[0]["status"] is None


async def test_grab_does_not_relaunch_while_a_scan_is_in_flight(store_with, config_with, monkeypatch):
    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    await p._grab_stats()
    await p._grab_stats()
    await p._grab_stats()
    assert len(scanner.instances) == 1  # still alive → not relaunched


async def test_grab_relaunches_once_the_scanner_is_dead(store_with, config_with, monkeypatch):
    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    await p._grab_stats()
    scanner.instances[0].finish()
    await p._grab_stats()
    assert len(scanner.instances) == 2
    assert scanner.instances[1].started is True


async def test_grab_returns_promptly_while_a_real_scan_is_in_flight(store_with, config_with, monkeypatch):
    """The scan must NOT be awaited. A real (non-fake) thread that blocks for
    a long time must not delay `_grab_stats()` by more than a few ms."""
    import glances.plugins.ports.model_v5 as model_v5

    release = threading.Event()

    class _SlowScanner(threading.Thread):
        def __init__(self, stats):
            super().__init__(daemon=True)
            self.stats = stats

        def run(self):
            release.wait(timeout=30)

        def stop(self, timeout=None):
            release.set()

    monkeypatch.setattr(model_v5, "ThreadScanner", _SlowScanner)
    p = _mk(store_with, config_with)
    try:
        started = time.monotonic()
        await p._grab_stats()  # launches the blocking thread
        await p._grab_stats()  # scan still in flight
        elapsed = time.monotonic() - started
        assert elapsed < 1.0, f"_grab_stats() blocked for {elapsed:.2f}s — it must not await the scan"
    finally:
        release.set()


async def test_grab_with_an_empty_scan_list_returns_empty_and_starts_nothing(store_with, config_with, monkeypatch):
    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with, {"refresh": "60", "timeout": "3", "port_default_gateway": "False"})
    assert await p._grab_stats() == []
    # Nothing to scan → no thread. Sweeping an empty list every cycle is pure waste.
    assert scanner.instances == []


def test_stop_stops_the_running_scanner(store_with, config_with, monkeypatch):
    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    p._thread = scanner([])
    p._thread.start()
    p.stop()
    assert p._thread is None
    assert scanner.instances[-1].stopped is True


def test_stop_without_a_scanner_is_a_noop(store_with, config_with, monkeypatch):
    _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    assert p.stop() is None  # never started → must not raise


def test_stop_swallows_a_raising_scanner(store_with, config_with, monkeypatch):
    _patch_scanner(monkeypatch)

    class _Boom:
        def stop(self, timeout=None):
            raise RuntimeError("boom")

    p = _mk(store_with, config_with)
    p._thread = _Boom()
    p.stop()  # must not raise — the scheduler tears every plugin down in sequence
    assert p._thread is None
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -k "grab or stop" -v`
Expected: FAIL — `AttributeError: module 'glances.plugins.ports.model_v5' has no attribute 'ThreadScanner'` on the `monkeypatch.setattr` calls, and `_grab_stats()` returning `[]`.

- [ ] **Step 3: Implement the fetch path and `stop()`**

In `glances/plugins/ports/model_v5.py`, add `ThreadScanner` to the imports (keep them alphabetically ordered as ruff expects):

```python
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.plugins.ports import ThreadScanner
from glances.ports_list import GlancesPortsList
from glances.web_list import GlancesWebList
```

Add the thread handle at the end of `__init__` (after `self._scan_list = ...`):

```python
        # The single background scanner sweeping the whole list. Relaunched by
        # `_grab_stats()` only when dead — v4 `update()` semantics.
        self._thread: ThreadScanner | None = None
```

Replace the placeholder `_grab_stats` with:

```python
    async def _grab_stats(self) -> list:
        """Return the current scan results; relaunch the scanner if it is dead.

        NON-BLOCKING by construction (design §4): this coroutine never awaits
        the scan. `ThreadScanner.run()` sweeps the list in its own thread —
        including the accepted hardcoded `time.sleep(1)` between ICMP probes —
        and writes `status` / `elapsed` straight into the live dicts. Each
        cycle we simply publish a snapshot of whatever the scanner has produced
        so far; items not yet reached keep `status = None` and render as
        `Scanning`.

        The snapshot is a per-item COPY: the base pipeline replaces item dicts
        in `_remove_parameters()`, and the scanner must keep owning the
        originals.
        """
        if not self._scan_list:
            # Nothing configured — empty payload, no thread. Sweeping an empty
            # list every cycle would be pure waste.
            return []
        if self._thread is None or not self._thread.is_alive():
            self._thread = ThreadScanner(self._scan_list)
            self._thread.start()
        return [dict(item) for item in self._scan_list]

    def stop(self) -> None:
        """Stop the background scanner (base teardown hook).

        The base `stop()` is synchronous; `GlancesScheduler.stop()` offloads it
        via `asyncio.to_thread`, so a blocking teardown here cannot stall the
        event loop (same contract as `containers`). Must be safe to call even
        if the plugin never produced stats.
        """
        if self._thread is None:
            return
        try:
            self._thread.stop()
        except Exception as e:
            logger.warning("ports: stopping the scanner thread failed: %s", e)
        self._thread = None
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -v`
Expected: all PASS (the whole file, Task 1 tests included).

- [ ] **Step 5: Confirm the scheduler teardown contract**

Run: `.venv/bin/python -c "import inspect; from glances.plugins.ports.model_v5 import PluginModel; assert not inspect.iscoroutinefunction(PluginModel.stop); import glances.scheduler_v5 as s; assert 'to_thread' in inspect.getsource(s.GlancesScheduler.stop); print('sync stop(), offloaded by the scheduler — OK')"`
Expected: prints `sync stop(), offloaded by the scheduler — OK`.

- [ ] **Step 6: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py && .venv/bin/python -m ruff format glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`
Expected: `All checks passed!`
Then: `git add glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`

---

### Task 3: ports model — bespoke `_levels` (`base_v5.py` untouched)

**Files:**
- Modify: `glances/plugins/ports/model_v5.py`
- Modify: `tests/test_plugin_ports_v5.py`

**Interfaces:**
- Produces on `PluginModel`:
  - `_WEB_OK_CODES: ClassVar[tuple[int, int, int]] = (200, 301, 302)`
  - `@staticmethod _port_level(item: dict[str, Any]) -> str | None`
  - `@staticmethod _web_level(item: dict[str, Any]) -> str | None`
  - `_derived_parameters(self) -> None` — overrides the base; sets
    `self._levels = {indice: {"status": {"level": <level>, "prominent": False}}}`
    for every item that resolves to a level. Items with no level get **no entry**
    (renderer falls back to `ColorRole.DEFAULT`).

**Level table (spec §5.3), implemented verbatim:**

| Kind | Condition | Level |
|---|---|---|
| port | `status is None` | careful |
| port | `status == 0` (catches `False`) | critical |
| port | `status > rtt_warning` | warning |
| web | `status is None` | careful |
| web | `status not in (200, 301, 302)` | critical |
| web | `elapsed > rtt_warning` | warning |

`status is None` short-circuits to `careful` for **both** kinds. Below that,
v4's last-truthy-wins precedence is preserved: `warning` overrides `critical`.

- [ ] **Step 1: Write the failing level tests**

Append to `tests/test_plugin_ports_v5.py`:

```python
def _levels_for(store_with, config_with, items):
    p = _mk(store_with, config_with)
    p._stats = items
    p._derived_parameters()
    return p._levels


# --- port kind ------------------------------------------------------------

def test_port_level_none_status_is_careful(store_with, config_with):
    item = {"indice": "port_1", "host": "h", "port": 80, "status": None, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["level"] == "careful"


def test_port_level_zero_status_is_critical(store_with, config_with):
    item = {"indice": "port_1", "host": "h", "port": 80, "status": 0, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["level"] == "critical"


def test_port_level_false_status_is_critical(store_with, config_with):
    # `_port_scan_tcp` writes `False` on failure; `False == 0` in Python, so v4's
    # `status == 0` condition catches it. Locked here so nobody "tightens" it to `is 0`.
    item = {"indice": "port_1", "host": "h", "port": 80, "status": False, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["level"] == "critical"


def test_port_level_rtt_above_threshold_is_warning(store_with, config_with):
    item = {"indice": "port_1", "host": "h", "port": 80, "status": 1.5, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["level"] == "warning"


def test_port_level_rtt_below_threshold_has_no_entry(store_with, config_with):
    item = {"indice": "port_1", "host": "h", "port": 80, "status": 0.2, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item]) == {}


def test_port_level_without_rtt_warning_has_no_entry(store_with, config_with):
    item = {"indice": "port_2", "host": "h", "port": 80, "status": 9.9, "rtt_warning": None}
    assert _levels_for(store_with, config_with, [item]) == {}


# --- web kind -------------------------------------------------------------

def test_web_level_none_status_is_careful(store_with, config_with):
    # Deliberate deviation from v4 (see plan reconciliation note 4): v4's
    # last-truthy-wins made an unscanned URL CRITICAL because
    # `None not in (200, 301, 302)`. Spec §5.3 says careful — matching the
    # `Scanning` label and the port branch.
    item = {"indice": "web_1", "url": "http://x", "status": None, "elapsed": 0, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "careful"


def test_web_level_bad_http_code_is_critical(store_with, config_with):
    item = {"indice": "web_1", "url": "http://x", "status": 404, "elapsed": 0.1, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "critical"


def test_web_level_error_string_is_critical(store_with, config_with):
    # `_web_scan` writes the literal string "Error" when requests raises.
    item = {"indice": "web_1", "url": "http://x", "status": "Error", "elapsed": 0, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "critical"


def test_web_level_slow_response_is_warning(store_with, config_with):
    item = {"indice": "web_1", "url": "http://x", "status": 200, "elapsed": 4.0, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "warning"


def test_web_level_warning_outranks_critical_v4_precedence(store_with, config_with):
    # v4 `get_default_ret_value` keeps the LAST truthy condition: a 500 that is
    # ALSO slower than rtt_warning resolves to WARNING, not CRITICAL.
    item = {"indice": "web_1", "url": "http://x", "status": 500, "elapsed": 4.0, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "warning"


def test_web_level_ok_codes_have_no_entry(store_with, config_with):
    items = [
        {"indice": "web_1", "url": "http://x", "status": 200, "elapsed": 0.1, "rtt_warning": 3.0},
        {"indice": "web_2", "url": "http://y", "status": 301, "elapsed": 0.1, "rtt_warning": None},
        {"indice": "web_3", "url": "http://z", "status": 302, "elapsed": 0.1, "rtt_warning": None},
    ]
    assert _levels_for(store_with, config_with, items) == {}


# --- both kinds in one list ----------------------------------------------

def test_both_kinds_are_levelled_in_the_same_list(store_with, config_with):
    items = [
        {"indice": "port_1", "host": "h", "port": 80, "status": 0, "rtt_warning": 1.0},
        {"indice": "web_1", "url": "http://x", "status": 200, "elapsed": 9.0, "rtt_warning": 3.0},
    ]
    levels = _levels_for(store_with, config_with, items)
    assert levels["port_1"]["status"]["level"] == "critical"
    assert levels["web_1"]["status"]["level"] == "warning"


def test_levels_are_not_prominent(store_with, config_with):
    # v4 colours the status text only — no highlighted background.
    item = {"indice": "port_1", "host": "h", "port": 80, "status": 0, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["prominent"] is False


def test_empty_stats_yields_empty_levels(store_with, config_with):
    assert _levels_for(store_with, config_with, []) == {}


def test_transform_strips_proxies_and_ssl_verify_from_the_payload(store_with, config_with):
    p = _mk(store_with, config_with)
    p._stats = [
        {
            "indice": "web_1",
            "url": "http://x",
            "description": "My Blog",
            "status": 200,
            "elapsed": 0.1,
            "rtt_warning": 3.0,
            "timeout": 3,
            "refresh": 60,
            "ssl_verify": True,
            "proxies": {"http": "http://user:pass@proxy:3128", "https": None},
            "key": "indice",
        }
    ]
    p._transform()
    assert "proxies" not in p._stats[0]
    assert "ssl_verify" not in p._stats[0]
    assert "key" not in p._stats[0]
    assert p._stats[0]["description"] == "My Blog"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -k "level or transform" -v`
Expected: FAIL — the base `_derived_parameters()` finds no `watched` field, so `_levels` stays `{}` and every level assertion raises `KeyError`. (`test_port_level_rtt_below_threshold_has_no_entry`, `test_web_level_ok_codes_have_no_entry`, `test_empty_stats_yields_empty_levels` and `test_transform_strips_...` already PASS.)

- [ ] **Step 3: Implement the bespoke level logic**

In `glances/plugins/ports/model_v5.py`, add the class constant just after `EMITS_ALERTS`:

```python
    # HTTP status codes v4 treats as healthy for a web item.
    _WEB_OK_CODES: ClassVar[tuple[int, ...]] = (200, 301, 302)
```

Then append these three methods to `PluginModel` (after `stop()`):

```python
    # ------------------------------------------------------------- levels
    #
    # BESPOKE, on purpose: `base_v5.py` is NOT modified by G6B (design §5.3).
    # `status` is a heterogeneous union whose level depends on the value's TYPE
    # as much as its magnitude, so neither the base's numeric ladder nor its
    # categorical mapping applies. A generic threshold hook was considered and
    # rejected as speculative — `ports` would be its only caller.

    @staticmethod
    def _port_level(item: dict[str, Any]) -> str | None:
        """Level for a port-scan item. Mirrors v4 `get_conds_if_port`."""
        status = item.get("status")
        if status is None:
            return "careful"  # not scanned yet → rendered as `Scanning`
        level: str | None = None
        # `False == 0` in Python: this single test covers both the ICMP
        # (`status = False`) and the TCP (`status = False`) timeout paths.
        if status == 0:
            level = "critical"
        rtt_warning = item.get("rtt_warning")
        # v4 keeps the LAST truthy condition, so WARNING outranks CRITICAL.
        if isinstance(status, (int, float)) and rtt_warning is not None and status > rtt_warning:
            level = "warning"
        return level

    @staticmethod
    def _web_level(item: dict[str, Any]) -> str | None:
        """Level for a web item. Mirrors v4 `get_conds_if_url`, except that a
        `None` status resolves to `careful` instead of `critical` (design §5.3):
        v4's last-truthy-wins painted every URL red for the whole first refresh
        window, before any scan had run."""
        status = item.get("status")
        if status is None:
            return "careful"  # not scanned yet → rendered as `Scanning`
        level: str | None = None
        # Covers a bad HTTP code AND the literal string "Error" written by
        # `ThreadScanner._web_scan` when `requests` raises.
        if status not in PluginModel._WEB_OK_CODES:
            level = "critical"
        rtt_warning = item.get("rtt_warning")
        elapsed = item.get("elapsed")
        # v4 keeps the LAST truthy condition, so WARNING outranks CRITICAL.
        if rtt_warning is not None and elapsed is not None and elapsed > rtt_warning:
            level = "warning"
        return level

    def _derived_parameters(self) -> None:
        """Compute `_levels` for both item kinds.

        Shape (collection): `{indice: {"status": {"level": …, "prominent": False}}}`.
        Items that resolve to no level get NO entry at all — the renderer then
        falls back to `ColorRole.DEFAULT`, mirroring v4's `'OK'` return value
        which carries no decoration.
        """
        self._levels = {}
        if not isinstance(self._stats, list):
            return
        for item in self._stats:
            if not isinstance(item, dict):
                continue
            indice = item.get("indice")
            if indice is None:
                continue
            if "url" in item:
                level = self._web_level(item)
            elif "host" in item:
                level = self._port_level(item)
            else:
                continue
            if level is None:
                continue
            # `prominent = False`: v4 colours the status text only, never the
            # background.
            self._levels[indice] = {"status": {"level": level, "prominent": False}}
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py -v`
Expected: all PASS (the whole file, Tasks 1–3).

- [ ] **Step 5: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py && .venv/bin/python -m ruff format glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`
Expected: `All checks passed!`
Then: `git add glances/plugins/ports/model_v5.py tests/test_plugin_ports_v5.py`

- [ ] **Step 6: Guard — `base_v5.py` was NOT touched**

Run: `git diff --cached --name-only -- glances/plugins/plugin/base_v5.py glances/ports_list.py glances/web_list.py glances/plugins/ports/__init__.py`
Expected: **empty output**. Any file listed here is a review failure — revert it.

---

### Task 4: ports renderer (`render_curses_v5.py`)

**Files:**
- Create: `glances/plugins/ports/render_curses_v5.py`
- Create: `tests/test_plugin_ports_render_curses_v5.py`

**Interfaces:**
- Consumes: `Cell`, `Row`, `ColorRole`, `_LEVEL_TO_ROLE` from `glances.outputs.curses_renderer_v5`; the payload written by Task 1–3 (`{"data": [...], "time_since_update": float, "_levels": {indice: {"status": {"level", "prominent"}}}}`).
- Produces: `render(payload, fields_desc=None, view=None) -> list[Row]` — **one row per item, NO title row and NO header row**. Declares `view` so `build_frame` auto-registers it as view-aware (unused today, signature parity with the other v5 renderers).
- Module constants: `_LEFT_SIDEBAR_MAX_WIDTH = 34`, `_STATUS_COL_WIDTH = 9`, `_MAX_WIDTH = 32`, `_NAME_MAX_WIDTH = _MAX_WIDTH - 7` (= 25).

**Status strings — reproduced from v4 `set_status_if_host` / `set_status_if_url`:**

| Kind | Condition | String |
|---|---|---|
| port | `host is None` | `None` |
| port | `status is None` | `Scanning` |
| port | `status is True` | `Open` |
| port | `status == 0` (catches `False`) | `Timeout` |
| port | otherwise (float RTT in seconds) | `{status * 1000:.0f}ms` |
| web | `status` is a number | `Code {status}` |
| web | `status is None` | `Scanning` |
| web | otherwise (the string written by the scanner) | `Error` |

- [ ] **Step 1: Write the failing renderer tests**

Create `tests/test_plugin_ports_render_curses_v5.py`:

```python
#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for the Glances v5 ports TUI renderer."""

from __future__ import annotations

from glances.outputs.curses_renderer_v5 import ColorRole
from glances.plugins.ports.render_curses_v5 import (
    _NAME_MAX_WIDTH,
    _STATUS_COL_WIDTH,
    render,
)


def _payload(data, levels=None):
    return {"data": data, "time_since_update": 2.0, "_levels": levels or {}}


def _texts(row):
    return "".join(c.text for c in row.cells)


def _status_text(row):
    return row.cells[-1].text.strip()


def test_empty_data_returns_empty():
    assert render(_payload([])) == []


def test_missing_data_key_returns_empty():
    assert render({}) == []


# --- NO TITLE ROW guard ---------------------------------------------------

def test_no_title_row_deliberate_do_not_fix():
    """`ports` sits directly under `network` in LEFT_SLOT; the two belong to the
    same functional domain and read as one continuous block. The absent title is
    that continuity, NOT an oversight (design §5.3). This test exists so a future
    reviewer cannot silently "align ports with the other LEFT plugins"."""
    data = [
        {"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0.012, "rtt_warning": None},
        {"indice": "web_1", "url": "http://x", "description": "My Blog", "status": 200, "elapsed": 0.1,
         "rtt_warning": None},
    ]
    rows = render(_payload(data))
    # Exactly one row per item — no title, no column header.
    assert len(rows) == len(data)
    assert "PORTS" not in _texts(rows[0]).upper()
    for row in rows:
        for cell in row.cells:
            assert cell.color is not ColorRole.HEADER
            assert cell.bold is False


# --- port-kind status strings --------------------------------------------

def test_port_status_scanning():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": None}]
    assert _status_text(render(_payload(data))[0]) == "Scanning"


def test_port_status_open_when_status_is_true():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": True}]
    assert _status_text(render(_payload(data))[0]) == "Open"


def test_port_status_timeout_when_status_is_false():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": False}]
    assert _status_text(render(_payload(data))[0]) == "Timeout"


def test_port_status_timeout_when_status_is_zero():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0}]
    assert _status_text(render(_payload(data))[0]) == "Timeout"


def test_port_status_rtt_in_milliseconds():
    # v4 stores the RTT in seconds and displays milliseconds, rounded to 0 dp.
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0.0123}]
    assert _status_text(render(_payload(data))[0]) == "12ms"


def test_port_status_none_host():
    # `get_default_gateway()` can return None → v4 prints the literal "None".
    data = [{"indice": "port_0", "host": None, "port": 0, "description": "DefaultGateway", "status": None}]
    assert _status_text(render(_payload(data))[0]) == "None"


# --- web-kind status strings ---------------------------------------------

def test_web_status_code():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": 404, "elapsed": 0.1}]
    assert _status_text(render(_payload(data))[0]) == "Code 404"


def test_web_status_scanning():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": None, "elapsed": 0}]
    assert _status_text(render(_payload(data))[0]) == "Scanning"


def test_web_status_error_string():
    data = [{"indice": "web_1", "url": "http://x", "description": "My Blog", "status": "Error", "elapsed": 0}]
    assert _status_text(render(_payload(data))[0]) == "Error"


# --- layout ---------------------------------------------------------------

def test_description_is_left_aligned_and_padded():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    name_cell = render(_payload(data))[0].cells[0]
    assert name_cell.text == "Box".ljust(_NAME_MAX_WIDTH)


def test_long_description_is_truncated():
    long_name = "A" * 80
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": long_name, "status": 0}]
    name_cell = render(_payload(data))[0].cells[0]
    assert name_cell.text == "A" * _NAME_MAX_WIDTH
    assert len(name_cell.text) == _NAME_MAX_WIDTH


def test_status_is_right_aligned_on_nine_and_glued():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    status_cell = render(_payload(data))[0].cells[-1]
    assert status_cell.text == "Timeout".rjust(_STATUS_COL_WIDTH)
    # glue=True → the painter adds NO separating space (v4 concatenates directly),
    # so the block spans exactly 25 + 9 = 34 = the left-sidebar budget.
    assert status_cell.glue is True


def test_block_fits_the_left_sidebar_budget():
    from glances.outputs.curses_renderer_v5 import PluginBlock

    data = [{"indice": "web_1", "url": "http://x", "description": "X" * 80, "status": 404, "elapsed": 0.1}]
    block = PluginBlock(name="ports", rows=render(_payload(data)))
    assert block.width == 34


def test_missing_description_renders_blank_padding():
    data = [{"indice": "port_1", "host": "h", "port": 80, "status": 0}]
    assert render(_payload(data))[0].cells[0].text == " " * _NAME_MAX_WIDTH


def test_item_with_neither_host_nor_url_is_skipped():
    data = [{"indice": "weird_1", "description": "?", "status": None}]
    assert render(_payload(data)) == []


# --- colours --------------------------------------------------------------

def test_port_status_cell_coloured_from_levels():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0}]
    levels = {"port_1": {"status": {"level": "critical", "prominent": False}}}
    cell = render(_payload(data, levels))[0].cells[-1]
    assert cell.color == ColorRole.CRITICAL
    assert cell.prominent is False


def test_web_status_cell_coloured_from_levels():
    data = [{"indice": "web_1", "url": "http://x", "description": "Blog", "status": 200, "elapsed": 9.0}]
    levels = {"web_1": {"status": {"level": "warning", "prominent": False}}}
    assert render(_payload(data, levels))[0].cells[-1].color == ColorRole.WARNING


def test_careful_level_colours_the_scanning_cell():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": None}]
    levels = {"port_1": {"status": {"level": "careful", "prominent": False}}}
    assert render(_payload(data, levels))[0].cells[-1].color == ColorRole.CAREFUL


def test_no_level_entry_falls_back_to_default_colour():
    data = [{"indice": "port_1", "host": "h", "port": 80, "description": "Box", "status": 0.01}]
    assert render(_payload(data))[0].cells[-1].color == ColorRole.DEFAULT


def test_both_kinds_render_in_one_block():
    data = [
        {"indice": "port_1", "host": "h", "port": 80, "description": "Home Box", "status": 0},
        {"indice": "web_1", "url": "http://x", "description": "My Blog", "status": 200, "elapsed": 0.1},
    ]
    levels = {
        "port_1": {"status": {"level": "critical", "prominent": False}},
        "web_1": {"status": {"level": "warning", "prominent": False}},
    }
    rows = render(_payload(data, levels))
    assert len(rows) == 2
    assert _status_text(rows[0]) == "Timeout"
    assert rows[0].cells[-1].color == ColorRole.CRITICAL
    assert _status_text(rows[1]) == "Code 200"
    assert rows[1].cells[-1].color == ColorRole.WARNING
```

- [ ] **Step 2: Run — expect FAIL**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_render_curses_v5.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'glances.plugins.ports.render_curses_v5'`.

- [ ] **Step 3: Implement the renderer**

Create `glances/plugins/ports/render_curses_v5.py`:

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — TUI curses renderer for the ports plugin.

Mirror of v4 `ports.msg_curse()`: one row per scanned item, the description
left-aligned and truncated, then the status right-aligned on 9 chars.

    Home Box                  12ms
    Internet ICMP          Timeout
    My Blog               Code 200

NO TITLE ROW — deliberate. `ports` sits directly under `network` in
`LEFT_SLOT`; the two belong to the same functional domain and read as one
continuous block. The missing title is that continuity, not an oversight
(design §5.3). `tests/test_plugin_ports_render_curses_v5.py::test_no_title_row_deliberate_do_not_fix`
locks it.

Width budget: v4 truncates the description to `max_width - 7` and then appends
a 9-char status, i.e. a block of `max_width + 2`. v5's painter hard-clips
LEFT-sidebar blocks at 34 chars, so the v4 formula is fed the `max_width` whose
+2 overshoot lands exactly on the budget: 32 - 7 = 25, and 25 + 9 = 34. The
status cell carries `glue=True` so the painter inserts no separating space
(v4 concatenates the two strings directly).

One list holds TWO item kinds and every branch below keys off that:

- web item  — has `url`; status is an HTTP code, `None`, or the string "Error";
- port item — has `host`; status is `None`, `True`, `False`/`0`, or a float RTT
  in seconds.
"""

from __future__ import annotations

import numbers
from typing import Any

from glances.outputs.curses_renderer_v5 import _LEVEL_TO_ROLE, Cell, ColorRole, Row

# Painter cap for a LEFT-sidebar block.
_LEFT_SIDEBAR_MAX_WIDTH = 34
# v4 right-aligns the status string on 9 chars.
_STATUS_COL_WIDTH = 9
# See the module docstring: 32 - 7 = 25, and 25 + 9 = _LEFT_SIDEBAR_MAX_WIDTH.
_MAX_WIDTH = _LEFT_SIDEBAR_MAX_WIDTH - _STATUS_COL_WIDTH + 7
_NAME_MAX_WIDTH = _MAX_WIDTH - 7


def _status_if_host(item: dict[str, Any]) -> str:
    """v4 `set_status_if_host`, reproduced verbatim."""
    if item.get("host") is None:
        # `get_default_gateway()` returns None when it cannot be resolved.
        return "None"
    status = item.get("status")
    if status is None:
        return "Scanning"
    if isinstance(status, bool) and status is True:
        return "Open"
    if status == 0:
        # `False == 0`: covers both the ICMP and the TCP timeout paths.
        return "Timeout"
    # v4 stores the RTT in seconds and displays milliseconds.
    return f"{status * 1000.0:.0f}ms"


def _status_if_url(item: dict[str, Any]) -> str:
    """v4 `set_status_if_url`, reproduced verbatim."""
    status = item.get("status")
    if isinstance(status, numbers.Number):
        return f"Code {status}"
    if status is None:
        return "Scanning"
    # The scanner writes the literal string "Error" when `requests` raises.
    return str(status)


def _level_role(entry: Any) -> tuple[ColorRole, bool]:
    if isinstance(entry, dict):
        return (_LEVEL_TO_ROLE.get(entry.get("level"), ColorRole.DEFAULT), bool(entry.get("prominent")))
    return (ColorRole.DEFAULT, False)


def render(
    payload: dict[str, Any],
    fields_desc: dict[str, dict[str, Any]] | None = None,
    view: dict[str, Any] | None = None,
) -> list[Row]:
    items: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw = payload.get("data")
        if isinstance(raw, list):
            items = [i for i in raw if isinstance(i, dict)]
    if not items:
        return []

    levels = payload.get("_levels")
    if not isinstance(levels, dict):
        levels = {}

    rows: list[Row] = []
    for item in items:
        # Branch on item kind. An item with neither key cannot be scanned and
        # is skipped rather than rendered as a blank status.
        if "url" in item:
            status_text = _status_if_url(item)
        elif "host" in item:
            status_text = _status_if_host(item)
        else:
            continue

        role, prominent = _level_role(levels.get(item.get("indice"), {}).get("status"))
        description = str(item.get("description") or "")[:_NAME_MAX_WIDTH]
        rows.append(
            Row(
                cells=[
                    Cell(text=f"{description:<{_NAME_MAX_WIDTH}}"),
                    Cell(
                        text=f"{status_text:>{_STATUS_COL_WIDTH}}",
                        color=role,
                        prominent=prominent,
                        glue=True,
                    ),
                ]
            )
        )
    return rows
```

- [ ] **Step 4: Run — expect PASS**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_render_curses_v5.py -v`
Expected: all PASS.

- [ ] **Step 5: Renderer auto-registers as view-aware + discovery smoke**

Run: `.venv/bin/python -c "from glances.outputs.curses_renderer_v5 import _discover_plugin_renderer, _RENDERER_ACCEPTS_VIEW; fn = _discover_plugin_renderer('ports'); assert fn is not None; assert _RENDERER_ACCEPTS_VIEW['ports'] is True; print('discovered + view-aware OK')"`
Expected: prints `discovered + view-aware OK`.

- [ ] **Step 6: Lint + stage**

Run: `.venv/bin/python -m ruff check glances/plugins/ports/render_curses_v5.py tests/test_plugin_ports_render_curses_v5.py && .venv/bin/python -m ruff format glances/plugins/ports/render_curses_v5.py tests/test_plugin_ports_render_curses_v5.py`
Expected: `All checks passed!`
Then: `git add glances/plugins/ports/render_curses_v5.py tests/test_plugin_ports_render_curses_v5.py`

---

### Task 5: docs — `docs/aoa/ports.rst` v5 note

**Files:**
- Modify: `docs/aoa/ports.rst`

- [ ] **Step 1: Confirm the toctree already lists `ports`**

Run: `grep -n ports docs/aoa/index.rst`
Expected: a line containing `ports` — the page is already in the toctree, do **NOT** re-add it.

- [ ] **Step 2: Append the v5 note**

Append to the end of `docs/aoa/ports.rst` (after the last `web_3_description=Google Fr` line of the code block), matching the style of the note added to `docs/aoa/vms.rst` in G6A:

```rst

.. note::

    The ``ports`` plugin colours the status of each entry but **never raises an
    alert**: nothing is written to the event history and no action is
    dispatched. The colour rules differ by entry kind.

    For a host/port entry:

    * *careful* while the scan has not run yet (``Scanning``);
    * *critical* when the scan timed out or the port is closed (``Timeout``);
    * *warning* when the round-trip time exceeds ``port_x_rtt_warning``
      (configured in **milliseconds**).

    For a URL entry:

    * *careful* while the scan has not run yet (``Scanning``);
    * *critical* when the HTTP status code is not 200, 301 or 302, or when the
      request failed (``Error``);
    * *warning* when the response time exceeds ``web_x_rtt_warning``
      (configured in **milliseconds**).

    The whole list is swept by a single background scanner on the global
    ``[ports] refresh`` cadence; ``port_x_refresh`` is not a per-entry timer.

    ``web_x_http_proxy`` / ``web_x_https_proxy`` may embed credentials, so the
    proxy settings and ``web_x_ssl_verify`` are **not** exposed through the
    REST API nor through any export module.
```

- [ ] **Step 3: Check the RST renders + stage**

Run: `.venv/bin/python -m docutils --report=warning docs/aoa/ports.rst /dev/null 2>&1 | head -5`
Expected: no output (no RST syntax warning). If `docutils` is not installed, run `.venv/bin/python -c "print(open('docs/aoa/ports.rst').read()[-1200:])"` and eyeball the block indentation instead (every note line indented by 4 spaces).
Then: `git add docs/aoa/ports.rst`

---

## Final verification (whole plan)

- [ ] **All ports tests pass**

Run: `.venv/bin/python -m pytest tests/test_plugin_ports_v5.py tests/test_plugin_ports_render_curses_v5.py -v`
Expected: all PASS, 0 failed.

- [ ] **Full suite — no regression**

Run: `.venv/bin/python -m pytest -q`
Expected: same baseline as before the branch (only the pre-existing, unrelated `tests/test_actions_sanitize.py::TestSecurePopen::test_pipe` may fail in isolation — flag to the maintainer if seen; it references none of the G6B modules).

- [ ] **Frozen files really are frozen**

Run: `git status --porcelain glances/plugins/plugin/base_v5.py glances/ports_list.py glances/web_list.py glances/plugins/ports/__init__.py glances/scheduler_v5.py glances/outputs/curses_renderer_v5.py NEWS.rst`
Expected: **empty output**. Anything listed is a review failure.

- [ ] **Lint/format clean across all touched files**

Run: `.venv/bin/python -m ruff check glances/plugins/ports tests/test_plugin_ports_v5.py tests/test_plugin_ports_render_curses_v5.py && .venv/bin/python -m ruff format --check glances/plugins/ports tests/test_plugin_ports_v5.py tests/test_plugin_ports_render_curses_v5.py`
Expected: `All checks passed!` and `2 files already formatted` (or equivalent).

- [ ] **Everything staged, nothing committed**

Run: `git status --short`
Expected: `A  glances/plugins/ports/model_v5.py`, `A  glances/plugins/ports/render_curses_v5.py`, `A  tests/test_plugin_ports_v5.py`, `A  tests/test_plugin_ports_render_curses_v5.py`, `M  docs/aoa/ports.rst` — and **no new commit** (`git log -1 --oneline` unchanged from the start of the task).
