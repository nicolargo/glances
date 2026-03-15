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
    __init__.py    # Plugin implementation
```

No registration needed — plugins are auto-discovered.

### Template

The plugin `__init__.py` must follow this pattern:

```python
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""<Name> plugin."""

from glances.plugins.plugin.model import GlancesPluginModel

# Fields description
# https://github.com/nicolargo/glances/wiki/How-to-create-a-new-plugin-%3F
fields_description = {
    'field_name': {
        'description': 'Human-readable description.',
        'unit': 'percent',  # percent, number, bytes, seconds, etc.
    },
}

class <Name>Plugin(GlancesPluginModel):
    """Glances <name> plugin."""

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args,
            config=config,
            fields_description=fields_description,
        )

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update the stats."""
        if self.input_method == 'local':
            stats = {}
            # Collect stats here (e.g., from psutil)
        else:
            stats = self.get_init_value()
        self.stats = stats
        return self.stats
```

### Key conventions

- Class name: `<Name>Plugin` (CamelCase with `Plugin` suffix)
- The `update()` method must use `@GlancesPluginModel._check_decorator` and `@GlancesPluginModel._log_result_decorator`
- `fields_description` declares metadata for each stat field (unit, thresholds, rates, alerts)
- Use `self.input_method == 'local'` to distinguish local vs SNMP/remote collection
- Optional: add `items_history_list` for time-series history support
- Optional: add `snmp_oid` dict for SNMP support
- If the plugin depends on another plugin, declare it in `glances/plugins/plugin/dag.py`

### After creation

1. Create a test file: `tests/test_plugin_<name>.py`
2. Run `make test-plugins` to verify
3. Add configuration section in `conf/glances.conf` if needed
