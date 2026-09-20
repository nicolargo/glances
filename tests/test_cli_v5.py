"""Glances v5 — argparse-level tests for the CLI (main_v5.build_parser).

Covers the new G2 dispatch flags:
- ``-s`` / ``--server`` — opt in to REST API mode (headless).
- ``--enable-mcp`` — mount the MCP endpoint; requires ``--server``.

Plus the legacy ``--quiet`` / ``--no-tui`` flag is still accepted
(deprecation note in a follow-up phase — see plan G2 Task 1 Step 3 and
the "Open points" section).
"""

from __future__ import annotations

import argparse

import pytest

from glances.main_v5 import apply_process_flags, build_parser, validate_args
from glances.processes import glances_processes

# ---------------------------------------------------------------- parser


def test_parser_accepts_short_server_flag():
    args = build_parser().parse_args(["-s"])
    assert args.server is True


def test_parser_accepts_long_server_flag():
    args = build_parser().parse_args(["--server"])
    assert args.server is True


def test_parser_default_server_is_false():
    args = build_parser().parse_args([])
    assert args.server is False


def test_parser_accepts_enable_mcp_flag():
    args = build_parser().parse_args(["-s", "--enable-mcp"])
    assert args.enable_mcp is True


def test_parser_default_enable_mcp_is_false():
    args = build_parser().parse_args([])
    assert args.enable_mcp is False


def test_parser_quiet_and_no_tui_are_aliases():
    """The legacy flag has two spellings — both set ``args.no_tui``."""
    args_quiet = build_parser().parse_args(["--quiet"])
    args_no_tui = build_parser().parse_args(["--no-tui"])
    assert args_quiet.no_tui is True
    assert args_no_tui.no_tui is True


def test_parser_default_no_tui_is_false():
    args = build_parser().parse_args([])
    assert args.no_tui is False


def test_parser_keeps_existing_flags_working():
    """Sanity: pre-G2 flags still parse."""
    args = build_parser().parse_args(["-C", "/tmp/glances.conf", "--bind", "0.0.0.0", "--port", "8080", "-d"])
    assert args.config_path == "/tmp/glances.conf"
    assert args.bind == "0.0.0.0"
    assert args.port == 8080
    assert args.debug is True


# ---------------------------------------------------------------- validation


def test_validate_rejects_mcp_without_server(capsys):
    """``--enable-mcp`` requires ``--server`` — error + exit."""
    args = build_parser().parse_args(["--enable-mcp"])
    with pytest.raises(SystemExit) as exc:
        validate_args(args)
    # argparse's parser.error() exits with code 2.
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--enable-mcp" in err
    assert "--server" in err


def test_validate_accepts_server_alone(capsys):
    args = build_parser().parse_args(["-s"])
    # Must not raise.
    validate_args(args)
    # No error output.
    assert capsys.readouterr().err == ""


def test_validate_accepts_server_with_mcp(capsys):
    args = build_parser().parse_args(["-s", "--enable-mcp"])
    validate_args(args)
    assert capsys.readouterr().err == ""


def test_validate_accepts_default_mode(capsys):
    args = build_parser().parse_args([])
    validate_args(args)
    assert capsys.readouterr().err == ""


def test_validate_accepts_quiet_alone(capsys):
    """Legacy --quiet without -s is still accepted (deprecation later)."""
    args = build_parser().parse_args(["--quiet"])
    validate_args(args)
    assert capsys.readouterr().err == ""


def test_validate_accepts_server_with_quiet(capsys, caplog):
    """``-s --quiet`` is harmless — -s already implies headless. Log a hint."""
    args = build_parser().parse_args(["-s", "--quiet"])
    with caplog.at_level("INFO"):
        validate_args(args)
    assert capsys.readouterr().err == ""
    # A hint mentioning that -s already implies headless is logged.
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert "--server" in joined or "-s" in joined


# ---------------------------------------------------------------- shape


def test_parser_is_argument_parser():
    assert isinstance(build_parser(), argparse.ArgumentParser)


# ---------------------------------------------------------------- processes


def test_the_programs_option_parses():
    args = build_parser().parse_args(["--programs"])
    assert args.programs is True


def test_the_default_is_the_process_list():
    args = build_parser().parse_args([])
    assert args.programs is False


def test_the_sort_option_uses_v4s_dest_and_choices():
    """A script written against v4 must keep working against v5, so the
    dest name is v4's (`sort_processes_key`), not a v5 invention."""
    args = build_parser().parse_args(["--sort-processes", "memory_percent"])
    assert args.sort_processes_key == "memory_percent"


def test_the_sort_option_rejects_a_value_outside_the_shared_list():
    from glances.processes import sort_processes_stats_list

    assert "nonsense" not in sort_processes_stats_list
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--sort-processes", "nonsense"])


def test_the_sort_option_is_applied_to_the_process_engine():
    """A parsed-but-unwired flag would have the WebUI underline a column
    the engine never actually sorts by — ``apply_process_flags`` must push
    ``args.sort_processes_key`` onto the ``glances_processes`` singleton.

    ``glances_processes`` is a module-level singleton shared with every
    other test in the suite, so its pre-existing sort state is saved and
    restored directly (bypassing ``set_sort_key``'s ``'auto'`` special-case)
    to avoid leaking into other tests.
    """
    saved_key, saved_auto = glances_processes._sort_key, glances_processes.auto_sort
    try:
        args = build_parser().parse_args(["--sort-processes", "memory_percent"])
        apply_process_flags(args)
        assert glances_processes.sort_key == "memory_percent"
        # v4 parity: an explicit CLI key turns OFF auto-sort.
        assert glances_processes.auto_sort is False
    finally:
        glances_processes._sort_key = saved_key
        glances_processes.auto_sort = saved_auto


def test_the_default_leaves_the_process_engine_untouched():
    """No ``--sort-processes`` on the CLI must not touch the engine's sort
    state at all (not even to reset it) — ``args.sort_processes_key`` is
    ``None`` by default and ``apply_process_flags`` must no-op."""
    saved_key, saved_auto = glances_processes._sort_key, glances_processes.auto_sort
    try:
        glances_processes._sort_key = "username"
        glances_processes.auto_sort = False
        args = build_parser().parse_args([])
        apply_process_flags(args)
        assert glances_processes.sort_key == "username"
        assert glances_processes.auto_sort is False
    finally:
        glances_processes._sort_key = saved_key
        glances_processes.auto_sort = saved_auto
