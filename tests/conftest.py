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
import shlex
import subprocess
import time

import pytest
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService

SERVER_PORT = 61234
URL = f"http://localhost:{SERVER_PORT}"


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
def firefox_browser():
    """Init Firefox browser."""
    opts = FirefoxOptions()
    opts.add_argument("--headless")
    srv = FirefoxService(executable_path="/snap/bin/geckodriver")
    driver = webdriver.Firefox(options=opts, service=srv)

    # Yield the WebDriver instance
    driver.implicitly_wait(10)
    yield driver

    # Close the WebDriver instance
    driver.quit()
