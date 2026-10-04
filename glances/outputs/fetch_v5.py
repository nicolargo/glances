#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — `--fetch`: a neofetch-like summary, v4's layout in the TUI's colours.

v4 parity (`glances/outputs/glances_stdout_fetch.py`, `--fetch-template`).
The layout is v4's -- its lines, its emojis, its `■□` bars, its top-process
lists -- by maintainer decision (2026-09-27), after a first version that
copied the TUI's blocks. What v5 adds is the TUI's colour code:

- A bar and its percentage take the colour of the field's alert level, from
  the same thresholds the TUI colours with (`_levels`): green, blue,
  magenta, red. v4 drew a CPU at 95 % like a CPU at 5 %.
- Titles are bold, like the TUI's block titles.
- Colours only when stdout is a terminal and `NO_COLOR` is unset.
  `--disable-unicode` draws the bars and the rule in ASCII.

Templates are Jinja, rendered with `gl` (the v5 Python API, `api_v5`) and
`ui` (the helpers below). v4 templates break on purpose: their field names
are v4's (maintainer decision, 2026-09-26). An undefined name fails loudly
instead of printing a blank.
"""

from __future__ import annotations

import os
import re
import sys
import time
from typing import Any, TextIO

import jinja2

from glances.outputs.curses_formatters_v5 import format_value

# The TUI's level colours as ANSI SGR codes (glances_curses_v5._init_colors):
# green, blue, magenta, red. Titles are bold in the terminal's own foreground
# rather than forced white, so they stay readable on a light background too.
_LEVEL_SGR = {"ok": "32", "careful": "34", "warning": "35", "critical": "31"}
_BOLD = "1"
_ANSI = re.compile(r"\x1b\[[0-9;]*m")

# How long to collect before rendering: a rate (network, disk I/O) or a CPU
# percentage needs two samples some time apart. v4 rendered straight after
# its first update, so its rates covered a few milliseconds.
DEFAULT_WAIT = 1.0

# v4's default template (`glances_stdout_fetch.py`), on v5's field names and
# with the TUI's colours.
DEFAULT_TEMPLATE = """\
{{ ui.rule() }}
✨ {{ ui.title(gl.system['hostname']) }}\
{{ ' | ' + gl.ip['address'] if gl.ip.get('address') else '' }} | Uptime: {{ ui.uptime() }}
⚙️  {{ gl.system['hr_name'] }}

💡 {{ ui.title('LOAD') }}     {{ ui.number('load', 'min1') }}/min1 |\
 {{ ui.number('load', 'min5') }}/min5 |\
 {{ ui.number('load', 'min15') }}/min15
⚡ {{ ui.title('CPU') }}      {{ ui.bar('cpu', 'total') }} {{ ui.percent('cpu', 'total') }}\
 of {{ gl.core['log'] }} cores
🧠 {{ ui.title('MEM') }}      {{ ui.bar('mem', 'percent') }} {{ ui.percent('mem', 'percent') }}\
 ({{ gl.auto_unit(gl.mem['used']) }} / {{ gl.auto_unit(gl.mem['total']) }})
{% for fs in gl.fs.keys() %}\
💾 {% if loop.index == 1 %}{{ ui.title('DISK') }}{% else %}    {% endif %}\
     {{ ui.bar('fs', 'percent', fs) }} {{ ui.percent('fs', 'percent', fs) }}\
 ({{ gl.auto_unit(gl.fs[fs]['used']) }} / {{ gl.auto_unit(gl.fs[fs]['size']) }}) for {{ fs }}
{% endfor %}\
{% for net in ui.visible('network') %}\
📡 {% if loop.index == 1 %}{{ ui.title('NET') }}{% else %}   {% endif %}\
      ↓ {{ ui.bits('network', 'bytes_recv', net) }}/s ↑ {{ ui.bits('network', 'bytes_sent', net) }}/s for {{ net }}
{% endfor %}\

🔥 {{ ui.title('TOP PROCESS by CPU') }}
{% for p in gl.top_process() %}\
{{ loop.index }}️⃣ {{ ui.pad(p['name'], 20) }}\
    ⚡ {{ ui.pad(ui.process(p, 'cpu_percent') ~ '% CPU', 11) }}\
    🧠 {{ gl.auto_unit(p['memory_info']['rss']) }}B MEM
{% endfor %}\
🔥 {{ ui.title('TOP PROCESS by MEM') }}
{% for p in gl.top_process(sorted_by='memory_percent', sorted_by_secondary='cpu_percent') %}\
{{ loop.index }}️⃣ {{ ui.pad(p['name'], 20) }}\
    🧠 {{ ui.pad(gl.auto_unit(p['memory_info']['rss']) ~ 'B MEM', 10) }}\
    ⚡ {{ ui.process(p, 'cpu_percent') }}% CPU
{% endfor %}\
{{ ui.rule() }}
"""


def visible_len(text: str) -> int:
    """Length on screen: ANSI escapes take no column."""
    return len(_ANSI.sub("", text))


class FetchUI:
    """The helpers a fetch template gets as `ui`.

    Every value helper takes a plugin name, a field and, for a collection, the
    item's key (`ui.percent('fs', 'percent', '/home')`), because the colour
    comes from that item's level, not from the value alone.
    """

    def __init__(self, gl: Any, color: bool = True, unicode: bool = True) -> None:
        self._gl = gl
        self._color = color
        self._unicode = unicode

    def _sgr(self, text: str, code: str | None) -> str:
        if not self._color or not code or not text:
            return text
        return f"\x1b[{code}m{text}\x1b[0m"

    def _view(self, plugin: str) -> Any:
        return getattr(self._gl, plugin)

    # ------------------------------------------------------------- reading

    def value(self, plugin: str, field: str, item: Any = None) -> Any:
        """The raw value of `field` (of `item`, for a collection); None if absent."""
        view = self._view(plugin)
        row = view.get(item, {}) if item is not None else view
        return row.get(field)

    def level(self, plugin: str, field: str, item: Any = None) -> str | None:
        """The alert level of `field` (`ok`, `careful`, `warning`, `critical`), or None."""
        levels = self._view(plugin).levels
        if item is not None:
            levels = levels.get(item) or levels.get(str(item)) or {}
        return (levels.get(field) or {}).get("level")

    def visible(self, plugin: str) -> list[Any]:
        """The keys of a collection the TUI would draw (not hidden by `hide_zero` and the like)."""
        view = self._view(plugin)
        return [key for key in view.keys() if not view[key].get("hidden")]

    # ------------------------------------------------------------ painting

    def color(self, text: Any, level: str | None) -> str:
        """Text in the colour of an alert level."""
        return self._sgr(str(text), _LEVEL_SGR.get(level or ""))

    def title(self, text: Any) -> str:
        """Text styled as a TUI title: bold."""
        return self._sgr(str(text), _BOLD)

    def percent(self, plugin: str, field: str, item: Any = None) -> str:
        """`12.3%`, in the colour of the field's level."""
        value = self.value(plugin, field, item)
        text = "-" if value is None else f"{value:.1f}%"
        return self.color(text, self.level(plugin, field, item))

    def number(self, plugin: str, field: str, item: Any = None, fmt: str = "{:.2f}") -> str:
        """A number (`0.45`), in the colour of the field's level."""
        value = self.value(plugin, field, item)
        return self.color("-" if value is None else fmt.format(value), self.level(plugin, field, item))

    def bar(self, plugin: str, field: str, item: Any = None, size: int = 18) -> str:
        """v4's `■■□□□` bar for a percentage, in the colour of the field's level."""
        value = self.value(plugin, field, item) or 0
        full, empty = ("■", "□") if self._unicode else ("#", "-")
        return self.color(
            self._gl.bar(value, size=size, bar_char=full, empty_char=empty), self.level(plugin, field, item)
        )

    def bits(self, plugin: str, field: str, item: Any = None) -> str:
        """A byte rate as bits, as the TUI's network block shows it (`3.3Kb`)."""
        value = self.value(plugin, field, item)
        return "-" if value is None else f"{self._gl.auto_unit(value * 8, low_precision=True)}b"

    def process(self, process: dict[str, Any], field: str) -> str:
        """A process's value, in the colour of its level in the process list."""
        value = process.get(field)
        text = "-" if value is None else f"{value:.1f}"
        return self.color(text, self.level("processlist", field, process.get("pid")))

    def uptime(self) -> str:
        """The uptime, formatted as the TUI's header shows it (`38m03s`)."""
        return format_value(self._gl.uptime["seconds"], {"unit": "seconds"})

    def rule(self, width: int = 79) -> str:
        """v4's heavy rule."""
        return ("━" if self._unicode else "=") * width

    def pad(self, text: Any, width: int) -> str:
        """`text` cut or padded to `width` columns, colour escapes not counted."""
        text = str(text)
        if visible_len(text) == len(text):
            text = text[:width]
        return text + " " * max(0, width - visible_len(text))


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
    disable_config_exec: bool = False,
) -> int:
    """`--fetch`: collect for `wait` seconds, render the template, print it.

    `disable_config_exec` carries `--disable-config-exec` to the API, which
    loads its own config: the AMPs it builds must honour the flag.
    """
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
    with GlancesAPI(config_path=config_path, disable_config_exec=disable_config_exec) as gl:
        time.sleep(wait)
        try:
            text = render(template_text, gl, FetchUI(gl, color=color, unicode=unicode))
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
