#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Containers plugin."""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from glances.globals import iteritems, itervalues
from glances.logger import logger
from glances.plugins.containers.engines import ContainersExtension
from glances.plugins.containers.engines.docker import DockerExtension, import_docker_error_tag
from glances.plugins.containers.engines.podman import PodmanExtension, import_podman_error_tag
from glances.plugins.plugin.model import GlancesPluginModel
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
        'description': 'Container name',
    },
    'id': {
        'description': 'Container ID',
    },
    'image': {
        'description': 'Container image',
    },
    'status': {
        'description': 'Container status',
    },
    'created': {
        'description': 'Container creation date',
    },
    'command': {
        'description': 'Container command',
    },
    'cpu_percent': {
        'description': 'Container CPU consumption',
        'unit': 'percent',
    },
    'memory_usage': {
        'description': 'Container memory usage',
        'unit': 'byte',
    },
    'io_rx': {
        'description': 'Container IO bytes read rate',
        'unit': 'bytepersecond',
    },
    'io_wx': {
        'description': 'Container IO bytes write rate',
        'unit': 'bytepersecond',
    },
    'network_rx': {
        'description': 'Container network RX bitrate',
        'unit': 'bitpersecond',
    },
    'network_tx': {
        'description': 'Container network TX bitrate',
        'unit': 'bitpersecond',
    },
    'uptime': {
        'description': 'Container uptime',
    },
    'engine': {
        'description': 'Container engine (Docker and Podman are currently supported)',
    },
    'pod_name': {
        'description': 'Pod name (only with Podman)',
    },
    'pod_id': {
        'description': 'Pod ID (only with Podman)',
    },
}

# Define the items history list (list of items to add to history)
# TODO: For the moment limited to the CPU. Had to change the graph exports
#       method to display one graph per container.
# items_history_list = [{'name': 'cpu_percent',
#                        'description': 'Container CPU consumption in %',
#                        'y_unit': '%'},
#                       {'name': 'memory_usage',
#                        'description': 'Container memory usage in bytes',
#                        'y_unit': 'B'},
#                       {'name': 'network_rx',
#                        'description': 'Container network RX bitrate in bits per second',
#                        'y_unit': 'bps'},
#                       {'name': 'network_tx',
#                        'description': 'Container network TX bitrate in bits per second',
#                        'y_unit': 'bps'},
#                       {'name': 'io_r',
#                        'description': 'Container IO bytes read per second',
#                        'y_unit': 'Bps'},
#                       {'name': 'io_w',
#                        'description': 'Container IO bytes write per second',
#                        'y_unit': 'Bps'}]
items_history_list = [{'name': 'cpu_percent', 'description': 'Container CPU consumption in %', 'y_unit': '%'}]

# List of key to remove before export
export_exclude_list = ['cpu', 'io', 'memory', 'network']

# Sort dictionary for human
sort_for_human = {
    'io_counters': 'disk IO',
    'cpu_percent': 'CPU consumption',
    'memory_usage': 'memory consumption',
    'cpu_times': 'uptime',
    'name': 'container name',
    None: 'None',
}


class PluginModel(GlancesPluginModel):
    """Glances Docker plugin.

    stats is a dict: {'version': {...}, 'containers': [{}, {}]}
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(
            args=args, config=config, items_history_list=items_history_list, fields_description=fields_description
        )

        # The plugin can be disabled using: args.disable_docker
        self.args = args

        # Default config keys
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        self.watchers: Dict[str, ContainersExtension] = {}

        # Init the Docker API
        if not import_docker_error_tag:
            self.watchers['docker'] = DockerExtension()

        # Init the Podman API
        if not import_podman_error_tag:
            self.watchers['podman'] = PodmanExtension(podman_sock=self._podman_sock())

        # Sort key
        self.sort_key = None

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def _podman_sock(self) -> str:
        """Return the podman sock.
        Could be desfined in the [docker] section thanks to the podman_sock option.
        Default value: unix:///run/user/1000/podman/podman.sock
        """
        conf_podman_sock = self.get_conf_value('podman_sock')
        if len(conf_podman_sock) == 0:
            return "unix:///run/user/1000/podman/podman.sock"
        return conf_podman_sock[0]

    def exit(self) -> None:
        """Overwrite the exit method to close threads."""
        for watcher in itervalues(self.watchers):
            watcher.stop()

        # Call the father class
        super().exit()

    def get_key(self) -> str:
        """Return the key of the list."""
        return 'name'

    def get_export(self) -> List[Dict]:
        """Overwrite the default export method.

        - Only exports containers
        - The key is the first container name
        """
        try:
            ret = deepcopy(self.stats)
        except KeyError as e:
            logger.debug(f"docker plugin - Docker export error {e}")
            ret = []

        # Remove fields uses to compute rate
        for container in ret:
            for i in export_exclude_list:
                container.pop(i)

        return ret

    def _all_tag(self) -> bool:
        """Return the all tag of the Glances/Docker configuration file.

        # By default, Glances only display running containers
        # Set the following key to True to display all containers
        all=True
        """
        all_tag = self.get_conf_value('all')
        if len(all_tag) == 0:
            return False
        return all_tag[0].lower() == 'true'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self) -> List[Dict]:
        """Update Docker and podman stats using the input method."""
        # Connection should be ok
        if not self.watchers:
            return self.get_init_value()

        if self.input_method != 'local':
            return self.get_init_value()

        # Update stats
        stats = []
        for engine, watcher in iteritems(self.watchers):
            version, containers = watcher.update(all_tag=self._all_tag())
            for container in containers:
                container["engine"] = 'docker'
            stats.extend(containers)

        # Sort and update the stats
        # @TODO: Have a look because sort did not work for the moment (need memory stats ?)
        self.sort_key, self.stats = sort_docker_stats(stats)
        return self.stats

    @staticmethod
    def memory_usage_no_cache(mem: Dict[str, float]) -> float:
        """Return the 'real' memory usage by removing inactive_file to usage"""
        # Ref: https://github.com/docker/docker-py/issues/3210
        return mem['usage'] - (mem['inactive_file'] if 'inactive_file' in mem else 0)

    def update_views(self) -> bool:
        """Update stats views."""
        # Call the father's method
        super().update_views()

        if not self.stats:
            return False

        # Add specifics information
        # Alert
        for i in self.stats:
            # Init the views for the current container (key = container name)
            self.views[i[self.get_key()]] = {'cpu': {}, 'mem': {}}
            # CPU alert
            if 'cpu' in i and 'total' in i['cpu']:
                # Looking for specific CPU container threshold in the conf file
                alert = self.get_alert(i['cpu']['total'], header=i['name'] + '_cpu', action_key=i['name'])
                if alert == 'DEFAULT':
                    # Not found ? Get back to default CPU threshold value
                    alert = self.get_alert(i['cpu']['total'], header='cpu')
                self.views[i[self.get_key()]]['cpu']['decoration'] = alert
            # MEM alert
            if 'memory' in i and 'usage' in i['memory']:
                # Looking for specific MEM container threshold in the conf file
                alert = self.get_alert(
                    self.memory_usage_no_cache(i['memory']),
                    maximum=i['memory']['limit'],
                    header=i['name'] + '_mem',
                    action_key=i['name'],
                )
                if alert == 'DEFAULT':
                    # Not found ? Get back to default MEM threshold value
                    alert = self.get_alert(
                        self.memory_usage_no_cache(i['memory']), maximum=i['memory']['limit'], header='mem'
                    )
                self.views[i[self.get_key()]]['mem']['decoration'] = alert

        # Display Engine and Pod name ?
        show_pod_name = False
        if any(ct.get("pod_name") for ct in self.stats):
            show_pod_name = True
        self.views['show_pod_name'] = show_pod_name
        show_engine_name = False
        if len({ct["engine"] for ct in self.stats}) > 1:
            show_engine_name = True
        self.views['show_engine_name'] = show_engine_name

        return True

    def msg_curse(self, args=None, max_width: Optional[int] = None) -> List[str]:
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist (and non null) and display plugin enable...
        if not self.stats or len(self.stats) == 0 or self.is_disabled():
            return ret

        # Build the string message
        # Title
        msg = '{}'.format('CONTAINERS')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = f' {len(self.stats)}'
        ret.append(self.curse_add_line(msg))
        msg = f' sorted by {sort_for_human[self.sort_key]}'
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        # Header
        ret.append(self.curse_new_line())
        # Get the maximum containers name
        # Max size is configurable. See feature request #1723.
        name_max_width = min(
            self.config.get_int_value('containers', 'max_name_size', default=20) if self.config is not None else 20,
            len(max(self.stats, key=lambda x: len(x['name']))['name']),
        )

        if self.views['show_engine_name']:
            msg = ' {:{width}}'.format('Engine', width=6)
            ret.append(self.curse_add_line(msg))
        if self.views['show_pod_name']:
            msg = ' {:{width}}'.format('Pod', width=12)
            ret.append(self.curse_add_line(msg))
        msg = ' {:{width}}'.format('Name', width=name_max_width)
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'name' else 'DEFAULT'))
        msg = '{:>10}'.format('Status')
        ret.append(self.curse_add_line(msg))
        msg = '{:>10}'.format('Uptime')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format('CPU%')
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'cpu_percent' else 'DEFAULT'))
        msg = '{:>7}'.format('MEM')
        ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'memory_usage' else 'DEFAULT'))
        msg = '/{:<7}'.format('MAX')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('IOR/s')
        ret.append(self.curse_add_line(msg))
        msg = ' {:<7}'.format('IOW/s')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('Rx/s')
        ret.append(self.curse_add_line(msg))
        msg = ' {:<7}'.format('Tx/s')
        ret.append(self.curse_add_line(msg))
        msg = ' {:8}'.format('Command')
        ret.append(self.curse_add_line(msg))

        # Data
        for container in self.stats:
            ret.append(self.curse_new_line())
            if self.views['show_engine_name']:
                ret.append(self.curse_add_line(' {:{width}}'.format(container["engine"], width=6)))
            if self.views['show_pod_name']:
                ret.append(self.curse_add_line(' {:{width}}'.format(container.get("pod_id", "-"), width=12)))
            # Name
            ret.append(
                self.curse_add_line(' {:{width}}'.format(container['name'][:name_max_width], width=name_max_width))
            )
            # Status
            status = self.container_alert(container['status'])
            msg = '{:>10}'.format(container['status'][0:10])
            ret.append(self.curse_add_line(msg, status))
            # Uptime
            if container['uptime']:
                msg = '{:>10}'.format(container['uptime'])
            else:
                msg = '{:>10}'.format('_')
            ret.append(self.curse_add_line(msg))
            # CPU
            try:
                msg = '{:>6.1f}'.format(container['cpu']['total'])
            except (KeyError, TypeError):
                msg = '{:>6}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'], key='cpu', option='decoration')))
            # MEM
            try:
                msg = '{:>7}'.format(self.auto_unit(self.memory_usage_no_cache(container['memory'])))
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'], key='mem', option='decoration')))
            try:
                msg = '/{:<7}'.format(self.auto_unit(container['memory']['limit']))
            except (KeyError, TypeError):
                msg = '/{:<7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # IO R/W
            unit = 'B'
            try:
                value = self.auto_unit(int(container['io_rx'])) + unit
                msg = f'{value:>7}'
            except (KeyError, TypeError):
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg))
            try:
                value = self.auto_unit(int(container['io_wx'])) + unit
                msg = f' {value:<7}'
            except (KeyError, TypeError):
                msg = ' {:<7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # NET RX/TX
            if args.byte:
                # Bytes per second (for dummy)
                to_bit = 1
                unit = ''
            else:
                # Bits per second (for real network administrator | Default)
                to_bit = 8
                unit = 'b'
            try:
                value = self.auto_unit(int(container['network_rx'] * to_bit)) + unit
                msg = f'{value:>7}'
            except (KeyError, TypeError):
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg))
            try:
                value = self.auto_unit(int(container['network_tx'] * to_bit)) + unit
                msg = f' {value:<7}'
            except (KeyError, TypeError):
                msg = ' {:<7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # Command
            if container['command'] is not None:
                msg = ' {}'.format(container['command'])
            else:
                msg = ' {}'.format('_')
            ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    @staticmethod
    def container_alert(status: str) -> str:
        """Analyse the container status."""
        if status == 'running':
            return 'OK'
        if status == 'exited':
            return 'WARNING'
        if status == 'dead':
            return 'CRITICAL'
        return 'CAREFUL'


def sort_docker_stats(stats: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    # Sort Docker stats using the same function than processes
    sort_by = glances_processes.sort_key
    sort_by_secondary = 'memory_usage'
    if sort_by == 'memory_percent':
        sort_by = 'memory_usage'
        sort_by_secondary = 'cpu_percent'
    elif sort_by in ['username', 'io_counters', 'cpu_times']:
        sort_by = 'cpu_percent'

    # Sort docker stats
    sort_stats_processes(
        stats,
        sorted_by=sort_by,
        sorted_by_secondary=sort_by_secondary,
        # Reverse for all but name
        reverse=glances_processes.sort_key != 'name',
    )

    # Return the main sort key and the sorted stats
    return sort_by, stats
