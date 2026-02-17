#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite fixtures.

This module provides pytest fixtures for testing Glances plugins and components.

For WebUI tests, the following are required:
- chromedriver command line (example on Ubuntu system):
  $ sudo apt install chromium-chromedriver
- The chromedriver command line should be in your path (/usr/bin)
"""

import logging
import os
import shlex
import subprocess
import time
from unittest.mock import patch

import pytest

from glances.main import GlancesMain
from glances.stats import GlancesStats

# Optional imports for WebUI testing
try:
    from selenium import webdriver
    from selenium.webdriver import ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

SERVER_PORT = 61234
URL = f"http://localhost:{SERVER_PORT}"


@pytest.fixture(scope="session")
def logger():
    return logging.getLogger(__name__)


@pytest.fixture(scope="session")
def glances_stats():
    testargs = ["glances", "-C", "./conf/glances.conf"]
    with patch('sys.argv', testargs):
        core = GlancesMain()
    stats = GlancesStats(config=core.get_config(), args=core.get_args())
    yield stats
    stats.end()


@pytest.fixture(scope="module")
def glances_stats_no_history():
    testargs = ["glances", "-C", "./conf/glances.conf"]
    with patch('sys.argv', testargs):
        core = GlancesMain()
    args = core.get_args()
    args.time = 1
    args.cached_time = 1
    args.disable_history = True
    stats = GlancesStats(config=core.get_config(), args=args)
    yield stats
    stats.end()


@pytest.fixture(scope="session")
def glances_webserver():
    if os.path.isfile('.venv/bin/python'):
        cmdline = ".venv/bin/python"
    else:
        cmdline = "python"
    cmdline += f" -m glances -B 0.0.0.0 -w --browser -p {SERVER_PORT} -C ./conf/glances.conf"
    args = shlex.split(cmdline)
    pid = subprocess.Popen(args)
    time.sleep(3)
    yield pid
    pid.terminate()
    time.sleep(1)


@pytest.fixture(scope="session")
def web_browser():
    """Init Chrome browser for WebUI testing.

    Requires selenium and webdriver-manager packages.
    """
    if not SELENIUM_AVAILABLE:
        pytest.skip("selenium not installed - skipping WebUI tests")

    opt = ChromeOptions()
    opt.add_argument("--headless")
    opt.add_argument("--start-maximized")
    srv = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(options=opt, service=srv)

    # Yield the WebDriver instance
    driver.implicitly_wait(10)
    yield driver

    # Close the WebDriver instance
    driver.quit()
