#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 joyhsia
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Docker collection filters must run before stats streams are started."""

from unittest.mock import MagicMock, patch

import pytest

from glances.plugins.containers import model as containers_model
from glances.plugins.containers.engines import docker as docker_engine
from tests.test_plugin_docker import FakeContainer, make_monitor


@pytest.fixture
def plugin_with(store_with, config_with, monkeypatch):
    for engine in ("docker", "podman", "lxd"):
        monkeypatch.setattr(containers_model, f"disable_plugin_{engine}", True)

    def factory(options):
        plugin = containers_model.PluginModel(store_with(), config_with({"containers": options}))
        monitor = make_monitor([FakeContainer("a"), FakeContainer("b"), FakeContainer("c")])
        plugin.monitors = [monitor]
        return plugin, monitor

    return factory


@pytest.mark.parametrize(
    ("patterns", "expected"),
    [
        ("name-b", {"a", "c"}),
        ("^NAME-[ab]$", {"c"}),
        (" ^name-a$ , ^name-c$ ", {"b"}),
    ],
)
def test_no_stats_does_not_create_fetchers(plugin_with, patterns, expected):
    plugin, monitor = plugin_with({"no_stats": patterns})
    with patch.object(docker_engine, "DockerStatsFetcher", side_effect=lambda _: MagicMock()) as fetcher:
        stats = plugin._update_monitors()
    assert {call.args[0].id for call in fetcher.call_args_list} == expected
    assert set(monitor.stats_fetchers) == expected
    assert {item["id"] for item in stats} == expected


@pytest.mark.parametrize("options", [{}, {"show": "name-a"}, {"hide": "name-b"}])
def test_display_filters_do_not_change_collection(plugin_with, options):
    plugin, monitor = plugin_with(options)
    with patch.object(docker_engine, "DockerStatsFetcher", side_effect=lambda _: MagicMock()):
        stats = plugin._update_monitors()
    assert set(monitor.stats_fetchers) == {"a", "b", "c"}
    assert {item["id"] for item in stats} == {"a", "b", "c"}


def test_no_stats_stops_existing_fetchers_and_can_be_removed(plugin_with, config_with):
    plugin, monitor = plugin_with({})
    with patch.object(docker_engine, "DockerStatsFetcher", side_effect=lambda _: MagicMock()) as fetcher:
        plugin._update_monitors()
        original = dict(monitor.stats_fetchers)

        plugin.config = config_with({"containers": {"no_stats": "^name-b$"}})
        stats = plugin._update_monitors()
        assert {item["id"] for item in stats} == {"a", "c"}
        original["b"].stop.assert_called_once_with()
        original["a"].stop.assert_not_called()
        assert "b" not in monitor.image_cache
        assert monitor.stats_fetchers["a"] is original["a"]

        plugin.config = config_with({"containers": {}})
        stats = plugin._update_monitors()
        assert {item["id"] for item in stats} == {"a", "b", "c"}
        assert monitor.stats_fetchers["b"] is not original["b"]
        assert fetcher.call_count == 4


def test_invalid_no_stats_regex_is_ignored(plugin_with, caplog):
    plugin, monitor = plugin_with({"no_stats": "["})
    with patch.object(docker_engine, "DockerStatsFetcher", side_effect=lambda _: MagicMock()):
        stats = plugin._update_monitors()
    assert {item["id"] for item in stats} == {"a", "b", "c"}
    assert set(monitor.stats_fetchers) == {"a", "b", "c"}
    assert "no_stats" in caplog.text


def test_no_stats_does_not_change_other_engines(plugin_with):
    plugin, _ = plugin_with({"no_stats": ".*"})
    monitor = MagicMock()
    monitor.update.return_value = ({}, [{"name": "name-a", "id": "a", "engine": "podman"}])
    plugin.monitors = [monitor]
    assert [item["id"] for item in plugin._update_monitors()] == ["a"]
    monitor.update.assert_called_once_with(all_tag=False)
