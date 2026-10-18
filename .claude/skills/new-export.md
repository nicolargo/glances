# Skill: Create a New Export Module

Scaffold a new Glances export module following project conventions.

## Instructions

Ask the user for:
1. **Export name** (lowercase, e.g., `clickhouse`)
2. **Target system** (database, message queue, file format, etc.)
3. **Required Python library** (e.g., `clickhouse-driver`)

Then create the export following this structure:

### File structure

```
glances/exports/glances_<name>/
    __init__.py    # Package marker (docstring only)
    export.py      # Export implementation
```

No registration needed — `discover_exporters()` (`glances/main.py`) imports
`glances.exports.glances_<name>.export` when the user passes
`--export <name>`.

### Template

The `export.py` module must follow this pattern (see
`glances/exports/glances_statsd/export.py` for a complete short example and
`SKILL-exporter.md` for the contract):

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances — <Name> export module."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from glances.exports.export_base import GlancesExportBase
from glances.logger import logger

if TYPE_CHECKING:
    import argparse

    from glances.config import GlancesConfig


class Export(GlancesExportBase):
    """Send Glances stats to <Name>."""

    export_name = "<name>"

    def __init__(self, config: GlancesConfig, args: argparse.Namespace | None = None) -> None:
        super().__init__(config, args)
        # Load host, port (mandatory) and options from the [<name>] section
        if not self.load_conf("<name>", mandatories=("host", "port"), options=()):
            logger.critical("Missing <name> config")
            sys.exit(2)
        self.client = self.init()

    def init(self) -> Any:
        """Connect to the target system. Import the client library lazily."""
        try:
            from <library> import Client
        except ImportError as e:
            logger.critical("Export <name> needs the <library> library (%s)", e)
            sys.exit(2)
        logger.info("Stats will be exported to <Name> %s:%s", self.host, self.port)
        return Client(self.host, int(self.port))

    def export(self, name: str, columns: list[str], points: list[Any]) -> None:
        """Export one plugin's stats (blocking I/O is fine: runs in a worker thread).

        Args:
            name: Plugin name (e.g., 'cpu', 'mem')
            columns: List of field names
            points: List of field values (same order as columns)
        """
        try:
            self.client.send(name, dict(zip(columns, points)))
        except Exception as e:
            logger.warning("Cannot export %s stats to <Name> (%s)", name, e)

    def exit(self) -> None:
        super().exit()  # FIRST: waits for an in-flight update()
        self.client.close()
```

### Key conventions

- Directory: `glances/exports/glances_<name>/`, implementation in `export.py`
- Class must be named `Export` (exactly) and inherit from `GlancesExportBase`
- `export_name` matches the directory suffix and the `--export` token
- Configuration is loaded from the `[<name>]` section in `glances.conf` with
  `self.load_conf()`; a missing section or mandatory key is fatal
- `update()` (base class) calls `plugin.get_export()` then
  `export(name, columns, points)` for each plugin, once per `[export] refresh`
- Never read the `StatsStore` directly; never interpolate monitored data
  into a query (CVE-2026-32611 pattern)
- Name sensitive config keys so they match `GlancesConfig.SECRET_KEYS` (`password`,
  `token`, …) and `as_dict_secure()` redacts them

### After creation

1. Add the dependency to `pyproject.toml` under the appropriate optional group
2. Add a `[<name>]` section in `conf/glances.conf` with all config keys (commented out)
3. Add unit tests `tests/test_export_<name>.py` (fakes in `tests/export_fakes.py`)
   and, optionally, an integration script `tests/test_export_<name>.sh`
4. Run `make test` to verify no regressions
