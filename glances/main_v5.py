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
from glances.webserver_v5 import build_app, register_plugin

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
        "--quiet",
        "--no-tui",
        dest="no_tui",
        action="store_true",
        help="Disable the curses TUI (REST API only). Useful for headless / server-mode deployments.",
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
) -> tuple[FastAPI, AsyncScheduler, str, int, TuiV5 | None]:
    """Wire every Phase 1 component into a runnable tuple.

    Also instantiates the curses TUI thread unless ``--no-tui`` is set.
    The TUI is started by `serve()`, not here.
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

    # CLI --api-doc overrides config — apply via env-style overlay so
    # build_app picks it up from a single source of truth.
    if args.api_doc is not None:
        config._merged.setdefault("outputs", {})["api_doc"] = bool(args.api_doc)

    app = build_app(config=config, store=store, alerts=alerts)
    for plugin in plugins:
        register_plugin(app, plugin)

    scheduler = AsyncScheduler(store, config, alerts=alerts)
    for plugin in plugins:
        scheduler.register(plugin)

    host = args.bind or config.get("outputs", "bind_address", _DEFAULT_BIND_ADDRESS)
    port = args.port or config.get("outputs", "port", _DEFAULT_PORT)

    tui: TuiV5 | None = None
    if not getattr(args, "no_tui", False):
        # Local import — curses is platform-dependent and only needed when the TUI is on.
        from glances.outputs.glances_curses_v5 import TuiV5 as _TuiV5

        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins]
        fields_by_plugin = {p.plugin_name: p._fields for p in plugins}
        refresh = float(config.get("outputs", "tui_refresh_interval", 1.0))
        # When the user quits the TUI via `q`/ESC we must also stop uvicorn,
        # otherwise the process keeps running and the shell prompt stays
        # blocked until Ctrl-C. SIGINT is delivered to the main thread,
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
    app: FastAPI,
    scheduler: AsyncScheduler,
    host: str,
    port: int,
    tui: TuiV5 | None = None,
) -> None:
    """Run scheduler, uvicorn, and (optionally) the TUI thread concurrently."""
    scheduler_task: asyncio.Task[None] | None = None
    if scheduler._entries:  # type: ignore[attr-defined]
        scheduler_task = asyncio.create_task(scheduler.run_forever())

    if tui is not None:
        tui.start()

    uvi_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(uvi_config)
    try:
        await server.serve()
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

    if args.set_password:
        return cli_set_password()

    config = GlancesConfigV5(cli_config_path=args.config_path)
    app, scheduler, host, port, tui = assemble(args, config)

    logger.info("Starting Glances v5 REST API on http://%s:%d", host, port)
    try:
        asyncio.run(serve(app, scheduler, host, port, tui))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
