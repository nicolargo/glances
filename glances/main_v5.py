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
import tracemalloc
from typing import TYPE_CHECKING

import glances.exports as _exports_pkg
import glances.plugins as _plugins_pkg
from glances.actions_v5 import discover_actions
from glances.alerts_v5 import GlancesAlerts
from glances.config_v5 import ConfigFileError, GlancesConfigV5
from glances.exports.export_base_v5 import GlancesExportBase
from glances.history_v5 import HistoryStoreV5, resolve_history_size
from glances.plugins.plugin.base_v5 import GlancesPluginBase
from glances.processes import glances_processes, sort_processes_stats_list
from glances.scheduler_v5 import AsyncScheduler
from glances.security_v5 import hash_password, verify_password
from glances.stats_store_v5 import StatsStoreV5

# Shell completion (`--print-completion`), v4 parity (`main.py:17-22`). Optional:
# shtab is not installed on Windows, and the option is then simply absent.
try:
    import shtab
except ImportError:
    shtab = None

if TYPE_CHECKING:
    from fastapi import FastAPI

    from glances.outputs.glances_curses_v5 import TuiV5

logger = logging.getLogger(__name__)

_VERSION = "5.0.0a1"
_DEFAULT_BIND_ADDRESS = "127.0.0.1"
_DEFAULT_PORT = 61208


# --------------------------------------------------------------- argparse


def stdout_requested(args: argparse.Namespace) -> bool:
    """True when one of the `--stdout*` outputs replaces the TUI."""
    return bool(
        getattr(args, "stdout", None) or getattr(args, "stdout_json", None) or getattr(args, "stdout_csv", None)
    )


def _global_refresh(config: GlancesConfigV5) -> float:
    """`[global] refresh`, else its `refresh_time` alias -- the scheduler's order."""
    value = config.get("global", "refresh", -1.0)
    if not (isinstance(value, (int, float)) and value > 0):
        value = config.get("global", "refresh_time", 2.0)
    return float(value)


def modules_list() -> str:
    """`--modules-list` (v4 `standalone.py:122-125`): every plugin and exporter, enabled or not.

    Exporters are found by module name, without importing them: an optional
    client library that is not installed must not hide the exporter from a
    listing whose purpose is to say what exists.
    """
    from glances import exports as _exports_pkg

    plugins = sorted(cls.plugin_name for _, cls in discover_plugin_classes())
    exporters = sorted(
        info.name.removeprefix("glances_")
        for root in _exports_pkg.__path__
        for info in pkgutil.iter_modules([root])
        if info.ispkg
        and info.name.startswith("glances_")
        and os.path.isfile(os.path.join(root, info.name, "export_v5.py"))
    )
    return f"Plugins list: {', '.join(plugins)}\nExporters list: {', '.join(exporters)}"


def open_web_ui(host: str, port: int) -> None:
    """`--open-web-browser` (v4 issue #946): open the Web UI in a new tab.

    A wildcard bind address is not somewhere a browser can go, so it is
    opened as localhost. Best effort: no browser is not an error.
    """
    import webbrowser

    target = "localhost" if host in ("0.0.0.0", "::", "") else host
    if ":" in target:
        target = f"[{target}]"
    try:
        webbrowser.open(f"http://{target}:{port}/", new=2, autoraise=True)
    except webbrowser.Error as exc:
        logger.warning("--open-web-browser: could not open a browser (%s)", exc)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="glances-v5",
        description="Glances v5 — REST monitoring server (Phase 1 alpha).",
    )
    if shtab is not None:
        shtab.add_argument_to(parser, ["--print-completion"])
    config_arg = parser.add_argument(
        "-C",
        "--config",
        dest="config_path",
        metavar="<path>",
        help="Path to an additional glances.conf file (overlays system/user defaults).",
    )
    if shtab is not None:
        # Complete `-C` with file names, as v4 does.
        config_arg.complete = shtab.FILE
    parser.add_argument(
        "-B",
        "--bind",
        dest="bind",
        metavar="<addr>",
        help="Bind address (overrides [outputs] bind_address; default 127.0.0.1).",
    )
    parser.add_argument(
        "-p",
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
        # v4's web server mode (`-w`, REST + Web UI) IS v5's server mode; v4's
        # `-s` (XML-RPC) has no v5 equivalent, so both spellings land here.
        "-w",
        "--webserver",
        dest="server",
        action="store_true",
        help=(
            "Run as a REST API server (FastAPI on bind_address:port) and serve the "
            "Web UI. Headless — no curses TUI. Without this flag, Glances runs in "
            "TUI mode and does not bind any TCP socket. Use --disable-webui for a "
            "headless REST-only deployment. -w/--webserver is the v4 spelling."
        ),
    )
    parser.add_argument(
        "--disable-webui",
        action="store_true",
        help="Serve the REST API without the Web UI (requires --server).",
    )
    parser.add_argument(
        "--enable-mcp",
        dest="enable_mcp",
        action="store_true",
        help="Mount the MCP endpoint at /mcp. Requires --server. Off by default.",
    )
    parser.add_argument(
        "--export",
        dest="export",
        metavar="<a,b>",
        help="Enable export modules (comma-separated list, e.g. csv,influxdb2).",
    )
    parser.add_argument(
        "--export-csv-file",
        dest="export_csv_file",
        default="./glances.csv",
        metavar="<path>",
        help="File path for the CSV exporter (default ./glances.csv).",
    )
    parser.add_argument(
        "--export-csv-overwrite",
        dest="export_csv_overwrite",
        action="store_true",
        help="Overwrite the CSV file instead of appending to it.",
    )
    parser.add_argument(
        "--export-json-file",
        dest="export_json_file",
        default="./glances.json",
        metavar="<path>",
        help="File path for the JSON exporter (default ./glances.json).",
    )
    parser.add_argument(
        "--export-process-filter",
        default=None,
        type=str,
        dest="export_process_filter",
        help="set the export process filter (comma-separated list of regular expression)",
    )
    parser.add_argument(
        "--disable-plugin",
        "--disable-plugins",
        "--disable",
        dest="disable_plugin",
        metavar="<a,b>",
        help="Disable plugin (comma-separated list or 'all'). If 'all' is used, "
        "then you need to configure --enable-plugin.",
    )
    parser.add_argument(
        "--enable-plugin",
        "--enable-plugins",
        "--enable",
        dest="enable_plugin",
        metavar="<a,b>",
        help="Enable plugin (comma-separated list).",
    )
    parser.add_argument(
        "-q",
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
        "-1",
        "--percpu",
        "--per-cpu",
        dest="percpu",
        action="store_true",
        default=False,
        help="Start TUI with the per-CPU view in quicklook.",
    )
    parser.add_argument(
        "-4",
        "--full-quicklook",
        dest="full_quicklook",
        action="store_true",
        default=False,
        help="Start TUI with the full-width quicklook (hides cpu/mem/... top blocks).",
    )
    parser.add_argument(
        "-6",
        "--meangpu",
        dest="meangpu",
        action="store_true",
        default=False,
        help="Show a single mean GPU summary instead of per-GPU lines.",
    )
    parser.add_argument(
        "-t",
        "--time",
        dest="time",
        type=float,
        default=None,
        metavar="<sec>",
        help="Refresh rate in seconds (overrides [global] refresh; default 2).",
    )
    parser.add_argument(
        "--strftime",
        dest="strftime_format",
        default=None,
        metavar="<format>",
        help="strftime format for the current date (overrides [global] strftime_format).",
    )
    parser.add_argument(
        "--diskio-iops",
        dest="diskio_iops",
        action="store_true",
        default=False,
        help="Display disk I/O operations per second instead of byte rates. Toggle live with B.",
    )
    parser.add_argument(
        "--process-short-name",
        dest="process_short_name",
        action="store_true",
        default=True,
        help="Show the short process name in the command column (default). Toggle live with /.",
    )
    parser.add_argument(
        "--process-long-name",
        dest="process_short_name",
        action="store_false",
        help="Show the full command line in the command column. Toggle live with /.",
    )
    # v4's startup visibility flags. Each one is a set of SHOW/HIDE keys
    # pressed before the first frame (`TuiV5._STARTUP_HIDE_KEYS`, mirrored by
    # the WebUI), so the key itself brings the block back, as in v4.
    parser.add_argument(
        "-2",
        "--disable-left-sidebar",
        dest="disable_left_sidebar",
        action="store_true",
        default=False,
        help="Start with the left sidebar hidden (network, disk I/O, FS, sensors...). Toggle with 2.",
    )
    parser.add_argument(
        "-3",
        "--disable-quicklook",
        dest="disable_quicklook",
        action="store_true",
        default=False,
        help="Start with quicklook hidden. Toggle with 3.",
    )
    parser.add_argument(
        "-5",
        "--disable-top",
        dest="disable_top",
        action="store_true",
        default=False,
        help="Start with the top menu hidden (quicklook, CPU, MEM, SWAP, LOAD). Toggle with 5.",
    )
    parser.add_argument(
        "--disable-process",
        dest="disable_process",
        action="store_true",
        default=False,
        help="Start with the process blocks hidden. Toggle with z. "
        "Use --disable-plugin processcount to stop collecting them.",
    )
    parser.add_argument(
        "--light",
        "--enable-light",
        dest="enable_light",
        action="store_true",
        default=False,
        help="Light mode: start with only the top menu (hides the left sidebar, processes, alerts, AMPs, "
        "containers and VMs).",
    )
    parser.add_argument(
        "--enable-irq",
        dest="enable_irq",
        action="store_true",
        default=False,
        help="Enable the IRQ plugin (same as --enable-plugin irq).",
    )
    parser.add_argument(
        "-0",
        "--disable-irix",
        dest="load_irix",
        action="store_true",
        default=False,
        help="Irix mode: show the load average as a percentage of the CPU cores. Toggle with 0.",
    )
    parser.add_argument(
        "--hide-kernel-threads",
        dest="no_kernel_threads",
        action="store_true",
        default=False,
        help="Hide kernel threads in the process list (not available on Windows).",
    )
    parser.add_argument(
        "--diskio-show-ramfs",
        dest="diskio_show_ramfs",
        action="store_true",
        default=False,
        help="Show RAM disks (ram*) in the disk I/O plugin (hidden by default). Config: [diskio] show_ramfs.",
    )
    parser.add_argument(
        "--disable-bold",
        dest="disable_bold",
        action="store_true",
        default=False,
        help="Disable bold text in the curses interface.",
    )
    parser.add_argument(
        "--disable-bg",
        dest="disable_bg",
        action="store_true",
        default=False,
        help="Disable background colours in the curses interface. Config fallback: [outputs] disable_bg.",
    )
    parser.add_argument(
        "--disable-separator",
        dest="disable_separator",
        action="store_true",
        default=False,
        help="Disable the separator lines in the curses interface. Config fallback: [outputs] separator.",
    )
    parser.add_argument(
        "--stdout",
        dest="stdout",
        default=None,
        metavar="<plugin[.key].attr,...>",
        help="Print stats to stdout, one line per stat and refresh (e.g. cpu.user,mem.percent,network,all). No TUI.",
    )
    parser.add_argument(
        "--stdout-json",
        dest="stdout_json",
        default=None,
        metavar="<plugin,...>",
        help="Print the selected plugins' stats to stdout as one JSON object per refresh. No TUI.",
    )
    parser.add_argument(
        "--stdout-csv",
        dest="stdout_csv",
        default=None,
        metavar="<plugin[.attr],...>",
        help="Print the selected stats to stdout as CSV: a header line, then one line per refresh. No TUI.",
    )
    parser.add_argument(
        "--memory-leak",
        dest="memory_leak",
        action="store_true",
        default=False,
        help=(
            "Test for memory leaks and exit: collect for --stop-after seconds (default 60) to warm up, "
            "then as long again, and print the memory growth between the two."
        ),
    )
    parser.add_argument(
        "--stop-after",
        dest="stop_after",
        type=int,
        default=None,
        metavar="<n>",
        help="Stop after n refreshes (TUI and stdout modes).",
    )
    parser.add_argument(
        "--open-web-browser",
        dest="open_web_browser",
        action="store_true",
        default=False,
        help="Open the Web UI in the default web browser at startup (requires --server).",
    )
    parser.add_argument(
        "--modules-list",
        "--module-list",
        dest="modules_list",
        action="store_true",
        default=False,
        help="Print the plugin and exporter lists and exit.",
    )
    parser.add_argument(
        "--sort-processes",
        dest="sort_processes_key",
        choices=sort_processes_stats_list,
        help='Sort processes by: {}'.format(', '.join(sort_processes_stats_list)),
    )
    parser.add_argument(
        "--programs",
        "--program",
        action="store_true",
        default=False,
        dest="programs",
        help="Accumulate processes by program",
    )
    parser.add_argument(
        "--fahrenheit",
        dest="fahrenheit",
        action="store_true",
        default=False,
        help="Display temperatures in Fahrenheit (default: Celsius).",
    )
    parser.add_argument(
        "--hide-public-info",
        dest="hide_public_info",
        action="store_true",
        default=False,
        help="Mask the last two octets of the public IP address in the TUI (a.b.c.d -> a.b.*.*).",
    )
    parser.add_argument(
        "-b",
        "--byte",
        dest="byte",
        action="store_true",
        default=False,
        help="Display network rate in bytes per second (default: bits per second).",
    )
    parser.add_argument(
        "--diskio-latency",
        dest="diskio_latency",
        action="store_true",
        default=False,
        help="Display disk I/O latency (ms per read/write operation) instead of byte rates. Toggle live with L.",
    )
    parser.add_argument(
        "--fs-free-space",
        dest="fs_free_space",
        action="store_true",
        default=False,
        help="Display filesystem free space instead of used space (default: used). Config fallback: [fs] free_space.",
    )
    parser.add_argument(
        "--disable-history",
        dest="disable_history",
        action="store_true",
        default=False,
        help="disable the stats history (same as [global] history_size=0)",
    )
    parser.add_argument(
        "--disable-unicode",
        dest="disable_unicode",
        action="store_true",
        default=False,
        help="disable unicode characters in the curses interface",
    )
    parser.add_argument(
        "-f",
        "--process-filter",
        dest="process_filter",
        default=None,
        type=str,
        help="set the process filter pattern (regular expression); TUI mode only",
    )
    parser.add_argument(
        "--process-focus",
        dest="process_focus",
        default=None,
        type=str,
        help="set a process list to focus on (comma-separated list of Glances filters); TUI mode only. "
        "Config fallback: [processlist] focus.",
    )
    parser.add_argument(
        "--arrow-keys-sort",
        dest="arrow_keys_sort",
        action="store_true",
        default=False,
        help="use the arrow keys to step the process sort, and SHIFT+arrows to scroll the command column "
        "(the default is the other way round)",
    )
    parser.add_argument(
        "--disable-cursor",
        dest="disable_cursor",
        action="store_true",
        default=False,
        help="disable the process-selection cursor (UP/DOWN) in the curses interface",
    )
    parser.add_argument(
        "--disable-config-exec",
        dest="disable_config_exec",
        action="store_true",
        default=False,
        help="Disable shell operator interpretation (&&, |, >) in the on-alert action "
        "commands read from glances.conf (recommended for system services).",
    )
    parser.add_argument(
        "--set-password",
        action="store_true",
        help="Generate a PBKDF2 password hash interactively and print it to stdout. Does NOT modify glances.conf.",
    )
    parser.add_argument(
        "-V",
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
    # The stdout outputs replace the TUI (v4: standalone only), so they cannot
    # share a run with the server, and one run prints one format.
    chosen = [name for name in ("stdout", "stdout_json", "stdout_csv") if getattr(args, name, None)]
    if chosen and args.server:
        build_parser().error("--stdout, --stdout-json and --stdout-csv cannot be combined with --server (-s).")
    if len(chosen) > 1:
        build_parser().error("Use only one of --stdout, --stdout-json and --stdout-csv.")
    if getattr(args, "open_web_browser", False) and (not args.server or args.disable_webui):
        build_parser().error("--open-web-browser requires --server (-s) with the Web UI enabled.")
    if getattr(args, "stop_after", None) is not None and args.stop_after <= 0:
        build_parser().error("--stop-after needs a positive number of refreshes.")
    if getattr(args, "memory_leak", False) and (args.server or chosen):
        build_parser().error("--memory-leak runs on its own: it cannot be combined with --server or --stdout*.")


# --------------------------------------------------------------- logging


def _console_handlers() -> list[logging.StreamHandler]:
    """The root handlers that write to a stream rather than a file.

    ``FileHandler`` subclasses ``StreamHandler``, so the rotating file handler
    has to be excluded explicitly or it matches here too — and lowering *its*
    level is not what any caller means by "the console".
    """
    root = logging.getLogger()
    return [h for h in root.handlers if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)]


def setup_logging(debug: bool, server: bool = False) -> None:
    """Configure logging from v4's own configuration: a rotating file handler
    that takes everything, plus a console handler whose level depends on
    whether a curses TUI is going to own the terminal.

    **In TUI mode the console threshold is not a preference, it is a
    correctness requirement.** stderr *is* the terminal curses is painting, so
    a single WARNING scrolls the screen and desynchronises ncurses' model of
    it — text bleeds across columns and the display stays corrupted until the
    next full repaint. v4 avoids this by pinning the console to CRITICAL and
    sending the real log to a file; v5 used to call ``logging.basicConfig()``,
    whose default handler writes every INFO and WARNING straight to that
    terminal.

    ``server`` (``-s``) has no curses to protect, so there the console carries
    the normal log — INFO, or DEBUG under ``--debug``. **This is a deliberate
    v4 divergence** (maintainer's call, 2026-09-22): v4 keeps the console at
    CRITICAL in every mode, which leaves an operator running a foreground
    server, or reading ``docker logs``, with a silent process.

    ``--quiet`` / ``--no-tui`` also runs without curses, but keeps the quiet
    console its name promises. Only ``-s`` opts into the verbose one.

    ``glances.logger`` is the single source of truth for the file location
    (XDG-aware, `$LOG_CFG` override, rotation at 1 MB × 3), for the handler
    set and for the formats — all reused, none duplicated here. It is already
    in the process, since shared v4 modules import it; calling
    ``glances_logger()`` re-applies it, which also makes this idempotent and
    keeps what ``force=True`` was there for: ``dictConfig`` replaces the root
    handler list outright, so a handler a harness (pytest) attached after the
    import is dropped.

    ``debug`` raises the *root* level, exactly like v4's ``init_debug``
    (``glances/main.py:710-714``).
    """
    # Local import: this applies the logging configuration as a side effect,
    # so it must not run at module import time in a library context.
    from glances.logger import LOGGING_CFG, glances_logger

    glances_logger()
    level = logging.DEBUG if debug else logging.INFO
    logging.getLogger().setLevel(level)

    if not server:
        return
    # Server mode: the console becomes the log. v4's `console` handler carries
    # the `free` format (bare `%(message)s`), which is right for the CRITICAL
    # death-rattle it normally is, but drops the severity from a stream an
    # operator now reads as a log. Promote it to v4's own `standard` format
    # rather than inventing one.
    fmt = logging.Formatter(LOGGING_CFG["formatters"]["standard"]["format"])
    for handler in _console_handlers():
        handler.setLevel(level)
        handler.setFormatter(fmt)


# --------------------------------------------------------------- discovery


def discover_plugin_classes() -> list[tuple[str, type[GlancesPluginBase]]]:
    """Return every concrete v5 ``PluginModel`` class, unfiltered.

    Looks for ``glances.plugins.<name>.model_v5`` modules carrying a
    ``PluginModel`` class that subclasses ``GlancesPluginBase``. Defensive
    against broken modules: any failure logs a WARNING and skips.

    Split out of ``discover_plugins()`` so that the class catalogue stays
    available independently of what is currently instantiated — the entry
    point a future runtime toggle (issue #3548) needs to bring a disabled
    plugin up without restarting the process.
    """
    classes: list[tuple[str, type[GlancesPluginBase]]] = []

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

        classes.append((full_name, cls))

    return classes


def discover_plugins(store: StatsStoreV5, config: GlancesConfigV5) -> list[GlancesPluginBase]:
    """Instantiate every discovered v5 plugin that is not disabled.

    A plugin whose ``[<plugin_name>] disable`` resolves to true is NOT
    instantiated at all: some plugins do real work in ``__init__``
    (``ports`` builds its scan list and starts a background thread), so
    gating inside ``_grab_stats()`` would be too late. An **empty registry
    is a valid state** — see ``MEMORY.md`` (issue #3548, runtime plugin
    toggling via REST); ``discover_plugin_classes()`` keeps the full
    catalogue reachable for a later re-enable.
    """
    plugins: list[GlancesPluginBase] = []
    seen: set[str] = set()

    for full_name, cls in discover_plugin_classes():
        if cls.is_disabled(config):
            logger.debug("Plugin discovery: %s disabled by config — not instantiated", cls.plugin_name or full_name)
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


def apply_process_flags(args: argparse.Namespace) -> None:
    """Apply ``--sort-processes`` to the ``glances_processes`` engine singleton.

    v4 parity (`glances/plugins/processlist/__init__.py:235-236`): v4 applies
    this on every plugin `update()` call; v5 applies it once here, at startup,
    since the engine singleton retains the setting across cycles (the TUI's
    `j`/sort hotkeys are the only thing that can change it afterwards).

    ``auto=False`` is deliberate (v4 parity): an explicit CLI key turns OFF
    the auto-sort that would otherwise re-pick the key from the dominant
    active alert each cycle (see ``GlancesAlerts._auto_sort_key``, which
    calls ``set_sort_key(key, auto=True)``).
    """
    if getattr(args, "sort_processes_key", None) is not None:
        glances_processes.set_sort_key(args.sort_processes_key, False)


def apply_export_flags(args: argparse.Namespace) -> None:
    """Expand ``--export a,b`` into ``args.export_a = True`` booleans.

    v4 parity (`glances/main.py:755`): each exporter reads its own
    ``args.export_<name>`` rather than parsing the list itself.
    """
    if not getattr(args, "export", None):
        return
    for name in args.export.split(","):
        name = name.strip()
        if name:
            setattr(args, f"export_{name}", True)


def apply_plugin_flags(args: argparse.Namespace, config: GlancesConfigV5) -> None:
    """Overlay ``--disable-plugin`` / ``--enable-plugin`` onto the config.

    v4 parity (`glances/main.py:730-770`, ``init_plugins``): v5 does not
    introduce a new gating mechanism — ``GlancesPluginBase.is_disabled()``
    already reads ``[<plugin>] disable`` from the merged config, so this
    writes into the same overlay dict used by ``--disable-config-exec`` /
    ``--api-doc`` / ``--enable-mcp``.

    Must run BEFORE ``discover_plugins()`` reads the overlay. Deliberate
    divergence from v4: an unknown plugin name is FATAL here (v4 silently
    accepted typos and did nothing).
    """
    # `--enable-irq` (v4 `main.py:320`) is `--enable-plugin irq` by another
    # name: the plugin is disabled by default and this is its one switch.
    if getattr(args, "enable_irq", False):
        args.enable_plugin = ",".join(filter(None, [args.enable_plugin, "irq"]))
    if args.disable_plugin is None and args.enable_plugin is None:
        return

    known_names = {cls.plugin_name for _, cls in discover_plugin_classes()}

    disable_names = [p.strip() for p in args.disable_plugin.split(",")] if args.disable_plugin else []
    enable_names = [p.strip() for p in args.enable_plugin.split(",")] if args.enable_plugin else []
    # Snapshot the EXPLICIT --disable-plugin request before 'all' is expanded
    # below — the processcount/processlist coupling must key off what the
    # user actually typed, not off the expanded list (which would otherwise
    # make 'all' silently drag processcount into the coupling check and
    # re-disable an explicitly --enable-plugin'd processlist/programlist).
    explicit_disable_names = set(disable_names)

    # Validate BOTH lists before applying anything, so a typo cannot leave
    # a half-applied configuration. 'all' is a keyword, not a plugin name.
    for name in [*disable_names, *enable_names]:
        if name != "all" and name not in known_names:
            logger.critical("Unknown plugin %r passed to --disable-plugin/--enable-plugin", name)
            sys.exit(2)

    if "all" in disable_names:
        if not args.enable_plugin:
            logger.critical("'all' key in --disable-plugin needs to be used with --enable-plugin")
            sys.exit(2)
        logger.info("'all' key in --disable-plugin, only plugins defined with --enable-plugin will be available")
        disable_names = list(known_names)

    # Apply disables first, then enables — enable wins on conflict (v4 semantics).
    for name in disable_names:
        config._merged.setdefault(name, {})["disable"] = True
    for name in enable_names:
        config._merged.setdefault(name, {})["disable"] = False

    # Processlist is updated in processcount (v4 parity, main.py:765-770).
    # Keyed on the EXPLICIT disable request (not the 'all'-expanded list) so
    # that '--disable-plugin all --enable-plugin processlist' (or programlist)
    # does not get processcount's expansion-only disable re-disabling the
    # plugin the user just asked to enable.
    if "processcount" in explicit_disable_names and "processcount" not in enable_names:
        logger.warning("Processcount is disabled, so processlist (updated by processcount) is also disabled")
        config._merged.setdefault("processlist", {})["disable"] = True
    elif "processlist" in enable_names or "programlist" in enable_names:
        config._merged.setdefault("processcount", {})["disable"] = False


def discover_exporters(config: GlancesConfigV5, args: argparse.Namespace) -> list[GlancesExportBase]:
    """Instantiate every exporter the user asked for on the command line.

    Looks for ``glances.exports.glances_<name>.export_v5`` modules carrying
    an ``Export`` class. A module whose optional client library is missing
    raises ImportError: that is FATAL when the user asked for it (they
    passed ``--export influxdb2`` and deserve to know the library is not
    installed), and invisible when they did not.
    """
    exporters: list[GlancesExportBase] = []

    for module_info in pkgutil.iter_modules(_exports_pkg.__path__):
        if not module_info.ispkg or not module_info.name.startswith("glances_"):
            continue
        name = module_info.name[len("glances_") :]
        if not getattr(args, f"export_{name}", False):
            continue

        full_name = f"glances.exports.{module_info.name}.export_v5"
        try:
            module = importlib.import_module(full_name)
        except ImportError as e:
            logger.critical("Export %s requested but unavailable (%s)", name, e)
            sys.exit(2)

        cls = getattr(module, "Export", None)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, GlancesExportBase):
            logger.critical("Export %s: module %s has no usable Export class", name, full_name)
            sys.exit(2)

        exporters.append(cls(config, args))
        logger.info("Export module %s enabled", name)

    return exporters


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


def attach_history(plugins: list[GlancesPluginBase], config: GlancesConfigV5, args: argparse.Namespace) -> None:
    """Give every plugin the one shared stats history store (design 2026-09-26).

    No store at all when `[global] history_size=0` or `--disable-history`:
    each plugin then skips recording outright.
    """
    size = resolve_history_size(config, getattr(args, "disable_history", False))
    history = HistoryStoreV5(size) if size > 0 else None
    for plugin in plugins:
        plugin.history = history


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
    if args.disable_config_exec:
        # Flip the hardening gate via the same overlay mechanism used for
        # api_doc / enable_mcp. Applied before the actions are built, and
        # outside the `--server` branch: the flag must hold in TUI mode too.
        # One-way: the CLI can only harden, never relax a config that already
        # sets the key (CVE-2026-68519).
        config._merged.setdefault("global", {})["disable_config_exec"] = True
    # `-t` / `--strftime`: the same overlay, before the scheduler and the
    # plugins read them. `[global] refresh` is what the scheduler and the TUI
    # cadence resolve first; `now` reads `strftime_format` at construction.
    if getattr(args, "time", None) is not None:
        if args.time > 0:
            config._merged.setdefault("global", {})["refresh"] = float(args.time)
        else:
            logger.warning("Ignoring -t/--time %s: the refresh rate must be > 0", args.time)
    # `--diskio-show-ramfs` (v4 `diskio/__init__.py:154`): the plugin reads
    # its own section, as `--fs-free-space` does for fs.
    if getattr(args, "diskio_show_ramfs", False):
        config._merged.setdefault("diskio", {})["show_ramfs"] = True
    # `--hide-kernel-threads` (v4 `standalone.py:73-75`): an operator choice on
    # what the engine collects, so it holds in server mode too (v4's webserver
    # applies it as well) -- unlike the filters a TUI user types.
    if getattr(args, "no_kernel_threads", False) and not sys.platform.startswith("win"):
        glances_processes.disable_kernel_threads()
    if getattr(args, "strftime_format", None):
        config._merged.setdefault("global", {})["strftime_format"] = args.strftime_format
    if getattr(args, "export_process_filter", None):
        # Same overlay mechanism as disable_config_exec / api_doc / enable_mcp.
        # CLI wins over `[processlist] export` from the config file (v4
        # parity, issue #794). Must run before discover_plugins() below —
        # processlist/programlist compile this filter in __init__.
        config._merged.setdefault("processlist", {})["export"] = args.export_process_filter
    if getattr(args, "fs_free_space", False):
        # Same overlay mechanism as disable_config_exec / api_doc / enable_mcp.
        # CLI wins over `[fs] free_space` (v4 parity, `main.py:832`
        # `init_ui_mode`, design §5.4). Must run before discover_plugins()
        # below — the fs plugin reads `free_space` in `__init__`.
        config._merged.setdefault("fs", {})["free_space"] = True
    actions = discover_actions("glances.actions_v5", config)
    # Wire the process engine so the alert pipeline can drive the dynamic
    # process auto-sort (v4 parity) — the sort key follows the dominant
    # active alert (MEM → memory_percent, CPU iowait → io_counters).
    # `glances_processes` is the same singleton imported at module level.
    alerts = GlancesAlerts(config, actions=actions, process_engine=glances_processes)

    apply_plugin_flags(args, config)
    apply_process_flags(args)
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

    attach_history(plugins, config, args)

    scheduler = AsyncScheduler(store, config, alerts=alerts)
    for plugin in plugins:
        scheduler.register(plugin)

    apply_export_flags(args)
    for exporter in discover_exporters(config, args):
        scheduler.register_exporter(exporter)

    host = args.bind or config.get("outputs", "bind_address", _DEFAULT_BIND_ADDRESS)
    port = args.port or config.get("outputs", "port", _DEFAULT_PORT)

    app: FastAPI | None = None
    tui: TuiV5 | None = None

    if args.server:
        # REST API mode: build the FastAPI app. The TUI is not started —
        # ``-s`` is headless per G2 design alignment point 1.
        # Local import — pulling FastAPI/pydantic in costs ~9 MB of RSS and
        # ~0.14s of CPU, and the TUI mode below never touches any of it.
        from glances.webserver_v5 import attach_mcp, build_app, register_plugin

        if args.api_doc is not None:
            config._merged.setdefault("outputs", {})["api_doc"] = bool(args.api_doc)
        if args.enable_mcp:
            # Flip the MCP gate via the same overlay mechanism used for api_doc.
            # `attach_mcp` reads `[outputs] enable_mcp` from the merged config
            # — no need to pass the flag explicitly through the call chain.
            config._merged.setdefault("outputs", {})["enable_mcp"] = True
        app = build_app(config=config, store=store, alerts=alerts, args=args)
        for plugin in plugins:
            register_plugin(app, plugin)
        # Plugin registry is now populated — mount /mcp if the gate is on.
        attach_mcp(app, config=config, store=store, plugins=plugins, alerts=alerts)
    elif stdout_requested(args):
        # `--stdout*` (v4 `glances/outputs/glances_stdout*.py`): the printer
        # takes the TUI's place and lifecycle, so `serve` needs no new branch.
        from glances.outputs.stdout_v5 import StdoutV5

        tui = StdoutV5(
            plugins=plugins,
            refresh_interval=_global_refresh(config),
            stdout=args.stdout,
            stdout_json=args.stdout_json,
            stdout_csv=args.stdout_csv,
            stop_after=getattr(args, "stop_after", None),
            on_quit=lambda: os.kill(os.getpid(), signal.SIGINT),
        )
    elif not getattr(args, "no_tui", False):
        # TUI mode: no FastAPI app, no uvicorn — only the curses thread
        # reading from the shared StatsStoreV5.
        # Local import — curses is platform-dependent and only needed when the TUI is on.
        from glances.outputs.glances_curses_v5 import STARTUP_HIDE_KEYS
        from glances.outputs.glances_curses_v5 import TuiV5 as _TuiV5

        # `-f/--process-filter` (v4 `main.py:513-519`). Applied here and not
        # in server mode: `glances_processes.process_filter` is global to the
        # process, and a server-wide filter would silently narrow what every
        # REST client sees -- v4 logs "only available in standalone mode" for
        # the same reason (`main.py:150-152`). The `ENTER` hotkey writes this
        # same property.
        if getattr(args, "process_filter", None):
            glances_processes.process_filter = args.process_filter
            if glances_processes.process_filter is None:
                logger.error("Invalid --process-filter pattern (not a regular expression): %s", args.process_filter)
        # `--process-focus`, else `[processlist] focus` (v4 `main.py:521-527`,
        # `processlist/__init__.py:253-256`). TUI mode only for the reason the
        # filter is: the engine is process-global, a server-wide focus would
        # narrow what every REST client sees. The setter REPLACES the list, so
        # the command line wins over the config rather than widening it.
        focus = getattr(args, "process_focus", None) or config.get("processlist", "focus", "")
        if focus:
            glances_processes.process_focus = focus
            logger.info("Process focus set to: %s", focus)

        registry = [(p.plugin_name, p.IS_COLLECTION) for p in plugins if p.DISPLAY_IN_TUI]
        fields_by_plugin = {p.plugin_name: p._fields for p in plugins if p.DISPLAY_IN_TUI}
        # TUI repaint cadence. Default to the global plugin refresh
        # interval — there is no point repainting more often than the
        # data underneath changes. Operators who *want* a faster TUI can
        # set ``[outputs] tui_refresh_interval`` explicitly.
        # `[global] refresh` (v4 key) takes precedence over the `refresh_time`
        # alias, mirroring the scheduler's resolution.
        refresh = float(config.get("outputs", "tui_refresh_interval", _global_refresh(config)))
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
            full_quicklook=getattr(args, "full_quicklook", False),
            percpu=getattr(args, "percpu", False),
            meangpu=getattr(args, "meangpu", False),
            fahrenheit=getattr(args, "fahrenheit", False),
            hide_public_info=getattr(args, "hide_public_info", False),
            byte=getattr(args, "byte", False),
            diskio_latency=getattr(args, "diskio_latency", False),
            diskio_iops=getattr(args, "diskio_iops", False),
            load_irix=getattr(args, "load_irix", False),
            startup_hidden_flags={flag for flag in STARTUP_HIDE_KEYS if getattr(args, flag, False)},
            disable_bold=getattr(args, "disable_bold", False),
            disable_bg=getattr(args, "disable_bg", False),
            disable_separator=getattr(args, "disable_separator", False),
            stop_after=getattr(args, "stop_after", None),
            process_short_name=getattr(args, "process_short_name", True),
            disable_unicode=getattr(args, "disable_unicode", False),
            disable_cursor=getattr(args, "disable_cursor", False),
            arrow_keys_sort=getattr(args, "arrow_keys_sort", False),
            programs=getattr(args, "programs", False),
        )

    return app, scheduler, host, int(port), tui


# --------------------------------------------------------------- memory leak

# v4 `main.py:882-887`: 60 refreshes of 1 s when --stop-after is not given.
_MEMORY_LEAK_DEFAULT_CYCLES = 60


def apply_memory_leak_flags(args: argparse.Namespace, config: GlancesConfigV5) -> int:
    """Set up a `--memory-leak` run, as v4 does; return its cycle count.

    No TUI, a 1 s refresh, and no stats history -- a history filling up
    would read as a leak. Must run before `assemble()`.
    """
    args.no_tui = True
    args.disable_history = True
    config._merged.setdefault("global", {})["refresh"] = 1.0
    return args.stop_after or _MEMORY_LEAK_DEFAULT_CYCLES


async def measure_memory_leak(scheduler: AsyncScheduler, seconds: float) -> list[tracemalloc.StatisticDiff]:
    """Collect for `seconds` to warm up, snapshot, collect as long again, diff.

    The warm-up is what keeps one-off allocations (imports, caches, the first
    psutil handles) out of the figure. `tracemalloc` must already be tracing.
    Mirrors v4 `check_memleak` / `maybe_trace_memleak` (`glances/__init__.py`).
    """
    task = asyncio.create_task(scheduler.run_forever())
    try:
        await asyncio.sleep(seconds)
        begin = tracemalloc.take_snapshot()
        await asyncio.sleep(seconds)
        end = tracemalloc.take_snapshot()
    finally:
        await scheduler.stop()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
    return end.compare_to(begin, "filename")


def run_memory_leak(args: argparse.Namespace, config: GlancesConfigV5) -> int:
    """`--memory-leak`: print the growth between two snapshots, log the top 5."""
    tracemalloc.start()
    cycles = apply_memory_leak_flags(args, config)
    _app, scheduler, _host, _port, _tui = assemble(args, config)
    print(f"Memory leak detection, please wait ~{2 * cycles} seconds...")
    diff = asyncio.run(measure_memory_leak(scheduler, float(cycles)))
    tracemalloc.stop()
    print(f"Memory consumption: {sum(stat.size_diff for stat in diff) / 1000:.1f}KB (see log for details)")
    logger.info("Memory consumption (top 5):")
    for stat in diff[:5]:
        logger.info(stat)
    return 0


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
            # Local import, same reason as `build_app` in `assemble()`: the
            # TUI mode below binds no socket and must not pay for uvicorn.
            import uvicorn

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
    # `server` decides the console verbosity: only the TUI needs the terminal
    # kept clean, and `-s` never starts one (`assemble`).
    setup_logging(args.debug, server=args.server)
    validate_args(args)

    if args.set_password:
        return cli_set_password()
    if getattr(args, "modules_list", False):
        print(modules_list())
        return 0

    try:
        config = GlancesConfigV5(cli_config_path=args.config_path)
    except ConfigFileError as e:
        logger.critical("%s", e)
        sys.exit(2)
    if getattr(args, "memory_leak", False):
        return run_memory_leak(args, config)
    app, scheduler, host, port, tui = assemble(args, config)

    if args.server:
        logger.info("Starting Glances v5 REST API on http://%s:%d", host, port)
        if getattr(args, "open_web_browser", False):
            open_web_ui(host, port)
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
