#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Vms plugin."""

from copy import deepcopy
from typing import Any, Optional

from glances.globals import iteritems
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel
from glances.plugins.vms.engines import VmsExtension
from glances.plugins.vms.engines.multipass import VmExtension
from glances.processes import glances_processes
from glances.processes import sort_stats as sort_stats_processes

# Fields description
# description: human readable description
# short_name: shortname to use un UI
# unit: unit type
# rate: is it a rate ? If yes, // by time_since_update when displayed,
# min_symbol: Auto unit should be used if value > than 1 'X' (K, M, G)...
fields_description = {
    'name': {
        'description': 'Vm name',
    },
    'id': {
        'description': 'Vm ID',
    },
    'release': {
        'description': 'Vm release',
    },
    'status': {
        'description': 'Vm status',
    },
    'cpu_count': {
        'description': 'Vm CPU count',
    },
    'memory_usage': {
        'description': 'Vm memory usage',
        'unit': 'byte',
    },
    'memory_total': {
        'description': 'Vm memory total',
        'unit': 'byte',
    },
    'load_1min': {
        'description': 'Vm Load last 1 min',
    },
    'load_5min': {
        'description': 'Vm Load last 5 mins',
    },
    'load_15min': {
        'description': 'Vm Load last 15 mins',
    },
    'ipv4': {
        'description': 'Vm IP v4 address',
    },
    'engine': {
        'description': 'VM engine name (only Mutlipass is currently supported)',
    },
    'engine_version': {
        'description': 'VM engine version',
    },
}

# Define the items history list (list of items to add to history)
items_history_list = [{'name': 'memory_usage', 'description': 'Vm MEM usage', 'y_unit': 'byte'}]

# List of key to remove before export
export_exclude_list = []

# Sort dictionary for human
sort_for_human = {
    'cpu_count': 'CPU count',
    'memory_usage': 'memory consumption',
    'load_1min': 'load',
    'name': 'VM name',
    None: 'None',
}


class PluginModel(GlancesPluginModel):
    """Glances Vm plugin.

    stats is a dict: {'version': {...}, 'vms': [{}, {}]}
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args, config=config, items_history_list=items_history_list, fields_description=fields_description
        )

        # The plugin can be disabled using: args.disable_vm
        self.args = args

        # Default config keys
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        self.watchers: dict[str, VmsExtension] = {}

        # Init the Multipass API
        self.watchers['multipass'] = VmExtension()

        # Sort key
        self.sort_key = None

    def get_key(self) -> str:
        """Return the key of the list."""
        return 'name'

    def get_export(self) -> list[dict]:
        """Overwrite the default export method.

        - Only exports vms
        - The key is the first vm name
        """
        try:
            ret = deepcopy(self.stats)
        except KeyError as e:
            logger.debug(f"vm plugin - Vm export error {e}")
            ret = []

        # Remove fields uses to compute rate
        for vm in ret:
            for i in export_exclude_list:
                vm.pop(i)

        return ret

    def _all_tag(self) -> bool:
        """Return the all tag of the Glances/Vm configuration file.

        # By default, Glances only display running vms
        # Set the following key to True to display all vms
        all=True
        """
        all_tag = self.get_conf_value('all')
        if not all_tag:
            return False
        return all_tag[0].lower() == 'true'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self) -> list[dict]:
        """Update VMs stats using the input method."""
        # Connection should be ok
        if not self.watchers or self.input_method != 'local':
            return self.get_init_value()

        # Update stats
        stats = []
        for engine, watcher in iteritems(self.watchers):
            version, vms = watcher.update(all_tag=self._all_tag())
            for vm in vms:
                vm["engine"] = engine
                vm["engine_version"] = version
            stats.extend(vms)

        # Sort and update the stats
        # TODO: test
        self.sort_key, self.stats = sort_vm_stats(stats)
        return self.stats

    def update_views(self) -> bool:
        """Update stats views."""
        # Call the father's method
        super().update_views()

        if not self.stats:
            return False

        # Display Engine ?
        show_engine_name = False
        if len({ct["engine"] for ct in self.stats}) > 1:
            show_engine_name = True
        self.views['show_engine_name'] = show_engine_name

        return True

    def msg_curse(self, args=None, max_width: Optional[int] = None) -> list[str]:
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist (and non null) and display plugin enable...
        if not self.stats or len(self.stats) == 0 or self.is_disabled():
            return ret

        # Build the string message
        # Title
        msg = '{}'.format('VMs')
        ret.append(self.curse_add_line(msg, "TITLE"))
        if len(self.stats) > 1:
            msg = f' {len(self.stats)}'
            ret.append(self.curse_add_line(msg))
            msg = f' sorted by {sort_for_human[self.sort_key]}'
            ret.append(self.curse_add_line(msg))
        if not self.views['show_engine_name']:
            msg = f' (served by {self.stats[0].get("engine", "")})'
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        # Header
        ret.append(self.curse_new_line())
        # Get the maximum VMs name
        # Max size is configurable. See feature request #1723.
        name_max_width = min(
            self.config.get_int_value('vms', 'max_name_size', default=20) if self.config is not None else 20,
            len(max(self.stats, key=lambda x: len(x['name']))['name']),
        )

        if self.views['show_engine_name']:
            msg = ' {:{width}}'.format('Engine', width=8)
            ret.append(self.curse_add_line(msg))
        msg = ' {:{width}}'.format('Name', width=name_max_width)
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'name' else 'DEFAULT'))
        msg = '{:>10}'.format('Status')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format('Core')
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'cpu_count' else 'DEFAULT'))
        msg = '{:>7}'.format('MEM')
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'memory_usage' else 'DEFAULT'))
        msg = '/{:<7}'.format('MAX')
        ret.append(self.curse_add_line(msg))
        msg = '{:>17}'.format('LOAD 1/5/15min')
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'load_1min' else 'DEFAULT'))
        msg = '{:>10}'.format('Release')
        ret.append(self.curse_add_line(msg))

        # Data
        for vm in self.stats:
            ret.append(self.curse_new_line())
            if self.views['show_engine_name']:
                ret.append(self.curse_add_line(' {:{width}}'.format(vm["engine"], width=8)))
            # Name
            ret.append(self.curse_add_line(' {:{width}}'.format(vm['name'][:name_max_width], width=name_max_width)))
            # Status
            status = self.vm_alert(vm['status'])
            msg = '{:>10}'.format(vm['status'][0:10])
            ret.append(self.curse_add_line(msg, status))
            # CPU (count)
            try:
                msg = '{:>6}'.format(vm['cpu_count'])
            except (KeyError, TypeError):
                msg = '{:>6}'.format('-')
            ret.append(self.curse_add_line(msg, self.get_views(item=vm['name'], key='cpu_count', option='decoration')))
            # MEM
            try:
                msg = '{:>7}'.format(self.auto_unit(vm['memory_usage']))
            except KeyError:
                msg = '{:>7}'.format('-')
            ret.append(
                self.curse_add_line(msg, self.get_views(item=vm['name'], key='memory_usage', option='decoration'))
            )
            try:
                msg = '/{:<7}'.format(self.auto_unit(vm['memory_total']))
            except (KeyError, TypeError):
                msg = '/{:<7}'.format('-')
            ret.append(self.curse_add_line(msg))
            # LOAD
            try:
                msg = '{:>5.1f}/{:>5.1f}/{:>5.1f}'.format(vm['load_1min'], vm['load_5min'], vm['load_15min'])
            except (KeyError, TypeError):
                msg = '{:>5}/{:>5}/{:>5}'.format('-', '-', '-')
            ret.append(self.curse_add_line(msg, self.get_views(item=vm['name'], key='load_1min', option='decoration')))
            # Release
            if vm['release'] is not None:
                msg = '   {}'.format(vm['release'])
            else:
                msg = '   {}'.format('-')
            ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    @staticmethod
    def vm_alert(status: str) -> str:
        """Analyse the vm status.
        For multipass: https://multipass.run/docs/instance-states
        """
        if status == 'running':
            return 'OK'
        if status in ['starting', 'restarting', 'delayed shutdown']:
            return 'WARNING'
        return 'INFO'


def sort_vm_stats(stats: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    # Make VM sort related to process sort
    if glances_processes.sort_key == 'memory_percent':
        sort_by = 'memory_usage'
        sort_by_secondary = 'load_1min'
    elif glances_processes.sort_key == 'name':
        sort_by = 'name'
        sort_by_secondary = 'load_1min'
    else:
        sort_by = 'load_1min'
        sort_by_secondary = 'memory_usage'

    # Sort vm stats
    sort_stats_processes(
        stats,
        sorted_by=sort_by,
        sorted_by_secondary=sort_by_secondary,
        # Reverse for all but name
        reverse=glances_processes.sort_key != 'name',
    )

    # Return the main sort key and the sorted stats
    return sort_by, stats
