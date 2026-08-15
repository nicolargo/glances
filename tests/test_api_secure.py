#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Regression tests for GHSA-4h34-v6r8-mmjc (CVE-2026-68520).

Both /api/4/config and /api/4/args serve a sanitised view when Glances runs
without authentication, and both used to filter on key names only:
- `[ip] public_username` was returned in full (the reported leak),
- `[ip] public_api=https://user:pass@host/` leaked the embedded credentials.

/api/4/args had no reachable leak (`-u <login>` forces a password, so the
authenticated view is used), but shared the same design flaw: a hand
maintained key list and no value level check. Both endpoints now go through
the same secure_option() sanitiser.

These tests verify that login names and URL userinfo are redacted, and that
non-sensitive keys sharing the `user` prefix (CPU/load thresholds) are not.
"""

import os
import textwrap
from argparse import Namespace

from glances.config import Config
from glances.outputs.glances_restful_api import GlancesRestfulApi

CONF = """
[ip]
public_api=https://admin:secret123@ipv4.ipleak.net/json/
public_username=myname
public_password=mysecret
public_field=ip

[influxdb]
host=localhost
user=root
password=root

[cpu]
user_careful=50
user_critical=90
user_log=True

[ports]
web_1_url=https://alice:pwd1@blog.example.com
web_2_url=https://bob:pwd2@github.example.com

[passwords]
host_regexp=.*
"""


class _RestfulApiStub(GlancesRestfulApi):
    """GlancesRestfulApi reduced to what _sanitize_args() needs (no server startup)."""

    def __init__(self, args):
        self.args = args


def _sanitize_args(**kwargs):
    """Run GlancesRestfulApi._sanitize_args() against a stub holding only args."""
    defaults = {
        'password': '',
        'username': 'glances',
        'username_used': None,
        'username_prompt': False,
        'password_prompt': False,
        'snmp_user': 'private',
        'snmp_auth': 'password',
        'snmp_community': 'public',
        'conf_file': '/etc/glances/glances.conf',
        'client': None,
        'port': 61208,
        'time': 2.0,
    }
    defaults.update(kwargs)
    return _RestfulApiStub(Namespace(**defaults))._sanitize_args()


def _config(tmp_path):
    """Load a Config from a glances.conf built in tmp_path."""
    conf_file = os.path.join(str(tmp_path), 'glances.conf')
    with open(conf_file, 'w', encoding='utf-8') as f:
        f.write(textwrap.dedent(CONF))
    return Config(config_dir=conf_file)


def test_url_embedded_credentials_are_redacted(tmp_path):
    """A credential bearing URL must not expose its userinfo."""
    secure = _config(tmp_path).as_dict_secure()

    assert secure['ip']['public_api'] == 'https://********@ipv4.ipleak.net/json/'
    assert 'admin' not in secure['ip']['public_api']
    assert 'secret123' not in secure['ip']['public_api']


def test_url_without_credentials_is_untouched(tmp_path):
    """Only the userinfo part is removed, the rest of the value is kept."""
    secure = _config(tmp_path).as_dict_secure()

    assert secure['ip']['public_field'] == 'ip'
    assert secure['influxdb']['host'] == 'localhost'


def test_every_url_of_a_multi_url_value_is_redacted(tmp_path):
    secure = _config(tmp_path).as_dict_secure()

    assert secure['ports']['web_1_url'] == 'https://********@blog.example.com'
    assert secure['ports']['web_2_url'] == 'https://********@github.example.com'


def test_login_names_are_redacted(tmp_path):
    """`username` and `user` are credentials, they must be masked."""
    secure = _config(tmp_path).as_dict_secure()

    assert secure['ip']['public_username'] == '********'
    assert secure['influxdb']['user'] == '********'


def test_passwords_are_still_redacted(tmp_path):
    secure = _config(tmp_path).as_dict_secure()

    assert secure['ip']['public_password'] == '********'
    assert secure['influxdb']['password'] == '********'


def test_passwords_section_is_still_blocked(tmp_path):
    secure = _config(tmp_path).as_dict_secure()

    assert 'passwords' not in secure


def test_cpu_user_thresholds_are_not_redacted(tmp_path):
    """`user_*` thresholds are not credentials, masking them breaks the Web UI."""
    secure = _config(tmp_path).as_dict_secure()

    assert secure['cpu']['user_careful'] == '50'
    assert secure['cpu']['user_critical'] == '90'
    assert secure['cpu']['user_log'] == 'True'


# ---------------------------------------------------------------------------
# /api/4/args
# ---------------------------------------------------------------------------


def test_args_login_is_redacted():
    """Any login name is redacted, not only the `username` key of the hardcoded list."""
    args_json = _sanitize_args(username_used='alice')

    assert args_json['username_used'] == '********'


def test_args_url_embedded_credentials_are_redacted():
    """Defence in depth: no argument carries an URL userinfo today."""
    args_json = _sanitize_args(client='https://admin:secret123@glances.example.com')

    assert args_json['client'] == 'https://********@glances.example.com'


def test_args_hardcoded_sensitive_keys_are_still_redacted():
    args_json = _sanitize_args()

    for key in ('password', 'username', 'snmp_user', 'snmp_auth', 'snmp_community', 'conf_file'):
        assert args_json[key] == '********', key


def test_args_non_string_values_keep_their_type():
    """Booleans cannot carry a credential, redacting them would change the API contract."""
    args_json = _sanitize_args()

    assert args_json['password_prompt'] is False
    assert args_json['username_prompt'] is False
    assert args_json['port'] == 61208
    assert args_json['time'] == 2.0


def test_args_authenticated_view_only_redacts_the_password():
    """With --password set, the authenticated view stays as complete as /api/4/config."""
    args_json = _sanitize_args(password='deadbeef', username_used='alice')

    assert args_json['password'] == '********'
    assert args_json['username_used'] == 'alice'
    assert args_json['conf_file'] == '/etc/glances/glances.conf'
