# Skill: Create a New Plugin

Scaffold a new Glances monitoring plugin following project conventions.

## Instructions

Ask the user for:
1. **Plugin name** (lowercase, e.g., `battery`)
2. **What it monitors** (brief description)
3. **Data source** (psutil, sysfs, external library, etc.)

Then create the plugin following this structure:

### File structure

```
glances/plugins/<name>/
    __init__.py         # Package marker (docstring only)
    model.py            # Plugin implementation (class PluginModel)
    render_curses.py    # OPTIONAL — per-plugin TUI layout
```

No registration needed — `discover_plugins()` (`glances/main.py`) imports
every `glances.plugins.<name>.model`. Its place in the TUI comes from the
slot tuples in `glances/outputs/curses_renderer.py` (`LEFT_SLOT`,
`RIGHT_SLOT`, …). The WebUI needs `glances/outputs/static/js/Plugin<Name>.vue`
and one entry in `glances/outputs/static/js/plugins/index.js`.

### Template

`model.py` must follow this pattern (see `SKILL-plugin.md` for the full
contract and `glances/plugins/uptime/model.py` for a short example):

```python
#
# Glances - An eye on your system
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Glances — <name> plugin (scalar)."""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

import psutil

from glances.plugins.plugin.base import GlancesPluginBase


class PluginModel(GlancesPluginBase[dict]):
    """<Name> plugin (scalar)."""

    plugin_name: ClassVar[str] = "<name>"
    IS_COLLECTION: ClassVar[bool] = False

    fields_description: ClassVar[dict[str, dict[str, Any]]] = {
        "field_name": {
            "description": "Human-readable description.",
            "unit": "percent",  # percent, number, bytes, bytespers, seconds, string, ...
            "watched": True,
            "default_thresholds": {"careful": 50.0, "warning": 70.0, "critical": 90.0},
        },
    }

    async def _grab_stats(self) -> dict:
        """Collect the raw stats. Blocking calls go through asyncio.to_thread()."""
        value = await asyncio.to_thread(psutil.cpu_percent)
        return {"field_name": value}
```

### Key conventions

- Class name: `PluginModel` (exactly), in `glances/plugins/<name>/model.py`
- Inherit from `GlancesPluginBase[dict]` (scalar) or `GlancesPluginBase[list]`
  (collection, `IS_COLLECTION = True`, exactly one field with `primary_key: True`)
- `_grab_stats()` is the only mandatory hook; never override `update()`
- `fields_description` declares metadata for each field (unit, thresholds,
  `rate`, `watched`, `exportable`); undeclared fields are stripped
- Keep `model.py` free of curses / UI code — layout goes in `render_curses.py`
- No SNMP: SNMP is not ported to v5

### After creation

1. Create a test file: `tests/test_plugin_<name>.py` (and
   `tests/test_plugin_<name>_render_curses.py` with a `render_curses.py`)
2. Run `make test-plugins` to verify
3. Add configuration section in `conf/glances.conf` if needed
