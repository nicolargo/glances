#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — unit tests for the CLI entrypoint (Phase 1.7).

Test stack: pytest + pytest-asyncio (auto mode). See architecture decisions §9.

Coverage:
- build_parser: defaults, individual flags, --version, --no-api-doc
- setup_logging: respects --debug
- discover_plugins: finds the 5 concrete plugins, empty registry tolerated
  (no error), broken module skipped with WARNING
- cli_set_password: round-trip success, mismatch rejected, empty rejected,
  KeyboardInterrupt handled
- assemble: CLI bind/port override config; CLI overrides default;
  scheduler+app share plugins; alerts wired into scheduler
- serve: scheduler stopped after uvicorn.Server.serve returns
- main: dispatches to set-password path
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from unittest.mock import AsyncMock, patch

import pytest

from glances.config_v5 import GlancesConfigV5
from glances.main_v5 import (
    apply_plugin_flags,
    assemble,
    build_parser,
    cli_set_password,
    discover_plugin_classes,
    discover_plugins,
    main,
    serve,
    setup_logging,
)
from glances.stats_store_v5 import StatsStoreV5

# ----------------------------------------------------------- fixtures


@pytest.fixture
def config(tmp_path, monkeypatch) -> GlancesConfigV5:
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    monkeypatch.delenv("GLANCES_CONFIG_FILE", raising=False)
    for env_key in list(__import__("os").environ):
        if env_key.startswith("GLANCES_"):
            monkeypatch.delenv(env_key, raising=False)
    return GlancesConfigV5()


# ----------------------------------------------------------- argparse


def test_build_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.config_path is None
    assert args.bind is None
    assert args.port is None
    assert args.api_doc is None
    assert args.debug is False
    assert args.set_password is False


def test_build_parser_flags():
    parser = build_parser()
    args = parser.parse_args(["--bind", "0.0.0.0", "--port", "8080", "-d"])
    assert args.bind == "0.0.0.0"
    assert args.port == 8080
    assert args.debug is True


def test_build_parser_no_api_doc():
    parser = build_parser()
    args = parser.parse_args(["--no-api-doc"])
    assert args.api_doc is False


def test_meangpu_and_fahrenheit_flags_parse():
    parser = build_parser()
    args = parser.parse_args(["--meangpu", "--fahrenheit"])
    assert args.meangpu is True
    assert args.fahrenheit is True


def test_meangpu_fahrenheit_default_false():
    parser = build_parser()
    args = parser.parse_args([])
    assert getattr(args, "meangpu", False) is False
    assert getattr(args, "fahrenheit", False) is False


def test_build_parser_version_exits(capsys):
    parser = build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["--version"])
    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "Glances 5." in captured.out


# ----------------------------------------------------------- logging


def test_setup_logging_debug_sets_debug_level():
    setup_logging(debug=True)
    assert logging.getLogger().level == logging.DEBUG


def test_setup_logging_normal_sets_info_level():
    setup_logging(debug=False)
    assert logging.getLogger().level == logging.INFO


# ----------------------------------------------------------- discover_plugins


def test_discover_plugins_finds_concrete_v5_plugins(config):
    store = StatsStoreV5()
    plugins = discover_plugins(store, config)
    names = {p.plugin_name for p in plugins}
    # Phase 1.1..1.3 shipped these; the test must continue to pass when
    # new plugins are added.
    assert {"cpu", "mem", "load", "network", "percpu"}.issubset(names)


def test_discover_plugins_empty_when_no_modules(config, monkeypatch):
    """Simulate an empty plugins package: empty result is a *valid* state."""

    class _FakePkg:
        __path__ = []

    store = StatsStoreV5()
    monkeypatch.setattr("glances.main_v5._plugins_pkg", _FakePkg)
    plugins = discover_plugins(store, config)
    assert plugins == []


# ------------------------------------------------- discover_plugins / disable


def _config_with(tmp_path, monkeypatch, body: str) -> GlancesConfigV5:
    xdg_conf = tmp_path / "xdg" / "glances" / "glances.conf"
    xdg_conf.parent.mkdir(parents=True, exist_ok=True)
    xdg_conf.write_text(body)
    monkeypatch.setattr(GlancesConfigV5, "SYSTEM_CONFIG_PATH", tmp_path / "no-system.conf")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    return GlancesConfigV5()


def test_discover_plugins_skips_disabled_plugin(tmp_path, monkeypatch):
    """`[<plugin>] disable=True` must keep the plugin from being built at all.

    Not merely from collecting: `ports` builds its scan list and starts a
    background thread in `__init__`, so gating inside `_grab_stats()`
    would be too late.
    """
    cfg = _config_with(tmp_path, monkeypatch, "[folders]\ndisable=True\n[ports]\ndisable=True\n")
    names = {p.plugin_name for p in discover_plugins(StatsStoreV5(), cfg)}
    assert "folders" not in names
    assert "ports" not in names
    # ...while the rest of the registry is untouched.
    assert "cpu" in names


def test_discover_plugins_keeps_enabled_plugin(tmp_path, monkeypatch):
    cfg = _config_with(tmp_path, monkeypatch, "[folders]\ndisable=False\n[ports]\ndisable=False\n")
    names = {p.plugin_name for p in discover_plugins(StatsStoreV5(), cfg)}
    assert {"folders", "ports"}.issubset(names)


def test_shipped_defaults_resolve_as_expected(config):
    """No user config at all -> each plugin's own default applies."""
    names = {p.plugin_name for p in discover_plugins(StatsStoreV5(), config)}
    # Ship disabled (v4 `[<plugin>] disable=True`).
    assert names.isdisjoint({"connections", "npu", "vms"})
    # Ship enabled.
    assert {"folders", "ports", "cpu"}.issubset(names)


def test_is_disabled_reads_the_config_key(tmp_path, monkeypatch):
    from glances.plugins.connections.model_v5 import PluginModel as Connections
    from glances.plugins.folders.model_v5 import PluginModel as Folders

    cfg = _config_with(tmp_path, monkeypatch, "[connections]\ndisable=False\n[folders]\ndisable=True\n")
    assert Connections.is_disabled(cfg) is False
    assert Folders.is_disabled(cfg) is True


def test_discover_plugin_classes_lists_disabled_plugins_too(config):
    """The class catalogue must stay complete: issue #3548 (runtime toggle)
    needs a way to instantiate a plugin that was disabled at startup."""
    catalogue = {cls.plugin_name for _, cls in discover_plugin_classes()}
    assert {"connections", "npu", "vms", "folders", "ports"}.issubset(catalogue)


def test_discover_plugins_skips_broken_module(config, monkeypatch, caplog):
    import types as _types

    class _FakeModuleInfo:
        def __init__(self, name):
            self.name = name
            self.ispkg = True

    class _FakePkg:
        __path__ = ["unused"]

    def fake_iter_modules(_paths):
        return [_FakeModuleInfo("brokenplug")]

    def fake_import_module(name):
        if name == "glances.plugins.brokenplug.model_v5":
            raise RuntimeError("boom")
        return _types.ModuleType(name)

    monkeypatch.setattr("glances.main_v5._plugins_pkg", _FakePkg)
    monkeypatch.setattr("glances.main_v5.pkgutil.iter_modules", fake_iter_modules)
    monkeypatch.setattr("glances.main_v5.importlib.import_module", fake_import_module)

    with caplog.at_level(logging.WARNING):
        plugins = discover_plugins(StatsStoreV5(), config)
    assert plugins == []
    assert any("import of" in rec.message and "failed" in rec.message for rec in caplog.records)


# ----------------------------------------------------------- set-password


def test_cli_set_password_round_trip(monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "hunter2")
    rc = cli_set_password()
    out = capsys.readouterr().out
    assert rc == 0
    assert "[outputs] password" in out
    # The printed line has the form salt$hex — verify_password accepts it.
    hash_line = next(line for line in out.splitlines() if "$" in line and " " not in line)
    from glances.security_v5 import verify_password

    assert verify_password("hunter2", hash_line) is True


def test_cli_set_password_mismatch(monkeypatch, capsys):
    inputs = iter(["abc", "xyz"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(inputs))
    rc = cli_set_password()
    err = capsys.readouterr().err
    assert rc == 1
    assert "do not match" in err


def test_cli_set_password_empty(monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")
    rc = cli_set_password()
    err = capsys.readouterr().err
    assert rc == 1
    assert "Empty" in err


def test_cli_set_password_keyboard_interrupt(monkeypatch, capsys):
    def _interrupt(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("getpass.getpass", _interrupt)
    rc = cli_set_password()
    assert rc == 1
    assert "Aborted" in capsys.readouterr().err


# ----------------------------------------------------------- assemble


def test_disable_config_exec_defaults_to_false():
    assert build_parser().parse_args([]).disable_config_exec is False


def test_disable_config_exec_flag_parses():
    assert build_parser().parse_args(["--disable-config-exec"]).disable_config_exec is True


def test_disable_config_exec_flag_hardens_the_shell_action(config):
    """CVE-2026-68519: the flag must reach the on-alert action commands.

    Checked through `assemble()` (not the parser) because the flag travels via
    the config overlay — the same mechanism as `--api-doc` / `--enable-mcp`.
    """
    args = build_parser().parse_args(["-s", "--disable-config-exec"])
    _, scheduler, _, _, _tui = assemble(args, config)
    assert scheduler.alerts.actions["action"].allow_operators() is False


def test_shell_action_allows_operators_without_the_flag(config):
    args = build_parser().parse_args(["-s"])
    _, scheduler, _, _, _tui = assemble(args, config)
    assert scheduler.alerts.actions["action"].allow_operators() is True


def test_assemble_resolves_bind_and_port_from_cli(config):
    args = build_parser().parse_args(["-s", "--bind", "0.0.0.0", "--port", "1234"])
    app, scheduler, host, port, _tui = assemble(args, config)
    assert host == "0.0.0.0"
    assert port == 1234
    # Scheduler picks up the plugins; app exposes them via registry.
    assert len(scheduler._entries) > 0
    assert app is not None and app.state.plugins  # at least one plugin registered


def test_assemble_resolves_bind_and_port_from_config(config, monkeypatch):
    monkeypatch.setenv("GLANCES_OUTPUTS__BIND_ADDRESS", "10.0.0.1")
    monkeypatch.setenv("GLANCES_OUTPUTS__PORT", "9999")
    cfg = GlancesConfigV5()
    args = build_parser().parse_args(["-s"])
    _, _, host, port, _tui = assemble(args, cfg)
    assert host == "10.0.0.1"
    assert port == 9999


def test_assemble_falls_back_to_defaults(config):
    args = build_parser().parse_args(["-s"])
    _, _, host, port, _tui = assemble(args, config)
    assert host == "127.0.0.1"
    assert port == 61208


def test_assemble_wires_alerts_into_scheduler(config):
    args = build_parser().parse_args(["-s"])
    _, scheduler, _, _, _tui = assemble(args, config)
    assert scheduler.alerts is not None


def test_assemble_api_doc_cli_override(config):
    args = build_parser().parse_args(["-s", "--no-api-doc"])
    app, _, _, _, _tui = assemble(args, config)
    # /docs disabled → no Swagger route on the app.
    assert app is not None
    routes = [getattr(r, "path", None) for r in app.routes]
    assert "/docs" not in routes


# ---------------------------------------------------------------- mode dispatch (G2)


def test_assemble_default_mode_builds_no_app(config):
    """Without -s, assemble() does not build a FastAPI app (TUI-only mode)."""
    args = build_parser().parse_args([])
    app, scheduler, _host, _port, tui = assemble(args, config)
    assert app is None
    assert tui is not None
    # Scheduler is still wired — the TUI needs it.
    assert scheduler is not None


def test_assemble_server_mode_skips_tui(config):
    """With -s, assemble() returns tui=None (headless per design alignment #1)."""
    args = build_parser().parse_args(["-s"])
    app, _scheduler, _host, _port, tui = assemble(args, config)
    assert app is not None
    assert tui is None


def test_assemble_server_mode_plus_no_tui_is_idempotent(config):
    """-s --quiet behaves like -s (TUI already off in server mode)."""
    args = build_parser().parse_args(["-s", "--quiet"])
    app, _scheduler, _host, _port, tui = assemble(args, config)
    assert app is not None
    assert tui is None


def test_assemble_default_mode_no_tui_disables_everything(config):
    """Default mode + --no-tui: no app AND no tui (scheduler-only, useful for test rigs)."""
    args = build_parser().parse_args(["--no-tui"])
    app, _scheduler, _host, _port, tui = assemble(args, config)
    assert app is None
    assert tui is None


# ---------------------------------------------------------------- MCP overlay (G3-MCP Task 3)


def _has_mcp_mount(app) -> bool:
    from starlette.routing import Mount

    return any(isinstance(r, Mount) and r.path == "/mcp" for r in app.routes)


def test_assemble_server_without_enable_mcp_does_not_mount(config):
    """``-s`` alone: REST API up, but no /mcp mount."""
    args = build_parser().parse_args(["-s"])
    app, _scheduler, _host, _port, _tui = assemble(args, config)
    assert app is not None
    assert not _has_mcp_mount(app)


def test_assemble_propagates_enable_mcp_overlay(config):
    """``-s --enable-mcp``: the CLI flag flips ``[outputs] enable_mcp`` and
    ``attach_mcp`` mounts /mcp."""
    args = build_parser().parse_args(["-s", "--enable-mcp"])
    app, _scheduler, _host, _port, _tui = assemble(args, config)
    assert app is not None
    # The CLI overlay must have set the config gate.
    assert config.get("outputs", "enable_mcp", False) is True
    # And attach_mcp must have honoured it.
    assert _has_mcp_mount(app)


# ----------------------------------------------------------- serve


def test_serve_stops_scheduler_after_uvicorn_returns(config):
    args = build_parser().parse_args(["-s"])
    app, scheduler, host, port, tui = assemble(args, config)

    with patch("uvicorn.Server") as MockServer:
        instance = MockServer.return_value
        instance.serve = AsyncMock(return_value=None)
        # Replace the loops so the test doesn't run real psutil-driven
        # plugin cycles. run_forever returns immediately; stop is a no-op
        # we observe to confirm cleanup is invoked.
        scheduler.run_forever = AsyncMock(return_value=None)  # type: ignore[method-assign]
        scheduler.stop = AsyncMock(return_value=None)  # type: ignore[method-assign]

        asyncio.run(serve(args, app, scheduler, host, port, tui))

        instance.serve.assert_awaited_once()
        scheduler.stop.assert_awaited()


def test_serve_tui_mode_does_not_instantiate_uvicorn(config):
    """Default mode (no -s): serve() must NOT build a uvicorn.Server."""
    args = build_parser().parse_args(["--no-tui"])
    app, scheduler, host, port, tui = assemble(args, config)
    # Sanity: assemble produced no FastAPI app.
    assert app is None

    scheduler.run_forever = AsyncMock(return_value=None)  # type: ignore[method-assign]
    scheduler.stop = AsyncMock(return_value=None)  # type: ignore[method-assign]

    with patch("uvicorn.Server") as MockServer:
        asyncio.run(serve(args, app, scheduler, host, port, tui))
        # The bind-no-socket contract: uvicorn.Server must never be
        # instantiated in TUI mode — otherwise it could open a port.
        MockServer.assert_not_called()

    scheduler.stop.assert_awaited()


def test_importing_main_v5_does_not_pull_the_web_stack():
    """The web stack must stay behind a lazy import.

    `uvicorn` and `glances.webserver_v5` are only reachable from the
    ``args.server`` branches. Importing them at module level cost the TUI
    ~10.8 MB of RSS and ~0.2s of startup CPU for code it never runs.
    Checked in a subprocess: another test in this session may already have
    imported FastAPI, which would mask the regression here.
    """
    code = (
        "import glances.main_v5, sys;"
        "print(sorted(m for m in ('fastapi', 'pydantic', 'starlette', 'uvicorn') if m in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"


# ----------------------------------------------------------- main


def test_main_dispatches_to_set_password(monkeypatch):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "")  # empty → exit 1
    rc = main(["--set-password"])
    assert rc == 1


# ---------------------------------------------------------------- TUI wiring


def test_parser_accepts_no_tui_flag():
    args = build_parser().parse_args(["--no-tui"])
    assert args.no_tui is True


def test_parser_tui_defaults_to_enabled():
    args = build_parser().parse_args([])
    assert args.no_tui is False


def test_parser_percpu_defaults_to_false():
    args = build_parser().parse_args([])
    assert args.percpu is False


def test_parser_percpu_can_be_enabled():
    args = build_parser().parse_args(["--percpu"])
    assert args.percpu is True


def test_parser_full_quicklook_defaults_to_false():
    args = build_parser().parse_args([])
    assert args.full_quicklook is False


def test_parser_full_quicklook_can_be_enabled():
    args = build_parser().parse_args(["--full-quicklook"])
    assert args.full_quicklook is True


def test_assemble_builds_tui_when_enabled(config):
    """assemble() returns a TuiV5 instance when --no-tui is not set."""
    args = build_parser().parse_args([])
    app, scheduler, host, port, tui = assemble(args, config)
    assert tui is not None


def test_assemble_skips_tui_when_no_tui(config):
    """assemble() returns None for the tui slot when --no-tui is set."""
    args = build_parser().parse_args(["--no-tui"])
    app, scheduler, host, port, tui = assemble(args, config)
    assert tui is None


def _tui_args(**overrides):
    """Build an args namespace for assemble(), seeded from the real parser.

    ``--disable-unicode`` is not a v5 parser flag (it lives on v4's parser,
    glances/main.py:658, and reaches v5 via getattr) so it cannot be set
    through parse_args — it is set directly as an attribute override.
    """
    args = build_parser().parse_args([])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def test_assemble_forwards_disable_unicode_to_the_tui(config, monkeypatch):
    """`--disable-unicode` reaches the TUI, otherwise the alert glyphs ignore it.

    ``_TuiV5`` is a *local* import inside ``assemble()`` (curses is only
    needed for the TUI branch), so the patch target is the real class in
    ``glances_curses_v5`` — patching a ``glances.main_v5._TuiV5`` module
    attribute would not reach the local binding.
    """
    captured = {}

    class _FakeTui:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("glances.outputs.glances_curses_v5.TuiV5", _FakeTui)
    args = _tui_args(disable_unicode=True)
    assemble(args, config)
    assert captured["disable_unicode"] is True


def test_assemble_registry_excludes_non_display_plugins(config, monkeypatch):
    """The TUI registry skips plugins with DISPLAY_IN_TUI=False; REST keeps all."""
    from glances.plugins.plugin.base_v5 import GlancesPluginBase

    class _Shown(GlancesPluginBase):
        plugin_name = "shown_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = True

        async def _grab_stats(self):
            return {}

    class _Hidden(GlancesPluginBase):
        plugin_name = "hidden_probe"
        IS_COLLECTION = False
        DISPLAY_IN_TUI = False

        async def _grab_stats(self):
            return {}

    store = StatsStoreV5()
    fakes = [_Shown(store, config), _Hidden(store, config)]
    monkeypatch.setattr("glances.main_v5.discover_plugins", lambda *a, **k: fakes)

    args = build_parser().parse_args([])  # TUI mode (no -s)
    _app, _scheduler, _host, _port, tui = assemble(args, config)

    registry_names = [name for name, _is_coll in tui.registry]
    assert "shown_probe" in registry_names
    assert "hidden_probe" not in registry_names


def test_assemble_tui_registry_shows_displayables_hides_rest_only(config):
    """End-to-end: the real discovered plugins route correctly.

    Displayed trivials (uptime/system/now) appear in the TUI registry;
    REST-only trivials (core/version/psutilversion) do not. All six are
    still discovered (served via REST)."""
    from glances.main_v5 import discover_plugins

    store = StatsStoreV5()
    all_names = {p.plugin_name for p in discover_plugins(store, config)}
    for name in ("uptime", "system", "now", "core", "version", "psutilversion"):
        assert name in all_names, f"{name} not discovered"

    args = build_parser().parse_args([])  # TUI mode
    _app, _scheduler, _host, _port, tui = assemble(args, config)
    registry_names = {name for name, _ in tui.registry}
    for name in ("uptime", "system", "now"):
        assert name in registry_names
    for name in ("core", "version", "psutilversion"):
        assert name not in registry_names


# ------------------------------------------------------ apply_plugin_flags


def test_apply_plugin_flags_disable_sets_overlay(config):
    args = build_parser().parse_args(["--disable-plugin", "cpu,mem"])
    apply_plugin_flags(args, config)
    assert config._merged["cpu"]["disable"] is True
    assert config._merged["mem"]["disable"] is True
    # exactly those two — nothing else got a 'disable' key written.
    for section, opts in config._merged.items():
        if section not in ("cpu", "mem"):
            assert "disable" not in opts


def test_apply_plugin_flags_enable_flips_disabled_by_default(config):
    args = build_parser().parse_args(["--enable-plugin", "npu"])
    apply_plugin_flags(args, config)
    assert config._merged["npu"]["disable"] is False


def test_apply_plugin_flags_enable_wins_on_conflict(config):
    args = build_parser().parse_args(["--disable-plugin", "cpu", "--enable-plugin", "cpu"])
    apply_plugin_flags(args, config)
    assert config._merged["cpu"]["disable"] is False


def test_apply_plugin_flags_disable_all_enable_cpu_leaves_only_cpu(config):
    args = build_parser().parse_args(["--disable-plugin", "all", "--enable-plugin", "cpu"])
    apply_plugin_flags(args, config)
    names = {p.plugin_name for p in discover_plugins(StatsStoreV5(), config)}
    assert names == {"cpu"}


def test_apply_plugin_flags_disable_all_without_enable_exits_2(config):
    args = build_parser().parse_args(["--disable-plugin", "all"])
    with pytest.raises(SystemExit) as excinfo:
        apply_plugin_flags(args, config)
    assert excinfo.value.code == 2


def test_apply_plugin_flags_unknown_disable_name_exits_2_untouched(config):
    args = build_parser().parse_args(["--disable-plugin", "cpu,bogusplugin"])
    with pytest.raises(SystemExit) as excinfo:
        apply_plugin_flags(args, config)
    assert excinfo.value.code == 2
    # Nothing applied before the exit — validation happens for both lists first.
    assert config._merged.get("cpu", {}).get("disable") is None


def test_apply_plugin_flags_unknown_enable_name_exits_2(config):
    args = build_parser().parse_args(["--enable-plugin", "cpuu"])
    with pytest.raises(SystemExit) as excinfo:
        apply_plugin_flags(args, config)
    assert excinfo.value.code == 2


def test_apply_plugin_flags_disabling_processcount_disables_processlist(config):
    args = build_parser().parse_args(["--disable-plugin", "processcount"])
    apply_plugin_flags(args, config)
    assert config._merged["processcount"]["disable"] is True
    assert config._merged["processlist"]["disable"] is True


def test_apply_plugin_flags_enabling_processlist_forces_processcount_enabled(config):
    args = build_parser().parse_args(["--enable-plugin", "processlist"])
    apply_plugin_flags(args, config)
    assert config._merged["processlist"]["disable"] is False
    assert config._merged["processcount"]["disable"] is False


def test_apply_plugin_flags_absent_flags_leave_overlay_untouched(config):
    args = build_parser().parse_args([])
    apply_plugin_flags(args, config)
    for opts in config._merged.values():
        assert "disable" not in opts


# --------------------------------------------- apply_plugin_flags: 'all' coupling (FIX 3)


def test_apply_plugin_flags_disable_all_enable_processlist(config):
    """'all' + --enable-plugin processlist must actually enable processlist.

    Regression: the coupling branch used to key off processcount's
    'all'-expanded disable=True and re-disable processlist AFTER the enable
    pass, no matter what the user asked for.
    """
    args = build_parser().parse_args(["--disable-plugin", "all", "--enable-plugin", "processlist"])
    apply_plugin_flags(args, config)
    assert config._merged["processcount"]["disable"] is False
    assert config._merged["processlist"]["disable"] is False
    # programlist was not explicitly enabled — stays disabled from the 'all' expansion.
    assert config._merged["programlist"]["disable"] is True


def test_apply_plugin_flags_disable_all_enable_programlist(config):
    args = build_parser().parse_args(["--disable-plugin", "all", "--enable-plugin", "programlist"])
    apply_plugin_flags(args, config)
    assert config._merged["processcount"]["disable"] is False
    assert config._merged["programlist"]["disable"] is False
    assert config._merged["processlist"]["disable"] is True


def test_apply_plugin_flags_explicit_processcount_disable_still_cascades(config):
    """An explicit (non-'all') --disable-plugin processcount still cascades to processlist.

    Same scenario as ``test_apply_plugin_flags_disabling_processcount_disables_processlist``
    above — kept here too as one of the four FIX 3 cases the task asks to cover explicitly.
    """
    args = build_parser().parse_args(["--disable-plugin", "processcount"])
    apply_plugin_flags(args, config)
    assert config._merged["processcount"]["disable"] is True
    assert config._merged["processlist"]["disable"] is True
