#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for web_x_ssl_verify in the URL monitoring list."""

import pytest

from glances.config import Config
from glances.web_list import GlancesWebList

CONFIG = """
[ports]
refresh=30
timeout=3
port_default_gateway=False
web_1_url=https://example.com
web_1_ssl_verify=false
web_2_url=https://example.com
web_2_ssl_verify=true
web_3_url=https://example.com
web_3_ssl_verify=/etc/ssl/certs/ca-bundle.crt
web_4_url=https://example.com
"""


@pytest.fixture
def web_list(tmp_path):
    conf_file = tmp_path / 'glances.conf'
    conf_file.write_text(CONFIG)
    return GlancesWebList(config=Config(config_dir=str(conf_file))).get_web_list()


def ssl_verify(web_list, indice):
    return next(web['ssl_verify'] for web in web_list if web['indice'] == indice)


# Requests reads a string `verify` as the path to a CA bundle, so a boolean written
# in the configuration file has to reach it as a boolean: 'false' (and 'true') used
# to fail every scan of the URL with "Could not find a suitable TLS CA certificate
# bundle, invalid path: false".
def test_ssl_verify_false_is_a_boolean(web_list):
    assert ssl_verify(web_list, 'web_1') is False


def test_ssl_verify_true_is_a_boolean(web_list):
    assert ssl_verify(web_list, 'web_2') is True


def test_ssl_verify_keeps_a_ca_bundle_path(web_list):
    assert ssl_verify(web_list, 'web_3') == '/etc/ssl/certs/ca-bundle.crt'


def test_ssl_verify_defaults_to_true(web_list):
    assert ssl_verify(web_list, 'web_4') is True
