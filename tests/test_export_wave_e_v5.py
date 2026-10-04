#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — wave E exporters (P3-3): restful and graph."""

from __future__ import annotations

import asyncio
import importlib.util
import os
import stat

import pytest
import requests

from glances.history_v5 import HistoryStoreV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.stats_store_v5 import StatsStoreV5
from tests.export_fakes_v5 import make_config, missing_module, plugins

# ---------------------------------------------------------------- restful

_RESTFUL = {"restful": {"host": "sink", "port": "6789", "protocol": "http", "path": "/in"}}


class _Response:
    def __init__(self, status=200):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_restful_posts_one_body_per_cycle(monkeypatch):
    from glances.exports.glances_restful import export_v5

    posts = []
    monkeypatch.setattr(export_v5.requests, "post", lambda url, **kw: posts.append((url, kw)) or _Response())
    config = make_config(_RESTFUL)
    exporter = export_v5.Export(config)
    built = plugins(config)
    exporter.update(built)
    exporter.update(built)
    assert len(posts) == 2, "one POST per cycle, the current one (v4 sent the previous cycle)"
    url, kwargs = posts[0]
    assert url == "http://sink:6789/in"
    assert kwargs["timeout"] == 15 and kwargs["allow_redirects"] is True
    body = kwargs["json"]
    assert set(body) == {"fakescalar", "fakecollection"}
    assert body["fakescalar"]["total"] == 12.5
    assert body["fakecollection"]["eth0.rx"] == 10


def test_restful_warns_on_a_refused_post(monkeypatch, caplog):
    from glances.exports.glances_restful import export_v5

    monkeypatch.setattr(export_v5.requests, "post", lambda url, **kw: _Response(500))
    config = make_config(_RESTFUL)
    export_v5.Export(config).update(plugins(config))
    assert "Cannot export stats to the RESTful endpoint http://sink:6789/in" in caplog.text


@pytest.mark.parametrize("missing", ["host", "port", "protocol", "path"])
def test_restful_keys_are_mandatory(missing):
    from glances.exports.glances_restful.export_v5 import Export

    section = {"restful": {k: v for k, v in _RESTFUL["restful"].items() if k != missing}}
    with pytest.raises(SystemExit):
        Export(make_config(section))


# ------------------------------------------------------------------ graph

requires_pygal = pytest.mark.skipif(importlib.util.find_spec("pygal") is None, reason="pygal not installed")


class _HistoryScalar(GlancesPluginBase[dict]):
    plugin_name = "histscalar"
    fields_description = {"total": {"description": "t", "unit": "percent", "history": True}}

    async def _grab_stats(self) -> dict:
        return {"total": 42.0}


class _HistoryCollection(GlancesPluginBase[list]):
    plugin_name = "histcoll"
    IS_COLLECTION = True
    fields_description = {
        "name": {"description": "n", "unit": "string", "primary_key": True},
        "rx": {"description": "r", "unit": "bytes", "history": True},
    }

    async def _grab_stats(self) -> list:
        return [{"name": "eth0", "rx": 10}, {"name": "wlan0", "rx": 20}]


def _history_plugins(config, cycles=3):
    store, history = StatsStoreV5(), HistoryStoreV5(size=100)
    built = [_HistoryScalar(store, config), _HistoryCollection(store, config)]
    for plugin in built:
        plugin.history = history
        for _ in range(cycles):
            asyncio.run(plugin.update())
    return built


def _graph(tmp_path, **section):
    from glances.exports.glances_graph.export_v5 import Export

    return Export(make_config({"graph": {"path": str(tmp_path), **section}}))


@requires_pygal
def test_graph_draws_one_svg_per_plugin_from_the_history(tmp_path):
    exporter = _graph(tmp_path)
    config = make_config({})
    built = _history_plugins(config)
    exporter.update(built)
    assert not list(tmp_path.glob("*.svg")), "nothing asked, generate_every=0: nothing drawn"
    assert str(tmp_path) in exporter.request()
    exporter.update(built)
    assert sorted(p.name for p in tmp_path.glob("*.svg")) == ["histcoll.svg", "histscalar.svg"]
    svg = (tmp_path / "histcoll.svg").read_text()
    assert "eth0.rx" in svg and "wlan0.rx" in svg, "a collection's series are <item>.<field>"
    assert "Histscalar" in (tmp_path / "histscalar.svg").read_text()


@requires_pygal
def test_graph_replaces_a_planted_symlink_instead_of_following_it(tmp_path):
    """Audit M7: a link at `<path>/<plugin>.svg` must not make Glances (often root) overwrite its target."""
    victim = tmp_path / "victim"
    victim.write_text("precious")
    out = tmp_path / "graphs"
    out.mkdir()
    (out / "histscalar.svg").symlink_to(victim)
    exporter = _graph(out)
    exporter.request()
    exporter.update(_history_plugins(make_config({})))
    assert victim.read_text() == "precious"
    assert not (out / "histscalar.svg").is_symlink()
    assert "Histscalar" in (out / "histscalar.svg").read_text()
    assert not list(out.glob(".*.tmp")), "no temporary file left behind"


@requires_pygal
def test_graph_files_get_the_mode_a_plain_open_would_give(tmp_path):
    exporter = _graph(tmp_path)
    exporter.request()
    exporter.update(_history_plugins(make_config({})))
    umask = os.umask(0)
    os.umask(umask)
    assert stat.S_IMODE((tmp_path / "histscalar.svg").stat().st_mode) == 0o666 & ~umask


@requires_pygal
def test_graph_default_folder_is_the_users_own(tmp_path, monkeypatch):
    """Not the shared temporary folder: `$XDG_DATA_HOME/glances/graphs`, private."""
    from glances.exports.glances_graph.export_v5 import Export

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    exporter = Export(make_config({}))
    assert exporter.path == str(tmp_path / "data" / "glances" / "graphs")
    assert stat.S_IMODE(os.stat(exporter.path).st_mode) == 0o700


@requires_pygal
def test_graph_warns_about_a_folder_others_can_write(tmp_path, caplog):
    tmp_path.chmod(0o777)
    with caplog.at_level("WARNING"):
        _graph(tmp_path)
    assert any("writable by other users" in r.getMessage() for r in caplog.records)


@requires_pygal
def test_graph_series_come_from_the_history_store(tmp_path):
    exporter = _graph(tmp_path)
    scalar, collection = _history_plugins(make_config({}), cycles=4)
    assert [v for _, v in exporter.series(scalar)["total"]] == [42.0] * 4
    assert set(exporter.series(collection)) == {"eth0.rx", "wlan0.rx"}


@requires_pygal
def test_graph_generate_every_draws_without_a_request(tmp_path, monkeypatch):
    from glances.exports.glances_graph import export_v5

    exporter = _graph(tmp_path, generate_every="60")
    built = _history_plugins(make_config({}))
    exporter.update(built)
    assert not list(tmp_path.glob("*.svg"))
    monkeypatch.setattr(export_v5.time, "monotonic", lambda: exporter._last_generation + 61)
    exporter.update(built)
    assert len(list(tmp_path.glob("*.svg"))) == 2


@requires_pygal
def test_graph_path_from_the_command_line_wins(tmp_path):
    import argparse

    from glances.exports.glances_graph.export_v5 import Export

    cli = tmp_path / "cli"
    exporter = Export(
        make_config({"graph": {"path": str(tmp_path / "conf")}}), argparse.Namespace(export_graph_path=str(cli))
    )
    assert exporter.path == str(cli) and cli.is_dir()


@requires_pygal
def test_graph_style_is_a_pygal_style_or_the_default(tmp_path):
    exporter = _graph(tmp_path, style="__class__")
    exporter.request()
    exporter.update(_history_plugins(make_config({})))
    assert (tmp_path / "histscalar.svg").exists(), "an unknown style name falls back to DarkStyle"


def test_graph_without_pygal_is_fatal_and_says_so(monkeypatch, caplog, tmp_path):
    missing_module(monkeypatch, "pygal")
    missing_module(monkeypatch, "pygal.style")
    from glances.exports.glances_graph.export_v5 import Export

    with pytest.raises(SystemExit):
        Export(make_config({"graph": {"path": str(tmp_path)}}))
    assert "pygal" in caplog.text


# ------------------------------------------------------------- TUI key g


def _tui(generate_graph=None):
    from unittest.mock import MagicMock

    from glances.outputs.glances_curses_v5 import TuiV5

    config = MagicMock()
    config.get.side_effect = lambda section, key, default=None: default
    return TuiV5(
        store=StatsStoreV5(),
        alerts=None,
        config=config,
        registry=[],
        fields_by_plugin={},
        generate_graph=generate_graph,
    )


def test_the_g_key_asks_the_graph_exporter(monkeypatch):
    asked = []
    tui = _tui(generate_graph=lambda: asked.append(1) or "Graphs will be written to /tmp/g")
    popups = []
    monkeypatch.setattr(tui, "_popup_info", lambda stdscr, message: popups.append(message))
    assert tui._handle_key(ord("g")) == "modal"
    tui._run_pending(None)
    assert asked == [1] and popups == ["Graphs will be written to /tmp/g"]


def test_the_g_key_says_when_the_graph_export_is_off(monkeypatch):
    tui = _tui()
    popups = []
    monkeypatch.setattr(tui, "_popup_info", lambda stdscr, message: popups.append(message))
    tui._handle_key(ord("g"))
    tui._run_pending(None)
    assert "--export graph" in popups[0]
