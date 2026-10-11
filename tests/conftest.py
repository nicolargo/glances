#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite fixtures.

This module provides pytest fixtures for testing Glances plugins and components.
"""

import logging
from pathlib import Path

import pytest

from glances.config import GlancesConfig
from glances.stats_store import StatsStore


@pytest.fixture(autouse=True)
def _isolate_user_config(tmp_path: Path, monkeypatch):
    """Never load the developer's ~/.config/glances/glances.conf.

    Both config loaders search the user config first ($XDG_CONFIG_HOME, else
    ~/.config), so a local conf silently overrides test defaults. Point
    XDG_CONFIG_HOME at an empty directory; tests that need a user conf set
    their own value, which wins over this one.
    """
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "isolated-xdg"))


@pytest.fixture(autouse=True)
def _testclient_on_localhost(monkeypatch):
    """Send TestClient requests as `Host: localhost`, not `testserver`.

    A v5 server bound to loopback (the default) answers a loopback `Host`
    only (DNS rebinding, `webserver._wire_trusted_hosts`). A test that
    passes its own `base_url` or `Host` header still wins.
    """
    try:
        from starlette.testclient import TestClient
    except ImportError:
        return
    init = TestClient.__init__

    def init_on_localhost(self, app, base_url="http://localhost", *args, **kwargs):
        init(self, app, base_url, *args, **kwargs)

    monkeypatch.setattr(TestClient, "__init__", init_on_localhost)


@pytest.fixture(scope="session")
def logger():
    return logging.getLogger(__name__)


@pytest.fixture
def store_with():
    """Factory fixture — returns a callable producing a fresh StatsStore.

    Shared across v5 plugin model tests (see
    tests/test_plugin_base_stop_and_threshold_field.py, the origin of
    this fixture).
    """

    def _factory() -> StatsStore:
        return StatsStore()

    return _factory


@pytest.fixture
def config_with(tmp_path: Path, monkeypatch):
    """Factory fixture — returns a callable that builds a real GlancesConfig
    from a ``{section: {key: value}}`` dict, backed by a temp glances.conf.
    """
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    xdg = tmp_path / "xdg"
    cfg_dir = xdg / "glances"
    cfg_dir.mkdir(parents=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))

    def _factory(sections: dict[str, dict[str, str]]) -> GlancesConfig:
        body = ""
        for section, options in sections.items():
            body += f"[{section}]\n"
            for key, value in options.items():
                body += f"{key}={value}\n"
        (cfg_dir / "glances.conf").write_text(body)
        return GlancesConfig()

    return _factory
