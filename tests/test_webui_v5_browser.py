#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the Web UI browser page, /browser (P3-6)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import build_app
from tests.test_webserver_v5 import config_factory  # noqa: F401 -- fixture

_STATIC = Path(__file__).parent.parent / "glances" / "outputs" / "static"
_BUNDLE = _STATIC / "public" / "browser5.js"
_PROBE = Path(__file__).parent / "fixtures" / "webui_render_probe.js"


def _app(config, browser: bool):
    return build_app(config=config, store=StatsStoreV5(), args=argparse.Namespace(disable_webui=False, browser=browser))


def test_browser_page_is_served_with_server_browser_only(config_factory):  # noqa: F811
    with TestClient(_app(config_factory(), browser=True)) as client:
        response = client.get("/browser")
    assert response.status_code == 200
    assert "static/browser5.js" in response.text

    app = _app(config_factory(), browser=False)
    assert "/browser" not in {getattr(route, "path", None) for route in app.routes}


def test_browser_page_has_the_main_pages_security_policy():
    """Same CSP as index_v5.html: one self-hosted bundle, nothing from another origin."""

    def csp(name: str) -> str:
        text = (_STATIC / "templates" / name).read_text(encoding="utf-8")
        return re.search(r'http-equiv="Content-Security-Policy"\s+content="([^"]+)"', text).group(1)

    assert csp("browser_v5.html") == csp("index_v5.html")


def test_mcp_cannot_shadow_the_browser_page(config_factory):  # noqa: F811
    from glances.webserver_v5 import resolve_mcp_path

    assert resolve_mcp_path(config_factory(mcp_path="/browser")) == "/mcp"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_the_browser_bundle_renders_the_list():
    """The built bundle against a fake DOM: rows, TUI colours, and links to each server's Web UI."""
    if not _BUNDLE.exists():
        pytest.fail(f"{_BUNDLE} is missing -- run `npm run build` in glances/outputs/static/")
    result = subprocess.run(["node", str(_PROBE), str(_BUNDLE)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and result.stderr == "", result.stderr
    page = json.loads(result.stdout)
    assert page["tagName"] == "MAIN"
    assert page["browserText"].startswith("3 Glances servers available")
    rows = page["browserRows"]
    assert [[c["text"] for c in row["cells"]] for row in rows] == [
        ["nas", "ONLINE", "91.3", "40"],
        ["beta", "OFFLINE", "?", "?"],
        ["evil", "PROTECTED", "?", "?"],
    ]
    assert [c["className"] for c in rows[0]["cells"][1:]] == ["gl-level-ok", "gl-level-critical", "gl-level-ok"]
    assert rows[1]["cells"][1]["className"] == "gl-level-critical"
    assert rows[2]["cells"][1]["className"] == "gl-level-warning"
    assert [row["href"] for row in rows] == ["http://10.0.0.1:61208/", "http://beta:61237/", None], (
        "a name that is not a host or an http(s) URL never becomes a link"
    )
