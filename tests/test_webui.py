#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances unitary tests suite for the WebUI."""


def test_title(glances_webserver, firefox_browser):
    """
    Test the title of the Glances home page
    """
    assert glances_webserver is not None
    firefox_browser.get("http://localhost:61234")
    assert "Glances" in firefox_browser.title
