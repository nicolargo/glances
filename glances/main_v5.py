#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 CLI entrypoint (Phase 1.7).

Assembles the v5 stack:

    config (file overlay + env + CLI)
        ↓
    plugins (auto-discovered from glances.plugins.*.model_v5)
        ↓
    StatsStoreV5
        ↓
    GlancesAlerts (with shell action registered via discover_actions)
        ↓
    AsyncScheduler (drives every plugin's update() loop + alerts ingest)
        ↓
    FastAPI app (build_app + register_plugin per plugin)
        ↓
    uvicorn.Server

The scheduler and uvicorn run concurrently via ``asyncio.gather``. A
SIGINT / SIGTERM cleanly stops uvicorn, which triggers scheduler
shutdown in the ``finally`` block.

Architecture references:
- §1.2  Async plugin update loop (the scheduler)
- §4    REST API server — FastAPI (the app)
- §3.4  GlancesAlerts (ingestion hook in the scheduler loop)
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import importlib
import logging
import os
import pkgutil
import signal
import sys
from typing import TYPE_CHECKING

import uvicorn

import glances.plugins as _plugins_pkg
from glances.actions_v5 import discover_actions
from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import GlancesConfigV5
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.scheduler_v5 import AsyncScheduler
from glances.security_v5 import hash_password, verify_password
from glances.stats_store_v5 import StatsStoreV5
from glances.webserver_v5 import attach_mcp, build_app, register_plugin

if TYPE_CHECKING:
    from fastapi import FastAPI

    from glances.outputs.glances_curses_v5 import TuiV5

logger = logging.getLogger(__name__)

_VERSION = "5.0.0a1"
_DEFAULT_BIND_ADDRESS = "127.0.0.1"
_DEFAULT_PORT = 61208


# --------------------------------------------------------------- argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glances-v5",
        description="Glances v5 — REST monitoring server (Phase 1 alpha).",
    )
    parser.add_argument(
        "-C",
        "--config",
        dest="config_path",
        metavar="<path>",
        help="Path to an additional glances.conf file (overlays system/user defaults).",
    )
    parser.add_argument(
        "--bind",
        dest="bind",
        metavar="<addr>",
        help="Bind address (overrides [outputs] bind_address; default 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        dest="port",
        type=int,
        metavar="<n>",
        help="Listening port (overrides [outputs] port; default 61208).",
    )
    parser.add_argument(
        "--api-doc",
        dest="api_doc",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable Swagger /docs and ReDoc /redoc (overrides [outputs] api_doc).",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug-level logging.",
    )
    parser.add_argument(
        "-s",
        "--server",
        dest="server",
        action="store_true",
        help=(
            "Run as a REST API server (FastAPI on bind_address:port). Headless — "
            "no curses TUI. Without this flag, Glances runs in TUI mode and does not "
            "bind any TCP socket."
        ),
    )
    parser.add_argument(
        "--enable-mcp",
        dest="enable_mcp",
        action="store_true",
        help="Mount the MCP endpoint at /mcp. Requires --server. Off by default.",
    )
    parser.add_argument(
        "--quiet",
        "--no-tui",
        dest="no_tui",
        action="store_true",
        help=(
            "Disable the curses TUI. Kept for backwards compatibility — "
            "prefer --server (-s) for headless REST deployments. "
            "May be repurposed or removed in a future v5 phase."
        ),
    )
    parser.add_argument(
        "--set-password",
        action="store_true",
        help="Generate a PBKDF2 password hash interactively and print it to stdout. Does NOT modify glances.conf.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"Glances {_VERSION}",
    )
    return parser


# --------------------------------------------------------------- validation


def validate_args(args: argparse.Namespace) -> None:
    """Validate cross-flag constraints after argparse parsing.

    - ``--enable-mcp`` is meaningful only in server mode — reject the
      combination ``--enable-mcp`` without ``--server`` so the user gets
      a clear error instead of a silently-ignored flag.
    - ``--server`` + ``--quiet`` is harmless (``-s`` already implies
      headless) but worth a log hint so the user knows ``--quiet`` is
      redundant.

    Calls ``build_parser().error(...)`` on rejection — argparse exits
    the process with status 2 after printing the message to stderr,
    matching the convention used for argparse-native validation.
    """
    if args.enable_mcp and not args.server:
        build_parser().error("--enable-mcp requires --server (-s). MCP is only mounted in REST server mode.")
    if args.server and args.no_tui:
        logger.info("--server (-s) already implies headless operation — the --quiet / --no-tui flag is redundant here.")


# --------------------------------------------------------------- logging


def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    # ``force=True`` resets existing handlers — required when the entrypoint
    # is invoked under pytest or any harness that has already attached a
    # default handler to the root logger.
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )


# --------------------------------------------------------------- discovery


def discover_plugins(store: StatsStoreV5, config: GlancesConfigV5) -> list[GlancesPluginBase]:
    """Auto-discover every concrete v5 plugin under ``glances.plugins.*``.

    Looks for ``glances.plugins.<name>.model_v5`` modules carrying a
    ``PluginModel`` class that subclasses ``GlancesPluginBase``. Defensive
    against broken modules: any failure logs a WARNING and skips. An
    **empty registry is a valid state** — see ``MEMORY.md`` (issue #3548,
    runtime plugin toggling via REST).
    """
    plugins: list[GlancesPluginBase] = []
    seen: set[str] = set()

    for module_info in pkgutil.iter_modules(_plugins_pkg.__path__):
        if not module_info.ispkg:
            continue
        sub_name = module_info.name
        full_name = f"glances.plugins.{sub_name}.model_v5"
        try:
            module = importlib.import_module(full_name)
        except ModuleNotFoundError:
            # Plugin not yet ported to v5 — silent skip.
            continue
        except Exception as e:
            logger.warning("Plugin discovery: import of %s failed (%s) — skipped", full_name, e)
            continue

        cls = getattr(module, "PluginModel", None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, GlancesPluginBase):
            continue

        try:
            instance = cls(store, config)
        except Exception as e:
            logger.warning("Plugin discovery: instantiating %s failed (%s) — skipped", full_name, e)
            continue

        if instance.plugin_name in seen:
            logger.warning(
                "Plugin discovery: duplicate plugin_name %r in %s — skipped",
                instance.plugin_name,
                full_name,
            )
            continue
        seen.add(instance.plugin_name)
        plugins.append(instance)

    return plugins


# --------------------------------------------------------------- set-password


def cli_set_password() -> int:
    """Interactive PBKDF2 hash generator. Prints the hash to stdout.

    Used by operators migrating from v4 (where hashes are not byte-compat
    with v5) or by anyone wiring up Basic Auth for the first time. The
    user pastes the printed value into ``[outputs] password`` of their
    ``glances.conf`` — we never touch the file.
    """
    try:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm:  ")
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.", file=sys.stderr)
        return 1
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if not password:
        print("Empty password rejected.", file=sys.stderr)
        return 1

    stored = hash_password(password)
    # Defensive: confirm the round-trip works before printing.
    if not verify_password(password, stored):
        print("Internal error: hash round-trip failed.", file=sys.stderr)
        return 1

    print()
    print("Paste this value into [outputs] password of your glances.conf:")
    print()
    print(stored)
    print()
    return 0


# --------------------------------------------------------------- assemble


def assemble(
    args: argparse.Namespace, config: GlancesConfigV5
) -> tuple[FastAPI | None, AsyncScheduler, str, int, TuiV5 | None]:
    """Wire every Phase 1 component into a runnable tuple, mode-dispatched.

    Returns ``(app, scheduler, host, port, tui)``:

    - **Server mode** (``args.server`` True): ``app`` is a fully-wired
      ``FastAPI`` instance, ``tui`` is ``None`` (``-s`` is headless per
      G2 design alignment).
    - **TUI mode** (default): ``app`` is ``None`` (no FastAPI app built,
      no socket will be bound), ``tui`` is a ``TuiV5`` thread unless
      ``--no-tui`` is also set (in which case ``tui`` is ``None`` too —
      degenerate "scheduler only" mode useful for test rigs).

    The scheduler, plugin registry, alerts pipeline, host and port are
    always built — they are shared by both modes.
    """
    store = StatsStoreV5()
    actions = discover_actions("glances.actions_v5")
    alerts = GlancesAlerts(config, actions=actions)

    plugins = discover_plugins(store, config)
    if not plugins:
        # Empty registry is a valid state — see project memory note about
        # issue #3548 (runtime plugin toggling). Log + continue.
        logger.warning(
            "No v5 plugins discovered. The server will start with an empty registry; "
            "plugins can be activated later via the REST API (issue #3548)."
        )
    else:
        logger.info("Discovered %d v5 plugins: %s", len(plugins), ", ".join(p.plugin_name for p in plugins))

    scheduler = AsyncScheduler(store, config, alerts=alerts)
    for plugin in plugins:
        scheduler.register(plugin)

    host = args.bind or config.get("outputs", "bind_address", _DEFAULT_BIND_ADDRESS)
    port = args.port or config.get("outputs", "port", _DEFAULT_PORT)

    app: FastAPI | None = None
    tui: TuiV5 | None = None

    if args.server:
        # REST API mode: build the FastAPI app. The TUI is not started —
        # ``-s`` is headless per G2 design alignment point 1.
        if args.api_doc is not None:
            config._merged.setdefault("outputs", {})["api_doc"] = bool(args.api_doc)
        if args.enable_mcp:
            # Flip the MCP gate via the same overlay mechanism used for api_doc.
            # `attach_mcp` reads `[outputs] enable_mcp` from the merged config
            # — no need to pass the flag explicitly through the call chain.
            config._merged.setdefault("outputs", {})["enable_mcp"] = True
        app = build_app(config=config, store=store, alerts=alerts)
        for plugin in plugins:
            register_plugin(app, plugin)
        # Plugin registry is now populated — mount /mcp if the gate is on.
        attach_mcp(app, config=config, store=store, plugins=plugins, alerts=alerts)
    elif not getattr(args, "no_tui", False):
        # TUI mode: no FastAPI app, no uvicorn — only the curses thread
        # reading from the shared StatsStoreV5.
        # Local import — curses is platform-dependent and only needed when the TUI is on.
        from glances.outputs.glances_curses_v5 import TuiV5 as _TuiV5

        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins]
        fields_by_plugin = {p.plugin_name: p._fields for p in plugins}
        refresh = float(config.get("outputs", "tui_refresh_interval", 1.0))
        # When the user quits the TUI via `q`/ESC we must also stop the
        # scheduler, otherwise the process keeps running and the shell
        # prompt stays blocked. SIGINT is delivered to the main thread,
        # raises KeyboardInterrupt inside `asyncio.run(serve(...))`, and
        # `serve`'s `finally` clause cleans up the scheduler.
        tui = _TuiV5(
            store=store,
            alerts=alerts,
            config=config,
            registry=registry,
            fields_by_plugin=fields_by_plugin,
            refresh_interval=refresh,
            on_quit=lambda: os.kill(os.getpid(), signal.SIGINT),
        )

    return app, scheduler, host, int(port), tui


# --------------------------------------------------------------- serve


async def serve(
    args: argparse.Namespace,
    app: FastAPI | None,
    scheduler: AsyncScheduler,
    host: str,
    port: int,
    tui: TuiV5 | None = None,
) -> None:
    """Run the scheduler and the mode-specific runtime concurrently.

    Two modes (mirrors ``assemble`` above):

    - **Server mode** (``args.server``): scheduler + uvicorn. No TUI
      thread is started (``app`` must be a real ``FastAPI`` instance).
    - **TUI mode** (default): scheduler + (optional) TUI thread, no
      uvicorn — no TCP socket is bound. Awaits ``scheduler_task`` until
      SIGINT (raised by the TUI's ``on_quit`` callback or Ctrl-C).
    """
    scheduler_task: asyncio.Task[None] | None = None
    if scheduler._entries:  # type: ignore[attr-defined]
        scheduler_task = asyncio.create_task(scheduler.run_forever())

    if tui is not None:
        tui.start()

    try:
        if args.server:
            assert app is not None, "assemble() must return a FastAPI app when args.server is True"
            uvi_config = uvicorn.Config(
                app,
                host=host,
                port=port,
                log_level="warning",
                access_log=False,
            )
            server = uvicorn.Server(uvi_config)
            await server.serve()
        else:
            # TUI mode: block until the scheduler task is cancelled by
            # SIGINT (TUI quit or Ctrl-C). If no plugins were discovered
            # there is no scheduler_task — wait on a never-set Event so
            # SIGINT is still the only termination signal.
            if scheduler_task is not None:
                with contextlib.suppress(asyncio.CancelledError):
                    await scheduler_task
            else:
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.Event().wait()
    finally:
        if tui is not None:
            tui.stop()
            # Join in a thread executor — never block the event loop.
            await asyncio.to_thread(tui.join, 2.0)
        await scheduler.stop()
        if scheduler_task is not None:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await scheduler_task


# --------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.debug)
    validate_args(args)

    if args.set_password:
        return cli_set_password()

    config = GlancesConfigV5(cli_config_path=args.config_path)
    app, scheduler, host, port, tui = assemble(args, config)

    if args.server:
        logger.info("Starting Glances v5 REST API on http://%s:%d", host, port)
    else:
        logger.info("Starting Glances v5 in TUI mode (no REST API bound).")
    try:
        asyncio.run(serve(args, app, scheduler, host, port, tui))
    except KeyboardInterrupt:
        pass
    finally:
        # Safety net: when the TUI is cleaned up via Ctrl-C, the curses
        # endwin() inside a worker thread sometimes leaves the terminal
        # with the cursor hidden. Re-emit DECTCEM (cursor visible) on
        # stdout — works on every VT100-compatible terminal and is a
        # no-op on dumb terminals.
        if tui is not None and sys.stdout.isatty():
            try:
                sys.stdout.write("\x1b[?25h")
                sys.stdout.flush()
            except OSError:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
