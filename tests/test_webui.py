#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the WebUI."""

import os
import tempfile
import time

import pytest
from selenium.webdriver.common.by import By

SCREENSHOT_RESOLUTIONS = [
    # PC
    (640, 480),
    (800, 600),
    (1024, 768),
    (1600, 900),
    (1280, 1024),
    (1600, 1200),
    (1920, 1200),
    # IPHONE
    (750, 1334),  # 8
    (1080, 1920),  # 8 Plus
    (1242, 2208),  # XS
    (1125, 2436),  # 11 Pro
    (1179, 2556),  # 15
    (1320, 2868),  # 16 Pro Max
    # PIXEL Phone
    (1080, 2400),  # Pixel 7
]


@pytest.fixture(scope="module")
def glances_homepage(web_browser):
    time.sleep(3)
    web_browser.get("http://localhost:61234")
    return web_browser


def test_screenshot(glances_webserver, glances_homepage):
    """
    Test Glances home page screenshot.
    """
    glances_webserver is not None
    for resolution in SCREENSHOT_RESOLUTIONS:
        glances_homepage.set_window_size(*resolution)
        glances_homepage.save_screenshot(
            os.path.join(tempfile.gettempdir(), f"glances-{'-'.join(map(str, list(resolution)))}.png")
        )


def test_loading_time(glances_webserver, glances_homepage):
    """
    Test Glances home page loading time.
    """
    assert glances_webserver is not None
    navigation_start = glances_homepage.execute_script("return window.performance.timing.navigationStart")
    response_start = glances_homepage.execute_script("return window.performance.timing.responseStart")
    dom_complete = glances_homepage.execute_script("return window.performance.timing.domComplete")
    backend_perf = response_start - navigation_start
    frontend_perf = dom_complete - response_start
    assert backend_perf < 1000  # ms
    assert frontend_perf < 1000  # ms


def test_title(glances_webserver, glances_homepage):
    """
    Test Glances home page title.
    """
    assert glances_webserver is not None
    assert "Glances" in glances_homepage.title


def test_plugins(glances_webserver, glances_homepage):
    """
    Test Glances defaults plugins.
    """
    assert glances_webserver is not None
    for plugin in [
        "system",
        "now",
        "uptime",
        "quicklook",
        "cpu",
        "mem",
        "memswap",
        "load",
        "network",
        "diskio",
        "fs",
        "sensors",
        "processcount",
        "processlist",
    ]:
        assert glances_homepage.find_element(By.ID, plugin) is not None
