#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""GHSA-mcm7-fmh3-v6v3: plugins are only ever imported from the installed package.

v4 loaded extra plugins from a directory (`-P`, `[global] plugin_dir`): a
writable directory there meant arbitrary code run by Glances, often as
root. v5 discovers `glances.plugins.<name>.model_v5` in the installed
`glances.plugins` package only, and has no plugin directory option.
"""

import os
import sys
from pathlib import Path

import pytest

import glances.plugins as plugins_pkg
from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import build_parser, discover_plugin_classes, discover_plugins
from glances.stats_store_v5 import StatsStoreV5

INSTALLED = Path(plugins_pkg.__file__).resolve().parent


def _plant(root: Path, canary: Path) -> None:
    """A plugin that records its own import: `<root>/glances/plugins/planted/model_v5.py`."""
    package = root / "glances" / "plugins" / "planted"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "model_v5.py").write_text(f"open({str(canary)!r}, 'w').close()\n")
    (root / "planted").mkdir()
    (root / "planted" / "__init__.py").write_text("")
    (root / "planted" / "model_v5.py").write_text(f"open({str(canary)!r}, 'w').close()\n")


def test_a_plugin_planted_in_the_working_directory_or_on_sys_path_is_never_imported(tmp_path, monkeypatch):
    canary = tmp_path / "imported"
    _plant(tmp_path, canary)
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    conf = tmp_path / "glances.conf"
    conf.write_text(f"[global]\nplugin_dir={tmp_path}\n")
    monkeypatch.setenv("GLANCES_GLOBAL__PLUGIN_DIR", str(tmp_path))

    classes = discover_plugin_classes()
    discover_plugins(StatsStoreV5(), GlancesConfigV5(cli_config_path=str(conf)))

    assert not canary.exists()
    assert "planted" not in {name.split(".")[2] for name, _cls in classes}
    assert not [m for m in sys.modules if m.endswith("planted.model_v5")]


def test_every_discovered_plugin_comes_from_the_installed_package():
    classes = discover_plugin_classes()
    assert classes
    for name, cls in classes:
        assert name.startswith("glances.plugins.") and name.endswith(".model_v5"), name
        source = Path(sys.modules[cls.__module__].__file__).resolve()
        assert source.is_relative_to(INSTALLED), source


@pytest.mark.parametrize("option", [["-P", os.curdir], ["--plugins", os.curdir]])
def test_there_is_no_plugin_directory_option(option):
    with pytest.raises(SystemExit):
        build_parser().parse_args(option)
