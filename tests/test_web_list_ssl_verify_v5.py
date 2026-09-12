#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Tests for web_x_ssl_verify read through the v5 configuration.

`ports/model_v5.py` reuses `GlancesWebList` VERBATIM (design §4) but hands it
a `GlancesConfigV5`, so every config accessor the v4 class calls has to exist
on the v5 object. `get_bool_value()` did not, and the resulting AttributeError
made `discover_plugins()` skip the whole `ports` plugin (port scans included)
for any operator with a `web_N_url` configured.
"""

import pytest

from glances.config_v5 import GlancesConfigV5
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
    return GlancesWebList(config=GlancesConfigV5(cli_config_path=str(conf_file))).get_web_list()


def ssl_verify(web_list, indice):
    return next(web['ssl_verify'] for web in web_list if web['indice'] == indice)


def test_ssl_verify_false_is_a_boolean(web_list):
    assert ssl_verify(web_list, 'web_1') is False


def test_ssl_verify_true_is_a_boolean(web_list):
    assert ssl_verify(web_list, 'web_2') is True


def test_ssl_verify_keeps_a_ca_bundle_path(web_list):
    assert ssl_verify(web_list, 'web_3') == '/etc/ssl/certs/ca-bundle.crt'


def test_ssl_verify_defaults_to_true(web_list):
    assert ssl_verify(web_list, 'web_4') is True
