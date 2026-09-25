#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The plugin limits must not publish the credentials of a plugin section.

load_limits() copies every option of the plugin section into the limits, so
they hold `[ip] public_password` or the `[ports]` web URL and proxies. The
limits are served by /api/4/<plugin>/limits, /api/4/all/limits, the XML-RPC
getAllLimits() and the MCP glances://limits resources, so the credentials go
through the same sanitiser as /api/4/config (see also GHSA-2jqf-3j6f-683p).
"""

import pytest

from glances.config import Config
from glances.plugins.cpu import CpuPlugin
from glances.plugins.ip import IpPlugin
from glances.plugins.ports import PortsPlugin
from glances.stats import GlancesStats

SECRET = 'Sup3rS3cret'
# A comma is valid in URL userinfo, and load_limits() splits values on it
PROXY_SECRET = 'Pr0xy,P4ss'

CONFIG = f"""
[ip]
public_disabled=True
public_api=https://svcmonitor:{SECRET}@ipinfo.example/json
public_username=svcmonitor
public_password={SECRET}

[ports]
refresh=60
port_default_gateway=False
web_1_url=https://svcmonitor:{SECRET}@intranet.corp.example/health
web_1_http_proxy=http://proxyuser:{PROXY_SECRET}@proxy.corp.example:3128
web_1_description=Intranet health
"""


@pytest.fixture
def config(tmp_path):
    conf_file = tmp_path / 'glances.conf'
    conf_file.write_text(CONFIG)
    return Config(config_dir=str(conf_file))


@pytest.fixture
def plugins(config):
    return {'ip': IpPlugin(config=config), 'ports': PortsPlugin(config=config)}


@pytest.fixture
def all_limits(plugins):
    stats = GlancesStats.__new__(GlancesStats)
    stats._plugins = plugins
    return stats.getAllLimitsAsDict(plugin_list=list(plugins))


def test_no_secret_in_all_limits(all_limits):
    published = repr(all_limits)

    assert SECRET not in published
    assert PROXY_SECRET not in published
    assert 'svcmonitor' not in published


def test_sensitive_keys_are_redacted(all_limits):
    assert all_limits['ip']['ip_public_username'] == ['********']
    assert all_limits['ip']['ip_public_password'] == ['********']


def test_url_userinfo_is_redacted(all_limits):
    assert all_limits['ip']['ip_public_api'] == ['https://********@ipinfo.example/json']
    assert all_limits['ports']['ports_web_1_url'] == ['https://********@intranet.corp.example/health']
    assert all_limits['ports']['ports_web_1_http_proxy'] == ['http://********@proxy.corp.example:3128']


def test_other_limits_are_unchanged(all_limits):
    assert all_limits['ports']['ports_refresh'] == 60.0
    assert all_limits['ports']['ports_web_1_description'] == ['Intranet health']
    assert all_limits['ip']['ip_public_disabled'] == ['True']


def test_option_names_without_plugin_prefix(tmp_path):
    """`user` and a numeric `token` are redacted, `user_careful` is a threshold."""
    conf_file = tmp_path / 'glances.conf'
    conf_file.write_text('[cpu]\nuser=svcmonitor\ntoken=123456\nuser_careful=50\nuser_critical=90\n')
    limits = CpuPlugin(config=Config(config_dir=str(conf_file))).get_limits()

    assert limits['cpu_user'] == ['********']
    assert limits['cpu_token'] == '********'
    assert limits['cpu_user_careful'] == 50.0
    assert limits['cpu_user_critical'] == 90.0


def test_plugin_still_reads_the_real_values(plugins):
    """Only the published copy is redacted, the plugin keeps its settings."""
    assert plugins['ip'].public_username == 'svcmonitor'
    assert plugins['ip'].public_password == SECRET
    assert plugins['ports'].get_limits('web_1_url') == [f'https://svcmonitor:{SECRET}@intranet.corp.example/health']
