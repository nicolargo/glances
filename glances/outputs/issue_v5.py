#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--issue`: a report to paste into a bug report.

v4 parity (`glances/outputs/glances_stdout_issue.py`), redesigned with the
maintainer on 2026-09-26 (mockups, architecture §10 "CLI — decided to port"):

- Markdown on stdout, never an ANSI escape: v4's colour codes land in the
  ticket as literal `[94m` noise. Progress goes to stderr, so
  `glances-v5 --issue > report.md` or a pipe to the clipboard stays clean.
- A versions table, then a plugins table sorted by update time, with errors
  first and the full exception, then the warnings logged during the run
  (e.g. an unrecognised v4 threshold key), then the payloads, folded.
- Identifiers are redacted: hostnames, IP addresses, user names, command-line
  arguments, folder paths (v4 masked the `ip` plugin only).
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import logging
import os
import platform
import re
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import Any, TextIO

import psutil

logger = logging.getLogger(__name__)

REDACTED = "***"

# Per plugin, the fields that identify a host, a network or a person
# (the list approved on 2026-09-26). Command lines are handled on their own:
# the program name stays, its arguments go.
_REDACT_FIELDS: dict[str, frozenset[str]] = {
    "system": frozenset({"hostname"}),
    "ip": frozenset({"address", "gateway", "public_address", "public_info_human"}),
    "cloud": frozenset({"id", "name"}),
    "ports": frozenset({"host"}),
    "processlist": frozenset({"username"}),
    "programlist": frozenset({"username"}),
    "folders": frozenset({"path"}),
}
_CMDLINE_PLUGINS = frozenset({"processlist", "programlist"})

# pyproject extras that only matter when configured, or that aggregate others.
_SKIPPED_EXTRAS = frozenset({"all", "export", "dev"})


@dataclass
class PluginResult:
    """What one plugin did on the measured cycle."""

    name: str
    status: str  # "ok", "empty", "error" or "disabled"
    seconds: float | None = None
    items: int | None = None
    error: str | None = None
    payload: Any = None


@dataclass
class Environment:
    """Everything the report says about the machine, not about the plugins."""

    rows: list[tuple[str, str]] = field(default_factory=list)


# ------------------------------------------------------------- redaction


def redact(plugin_name: str, payload: Any) -> Any:
    """A copy of `payload` with the plugin's identifying fields replaced."""
    fields = _REDACT_FIELDS.get(plugin_name, frozenset())
    cmdline = plugin_name in _CMDLINE_PLUGINS

    def one(item: Any) -> Any:
        if not isinstance(item, dict):
            return item
        out = {}
        for key, value in item.items():
            if key in fields and value not in (None, ""):
                out[key] = REDACTED
            elif cmdline and key == "cmdline" and isinstance(value, list) and value:
                out[key] = [os.path.basename(str(value[0]))] + ([REDACTED] if len(value) > 1 else [])
            else:
                out[key] = value
        return out

    if isinstance(payload, list):
        return [one(item) for item in payload]
    return one(payload)


def excerpt(payload: Any) -> Any:
    """The first item of a list, and how many were left out."""
    if isinstance(payload, list) and len(payload) > 1:
        return [payload[0], f"... {len(payload) - 1} more"]
    return payload


# ------------------------------------------------------------ environment


def optional_dependencies() -> str:
    """`name version` for each installed optional dependency, then the absent ones."""
    try:
        requirements = importlib.metadata.requires("glances") or []
    except importlib.metadata.PackageNotFoundError:
        return "unknown (Glances is not installed as a package)"
    present, absent = [], []
    seen: set[str] = set()
    for requirement in requirements:
        extra = re.search(r'extra == "([^"]+)"', requirement)
        if not extra or extra.group(1) in _SKIPPED_EXTRAS:
            continue
        name = re.match(r"[A-Za-z0-9_.\-]+", requirement).group(0)
        if name in seen:
            continue
        seen.add(name)
        try:
            present.append(f"{name} {importlib.metadata.version(name)}")
        except importlib.metadata.PackageNotFoundError:
            absent.append(name)
    parts = [", ".join(present) or "none"]
    if absent:
        parts.append("absent: " + ", ".join(absent))
    return "; ".join(parts)


def collect_environment(version: str, config_sources: list[str]) -> Environment:
    os_name = f"{platform.system()} {platform.release()} {platform.machine()}"
    try:
        os_name += f", {platform.freedesktop_os_release()['PRETTY_NAME']}"
    except (OSError, KeyError, AttributeError):
        pass
    size = shutil.get_terminal_size(fallback=(0, 0))
    terminal = ", ".join(
        part
        for part in (
            os.environ.get("TERM", "no TERM"),
            f"{size.columns}x{size.lines}" if size.columns else "",
            sys.stdout.encoding or "",
        )
        if part
    )
    return Environment(
        rows=[
            ("Glances", f"{version} (v5)"),
            ("Python", f"{platform.python_version()} ({platform.python_implementation()})"),
            ("psutil", psutil.__version__),
            ("OS", os_name),
            ("Config", ", ".join(config_sources) or "none (defaults)"),
            ("Terminal", terminal),
            ("Optional", optional_dependencies()),
        ]
    )


# ---------------------------------------------------------------- testing


class _Capture(logging.Handler):
    """Every WARNING+ record logged during the run."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _update_failure(record: logging.LogRecord) -> tuple[str, BaseException] | None:
    """(plugin, exception) when `record` is base_v5's "update failed" line.

    `GlancesPluginBase.update()` swallows its exception and logs it with the
    exception object as an argument, which is what lets the report name its
    type and last frame rather than v4's 38 truncated characters.
    """
    if record.msg == "Plugin %s update failed: %s" and isinstance(record.args, tuple) and len(record.args) == 2:
        name, exc = record.args
        if isinstance(exc, BaseException):
            return str(name), exc
    return None


def _describe(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    tb = exc.__traceback__
    while tb is not None and tb.tb_next is not None:
        tb = tb.tb_next
    if tb is not None:
        text += f" ({os.path.basename(tb.tb_frame.f_code.co_filename)}:{tb.tb_lineno})"
    return text


async def exercise_plugins(
    plugins: list[Any], disabled: list[str], wait: float = 2.0
) -> tuple[list[PluginResult], list[str]]:
    """Update every plugin twice (`wait` apart, for rates) and time the second.

    Returns the per-plugin results and the other warnings logged meanwhile.
    """
    capture = _Capture()
    root = logging.getLogger()
    root.addHandler(capture)
    try:
        for plugin in plugins:
            await plugin.update()
        await asyncio.sleep(wait)
        results: list[PluginResult] = []
        for plugin in plugins:
            before = len(capture.records)
            start = time.perf_counter()
            await plugin.update()
            seconds = time.perf_counter() - start
            failure = next((f for r in capture.records[before:] if (f := _update_failure(r))), None)
            if failure:
                results.append(PluginResult(plugin.plugin_name, "error", seconds, error=_describe(failure[1])))
                continue
            payload = plugin.get_api_payload()
            data = (
                payload.get("data")
                if plugin.IS_COLLECTION
                else {k: v for k, v in payload.items() if not k.startswith("_")}
            )
            results.append(
                PluginResult(
                    plugin.plugin_name,
                    "ok" if payload else "empty",
                    seconds,
                    items=len(data) if isinstance(data, list) else None,
                    payload=data,
                )
            )
    finally:
        root.removeHandler(capture)
    results += [PluginResult(name, "disabled") for name in disabled]
    warnings = []
    for record in capture.records:
        if _update_failure(record):
            continue
        line = f"{record.name}: {record.getMessage()}"
        if line not in warnings:
            warnings.append(line)
    return results, warnings


# --------------------------------------------------------------- rendering


def _cell(text: Any) -> str:
    """Make `text` safe inside a Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def summary(results: list[PluginResult]) -> str:
    counts = {status: sum(1 for r in results if r.status == status) for status in ("ok", "empty", "error", "disabled")}
    total_ms = sum(r.seconds or 0.0 for r in results) * 1000
    parts = [f"{counts['ok']} OK"]
    if counts["empty"]:
        parts.append(f"{counts['empty']} empty")
    parts += [f"{counts['disabled']} disabled", f"{counts['error']} error" + ("s" if counts["error"] > 1 else "")]
    return f"{len(results)} plugins: {', '.join(parts)}. Update time {total_ms:.1f} ms (2nd cycle)."


def render(env: Environment, results: list[PluginResult], warnings: list[str]) -> str:
    """The Markdown report."""
    lines = ["## Glances --issue report", "", "| Component | Version |", "|---|---|"]
    lines += [f"| {_cell(key)} | {_cell(value)} |" for key, value in env.rows]
    lines += ["", f"**{summary(results)}**", "", "| Plugin | Status | Update | Items |", "|---|---|--:|--:|"]
    measured = [r for r in results if r.status != "disabled"]
    # Errors first -- they are why the report exists -- then by update time.
    measured.sort(key=lambda r: (r.status != "error", -(r.seconds or 0.0)))
    for r in measured:
        status = f"ERROR: {r.error}" if r.status == "error" else r.status.upper()
        update = f"{r.seconds * 1000:.2f} ms" if r.seconds is not None else ""
        items = "" if r.items is None else str(r.items)
        lines.append(f"| {r.name} | {_cell(status)} | {update} | {items} |")
    disabled = sorted(r.name for r in results if r.status == "disabled")
    if disabled:
        lines.append(f"| {', '.join(disabled)} | disabled | | |")
    if warnings:
        lines += ["", f"**Warnings logged during the run ({len(warnings)})**", ""]
        lines += [f"- {_cell(w)}" for w in warnings]
    payloads = {r.name: excerpt(redact(r.name, r.payload)) for r in sorted(measured, key=lambda r: r.name) if r.payload}
    lines += [
        "",
        "<details><summary>Plugin payloads (redacted, first item of each list)</summary>",
        "",
        "```json",
        json.dumps(payloads, indent=1, default=str, sort_keys=True),
        "```",
        "",
        "</details>",
    ]
    return "\n".join(lines) + "\n"


def run(
    plugins: list[Any],
    disabled: list[str],
    version: str,
    config_sources: list[str],
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    wait: float = 2.0,
) -> int:
    """`--issue`: test every plugin, print the report. Always exits 0: the report is the result."""
    print(
        f"Glances {version}: testing {len(plugins) + len(disabled)} plugins over 2 cycles (~{wait:.0f} s)...", file=err
    )
    try:
        results, warnings = asyncio.run(exercise_plugins(plugins, disabled, wait))
    finally:
        for plugin in plugins:
            try:
                plugin.stop()
            except Exception:  # noqa: S110 -- best effort on the way out
                pass
    report = render(collect_environment(version, config_sources), results, warnings)
    print(f"Report: {summary(results)} {report.count(chr(10))} lines of Markdown below.", file=err)
    print("Redacted: hostnames, IP addresses, user names, command-line arguments, folder paths.", file=err)
    print("Review it before posting.", file=err)
    out.write(report)
    return 0
