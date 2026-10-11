#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The log file stays private to its user (security audit 2026-10-04, M8).

`glances.logger` is shared by v4 and v5. It used to fall back to
`<tmp>/glances-<user>.log`, mode 0644, when the home folder had no
`~/.local/share`: as root, a folder where another user can plant a link,
and a log readable by all.
"""

import importlib
import logging
import os
import stat
import sys

import pytest

import glances  # noqa: F401 -- `glances.logger` the module, not the logger it exports

logger_module = sys.modules["glances.logger"]

# Unix permission bits and a POSIX-only unusable home (`/proc/...`) do not exist on Windows.
posix_only = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes / paths")


def _mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_the_folder_is_created_private_under_the_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))  # Windows ignores HOME
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    folder = logger_module._log_folder()
    assert folder == str(tmp_path / ".local" / "share" / "glances")
    if sys.platform != "win32":
        assert _mode(folder) == 0o700


def test_xdg_cache_home_comes_first(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert logger_module._log_folder() == str(tmp_path / "glances")


@posix_only
def test_no_shared_temporary_folder_when_no_private_one_can_be_made(monkeypatch):
    monkeypatch.setenv("HOME", "/proc/no-such-home")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    assert logger_module._log_folder() is None


@posix_only
def test_the_log_file_is_created_owner_only(tmp_path):
    handler = logger_module.PrivateRotatingFileHandler(str(tmp_path / "glances.log"))
    try:
        handler.emit(logging.makeLogRecord({"msg": "hello"}))
    finally:
        handler.close()
    assert _mode(tmp_path / "glances.log") == 0o600


@posix_only
def test_a_log_left_readable_by_an_older_glances_is_tightened(tmp_path):
    log = tmp_path / "glances.log"
    log.write_text("old\n")
    log.chmod(0o644)
    logger_module.PrivateRotatingFileHandler(str(log)).close()
    assert _mode(log) == 0o600
    assert log.read_text() == "old\n", "appended to, not truncated"


@posix_only
def test_the_file_handler_is_a_no_op_without_a_log_folder(monkeypatch):
    monkeypatch.setenv("HOME", "/proc/no-such-home")
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    try:
        reloaded = importlib.reload(logger_module)
        assert reloaded.LOG_FILENAME is None
        assert reloaded.LOGGING_CFG["handlers"]["file"]["class"] == "logging.NullHandler"
    finally:
        monkeypatch.undo()
        importlib.reload(logger_module)
