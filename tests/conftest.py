#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the WebUI.

Need chromedriver command line (example on Ubuntu system):
$ sudo apt install chromium-chromedriver

The chromedriver command line should be in your path (/usr/bin)
"""

import logging
import os
import shlex
import subprocess
import time

import pytest
from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService

from glances.main import GlancesMain
from glances.stats import GlancesStats

SERVER_PORT = 61234
URL = f"http://localhost:{SERVER_PORT}"


@pytest.fixture(scope="session")
def logger():
    return logging.getLogger(__name__)


@pytest.fixture(scope="session")
def glances_stats():
    core = GlancesMain(args_begin_at=2)
    stats = GlancesStats(config=core.get_config(), args=core.get_args())
    yield stats
    stats.end()


@pytest.fixture(scope="module")
def glances_stats_no_history():
    core = GlancesMain(args_begin_at=2)
    args = core.get_args()
    args.time = 1
    args.cached_time = 1
    args.disable_history = True
    stats = GlancesStats(config=core.get_config(), args=args)
    yield stats
    stats.end()


@pytest.fixture(scope="session")
def glances_webserver():
    if os.path.isfile('./venv/bin/python'):
        cmdline = "./venv/bin/python"
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
    """Init Firefox browser."""
    opt = ChromeOptions()
    opt.add_argument("--headless")
    opt.add_argument("--start-maximized")
    srv = ChromeService()
    driver = webdriver.Chrome(options=opt, service=srv)

    # Yield the WebDriver instance
    driver.implicitly_wait(10)
    yield driver

    # Close the WebDriver instance
    driver.quit()
