#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — one version source: every v5 surface reads `glances.version_v5`.

`glances/__init__.py` still serves v4 on `develop-v5` (`__apiversion__ = '4'`
mounts v4's `/api/4`), so v5 keeps its own pair until the merge, when it moves
into `glances/__init__.py` (architecture §10, Phase 4).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from glances import version_v5, zeroconf_v5
from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import build_parser
from glances.outputs import restful_doc_v5
from glances.plugins.version.model_v5 import PluginModel as VersionPlugin
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import UNAUTH_PATHS, build_app


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "etc" / "glances.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_the_v5_release_is_a_v5_release():
    assert version_v5.__version__.split(".")[0] == version_v5.__apiversion__ == "5"


def test_dash_v_prints_the_v5_release(capsys):
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--version"])
    assert capsys.readouterr().out.strip() == f"Glances {version_v5.__version__}"


def test_status_and_the_router_read_the_v5_pair(config):
    client = TestClient(build_app(config=config, store=StatsStoreV5()))
    assert client.get("/status").json() == {
        "status": "ok",
        "version": version_v5.__apiversion__,
        "glances_version": version_v5.__version__,
    }
    paths = client.get("/openapi.json").json()["paths"]
    assert f"/api/{version_v5.__apiversion__}/pluginslist" in paths
    assert f"/api/{version_v5.__apiversion__}/token" in UNAUTH_PATHS


def test_the_generated_doc_and_zeroconf_read_the_api_version():
    assert restful_doc_v5.API_URL.endswith(f"/api/{version_v5.__apiversion__}")
    assert version_v5.__apiversion__.encode() == zeroconf_v5.API_VERSION


async def test_the_version_plugin_reports_the_v5_release(config):
    store = StatsStoreV5()
    await VersionPlugin(store, config).update()
    assert store.get("version")["version"] == version_v5.__version__
