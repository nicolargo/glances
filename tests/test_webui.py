#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the WebUI.

This test uses Selenium to test the Glances WebUI.
Under the wood, it uses the ChromeDriver.

Check your Chrome version with:
    /usr/bin/google-chrome --version
Check your ChromeDriver version with:
    /usr/bin/chromedriver --version

The (major) version should match.

If not, download and install the correct version of ChromeDriver.
https://googlechromelabs.github.io/chrome-for-testing/#stable
"""

import os
import tempfile
import time

import pytest
from selenium.common.exceptions import NoSuchElementException
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
    if glances_webserver is None:
        raise AssertionError("Glances webserver is not running")
    for resolution in SCREENSHOT_RESOLUTIONS:
        glances_homepage.set_window_size(*resolution)
        glances_homepage.save_screenshot(
            os.path.join(tempfile.gettempdir(), f"glances-{'-'.join(map(str, list(resolution)))}.png")
        )


def test_loading_time(glances_webserver, glances_homepage):
    """
    Test Glances home page loading time.
    """
    if glances_webserver is None:
        raise AssertionError("Glances webserver is not running")
    navigation_start = glances_homepage.execute_script("return window.performance.timing.navigationStart")
    response_start = glances_homepage.execute_script("return window.performance.timing.responseStart")
    dom_complete = glances_homepage.execute_script("return window.performance.timing.domComplete")
    backend_perf = response_start - navigation_start
    frontend_perf = dom_complete - response_start
    if backend_perf >= 2000:
        raise AssertionError(f"Backend performance is too slow: {backend_perf}ms (limit is 2000ms)")
    if frontend_perf >= 2000:
        raise AssertionError(f"Frontend performance is too slow: {frontend_perf}ms (limit is 2000ms)")


def test_title(glances_webserver, glances_homepage):
    """
    Test Glances home page title.
    """
    if glances_webserver is None:
        raise AssertionError("Glances webserver is not running")
    if "Glances" not in glances_homepage.title:
        raise AssertionError(f"Expected 'Glances' in title, but got '{glances_homepage.title}'")


def test_plugins(glances_webserver, glances_homepage):
    """
    Test Glances defaults plugins.
    """
    if glances_webserver is None:
        raise AssertionError("Glances webserver is not running")
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
        if plugin == 'sensors':
            try:
                assert glances_homepage.find_element(By.ID, plugin) is not None
            except NoSuchElementException:
                # Sensors can be hidden on VM
                pass
        else:
            assert glances_homepage.find_element(By.ID, plugin) is not None
