# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Docker plugin."""

import os
import threading
import time
from copy import deepcopy

from glances.compat import iterkeys, itervalues, nativestr, pretty_date
from glances.logger import logger
from glances.plugins.glances_plugin import GlancesPlugin
from glances.processes import sort_stats as sort_stats_processes, glances_processes
from glances.timer import getTimeSinceLastUpdate

# Docker-py library (optional and Linux-only)
# https://github.com/docker/docker-py
try:
    import docker
    from dateutil import parser, tz
except Exception as e:
    import_error_tag = True
    # Display debug message if import KeyError
    logger.warning("Error loading Docker deps Lib. Docker plugin is disabled ({})".format(e))
else:
    import_error_tag = False

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


class Plugin(GlancesPlugin):
    """Glances Docker plugin.

    stats is a dict: {'version': {...}, 'containers': [{}, {}]}
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config, items_history_list=items_history_list)

        # The plugin can be disabled using: args.disable_docker
        self.args = args

        # Default config keys
        self.config = config

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the Docker API
        self.docker_client = self.connect()

        # Dict of thread (to grab stats asynchronously, one thread is created per container)
        # key: Container Id
        # value: instance of ThreadDockerGrabber
        self.thread_list = {}

        # Dict of Network stats (Storing previous network stats to compute Rx/s and Tx/s)
        # key: Container Id
        # value: network stats dict
        self.network_old = {}

        # Dict of Disk IO stats (Storing previous disk_io stats to compute Rx/s and Tx/s)
        # key: Container Id
        # value: network stats dict
        self.io_old = {}

        # Sort key
        self.sort_key = None

        # Force a first update because we need two update to have the first stat
        self.update()
        self.refresh_timer.set(0)

    def exit(self):
        """Overwrite the exit method to close threads."""
        for t in itervalues(self.thread_list):
            t.stop()
        # Call the father class
        super(Plugin, self).exit()

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

    def connect(self):
        """Connect to the Docker server."""
        try:
            # If the following line replace the next one, the issue #1878
            # is reproduced (Docker containers information missing with Docker 20.10.x)
            # So, for the moment disable the timeout option
            ret = docker.from_env()
        except Exception as e:
            logger.error("docker plugin - Can not connect to Docker ({})".format(e))
            ret = None

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

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update Docker stats using the input method."""
        # Init new stats
        stats = self.get_init_value()

        # The Docker-py lib is mandatory and connection should be ok
        if import_error_tag or self.docker_client is None:
            return self.stats

        if self.input_method == 'local':
            # Update stats

            # Docker version
            # Example: {
            #     "KernelVersion": "3.16.4-tinycore64",
            #     "Arch": "amd64",
            #     "ApiVersion": "1.15",
            #     "Version": "1.3.0",
            #     "GitCommit": "c78088f",
            #     "Os": "linux",
            #     "GoVersion": "go1.3.3"
            # }
            try:
                stats['version'] = self.docker_client.version()
            except Exception as e:
                # Correct issue#649
                logger.error("{} plugin - Cannot get Docker version ({})".format(self.plugin_name, e))
                # We may have lost connection remove version info
                if 'version' in self.stats:
                    del self.stats['version']
                self.stats['containers'] = []
                return self.stats

            # Update current containers list
            try:
                # Issue #1152: Docker module doesn't export details about stopped containers
                # The Docker/all key of the configuration file should be set to True
                containers = self.docker_client.containers.list(all=self._all_tag()) or []
            except Exception as e:
                logger.error("{} plugin - Cannot get containers list ({})".format(self.plugin_name, e))
                # We may have lost connection empty the containers list.
                self.stats['containers'] = []
                return self.stats

            # Start new thread for new container
            for container in containers:
                if container.id not in self.thread_list:
                    # Thread did not exist in the internal dict
                    # Create it, add it to the internal dict and start it
                    logger.debug(
                        "{} plugin - Create thread for container {}".format(self.plugin_name, container.id[:12])
                    )
                    t = ThreadDockerGrabber(container)
                    self.thread_list[container.id] = t
                    t.start()

            # Stop threads for non-existing containers
            absent_containers = set(iterkeys(self.thread_list)) - set([c.id for c in containers])
            for container_id in absent_containers:
                # Stop the thread
                logger.debug("{} plugin - Stop thread for old container {}".format(self.plugin_name, container_id[:12]))
                self.thread_list[container_id].stop()
                # Delete the item from the dict
                del self.thread_list[container_id]

            # Get stats for all containers
            stats['containers'] = []
            for container in containers:
                # Shall we display the stats ?
                if not self.is_display(nativestr(container.name)):
                    continue

                # Init the stats for the current container
                container_stats = {}
                # The key is the container name and not the Id
                container_stats['key'] = self.get_key()
                # Export name
                container_stats['name'] = nativestr(container.name)
                # Container Id
                container_stats['Id'] = container.id
                # Container Image
                container_stats['Image'] = container.image.tags
                # Global stats (from attrs)
                # Container Status
                container_stats['Status'] = container.attrs['State']['Status']
                # Container Command (see #1912)
                container_stats['Command'] = []
                if container.attrs['Config'].get('Entrypoint', None):
                    container_stats['Command'].extend(container.attrs['Config'].get('Entrypoint', []))
                if container.attrs['Config'].get('Cmd', None):
                    container_stats['Command'].extend(container.attrs['Config'].get('Cmd', []))
                if not container_stats['Command']:
                    container_stats['Command'] = None
                # Standards stats
                # See https://docs.docker.com/engine/api/v1.41/#operation/ContainerStats
                # Be aware that the API can change... (example see issue #1857)
                if container_stats['Status'] in ('running', 'paused'):
                    # CPU
                    container_stats['cpu'] = self.get_docker_cpu(container.id, self.thread_list[container.id].stats)
                    container_stats['cpu_percent'] = container_stats['cpu'].get('total', None)
                    # MEM
                    container_stats['memory'] = self.get_docker_memory(
                        container.id, self.thread_list[container.id].stats
                    )
                    container_stats['memory_usage'] = container_stats['memory'].get('usage', None)
                    if container_stats['memory'].get('cache', None) is not None:
                        container_stats['memory_usage'] -= container_stats['memory']['cache']
                    # IO
                    container_stats['io'] = self.get_docker_io(container.id, self.thread_list[container.id].stats)
                    container_stats['io_r'] = container_stats['io'].get('ior', None)
                    container_stats['io_w'] = container_stats['io'].get('iow', None)
                    # NET
                    container_stats['network'] = self.get_docker_network(
                        container.id, self.thread_list[container.id].stats
                    )
                    container_stats['network_rx'] = container_stats['network'].get('rx', None)
                    container_stats['network_tx'] = container_stats['network'].get('tx', None)
                    # Uptime
                    container_stats['Uptime'] = pretty_date(
                        # parser.parse(container.attrs['State']['StartedAt']).replace(tzinfo=None)
                        parser.parse(container.attrs['State']['StartedAt'])
                        .astimezone(tz.tzlocal())
                        .replace(tzinfo=None)
                    )
                else:
                    container_stats['cpu'] = {}
                    container_stats['cpu_percent'] = None
                    container_stats['memory'] = {}
                    container_stats['memory_percent'] = None
                    container_stats['io'] = {}
                    container_stats['io_r'] = None
                    container_stats['io_w'] = None
                    container_stats['network'] = {}
                    container_stats['network_rx'] = None
                    container_stats['network_tx'] = None
                    container_stats['Uptime'] = None
                # Add current container stats to the stats list
                stats['containers'].append(container_stats)

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not available
            pass

        # Sort and update the stats
        self.sort_key, self.stats = sort_docker_stats(stats)

        return self.stats

    def get_docker_cpu(self, container_id, all_stats):
        """Return the container CPU usage.

        Input: id is the full container id
               all_stats is the output of the stats method of the Docker API
        Output: a dict {'total': 1.49}
        """
        cpu_stats = {'total': 0.0}

        try:
            cpu = {
                'system': all_stats['cpu_stats']['system_cpu_usage'],
                'total': all_stats['cpu_stats']['cpu_usage']['total_usage'],
            }
            precpu = {
                'system': all_stats['precpu_stats']['system_cpu_usage'],
                'total': all_stats['precpu_stats']['cpu_usage']['total_usage'],
            }
            # Issue #1857
            # If either precpu_stats.online_cpus or cpu_stats.online_cpus is nil
            # then for compatibility with older daemons the length of
            # the corresponding cpu_usage.percpu_usage array should be used.
            cpu['nb_core'] = all_stats['cpu_stats'].get('online_cpus', None)
            if cpu['nb_core'] is None:
                cpu['nb_core'] = len(all_stats['cpu_stats']['cpu_usage']['percpu_usage'] or [])
        except KeyError as e:
            logger.debug("docker plugin - Cannot grab CPU usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
        else:
            try:
                cpu_delta = cpu['total'] - precpu['total']
                system_cpu_delta = cpu['system'] - precpu['system']
                # CPU usage % = (cpu_delta / system_cpu_delta) * number_cpus * 100.0
                cpu_stats['total'] = (cpu_delta / system_cpu_delta) * cpu['nb_core'] * 100.0
            except TypeError as e:
                logger.debug("docker plugin - Cannot compute CPU usage for container {} ({})".format(container_id, e))
                logger.debug(all_stats)

        # Return the stats
        return cpu_stats

    def get_docker_memory(self, container_id, all_stats):
        """Return the container MEMORY.

        Input: id is the full container id
               all_stats is the output of the stats method of the Docker API
        Output: a dict {'rss': 1015808, 'cache': 356352,  'usage': ..., 'max_usage': ...}
        """
        memory_stats = {}
        # Read the stats
        try:
            # Mandatory fields
            memory_stats['usage'] = all_stats['memory_stats']['usage']
            memory_stats['limit'] = all_stats['memory_stats']['limit']
            # Issue #1857
            # Some stats are not always available in ['memory_stats']['stats']
            if 'rss' in all_stats['memory_stats']['stats']:
                memory_stats['rss'] = all_stats['memory_stats']['stats']['rss']
            elif 'total_rss' in all_stats['memory_stats']['stats']:
                memory_stats['rss'] = all_stats['memory_stats']['stats']['total_rss']
            else:
                memory_stats['rss'] = None
            memory_stats['cache'] = all_stats['memory_stats']['stats'].get('cache', None)
            memory_stats['max_usage'] = all_stats['memory_stats'].get('max_usage', None)
        except (KeyError, TypeError) as e:
            # all_stats do not have MEM information
            logger.debug("docker plugin - Cannot grab MEM usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
        # Return the stats
        return memory_stats

    def get_docker_network(self, container_id, all_stats):
        """Return the container network usage using the Docker API (v1.0 or higher).

        Input: id is the full container id
        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of bytes received
            tx: Number of bytes transmitted
        """
        # Init the returned dict
        network_new = {}

        # Read the rx/tx stats (in bytes)
        try:
            net_stats = all_stats["networks"]
        except KeyError as e:
            # all_stats do not have NETWORK information
            logger.debug("docker plugin - Cannot grab NET usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
            # No fallback available...
            return network_new

        # Previous network interface stats are stored in the self.network_old variable
        # By storing time data we enable Rx/s and Tx/s calculations in the XML/RPC API, which would otherwise
        # be overly difficult work for users of the API
        try:
            network_new['cumulative_rx'] = net_stats["eth0"]["rx_bytes"]
            network_new['cumulative_tx'] = net_stats["eth0"]["tx_bytes"]
        except KeyError as e:
            # all_stats do not have INTERFACE information
            logger.debug(
                "docker plugin - Cannot grab network interface usage for container {} ({})".format(container_id, e)
            )
            logger.debug(all_stats)
        else:
            network_new['time_since_update'] = getTimeSinceLastUpdate('docker_net_{}'.format(container_id))
            if container_id in self.network_old:
                network_new['rx'] = network_new['cumulative_rx'] - self.network_old[container_id]['cumulative_rx']
                network_new['tx'] = network_new['cumulative_tx'] - self.network_old[container_id]['cumulative_tx']

            # Save stats to compute next bitrate
            self.network_old[container_id] = network_new

        # Return the stats
        return network_new

    def get_docker_io(self, container_id, all_stats):
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Input: id is the full container id
        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of bytes read
            iow: Number of bytes written
        """
        # Init the returned dict
        io_new = {}

        # Read the ior/iow stats (in bytes)
        try:
            io_stats = all_stats["blkio_stats"]
        except KeyError as e:
            # all_stats do not have io information
            logger.debug("docker plugin - Cannot grab block IO usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
            # No fallback available...
            return io_new

        # Previous io interface stats are stored in the self.io_old variable
        # By storing time data we enable IoR/s and IoW/s calculations in the
        # XML/RPC API, which would otherwise be overly difficult work
        # for users of the API
        try:
            io_service_bytes_recursive = io_stats['io_service_bytes_recursive']

            # Read IOR and IOW value in the structure list of dict
            io_new['cumulative_ior'] = [i for i in io_service_bytes_recursive if i['op'].lower() == 'read'][0]['value']
            io_new['cumulative_iow'] = [i for i in io_service_bytes_recursive if i['op'].lower() == 'write'][0]['value']
        except (TypeError, IndexError, KeyError, AttributeError) as e:
            # all_stats do not have io information
            logger.debug("docker plugin - Cannot grab block IO usage for container {} ({})".format(container_id, e))
        else:
            io_new['time_since_update'] = getTimeSinceLastUpdate('docker_io_{}'.format(container_id))
            if container_id in self.io_old:
                io_new['ior'] = io_new['cumulative_ior'] - self.io_old[container_id]['cumulative_ior']
                io_new['iow'] = io_new['cumulative_iow'] - self.io_old[container_id]['cumulative_iow']

            # Save stats to compute next bitrate
            self.io_old[container_id] = io_new

        # Return the stats
        return io_new

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
        super(Plugin, self).update_views()

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
            self.config.get_int_value('docker', 'max_name_size', default=20) if self.config is not None else 20,
            len(max(self.stats['containers'], key=lambda x: len(x['name']))['name']),
        )
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
            ret.append(self.curse_add_line(msg, status))
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


class ThreadDockerGrabber(threading.Thread):
    """
    Specific thread to grab docker stats.

    stats is a dict
    """

    def __init__(self, container):
        """Init the class.

        container: instance of Docker-py Container
        """
        super(ThreadDockerGrabber, self).__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The docker-py return stats as a stream
        self._container = container
        self._stats_stream = container.stats(decode=True)
        # The class return the stats as a dict
        self._stats = {}
        logger.debug("docker plugin - Create thread for container {}".format(self._container.name))

    def run(self):
        """Grab the stats.

        Infinite loop, should be stopped by calling the stop() method
        """
        try:
            for i in self._stats_stream:
                self._stats = i
                time.sleep(0.1)
                if self.stopped():
                    break
        except Exception as e:
            logger.debug("docker plugin - Exception thrown during run ({})".format(e))
            self.stop()

    @property
    def stats(self):
        """Stats getter."""
        return self._stats

    @stats.setter
    def stats(self, value):
        """Stats setter."""
        self._stats = value

    def stop(self, timeout=None):
        """Stop the thread."""
        logger.debug("docker plugin - Close thread for container {}".format(self._container.name))
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()


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
