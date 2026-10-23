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

# `glances.logger` the module, not the logger it exports
logger_module = importlib.import_module("glances.logger")

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
def test_no_shared_temporary_folder_when_no_private_one_can_be_made(tmp_path, monkeypatch):
    # A folder cannot be created below a file, even by root (root can create
    # `/proc/...` where procfs is not mounted, e.g. on FreeBSD).
    not_a_folder = tmp_path / "a-file"
    not_a_folder.write_text("")
    monkeypatch.setenv("HOME", str(not_a_folder))
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
def test_the_file_handler_is_a_no_op_without_a_log_folder(tmp_path, monkeypatch):
    not_a_folder = tmp_path / "a-file"
    not_a_folder.write_text("")
    monkeypatch.setenv("HOME", str(not_a_folder))
    monkeypatch.delenv("XDG_CACHE_HOME", raising=False)
    try:
        reloaded = importlib.reload(logger_module)
        assert reloaded.LOG_FILENAME is None
        assert reloaded.LOGGING_CFG["handlers"]["file"]["class"] == "logging.NullHandler"
    finally:
        monkeypatch.undo()
        importlib.reload(logger_module)


# ---------------------------------------------------------------------------
# Running as root: nothing of another user is trusted (security audit 2026-10-17, X-2, I-10, S-10)
# ---------------------------------------------------------------------------


def test_a_log_folder_owned_by_another_user_is_skipped(tmp_path, monkeypatch):
    """Under `sudo -E`, `$XDG_CACHE_HOME/glances` is the invoking user's folder."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    monkeypatch.setattr(logger_module, "trusted_by_root", lambda path: path != str(tmp_path / "glances"))
    assert logger_module._log_folder() == str(tmp_path / "home" / ".local" / "share" / "glances")


@posix_only
def test_a_link_planted_at_the_log_file_is_not_followed(tmp_path):
    """The link's target used to receive root's log lines and be made 0600."""
    victim = tmp_path / "victim"
    victim.write_text("")
    victim.chmod(0o644)
    link = tmp_path / "glances.log"
    link.symlink_to(victim)
    with pytest.raises(OSError):
        logger_module.PrivateRotatingFileHandler(str(link)).close()
    assert _mode(victim) == 0o644
    assert victim.read_text() == ""


@posix_only
@pytest.mark.skipif(os.geteuid() != 0, reason="needs root to chown")
def test_the_mode_of_a_log_owned_by_another_user_is_left_alone(tmp_path):
    log = tmp_path / "glances.log"
    log.write_text("")
    log.chmod(0o644)
    os.chown(log, 65534, 65534)
    logger_module.PrivateRotatingFileHandler(str(log)).close()
    assert _mode(log) == 0o644


def test_an_untrusted_log_cfg_file_is_ignored(tmp_path, monkeypatch):
    cfg = tmp_path / "logging.json"
    cfg.write_text('{"version": 1, "root": {"level": "CRITICAL"}}')
    monkeypatch.setenv("LOG_CFG", str(cfg))
    monkeypatch.setattr(logger_module, "trusted_by_root", lambda path: False)
    root = logging.getLogger()
    level = root.level
    # dictConfig() replaces the root handlers, caplog's included: record the
    # warning on the logger instance itself.
    warnings = []
    monkeypatch.setattr(root, "warning", lambda msg, *args: warnings.append(msg % args))
    try:
        logger_module.glances_logger()
        assert root.level != logging.CRITICAL
        assert warnings and "LOG_CFG" in warnings[0] and str(cfg) in warnings[0]
    finally:
        monkeypatch.undo()
        logger_module.glances_logger()
        root.setLevel(level)
