#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the WebUI in a real browser (port of v4 `test_webui`).

Starts `glances-v5 -s` on a free port and drives headless Chromium through
Playwright (skipped when the `playwright` package is not installed). The
browser comes from `PLAYWRIGHT_BROWSERS_PATH` or `playwright install chromium`.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time

import pytest
import requests

sync_api = pytest.importorskip("playwright.sync_api")

# Same set as v4: PC, iPhone, Pixel.
SCREENSHOT_RESOLUTIONS = [
    (640, 480),
    (800, 600),
    (1024, 768),
    (1600, 900),
    (1280, 1024),
    (1600, 1200),
    (1920, 1200),
    (750, 1334),
    (1080, 1920),
    (1242, 2208),
    (1125, 2436),
    (1179, 2556),
    (1320, 2868),
    (1080, 2400),
]
STARTUP_TIMEOUT = 15


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def glances_v5_url():
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    # A config of its own, so the server never reads the user's glances.conf.
    xdg = tempfile.mkdtemp()
    env = {k: v for k, v in os.environ.items() if not k.startswith("GLANCES_")} | {"XDG_CONFIG_HOME": xdg}
    server = subprocess.Popen(
        [sys.executable, "-m", "glances.main_v5", "-s", "-B", "127.0.0.1", "-p", str(port)], env=env
    )
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT
        while True:
            if server.poll() is not None:
                pytest.fail(f"glances-v5 -s exited during startup with return code {server.returncode}")
            try:
                if requests.get(f"{url}/status", timeout=1).status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            if time.monotonic() > deadline:
                pytest.fail(f"glances-v5 -s did not answer within {STARTUP_TIMEOUT} seconds")
            time.sleep(0.5)
        yield url
    finally:
        server.terminate()
        server.wait(10)


@pytest.fixture(scope="module")
def homepage(glances_v5_url):
    with sync_api.sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(glances_v5_url)
        yield page
        browser.close()


def test_title(homepage):
    assert "Glances" in homepage.title()


def test_loading_time(homepage):
    timing = homepage.evaluate("() => window.performance.timing.toJSON()")
    backend = timing["responseStart"] - timing["navigationStart"]
    frontend = timing["domComplete"] - timing["responseStart"]
    assert backend < 2000, f"Backend performance is too slow: {backend}ms (limit is 2000ms)"
    assert frontend < 2000, f"Frontend performance is too slow: {frontend}ms (limit is 2000ms)"


def test_screenshot(homepage):
    """No assertion beyond the files: the screenshots are for manual review."""
    for width, height in SCREENSHOT_RESOLUTIONS:
        homepage.set_viewport_size({"width": width, "height": height})
        path = os.path.join(tempfile.gettempdir(), f"glances-v5-{width}-{height}.png")
        homepage.screenshot(path=path)
        assert os.path.getsize(path) > 0
