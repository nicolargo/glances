#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the Python API (design 2026-09-26, commit 1).

Real plugins throughout, restricted with `plugins=` so each test builds only
what it reads. Section numbers refer to
docs/superpowers/specs/2026-09-26-glances-v5-python-api-design.md.
"""

from __future__ import annotations

import asyncio
import gc
import os
import sys
import threading
import time
from collections.abc import Mapping

import pytest

from glances import api_v5 as api
from glances.config_v5 import GlancesConfigV5
from glances.globals import auto_unit
from glances.outputs.glances_bars import Bar


@pytest.fixture(autouse=True)
def _hermetic_config(tmp_path, monkeypatch):
    """No system or user glances.conf: only what a test writes."""
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    for key in list(os.environ):
        if key.startswith("GLANCES_"):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def conf(tmp_path):
    def write(body: str) -> str:
        path = tmp_path / "extra.conf"
        path.write_text(body)
        return str(path)

    return write


def _api_threads() -> list[threading.Thread]:
    return [t for t in threading.enumerate() if t.name == "glances-api-v5"]


def _count_updates(gl, name):
    """Wrap one plugin's update() with a counter (and an order log)."""
    plugin = gl._plugins[name]
    original = plugin.update
    calls = {"n": 0}

    async def counted():
        calls["n"] += 1
        gl._order.append(name)
        await original()

    plugin.update = counted
    return calls


# ------------------------------------------------------------- §5.1 the loop


def test_works_inside_a_running_event_loop():
    """The Jupyter case: `asyncio.run` would refuse to start here."""

    async def notebook_cell():
        with api.GlancesAPI(plugins=["mem"]) as gl:
            return gl.mem["percent"]

    assert isinstance(asyncio.run(notebook_cell()), float)


def test_close_joins_the_thread_and_stops_the_plugins(monkeypatch):
    gl = api.GlancesAPI(plugins=["mem"])
    stopped = []
    monkeypatch.setattr(gl._plugins["mem"], "stop", lambda: stopped.append("mem"))
    assert _api_threads()
    gl.close()
    assert stopped == ["mem"]
    assert not _api_threads()
    gl.close()  # idempotent


def test_a_forgotten_api_is_closed_by_its_finaliser():
    gl = api.GlancesAPI(plugins=["mem"])
    assert _api_threads()
    del gl
    gc.collect()
    assert not _api_threads()


# ------------------------------------------------------- §5.2 on demand


@pytest.fixture
def gl():
    with api.GlancesAPI(plugins=["cpu", "mem", "processlist"]) as instance:
        instance._order = []
        yield instance


def test_reads_within_the_ttl_update_once(gl):
    calls = _count_updates(gl, "cpu")
    gl._ttl = 3600
    gl.cpu, gl.cpu, gl.cpu
    assert calls["n"] == 1, "the first read updates (priming does not count), the others are cached"


def test_a_read_after_the_ttl_updates_again(gl):
    calls = _count_updates(gl, "cpu")
    gl._ttl = 0
    gl.cpu, gl.cpu
    assert calls["n"] == 2


def test_the_ttl_is_per_plugin(gl):
    """v4's maxsize=1 cache let alternating reads evict each other (defect 3)."""
    cpu, mem = _count_updates(gl, "cpu"), _count_updates(gl, "mem")
    gl._ttl = 3600
    for _ in range(3):
        gl.cpu, gl.mem
    assert (cpu["n"], mem["n"]) == (1, 1)


def test_the_ttl_is_read_from_global_refresh(conf):
    with api.GlancesAPI(config_path=conf("[global]\nrefresh=7\n"), plugins=["mem"]) as gl:
        assert gl._ttl == 7.0


def test_processlist_updates_processcount_first(gl):
    _count_updates(gl, "processcount")
    _count_updates(gl, "processlist")
    gl._ttl = 0
    gl.processlist
    assert gl._order == ["processcount", "processlist"]


def test_two_threads_reading_at_once_update_once(gl):
    calls = _count_updates(gl, "cpu")
    gl._ttl = 3600
    barrier = threading.Barrier(2)

    def read():
        barrier.wait()
        gl.cpu

    threads = [threading.Thread(target=read) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert calls["n"] == 1


def test_the_first_read_has_rates():
    """Priming leaves the first read to take the second sample a rate needs."""
    with api.GlancesAPI(plugins=["network"]) as gl:
        time.sleep(0.05)
        assert any(item["bytes_recv"] is not None for item in gl.network.values())


# ------------------------------------------------------- §5.3 background


def test_background_refreshes_without_reads(conf):
    with api.GlancesAPI(config_path=conf("[global]\nrefresh=1\n"), background=True, plugins=["cpu"]) as gl:
        before = len(gl.cpu.history()["timestamps"])
        time.sleep(2.5)
        assert len(gl.cpu.history()["timestamps"]) >= before + 2


def test_background_reads_do_not_update(conf):
    with api.GlancesAPI(config_path=conf("[global]\nrefresh=60\n"), background=True, plugins=["cpu"]) as gl:
        gl._order = []
        calls = _count_updates(gl, "cpu")
        gl.cpu, gl.cpu
        assert calls["n"] == 0


def test_no_alert_action_and_no_exporter_ever(conf):
    """An API object records alerts but never acts on the host (§5.3)."""
    body = "[mem]\ncritical=0\ncritical_action=touch /tmp/should-never-exist\n[export]\ncsv=true\n"
    with api.GlancesAPI(config_path=conf(body), background=True, plugins=["mem"]) as gl:
        assert gl._alerts.actions == {}
        assert gl._scheduler._exporters == []


def test_alerts_are_recorded_and_returned(conf):
    with api.GlancesAPI(
        config_path=conf("[alerts]\nwarmup_cycles=0\nmin_duration_seconds=0\n[mem]\ncritical=0.1\n"), plugins=["mem"]
    ) as gl:
        gl._ttl = 0
        gl.mem, gl.mem
        events = gl.alerts()
    assert any(e.get("plugin") == "mem" for e in events), events


# ------------------------------------------------------- §5.4 PluginView


def test_a_view_is_a_read_only_mapping_snapshot(gl):
    view = gl.mem
    assert isinstance(view, Mapping)
    assert isinstance(view.keys(), list), "v4 returns a list"
    view.raw["percent"] = -1
    assert gl.mem["percent"] != -1


def test_a_scalar_view_is_keyed_by_field(gl):
    view = gl.mem
    assert "percent" in view and view.get("nope", 0) == 0
    assert not any(key.startswith("_") for key in view)


def test_a_collection_view_is_keyed_by_primary_key(gl):
    view = gl.processlist
    pid = os.getpid()
    assert pid in view
    assert view[pid]["pid"] == pid


def test_a_view_matches_what_rest_serves(gl):
    view = gl.mem
    plugin = gl._plugins["mem"]
    payload = plugin.get_api_payload()
    assert view.levels == payload["_levels"]
    assert view.limits == plugin.get_limits()
    assert view.fields == plugin.fields_description
    assert view.raw == {k: v for k, v in payload.items() if not k.startswith("_")}


def test_processlist_is_not_narrowed_by_the_export_filter(gl):
    """`get_export()` keeps only `[processlist] export` matches: none by default."""
    assert len(gl.processlist) > 1


def test_view_history_is_the_rest_history(gl):
    gl._ttl = 0
    gl.mem, gl.mem
    assert gl.mem.history(nb=1) == gl._plugins["mem"].get_history(nb=1)
    assert len(gl.mem.history()["series"]["percent"]) >= 2


# ----------------------------------------------------- §5.5 construction


def test_sys_argv_is_never_read(monkeypatch):
    """v4 parsed the caller's command line (defect 2)."""
    monkeypatch.setattr(sys, "argv", ["myscript.py", "--definitely-not-a-glances-flag"])
    with api.GlancesAPI(plugins=["mem"]) as gl:
        assert gl.plugins() == ["mem"]


def test_config_path_layers_over_the_defaults(conf):
    with api.GlancesAPI(config_path=conf("[mem]\ncareful=11\nwarning=22\ncritical=33\n"), plugins=["mem"]) as gl:
        assert gl.mem.limits["percent"] == {"careful": 11.0, "warning": 22.0, "critical": 33.0}


def test_plugins_builds_only_those_and_their_dependencies():
    with api.GlancesAPI(plugins=["processlist"]) as gl:
        assert gl.plugins() == ["processcount", "processlist"]
        with pytest.raises(AttributeError):
            gl.cpu


def test_an_unknown_plugin_is_rejected():
    with pytest.raises(ValueError, match="nope"):
        api.GlancesAPI(plugins=["nope"])
    with api.GlancesAPI(plugins=["mem"]) as gl, pytest.raises(AttributeError):
        gl.nope


def test_a_disabled_plugin_names_its_config_key(conf):
    with api.GlancesAPI(config_path=conf("[mem]\ndisable=True\n"), plugins=["mem", "cpu"]) as gl:
        assert gl.plugins() == ["cpu"]
        with pytest.raises(AttributeError, match=r"\[mem\] disable"):
            gl.mem


def test_the_depends_on_declarations():
    from glances.plugins.processlist.model_v5 import PluginModel as ProcessList
    from glances.plugins.programlist.model_v5 import PluginModel as ProgramList

    assert ProcessList.DEPENDS_ON == ("processcount",)
    assert ProgramList.DEPENDS_ON == ("processcount",)


# ---------------------------------------------------------- §5.6 helpers


def test_version_is_the_major():
    with api.GlancesAPI(plugins=["mem"]) as gl:
        assert gl.__version__ == "5"


@pytest.mark.parametrize("number", [0, 1023, 6514897816, 3.5, None])
def test_auto_unit_is_v4s(number):
    with api.GlancesAPI(plugins=["mem"]) as gl:
        assert gl.auto_unit(number) == auto_unit(number)


@pytest.mark.parametrize("value", [0, 7.7, 50, 100])
def test_bar_is_v4s(value):
    expected = Bar(18, bar_char="■", empty_char="□", display_value=False)
    expected.percent = value
    with api.GlancesAPI(plugins=["mem"]) as gl:
        assert gl.bar(value) == expected.get()


def test_top_process_leaves_out_this_process_and_kernel_threads(gl):
    top = gl.top_process(limit=1000)
    assert os.getpid() not in [p["pid"] for p in top]
    assert all(p["cmdline"] for p in top)
    cpu = [p["cpu_percent"] for p in top]
    assert cpu == sorted(cpu, reverse=True)


# ------------------------------------------------------------- §5.7 docs


@pytest.fixture(scope="module")
def rst():
    from glances.api_v5_doc import render

    with api.GlancesAPI(plugins=["cpu", "mem", "network", "fs", "load", "processlist"]) as gl:
        return render(gl), gl.plugins()


def test_the_generated_page_parses_without_a_docutils_warning(rst):
    import io

    import docutils.core

    warnings = io.StringIO()
    docutils.core.publish_doctree(rst[0], settings_overrides={"report_level": 2, "warning_stream": warnings})
    assert warnings.getvalue() == ""


def test_the_generated_page_has_one_section_per_plugin(rst):
    page, plugins = rst
    for name in plugins:
        assert f"\nGlances {name}\n" in page, name


def test_the_generated_page_documents_every_public_method(rst):
    page = rst[0]
    for name in ("plugins", "alerts", "auto_unit", "bar", "top_process", "close"):
        assert f"GlancesAPI.{name}(" in page, name
    assert "PluginView.history(" in page


def test_free_text_is_escaped():
    from glances.api_v5_doc import _escape

    assert _escape("a *b* `c` d_ e|f") == r"a \*b\* \`c\` d\_ e\|f"


def test_the_notebook_runs(monkeypatch):
    """glances.ipynb is the API's most visible user: keep it runnable."""
    import json
    from pathlib import Path

    monkeypatch.setattr(time, "sleep", lambda _s: None)
    notebook = json.loads((Path(__file__).resolve().parent.parent / "glances.ipynb").read_text())
    namespace: dict = {}
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            exec(compile("".join(cell["source"]), "glances.ipynb", "exec"), namespace)  # noqa: S102
    assert not _api_threads(), "the notebook closes what it opens"


# ------------------------------------------------ refresh= (§10, decided)


def test_refresh_sets_the_on_demand_ttl(conf):
    with api.GlancesAPI(config_path=conf("[global]\nrefresh=7\n"), refresh=0.5, plugins=["mem"]) as gl:
        assert gl._ttl == 0.5, "the argument wins over glances.conf, as -t does"


def test_refresh_sets_the_background_cadence():
    with api.GlancesAPI(background=True, refresh=0.5, plugins=["cpu"]) as gl:
        before = len(gl.cpu.history()["timestamps"])
        time.sleep(1.8)
        assert len(gl.cpu.history()["timestamps"]) >= before + 3


@pytest.mark.parametrize("refresh", [0, -1])
def test_refresh_must_be_positive(refresh):
    with pytest.raises(ValueError, match="refresh"):
        api.GlancesAPI(refresh=refresh, plugins=["mem"])


def test_a_view_has_no_get_raw():
    """No v4 alias (maintainer, 2026-09-26): `.raw` replaces `get_raw()`."""
    with api.GlancesAPI(plugins=["mem"]) as gl:
        assert not hasattr(gl.mem, "get_raw")
        assert gl.mem.raw["percent"] == gl.mem["percent"]
