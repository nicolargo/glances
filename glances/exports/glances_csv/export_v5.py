#!/usr/bin/env python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances v5 — CSV export module.

Ported from the v4 module in this directory, with one deliberate departure:

- **A column-set change rotates the file instead of refusing to write.**
  v4 logged an error and stopped writing when the header no longer matched
  (issue #1525) — either at startup, against a pre-existing file, or later
  mid-run when a network interface, disk or container appeared/disappeared.
  Refusing to write loses data. v5 instead logs a WARNING and rolls over to
  a new file (``<base>-NNN.<ext>``) with the new column set as its header.
  Both triggers — the startup append-check and the mid-run width guard —
  go through the same rotation routine (``_rotate()``); see ``_write_cycle()``.

- **No limits are exported.** v4's CSV exporter overrides ``update()`` and
  reads the plugins' export payloads directly, bypassing the limits merge
  that every other exporter inherits. A CSV therefore carries measurements
  only. Reproduced here so existing CSV pipelines keep their column set.
"""

from __future__ import annotations

import csv
import os.path
import sys
import time
from typing import TYPE_CHECKING, Any

from glances.exports.export_base_v5 import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config_v5 import GlancesConfigV5
    from glances.plugins.plugin.base_v5 import GlancesPluginBase


class Export(GlancesExportBase):
    """Write one CSV row per export cycle."""

    export_name = "csv"

    def __init__(self, config: GlancesConfigV5, args: argparse.Namespace) -> None:
        super().__init__(config, args)

        # Base path used to derive rotation targets (`<base>-NNN.<ext>`).
        # ``self.csv_filename`` tracks whichever file is currently active —
        # it is reassigned by ``_rotate()`` — while ``_base_filename`` never
        # changes, so a second rotation computes ``-002`` from the original
        # name rather than stacking suffixes onto the first rotated name.
        self._base_filename = args.export_csv_file
        self.csv_filename = self._base_filename
        # How many `-NNN` indices have been consumed so far this run. A
        # collision (see `_next_rotation_path()`) can advance this past the
        # number of rotations actually performed.
        self._rotation_index = 0

        # Overwrite, or append to an existing file after a header check.
        if not os.path.isfile(self.csv_filename) or args.export_csv_overwrite:
            file_mode = "w"
            self.old_header: list[str] | None = None
        else:
            file_mode = "a"
            try:
                with open(self.csv_filename, newline="") as existing:
                    self.old_header = next(csv.reader(existing), None)
            except OSError as e:
                logger.critical("Cannot open existing CSV file: %s", e)
                sys.exit(2)

        try:
            self.csv_file = open(self.csv_filename, file_mode, newline="")
        except OSError as e:
            logger.critical("Cannot create the CSV file: %s", e)
            sys.exit(2)
        self.writer = csv.writer(self.csv_file)

        logger.info("Stats exported to CSV file: %s", self.csv_filename)
        self.first_line = True
        # Header committed for the currently active file. Every cycle after
        # the first compares its column set against this — a mismatch is a
        # divergence and triggers `_rotate()`, whether that's the very first
        # cycle finding an incompatible on-disk header (old_header, below)
        # or a later cycle drifting from what this run itself committed.
        self.committed_header: list[str] | None = None
        # Names of the plugins that contributed at least one column on the
        # PREVIOUS cycle, while still on `first_line` (i.e. before a header
        # has been committed for a genuinely new file). Plugins start
        # publishing at staggered times, so the first few cycles can each
        # have a different, growing contributing set — committing the
        # header off any of those would bake a warm-up artefact into the
        # file. `None` until the first cycle runs. See `_write_cycle()`.
        self._previous_contributing: set[str] | None = None

    def update(self, plugins: list[GlancesPluginBase]) -> None:
        """Write the header (first cycle only) then one row of values.

        Overrides the base implementation: a CSV row spans every plugin, so
        the whole cycle must be assembled before anything is written.

        Takes ``self._lifecycle_lock`` explicitly. The base ``update()``
        takes it, but this override never calls ``super().update()``, so
        without this the lock would never be held on the CSV path and
        ``exit()``'s barrier would have nothing to wait for — ``stop()``
        could close ``self.csv_file`` mid-row.
        """
        with self._lifecycle_lock:
            self._write_cycle(plugins)

    def _write_cycle(self, plugins: list[GlancesPluginBase]) -> None:
        """One CSV row. Always called with ``_lifecycle_lock`` held."""
        csv_header: list[str] = ["timestamp"]
        csv_data: list[Any] = [time.strftime("%Y-%m-%d %H:%M:%S")]
        contributing: set[str] = set()

        for plugin in plugins:
            if not getattr(plugin, "EXPORTABLE", True):
                continue
            payload = plugin.get_export()
            if not payload:
                continue
            contributing.add(plugin.plugin_name)
            payload = self._inject_key(plugin, payload)
            export_names, export_values = self.build_export(payload)
            csv_header += [f"{plugin.plugin_name}.{name}" for name in export_names]
            csv_data += export_values

        if csv_header == ["timestamp"]:
            # No plugin has published to the store yet (the export loop can
            # race ahead of the per-plugin loops on the very first cycles).
            # Write nothing and leave self.first_line as True so a later
            # cycle — once real data is available — writes the real header.
            #
            # If a deployment genuinely has no exportable plugin at all,
            # every cycle takes this path forever and the exporter simply
            # never writes anything, which is the correct outcome (there is
            # nothing to export).
            logger.debug("CSV export: no plugin data yet this cycle, skipping (no header written)")
            return

        if self.first_line:
            if self.old_header is None:
                # Genuinely new file: defer committing the header until the
                # contributing plugin set is STABLE across two consecutive
                # cycles — plugins publish at staggered times, so an early
                # cycle's set is a warm-up artefact, not the real schema.
                # Write nothing yet; the header/row land once this cycle's
                # set matches the previous one.
                if contributing != self._previous_contributing:
                    logger.debug(
                        "CSV export: contributing-plugin set changed since last cycle (%s -> %s) — "
                        "deferring header commit to avoid a warm-up artefact",
                        sorted(self._previous_contributing) if self._previous_contributing is not None else None,
                        sorted(contributing),
                    )
                    self._previous_contributing = contributing
                    return
                self.writer.writerow(csv_header)
                self.committed_header = list(csv_header)
            else:
                # Appending to an existing file (issue #1525): treat its
                # on-disk header as "committed" and let the generic check
                # below decide — a mismatch here is a divergence exactly
                # like a mid-run one, so it goes through the same rotation
                # routine instead of duplicating the comparison.
                self.committed_header = list(self.old_header)
                self.old_header = None
            self.first_line = False

        if self.committed_header is not None and csv_header != self.committed_header and not self._rotate(csv_header):
            # Rotation failed (see `_rotate()`) — the original file/header
            # are still active. Skip this cycle's row (its width no longer
            # matches `committed_header`) rather than corrupting the file.
            return

        self.writer.writerow(csv_data)
        self.csv_file.flush()

    def _rotate(self, new_header: list[str]) -> bool:
        """Open a fresh file, commit new_header, then close the old one.

        Called whenever the active file's committed header no longer
        matches the current cycle's column set — collection plugins are
        exported with a per-item prefix, so a new network interface, disk,
        or container appearing/disappearing legitimately changes it. Rather
        than refusing to write (v4, issue #1525), roll over to
        ``<base>-NNN.<ext>`` and keep exporting there. The caller writes
        this cycle's data row into the new file right after this returns.

        A RUNTIME failure (design §8) must never take the process down —
        this is called from the export worker, and an uncaught
        ``SystemExit`` there propagates out of ``asyncio.run`` and kills the
        TUI/REST server. So the new file is opened FIRST; the old one is
        only closed once that succeeds. On ``OSError`` this logs an ERROR
        and returns ``False`` — the existing file stays open and active,
        and the caller skips writing this cycle's (now-mismatched) row.
        """
        old_path = self.csv_filename
        old_header = self.committed_header or []
        new_path = self._next_rotation_path()

        added = sorted(set(new_header) - set(old_header))
        removed = sorted(set(old_header) - set(new_header))
        logger.warning(
            "CSV export: column set changed, rolling over %s -> %s (%d -> %d columns). Added: %s. Removed: %s.",
            old_path,
            new_path,
            len(old_header),
            len(new_header),
            self._format_column_names(added),
            self._format_column_names(removed),
        )

        try:
            new_file = open(new_path, "w", newline="")
        except OSError as e:
            logger.error(
                "CSV export: cannot create rotation file %s (%s) — keeping %s open, skipping this cycle's row",
                new_path,
                e,
                old_path,
            )
            return False

        self.csv_file.close()
        self.csv_file = new_file
        self.writer = csv.writer(self.csv_file)
        self.csv_filename = new_path
        self.committed_header = list(new_header)

        self.writer.writerow(new_header)
        logger.info("Stats exported to CSV file: %s", self.csv_filename)
        return True

    def _next_rotation_path(self) -> str:
        """Return the next free (or overwritable) rotation path.

        Advances ``self._rotation_index`` so a later rotation this run
        starts searching past whatever index was actually used — a
        collision left by a previous run must not be retried forever.
        """
        overwrite = bool(self.args.export_csv_overwrite)
        index = self._rotation_index + 1
        while True:
            candidate = self._rotated_path(self._base_filename, index)
            if overwrite or not os.path.isfile(candidate):
                self._rotation_index = index
                return candidate
            index += 1

    @staticmethod
    def _rotated_path(base_path: str, index: int) -> str:
        """Insert ``-NNN`` before the extension, zero-padded to 3 digits.

        ``/tmp/glances.csv`` -> ``/tmp/glances-001.csv``. No extension gets
        the suffix appended (``/tmp/glances`` -> ``/tmp/glances-001``).
        Several dots split on the LAST one (``/tmp/my.data.csv`` ->
        ``/tmp/my.data-001.csv``) — ``os.path.splitext`` already does that.
        """
        root, ext = os.path.splitext(base_path)
        return f"{root}-{index:03d}{ext}"

    @staticmethod
    def _format_column_names(names: list[str], limit: int = 5) -> str:
        if not names:
            return "(none)"
        if len(names) <= limit:
            return ", ".join(names)
        return f"{', '.join(names[:limit])}, ... and {len(names) - limit} more"

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Unused — everything happens in update()."""

    def exit(self) -> None:
        # super().exit() FIRST: acquiring and releasing the lock is a barrier
        # that waits for any in-flight update() to finish. Only then is it
        # safe to close the file — the scheduler has already cancelled the
        # export task, so no new update() can start after the barrier.
        super().exit()
        self.csv_file.close()
