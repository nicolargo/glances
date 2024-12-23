#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Containers plugin."""

from copy import deepcopy
from functools import partial, reduce
from typing import Any, Optional

from glances.globals import iteritems, itervalues, nativestr
from glances.logger import logger
from glances.plugins.containers.engines import ContainersExtension
from glances.plugins.containers.engines.docker import DockerExtension, disable_plugin_docker
from glances.plugins.containers.engines.podman import PodmanExtension, disable_plugin_podman
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

        self.watchers: dict[str, ContainersExtension] = {}

        # Init the Docker API
        if not disable_plugin_docker:
            self.watchers['docker'] = DockerExtension()

        # Init the Podman API
        if not disable_plugin_podman:
            self.watchers['podman'] = PodmanExtension(podman_sock=self._podman_sock())

        # Sort key
        self.sort_key = None

        # Set the key's list be disabled in order to only display specific attribute in the container list
        self.disable_stats = self.get_conf_value('disable_stats')

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def _podman_sock(self) -> str:
        """Return the podman sock.
        Could be desfined in the [docker] section thanks to the podman_sock option.
        Default value: unix:///run/user/1000/podman/podman.sock
        """
        conf_podman_sock = self.get_conf_value('podman_sock')
        if not conf_podman_sock:
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

    def get_export(self) -> list[dict]:
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
        if not all_tag:
            return False
        return all_tag[0].lower() == 'true'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self) -> list[dict]:
        """Update Docker and podman stats using the input method."""
        # Connection should be ok
        if not self.watchers:
            return self.get_init_value()

        if self.input_method != 'local':
            return self.get_init_value()

        # Update stats
        stats = []
        for engine, watcher in iteritems(self.watchers):
            _, containers = watcher.update(all_tag=self._all_tag())
            containers_filtered = []
            for container in containers:
                container["engine"] = engine
                if 'key' in container and container['key'] in container:
                    if not self.is_hide(nativestr(container[container['key']])):
                        containers_filtered.append(container)
                else:
                    containers_filtered.append(container)
            stats.extend(containers_filtered)

        # Sort and update the stats
        # @TODO: Have a look because sort did not work for the moment (need memory stats ?)
        self.sort_key, self.stats = sort_docker_stats(stats)
        return self.stats

    @staticmethod
    def memory_usage_no_cache(mem: dict[str, float]) -> float:
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

    def build_title(self, ret):
        msg = '{}'.format('CONTAINERS')
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
        return ret

    def maybe_add_engine_name_or_pod_line(self, ret):
        if self.views['show_engine_name']:
            ret = self.add_msg_to_line(ret, ' {:{width}}'.format('Engine', width=6))
        if self.views['show_pod_name']:
            ret = self.add_msg_to_line(ret, ' {:{width}}'.format('Pod', width=12))

        return ret

    def maybe_add_engine_name_or_pod_name(self, ret, container):
        ret.append(self.curse_new_line())
        if self.views['show_engine_name']:
            ret.append(self.curse_add_line(' {:{width}}'.format(container["engine"], width=6)))
        if self.views['show_pod_name']:
            ret.append(self.curse_add_line(' {:{width}}'.format(container.get("pod_id", "-"), width=12)))

        return ret

    def build_container_name(self, name_max_width):
        def build_for_this_max_length(ret, container):
            ret.append(
                self.curse_add_line(' {:{width}}'.format(container['name'][:name_max_width], width=name_max_width))
            )

            return ret

        return build_for_this_max_length

    def build_header(self, ret, name_max_width):
        ret.append(self.curse_new_line())

        ret = self.maybe_add_engine_name_or_pod_line(ret)

        if 'name' not in self.disable_stats:
            msg = ' {:{width}}'.format('Name', width=name_max_width)
            ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'name' else 'DEFAULT'))

        msgs = []
        if 'status' not in self.disable_stats:
            msgs.append('{:>10}'.format('Status'))
        if 'uptime' not in self.disable_stats:
            msgs.append('{:>10}'.format('Uptime'))
        ret = reduce(self.add_msg_to_line, msgs, ret)

        if 'cpu' not in self.disable_stats:
            msg = '{:>6}'.format('CPU%')
            ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'cpu_percent' else 'DEFAULT'))

        msgs = []
        if 'mem' not in self.disable_stats:
            msg = '{:>7}'.format('MEM')
            ret.append(self.curse_add_line(msg, 'SORT' if self.sort_key == 'memory_usage' else 'DEFAULT'))
            msgs.append('/{:<7}'.format('MAX'))

        if 'diskio' not in self.disable_stats:
            msgs.extend(['{:>7}'.format('IOR/s'), ' {:<7}'.format('IOW/s')])

        if 'networkio' not in self.disable_stats:
            msgs.extend(['{:>7}'.format('Rx/s'), ' {:<7}'.format('Tx/s')])

        if 'command' not in self.disable_stats:
            msgs.append(' {:8}'.format('Command'))

        return reduce(self.add_msg_to_line, msgs, ret)

    def add_msg_to_line(self, ret, msg):
        ret.append(self.curse_add_line(msg))

        return ret

    def get_max_of_container_names(self):
        return min(
            self.config.get_int_value('containers', 'max_name_size', default=20) if self.config is not None else 20,
            len(max(self.stats, key=lambda x: len(x['name']))['name']),
        )

    def build_status_name(self, ret, container):
        status = self.container_alert(container['status'])
        msg = '{:>10}'.format(container['status'][0:10])
        ret.append(self.curse_add_line(msg, status))

        return ret

    def build_uptime_line(self, ret, container):
        if container['uptime']:
            msg = '{:>10}'.format(container['uptime'])
        else:
            msg = '{:>10}'.format('_')

        return self.add_msg_to_line(ret, msg)

    def build_cpu_line(self, ret, container):
        try:
            msg = '{:>6.1f}'.format(container['cpu']['total'])
        except (KeyError, TypeError):
            msg = '{:>6}'.format('_')
        ret.append(self.curse_add_line(msg, self.get_views(item=container['name'], key='cpu', option='decoration')))

        return ret

    def build_memory_line(self, ret, container):
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

        return ret

    def build_io_line(self, ret, container):
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

        return ret

    def build_net_line(self, args):
        def build_with_this_args(ret, container):
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

            return ret

        return build_with_this_args

    def build_cmd_line(self, ret, container):
        if container['command'] is not None:
            msg = ' {}'.format(container['command'])
        else:
            msg = ' {}'.format('_')
        ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    def msg_curse(self, args=None, max_width: Optional[int] = None) -> list[str]:
        """Return the dict to display in the curse interface."""
        # Init the return message
        init = []

        # Only process if stats exist (and non null) and display plugin enable...
        conditions = [not self.stats, len(self.stats) == 0, self.is_disabled()]
        if any(conditions):
            return init

        # Build the string message
        # Get the maximum containers name
        # Max size is configurable. See feature request #1723.
        name_max_width = self.get_max_of_container_names()

        steps = [
            self.build_title,
            partial(self.build_header, name_max_width=name_max_width),
            self.build_data_line(name_max_width, args),
        ]

        return reduce(lambda ret, step: step(ret), steps, init)

    def build_data_line(self, name_max_width, args):
        def build_for_this_params(ret):
            build_data_with_params = self.build_container_data(name_max_width, args)
            return reduce(build_data_with_params, self.stats, ret)

        return build_for_this_params

    def build_container_data(self, name_max_width, args):
        def build_with_this_params(ret, container):
            steps = [self.maybe_add_engine_name_or_pod_name]
            if 'name' not in self.disable_stats:
                steps.append(self.build_container_name(name_max_width))
            if 'status' not in self.disable_stats:
                steps.append(self.build_status_name)
            if 'uptime' not in self.disable_stats:
                steps.append(self.build_uptime_line)
            if 'cpu' not in self.disable_stats:
                steps.append(self.build_cpu_line)
            if 'mem' not in self.disable_stats:
                steps.append(self.build_memory_line)
            if 'diskio' not in self.disable_stats:
                steps.append(self.build_io_line)
            if 'networkio' not in self.disable_stats:
                steps.append(self.build_net_line(args))
            if 'command' not in self.disable_stats:
                steps.append(self.build_cmd_line)

            return reduce(lambda ret, step: step(ret, container), steps, ret)

        return build_with_this_params

    @staticmethod
    def container_alert(status: str) -> str:
        """Analyse the container status.
        One of created, restarting, running, removing, paused, exited, or dead
        """
        if status == 'running':
            return 'OK'
        if status == 'dead':
            return 'ERROR'
        if status in ['created', 'restarting', 'exited']:
            return 'WARNING'
        return 'INFO'


def sort_docker_stats(stats: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    # Make VM sort related to process sort
    if glances_processes.sort_key == 'memory_percent':
        sort_by = 'memory_usage'
        sort_by_secondary = 'cpu_percent'
    elif glances_processes.sort_key == 'name':
        sort_by = 'name'
        sort_by_secondary = 'cpu_percent'
    else:
        sort_by = 'cpu_percent'
        sort_by_secondary = 'memory_usage'

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
