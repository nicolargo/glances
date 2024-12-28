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

import pytest
from selenium.webdriver.common.by import By


@pytest.fixture(scope="module")
def glances_homepage(firefox_browser):
    firefox_browser.get("http://localhost:61234")
    firefox_browser.save_screenshot(os.path.join(tempfile.gettempdir(), "glances.png"))
    return firefox_browser


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
