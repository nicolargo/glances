#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the WebUI."""

import pytest
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService


@pytest.fixture()
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


def test_title(firefox_browser):
    """
    Test the title of the Python.org website
    """
    firefox_browser.get("https://www.python.org")
    assert firefox_browser.title == "Welcome to Python.org"
