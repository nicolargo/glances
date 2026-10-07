# SPDX-FileCopyrightText: 2026 Glances contributors
# SPDX-License-Identifier: LGPL-3.0-only

"""Regression tests for the optional keys read by GlancesExport.load_conf."""

import pytest

from glances.config import Config
from glances.exports.export import GlancesExport


class DummyExport(GlancesExport):
    """Exporter with a default value for one of its optional keys."""

    def __init__(self, config):
        super().__init__(config=config)
        self.protocol = 'http'
        self.export_enable = self.load_conf('dummy', mandatories=['host', 'port'], options=['protocol', 'prefix'])


@pytest.fixture
def make_config(tmp_path):
    def _make_config(section):
        conf_file = tmp_path / 'glances.conf'
        conf_file.write_text(f'[dummy]\n{section}\n', encoding='utf-8')
        return Config(config_dir=str(conf_file))

    return _make_config


def test_missing_optional_key_keeps_the_exporter_default(make_config):
    exporter = DummyExport(make_config('host=localhost\nport=8086'))

    assert exporter.export_enable
    assert exporter.protocol == 'http'
    assert exporter.prefix is None


def test_configured_optional_key_overrides_the_exporter_default(make_config):
    exporter = DummyExport(make_config('host=localhost\nport=8086\nprotocol=https\nprefix=foo'))

    assert exporter.protocol == 'https'
    assert exporter.prefix == 'foo'
