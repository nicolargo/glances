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
    __init__.py    # Export implementation
```

No registration needed — exports are auto-discovered.

### Template

The export `__init__.py` must follow this pattern:

```python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""<Name> interface class."""

from glances.exports.export import GlancesExport
from glances.logger import logger


class Export(GlancesExport):
    """This class manages the <Name> export module."""

    def __init__(self, config=None, args=None):
        """Init the export module."""
        super().__init__(config=config, args=args)

        # Load config from [<name>] section in glances.conf
        self.host = self.config.get_value(self.export_name, 'host', default='localhost')
        self.port = self.config.get_int_value(self.export_name, 'port', default=9000)

        # Init the connection
        self.client = self._init_connection()

        # Set export_enable to True if connection succeeded
        self.export_enable = self.client is not None

    def _init_connection(self):
        """Connect to the target system. Return the connection object or None."""
        try:
            # Initialize your client here
            client = None
            logger.info(f"Connected to {self.export_name} ({self.host}:{self.port})")
            return client
        except Exception as e:
            logger.critical(f"Cannot connect to {self.export_name} ({self.host}:{self.port}): {e}")
            return None

    def export(self, name, columns, points):
        """Export the stats to the target system.

        Args:
            name: Plugin name (e.g., 'cpu', 'mem')
            columns: List of field names
            points: List of field values (same order as columns)
        """
        if not self.export_enable:
            return

        # Build and send data
        data = dict(zip(columns, points))
        try:
            # Send data to target system
            logger.debug(f"Export {name} to {self.export_name}")
        except Exception as e:
            logger.error(f"Cannot export {name} to {self.export_name}: {e}")
```

### Key conventions

- Directory: `glances/exports/glances_<name>/`
- Class must be named `Export` (exactly)
- Inherit from `GlancesExport`
- Configuration is loaded from `[<name>]` section in `glances.conf`
- `export_enable` must be set to `True` when the connection is established
- The `export(name, columns, points)` method is called for each plugin at each refresh cycle
- Use `self.export_name` to get the export module name (auto-derived)
- Mark sensitive config keys (passwords, tokens) so they are filtered from the API

### After creation

1. Add the dependency to `pyproject.toml` under the appropriate optional group
2. Add a `[<name>]` section in `conf/glances.conf` with all config keys (commented out)
3. Add an export test script: `tests/test_export_<name>.sh`
4. Run `make test` to verify no regressions
