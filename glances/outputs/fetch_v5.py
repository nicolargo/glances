#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--fetch`: a neofetch-like summary that looks like the TUI.

v4 parity (`glances/outputs/glances_stdout_fetch.py`, `--fetch-template`),
redesigned with the maintainer on 2026-09-26 (mockups; architecture §10):

- The blocks are the TUI's own: `ui.block("mem")` runs `mem`'s
  `render_curses_v5.render`, the renderer the TUI paints, through
  `curses_renderer_v5.render_plugin_rows`. Titles, units, thresholds and
  colours therefore match the TUI by construction, not by imitation. v4's
  emojis, which neither interface uses, are gone.
- Colours are the TUI's ANSI roles, warning in magenta, and only when stdout
  is a terminal and `NO_COLOR` is unset. `--disable-unicode` gives ASCII.
- Templates are Jinja, rendered with `gl` (the v5 Python API, `api_v5`) and
  `ui` (the helpers below). v4 templates break on purpose: their field names
  are v4's (maintainer decision, 2026-09-26). An undefined name fails loudly
  instead of printing a blank.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import time
from typing import Any, TextIO

import jinja2

from glances.outputs.curses_renderer_v5 import ColorRole, Row, render_plugin_rows

# The TUI's colour roles as ANSI SGR codes (glances_curses_v5._init_colors):
# green, blue, magenta, red. Titles are bold in the terminal's own foreground
# rather than forced white, so they stay readable on a light background too.
_SGR = {
    ColorRole.OK: "32",
    ColorRole.CAREFUL: "34",
    ColorRole.WARNING: "35",
    ColorRole.CRITICAL: "31",
    ColorRole.HEADER: "1",
}
_LEVEL_ROLE = {
    "ok": ColorRole.OK,
    "careful": ColorRole.CAREFUL,
    "warning": ColorRole.WARNING,
    "critical": ColorRole.CRITICAL,
}
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# How long to collect before rendering: a rate (network, disk I/O) or a CPU
# percentage needs two samples some time apart. v4 rendered straight after
# its first update, so its rates covered a few milliseconds.
DEFAULT_WAIT = 1.0

DEFAULT_TEMPLATE = """\
{{ ui.row('system', 'ip', 'uptime', gap=3) }}
{{ ui.rule() }}
{{ ui.row('quicklook', 'mem', 'load', 'memswap', 'cpu') }}
{{ ui.rule() }}
{{ ui.row('network', 'fs', max_rows=8) }}
{{ ui.rule() }}
{{ ui.top() }}
"""


def visible_len(text: str) -> int:
    """Length on screen: ANSI escapes take no column."""
    return len(_ANSI.sub("", text))


class FetchUI:
    """The helpers a fetch template gets as `ui`."""

    def __init__(self, gl: Any, color: bool = True, unicode: bool = True, width: int = 120) -> None:
        self._gl = gl
        self._color = color
        self._unicode = unicode
        self.width = width

    # ---------------------------------------------------------- painting

    def _sgr(self, text: str, codes: list[str]) -> str:
        if not self._color or not codes or not text:
            return text
        return f"\x1b[{';'.join(codes)}m{text}\x1b[0m"

    def _paint(self, row: Row) -> str:
        """One TUI row as text: one space between cells, none before a `glue` cell."""
        out = ""
        for i, cell in enumerate(row.cells):
            if i > 0 and not cell.glue:
                out += " "
            codes = [_SGR[cell.color]] if cell.color in _SGR else []
            if cell.bold and "1" not in codes:
                codes.append("1")
            if cell.underline:
                codes.append("4")
            if cell.prominent:
                codes.append("7")  # the TUI's filled badge
            out += self._sgr(cell.text, codes)
        return out

    def _lines(self, name: str, max_rows: int | None = None) -> list[str]:
        if name not in self._gl.plugins():
            return []
        payload = self._gl._payload(name)
        is_collection = "data" in payload
        if is_collection and not payload.get("data"):
            return []  # the TUI draws no lonely header either
        if not self._unicode and "bar_char" in payload:
            payload["bar_char"] = "|"
        fields = getattr(self._gl, name).fields
        rows = render_plugin_rows(name, payload, fields, is_collection, {"unicode": self._unicode})
        lines = [self._paint(row) for row in rows]
        return lines[:max_rows] if max_rows else lines

    # ----------------------------------------------------------- template API

    def block(self, name: str, max_rows: int | None = None) -> str:
        """A plugin's TUI block, as the TUI draws it ("" if the plugin is absent or empty)."""
        return "\n".join(self._lines(name, max_rows))

    def row(self, *names: str, gap: int = 2, max_rows: int | None = None) -> str:
        """Blocks side by side, like the TUI's top row. A block that would not fit `width` is left out."""
        blocks = []
        used = 0
        for name in names:
            lines = self._lines(name, max_rows)
            if not lines:
                continue
            block_width = max(visible_len(line) for line in lines)
            if used and used + gap + block_width > self.width:
                continue
            used += (gap if used else 0) + block_width
            blocks.append((lines, block_width))
        height = max((len(lines) for lines, _ in blocks), default=0)
        out = []
        for i in range(height):
            cells = []
            for lines, block_width in blocks:
                line = lines[i] if i < len(lines) else ""
                cells.append(line + " " * (block_width - visible_len(line)))
            out.append((" " * gap).join(cells).rstrip())
        return "\n".join(out)

    def rule(self, width: int | None = None) -> str:
        """The TUI's separator line."""
        return ("─" if self._unicode else "-") * (width or self.width)

    def title(self, text: str) -> str:
        """Text styled as a TUI block title."""
        return self._sgr(text, [_SGR[ColorRole.HEADER]])

    def color(self, text: Any, level: str | None) -> str:
        """Text in the colour of an alert level (`ok`, `careful`, `warning`, `critical`)."""
        role = _LEVEL_ROLE.get(level or "")
        return self._sgr(str(text), [_SGR[role]] if role else [])

    def top(self, limit: int = 3) -> str:
        """The top processes by CPU and by memory, side by side, TUI-styled."""
        if "processlist" not in self._gl.plugins():
            return ""
        levels = self._gl.processlist.levels

        def table(title: str, key: str, secondary: str) -> list[str]:
            head = self.title(f"{title:<18}") + " " + self.title(f"{'CPU%':>5} {'MEM%':>5} {'RES':>6}")
            lines = [head]
            for p in self._gl.top_process(limit=limit, sorted_by=key, sorted_by_secondary=secondary):
                pid_levels = levels.get(p["pid"], {}) or levels.get(str(p["pid"]), {})
                cpu = self.color(f"{p.get('cpu_percent') or 0:>5.1f}", pid_levels.get("cpu_percent", {}).get("level"))
                mem = self.color(
                    f"{p.get('memory_percent') or 0:>5.1f}", pid_levels.get("memory_percent", {}).get("level")
                )
                rss = (p.get("memory_info") or {}).get("rss")
                lines.append(
                    f"{str(p.get('name', ''))[:18]:<18} {cpu} {mem} {self._gl.auto_unit(rss, low_precision=True):>6}"
                )
            return lines

        left = table("TOP CPU", "cpu_percent", "memory_percent")
        right = table("TOP MEM", "memory_percent", "cpu_percent")
        width = max(visible_len(line) for line in left)
        return "\n".join(
            (a + " " * (width - visible_len(a)) + "   " + b).rstrip() for a, b in zip(left, right, strict=False)
        )


def render(template_text: str, gl: Any, ui: FetchUI) -> str:
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=False, keep_trailing_newline=True)  # noqa: S701 -- terminal text, not HTML
    return env.from_string(template_text).render(gl=gl, ui=ui)


def run(
    config_path: str | None,
    template_path: str | None,
    unicode: bool = True,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
    wait: float = DEFAULT_WAIT,
) -> int:
    """`--fetch`: collect for `wait` seconds, render the template, print it."""
    from glances.api_v5 import GlancesAPI

    if template_path:
        try:
            with open(template_path, encoding="utf-8") as f:
                template_text = f.read()
        except OSError as e:
            print(f"--fetch-template: cannot read {template_path}: {e}", file=err)
            return 2
    else:
        template_text = DEFAULT_TEMPLATE
    color = out.isatty() and "NO_COLOR" not in os.environ
    width = shutil.get_terminal_size(fallback=(120, 40)).columns
    with GlancesAPI(config_path=config_path) as gl:
        time.sleep(wait)
        try:
            text = render(template_text, gl, FetchUI(gl, color=color, unicode=unicode, width=width))
        except (jinja2.TemplateError, AttributeError, KeyError, TypeError) as e:
            # Most likely a v4 template: v5 renamed some fields (e.g. the
            # network rates are `bytes_recv`, not `bytes_recv_rate_per_sec`).
            print(f"--fetch: the template failed: {type(e).__name__}: {e}", file=err)
            print(
                "v4 templates need updating for v5 field names; see the plugin fields in docs/api/python.rst.", file=err
            )
            return 2
    out.write(text if text.endswith("\n") else text + "\n")
    return 0
