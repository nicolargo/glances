# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Containers plugin."""

import os
from copy import deepcopy

from glances.logger import logger
from glances.plugins.containers.engines.docker import DockerContainersExtension, import_docker_error_tag
from glances.plugins.containers.engines.podman import PodmanContainersExtension, import_podman_error_tag
from glances.plugins.plugin.model import GlancesPluginModel
from glances.processes import glances_processes
from glances.processes import sort_stats as sort_stats_processes

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
        super(PluginModel, self).__init__(args=args, config=config, items_history_list=items_history_list)

        # The plugin can be disabled using: args.disable_docker
        self.args = args

        # Default config keys
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the Docker API
        self.docker_extension = DockerContainersExtension() if not import_docker_error_tag else None

        # Init the Podman API
        if import_podman_error_tag:
            self.podman_client = None
        else:
            self.podman_client = PodmanContainersExtension(podman_sock=self._podman_sock())

        # Sort key
        self.sort_key = None

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def _podman_sock(self):
        """Return the podman sock.
        Could be desfined in the [docker] section thanks to the podman_sock option.
        Default value: unix:///run/user/1000/podman/podman.sock
        """
        conf_podman_sock = self.get_conf_value('podman_sock')
        if len(conf_podman_sock) == 0:
            return "unix:///run/user/1000/podman/podman.sock"
        else:
            return conf_podman_sock[0]

    def exit(self):
        """Overwrite the exit method to close threads."""
        if self.docker_extension:
            self.docker_extension.stop()
        if self.podman_client:
            self.podman_client.stop()
        # Call the father class
        super(PluginModel, self).exit()

    def get_key(self):
        """Return the key of the list."""
        return 'name'

    def get_export(self):
        """Overwrite the default export method.

        - Only exports containers
        - The key is the first container name
        """
        try:
            ret = deepcopy(self.stats['containers'])
        except KeyError as e:
            logger.debug("docker plugin - Docker export error {}".format(e))
            ret = []

        # Remove fields uses to compute rate
        for container in ret:
            for i in export_exclude_list:
                container.pop(i)

        return ret

    def _all_tag(self):
        """Return the all tag of the Glances/Docker configuration file.

        # By default, Glances only display running containers
        # Set the following key to True to display all containers
        all=True
        """
        all_tag = self.get_conf_value('all')
        if len(all_tag) == 0:
            return False
        else:
            return all_tag[0].lower() == 'true'

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
    def update(self):
        """Update Docker and podman stats using the input method."""
        # Connection should be ok
        if self.docker_extension is None and self.podman_client is None:
            return self.get_init_value()

        if self.input_method == 'local':
            # Update stats
            stats_docker = self.update_docker() if self.docker_extension else {}
            stats_podman = self.update_podman() if self.podman_client else {}
            stats = {
                'version': stats_docker.get('version', {}),
                'version_podman': stats_podman.get('version', {}),
                'containers': stats_docker.get('containers', []) + stats_podman.get('containers', []),
            }
        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not available
            pass

        # Sort and update the stats
        # @TODO: Have a look because sort did not work for the moment (need memory stats ?)
        self.sort_key, self.stats = sort_docker_stats(stats)

        return self.stats

    def update_docker(self):
        """Update Docker stats using the input method."""
        version, containers = self.docker_extension.update(all_tag=self._all_tag())
        for container in containers:
            container["engine"] = 'docker'
        return {"version": version, "containers": containers}

    def update_podman(self):
        """Update Podman stats."""
        version, containers = self.podman_client.update(all_tag=self._all_tag())
        for container in containers:
            container["engine"] = 'podman'
        return {"version": version, "containers": containers}

    def get_user_ticks(self):
        """Return the user ticks by reading the environment variable."""
        return os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    def get_stats_action(self):
        """Return stats for the action.

        Docker will return self.stats['containers']
        """
        return self.stats['containers']

    def update_views(self):
        """Update stats views."""
        # Call the father's method
        super(PluginModel, self).update_views()

        if 'containers' not in self.stats:
            return False

        # Add specifics information
        # Alert
        for i in self.stats['containers']:
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
                    i['memory']['usage'], maximum=i['memory']['limit'], header=i['name'] + '_mem', action_key=i['name']
                )
                if alert == 'DEFAULT':
                    # Not found ? Get back to default MEM threshold value
                    alert = self.get_alert(i['memory']['usage'], maximum=i['memory']['limit'], header='mem')
                self.views[i[self.get_key()]]['mem']['decoration'] = alert

        return True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist (and non null) and display plugin enable...
        if not self.stats or 'containers' not in self.stats or len(self.stats['containers']) == 0 or self.is_disabled():
            return ret

        show_pod_name = False
        if any(ct.get("pod_name") for ct in self.stats["containers"]):
            show_pod_name = True

        show_engine_name = False
        if len(set(ct["engine"] for ct in self.stats["containers"])) > 1:
            show_engine_name = True

        # Build the string message
        # Title
        msg = '{}'.format('CONTAINERS')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {}'.format(len(self.stats['containers']))
        ret.append(self.curse_add_line(msg))
        msg = ' sorted by {}'.format(sort_for_human[self.sort_key])
        ret.append(self.curse_add_line(msg))
        # msg = ' (served by Docker {})'.format(self.stats['version']["Version"])
        # ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        # Header
        ret.append(self.curse_new_line())
        # Get the maximum containers name
        # Max size is configurable. See feature request #1723.
        name_max_width = min(
            self.config.get_int_value('containers', 'max_name_size', default=20) if self.config is not None else 20,
            len(max(self.stats['containers'], key=lambda x: len(x['name']))['name']),
        )

        if show_engine_name:
            msg = ' {:{width}}'.format('Engine', width=6)
            ret.append(self.curse_add_line(msg))
        if show_pod_name:
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
        for container in self.stats['containers']:
            ret.append(self.curse_new_line())
            if show_engine_name:
                ret.append(self.curse_add_line(' {:{width}}'.format(container["engine"], width=6)))
            if show_pod_name:
                ret.append(self.curse_add_line(' {:{width}}'.format(container.get("pod_id", "-"), width=12)))
            # Name
            ret.append(self.curse_add_line(self._msg_name(container=container, max_width=name_max_width)))
            # Status
            status = self.container_alert(container['Status'])
            msg = '{:>10}'.format(container['Status'][0:10])
            ret.append(self.curse_add_line(msg, status))
            # Uptime
            if container['Uptime']:
                msg = '{:>10}'.format(container['Uptime'])
            else:
                msg = '{:>10}'.format('_')
            ret.append(self.curse_add_line(msg))
            # CPU
            try:
                msg = '{:>6.1f}'.format(container['cpu']['total'])
            except KeyError:
                msg = '{:>6}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'], key='cpu', option='decoration')))
            # MEM
            try:
                msg = '{:>7}'.format(self.auto_unit(container['memory']['usage']))
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'], key='mem', option='decoration')))
            try:
                msg = '/{:<7}'.format(self.auto_unit(container['memory']['limit']))
            except KeyError:
                msg = '/{:<7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # IO R/W
            unit = 'B'
            try:
                value = self.auto_unit(int(container['io']['ior'] // container['io']['time_since_update'])) + unit
                msg = '{:>7}'.format(value)
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg))
            try:
                value = self.auto_unit(int(container['io']['iow'] // container['io']['time_since_update'])) + unit
                msg = ' {:<7}'.format(value)
            except KeyError:
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
                value = (
                    self.auto_unit(
                        int(container['network']['rx'] // container['network']['time_since_update'] * to_bit)
                    )
                    + unit
                )
                msg = '{:>7}'.format(value)
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg))
            try:
                value = (
                    self.auto_unit(
                        int(container['network']['tx'] // container['network']['time_since_update'] * to_bit)
                    )
                    + unit
                )
                msg = ' {:<7}'.format(value)
            except KeyError:
                msg = ' {:<7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # Command
            if container['Command'] is not None:
                msg = ' {}'.format(' '.join(container['Command']))
            else:
                msg = ' {}'.format('_')
            ret.append(self.curse_add_line(msg, splittable=True))

        return ret

    def _msg_name(self, container, max_width):
        """Build the container name."""
        name = container['name'][:max_width]
        return ' {:{width}}'.format(name, width=max_width)

    def container_alert(self, status):
        """Analyse the container status."""
        if status == 'running':
            return 'OK'
        elif status == 'exited':
            return 'WARNING'
        elif status == 'dead':
            return 'CRITICAL'
        else:
            return 'CAREFUL'


def sort_docker_stats(stats):
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
        stats['containers'],
        sorted_by=sort_by,
        sorted_by_secondary=sort_by_secondary,
        # Reverse for all but name
        reverse=glances_processes.sort_key != 'name',
    )

    # Return the main sort key and the sorted stats
    return sort_by, stats
