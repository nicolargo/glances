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


@pytest.fixture
def redirecting_server():
    """Two real HTTP servers on 127.0.0.1 (GHSA-jrpw-qg6j-vqv3).

    `internal` stands for a service the attacker cannot reach: it answers
    JSON to anything and records each path it serves. `attacker` answers
    `/status` itself, as a Glances v5 server does, and redirects every other
    request to `internal`: 302 for a GET, 307 for a POST.
    Yields `(attacker_port, internal_hits)`.
    """
    import http.server
    import json
    import threading

    hits: list[str] = []

    class Internal(http.server.BaseHTTPRequestHandler):
        def _answer(self) -> None:
            hits.append(self.path)
            body = json.dumps({"total": "INTERNAL-ONLY", "access_token": "tok"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_GET = do_POST = _answer

        def log_message(self, *args) -> None:
            pass

    internal = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Internal)

    class Attacker(http.server.BaseHTTPRequestHandler):
        def _redirect(self, status: int) -> None:
            self.send_response(status)
            self.send_header("Location", f"http://127.0.0.1:{internal.server_port}{self.path}")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            if self.path != "/status":
                self._redirect(302)
                return
            body = b'{"status": "ok", "version": "5"}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            self._redirect(307)

        def log_message(self, *args) -> None:
            pass

    attacker = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Attacker)
    threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (internal, attacker)]
    for t in threads:
        t.start()
    try:
        yield attacker.server_port, hits
    finally:
        for s in (internal, attacker):
            s.shutdown()
            s.server_close()
