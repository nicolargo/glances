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

import threading
import time

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
    # Published on the fast global cadence; `[ports] refresh` throttles only
    # the background scan (Bug 2 fix).
    assert p.SCHEDULE_AT_GLOBAL_REFRESH is True


def test_scan_interval_reads_ports_refresh(store_with, config_with):
    p = _mk(store_with, config_with)  # _FULL_SECTION has refresh=60
    assert p._scan_interval == 60.0


def test_scan_interval_defaults_to_config_default_when_user_omits_it(store_with, config_with):
    # No user [ports] refresh → config DEFAULTS supply 30 (shipped conf value).
    p = PluginModel(store_with(), config_with({"ports": {"port_1_host": "h", "port_1_port": "80"}}))
    assert p._scan_interval == 30.0


def test_fields_present(store_with, config_with):
    p = _mk(store_with, config_with)
    fd = p.fields_description
    for key in (
        "indice",
        "description",
        "host",
        "port",
        "url",
        "status",
        "elapsed",
        "rtt_warning",
        "timeout",
        "refresh",
    ):
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
    # `port_1_port` is read via `config.get_value(section, key, 0)` (a
    # non-None int default): GlancesConfigV5.get_value's documented contract
    # (already landed, not owned by this plugin) delegates non-None defaults
    # to `get()` for type coercion, so the raw "80" becomes int 80 here -
    # consistent with `fields_description["port"]["unit"] == "number"`.
    assert p._scan_list[0]["port"] == 80
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


class _FakeScanner:
    """Stand-in for ThreadScanner: records construction and start/stop, and
    stays 'alive' until released — no socket, no subprocess, no sleep(1)."""

    instances: list[_FakeScanner] = []

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


async def test_grab_relaunches_once_the_scanner_is_dead_and_the_timer_fired(store_with, config_with, monkeypatch):
    from glances.timer import Timer

    scanner = _patch_scanner(monkeypatch)
    p = _mk(store_with, config_with)
    await p._grab_stats()
    scanner.instances[0].finish()  # scan complete
    # The scan is throttled to `[ports] refresh`: force the interval elapsed.
    p._scan_timer = Timer(-1)
    await p._grab_stats()
    assert len(scanner.instances) == 2
    assert scanner.instances[1].started is True


async def test_grab_does_not_relaunch_a_dead_scanner_before_the_timer_fires(store_with, config_with, monkeypatch):
    """Bug 2 core: the heavy scan is throttled to `[ports] refresh`. A dead
    scanner is NOT immediately relaunched — otherwise a plugin published on the
    fast global cadence would re-scan (ping / TCP / HTTP HEAD) every couple of
    seconds. Publication still happens every call; only the scan is throttled.
    """
    scanner = _patch_scanner(monkeypatch)
    # refresh=60 → the scan timer stays unfired across these rapid calls.
    p = _mk(store_with, config_with)
    out = await p._grab_stats()  # first sweep launches unconditionally
    assert len(scanner.instances) == 1
    scanner.instances[0].finish()
    # Several fast publication cycles while the timer is still counting down.
    for _ in range(3):
        out = await p._grab_stats()
    assert len(scanner.instances) == 1  # dead, but timer not fired → no re-scan
    # ...yet the snapshot is still published every cycle (v4 live-list parity).
    assert [i["indice"] for i in out] == ["port_1", "port_2", "web_1"]


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


def test_port_level_rtt_below_threshold_is_ok(store_with, config_with):
    # A reachable port within its RTT threshold is `ok` → painted GREEN, like
    # v4's `'OK'` return value (COLOR_GREEN). NOT `None`/no-entry.
    item = {"indice": "port_1", "host": "h", "port": 80, "status": 0.2, "rtt_warning": 1.0}
    assert _levels_for(store_with, config_with, [item])["port_1"]["status"]["level"] == "ok"


def test_port_level_without_rtt_warning_is_ok(store_with, config_with):
    item = {"indice": "port_2", "host": "h", "port": 80, "status": 9.9, "rtt_warning": None}
    assert _levels_for(store_with, config_with, [item])["port_2"]["status"]["level"] == "ok"


def test_port_level_open_status_is_ok(store_with, config_with):
    # ICMP success stores `True` (see `set_status_if_host` → "Open"): reachable,
    # so `ok` (green), never critical (`True == 0` is False).
    item = {"indice": "port_0", "host": "h", "port": 0, "status": True, "rtt_warning": None}
    assert _levels_for(store_with, config_with, [item])["port_0"]["status"]["level"] == "ok"


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


def test_web_level_critical_outranks_warning(store_with, config_with):
    # #3632: several conditions can match at once and the MOST SEVERE has to win.
    # A 500 that is ALSO slower than rtt_warning is critical — v4's
    # `get_default_ret_value` used to keep the last truthy condition and
    # downgraded it to warning.
    item = {"indice": "web_1", "url": "http://x", "status": 500, "elapsed": 4.0, "rtt_warning": 3.0}
    assert _levels_for(store_with, config_with, [item])["web_1"]["status"]["level"] == "critical"


def test_web_level_ok_codes_are_ok(store_with, config_with):
    # 200/301/302 within the response threshold → `ok` (green), like v4's `'OK'`.
    items = [
        {"indice": "web_1", "url": "http://x", "status": 200, "elapsed": 0.1, "rtt_warning": 3.0},
        {"indice": "web_2", "url": "http://y", "status": 301, "elapsed": 0.1, "rtt_warning": None},
        {"indice": "web_3", "url": "http://z", "status": 302, "elapsed": 0.1, "rtt_warning": None},
    ]
    levels = _levels_for(store_with, config_with, items)
    assert levels["web_1"]["status"]["level"] == "ok"
    assert levels["web_2"]["status"]["level"] == "ok"
    assert levels["web_3"]["status"]["level"] == "ok"


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
