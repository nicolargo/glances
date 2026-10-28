#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances — one version source: every surface reads `glances.__version__` / `__apiversion__`."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import glances as version
from glances import zeroconf
from glances.config import GlancesConfig
from glances.main import build_parser
from glances.outputs import restful_doc
from glances.plugins.version.model import PluginModel as VersionPlugin
from glances.stats_store import StatsStore
from glances.webserver import UNAUTH_PATHS, build_app


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfig:
    monkeypatch.setattr(GlancesConfig, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfig()


def test_the_release_is_a_5_x_release():
    assert version.__version__.split(".")[0] == version.__apiversion__ == "5"


def test_dash_v_prints_the_release(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert capsys.readouterr().out.strip() == f"Glances {version.__version__}"


def test_status_and_the_router_read_the_version_pair(config):
    client = TestClient(build_app(config=config, store=StatsStore()))
    assert client.get("/status").json() == {
        "status": "ok",
        "version": version.__apiversion__,
        "glances_version": version.__version__,
        "history": False,
    }
    paths = client.get("/openapi.json").json()["paths"]
    assert f"/api/{version.__apiversion__}/pluginslist" in paths
    assert f"/api/{version.__apiversion__}/token" in UNAUTH_PATHS


def test_the_generated_doc_and_zeroconf_read_the_api_version():
    assert restful_doc.API_URL.endswith(f"/api/{version.__apiversion__}")
    assert version.__apiversion__.encode() == zeroconf.API_VERSION


async def test_the_version_plugin_reports_the_release(config):
    store = StatsStore()
    await VersionPlugin(store, config).update()
    assert store.get("version")["version"] == version.__version__
