#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — the stdout outputs: ``--stdout``, ``--stdout-json``, ``--stdout-csv``.

v4 formats (``glances/outputs/glances_stdout*.py``), fed from each plugin's
``get_export()`` — the filtered view exporters already use, so what a script
reads here is what a time-series database receives.

- ``--stdout cpu,mem.used,network.eth0.bytes_recv`` prints ``plugin: {...}``,
  ``plugin.attribute: value`` or, for a collection, ``plugin.<key>.attribute:
  value`` per item (all items unless a key is given); ``all`` prints every
  plugin (v4 ``getAll``).
- ``--stdout-json cpu,mem`` prints one JSON object per refresh, keyed by plugin.
- ``--stdout-csv cpu,mem.used`` prints a header line on the first refresh,
  then one data line per refresh. A collection's columns are locked at
  header time: an item that disappears prints ``N/A``, one that appears later
  has no column (v4 parity).

The formatters are pure (``render_*``); ``StdoutV5`` is the thread that calls
them once per refresh. It has the TUI's lifecycle (``start``/``stop``/``join``)
so ``main_v5.serve`` runs it in the TUI's place.
"""

from __future__ import annotations

import json
import logging
import sys
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_NA = "N/A"
_SEP = ","


def parse_selection(spec: str) -> list[tuple[str, str | None, str | None]]:
    """``"cpu,mem.used,network.eth0.bytes_recv"`` → ``[(plugin, key, attribute), ...]``."""
    out: list[tuple[str, str | None, str | None]] = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(".")
        if len(pieces) == 1:
            out.append((pieces[0], None, None))
        elif len(pieces) == 2:
            out.append((pieces[0], None, pieces[1]))
        else:
            # The key may itself contain dots (a mount point, a disk alias):
            # the attribute is the last piece, the key everything between.
            out.append((pieces[0], ".".join(pieces[1:-1]), pieces[-1]))
    return out


def _item_key(item: dict[str, Any], pk: str | None) -> str:
    return str(item.get(pk)) if pk else "?"


def render_plain(
    selection: list[tuple[str, str | None, str | None]],
    exports: dict[str, Any],
    primary_keys: dict[str, str | None],
) -> list[str]:
    """v4 ``GlancesStdout.update``: one line per selected stat."""
    lines: list[str] = []
    for plugin, key, attribute in selection:
        if plugin == "all":
            lines.append(f"all: {exports}")
            break
        if plugin not in exports:
            continue
        stat = exports[plugin]
        if attribute is None:
            lines.append(f"{plugin}: {stat}")
        elif isinstance(stat, dict):
            if attribute in stat:
                lines.append(f"{plugin}.{attribute}: {stat[attribute]}")
            else:
                logger.error("Can not display stat %s.%s (unknown attribute)", plugin, attribute)
        elif isinstance(stat, list):
            pk = primary_keys.get(plugin)
            for item in stat:
                ident = _item_key(item, pk)
                if key is not None and ident != key:
                    continue
                if attribute in item:
                    lines.append(f"{plugin}.{ident}.{attribute}: {item[attribute]}")
    return lines


def render_json(plugins: list[str], exports: dict[str, Any]) -> str:
    """v4 ``GlancesStdoutJson``: one object per refresh, keyed by plugin."""
    return json.dumps({name: exports[name] for name in plugins if name in exports}, default=str)


class CsvRenderer:
    """v4 ``GlancesStdoutCsv``: a header line first, then data lines.

    Stateful by nature: the first call locks each collection's item order and
    field names, and every later line is aligned to that schema.
    """

    def __init__(self, selection: list[tuple[str, str | None]]) -> None:
        self.selection = selection
        self._header_done = False
        self._keys: dict[str, list[str]] = {}
        self._fields: dict[str, list[str]] = {}

    def render(self, exports: dict[str, Any], primary_keys: dict[str, str | None]) -> str:
        cells: list[str] = []
        for plugin, attribute in self.selection:
            if plugin not in exports:
                continue
            stat = exports[plugin]
            if self._header_done:
                cells.extend(self._data(plugin, attribute, stat, primary_keys.get(plugin)))
            else:
                cells.extend(self._header(plugin, attribute, stat, primary_keys.get(plugin)))
        self._header_done = True
        return _SEP.join(cells)

    def _header(self, plugin: str, attribute: str | None, stat: Any, pk: str | None) -> list[str]:
        if attribute is not None:
            return [f"{plugin}.{attribute}"]
        if isinstance(stat, dict):
            return [f"{plugin}.{k}" for k in stat]
        if isinstance(stat, list):
            items = [i for i in stat if isinstance(i, dict)]
            self._keys[plugin] = [_item_key(i, pk) for i in items]
            self._fields[plugin] = list(items[0].keys()) if items else []
            return [f"{plugin}.{_item_key(i, pk)}.{field}" for i in items for field in self._fields[plugin]]
        return [plugin]

    def _data(self, plugin: str, attribute: str | None, stat: Any, pk: str | None) -> list[str]:
        if attribute is not None:
            return [str(stat.get(attribute, _NA)) if isinstance(stat, dict) else _NA]
        if isinstance(stat, dict):
            return [str(v) for v in stat.values()]
        if isinstance(stat, list):
            current = {_item_key(i, pk): i for i in stat if isinstance(i, dict)}
            return [
                str(current.get(ident, {}).get(field, _NA))
                for ident in self._keys.get(plugin, [])
                for field in self._fields.get(plugin, [])
            ]
        return [str(stat)]


class StdoutV5(threading.Thread):
    """Print the selected stats once per refresh, until stopped.

    ``stop_after`` (``--stop-after``) counts PRINTS, not seconds, so a script
    asking for 3 lines gets exactly 3; ``on_quit`` then ends the process the
    way the TUI's `q` does.
    """

    def __init__(
        self,
        *,
        plugins: list[Any],
        refresh_interval: float,
        stdout: str | None = None,
        stdout_json: str | None = None,
        stdout_csv: str | None = None,
        stop_after: int | None = None,
        on_quit: Callable[[], None] | None = None,
        write: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(name="glances-stdout", daemon=True)
        self._plugins = {p.plugin_name: p for p in plugins}
        self._primary_keys = {p.plugin_name: getattr(p, "_primary_key", None) for p in plugins}
        self._refresh = max(0.1, float(refresh_interval))
        self._stop_after = stop_after
        self._on_quit = on_quit
        self._write = write or self._print
        self._stop_event = threading.Event()
        self._plain = parse_selection(stdout) if stdout else None
        self._json = [p for p, _, _ in parse_selection(stdout_json)] if stdout_json else None
        self._csv = CsvRenderer([(p, a) for p, _, a in parse_selection(stdout_csv)]) if stdout_csv else None

    @staticmethod
    def _print(text: str) -> None:
        sys.stdout.write(text + "\n")
        sys.stdout.flush()

    def _wanted(self) -> set[str]:
        if self._plain is not None:
            if any(p == "all" for p, _, _ in self._plain):
                return set(self._plugins)
            return {p for p, _, _ in self._plain}
        if self._json is not None:
            return set(self._json)
        return {p for p, _ in self._csv.selection} if self._csv else set()

    def _exports(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for name in self._wanted():
            plugin = self._plugins.get(name)
            if plugin is None:
                continue
            try:
                out[name] = plugin.get_export()
            except Exception as exc:  # noqa: BLE001 -- one broken plugin must not end the stream
                logger.debug("stdout: %s.get_export() failed: %s", name, exc)
        return out

    def output_once(self) -> None:
        """Print one refresh worth of output."""
        exports = self._exports()
        if self._plain is not None:
            for line in render_plain(self._plain, exports, self._primary_keys):
                self._write(line)
        elif self._json is not None:
            self._write(render_json(self._json, exports))
        elif self._csv is not None:
            self._write(self._csv.render(exports, self._primary_keys))

    def run(self) -> None:
        printed = 0
        # The first print waits one refresh, so every plugin has collected
        # at least once (v4 prints after its initial update).
        while not self._stop_event.wait(self._refresh):
            self.output_once()
            printed += 1
            if self._stop_after is not None and printed >= self._stop_after:
                if self._on_quit is not None:
                    self._on_quit()
                return

    def stop(self) -> None:
        self._stop_event.set()
