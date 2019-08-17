# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2019 Nicolargo <nicolas@nicolargo.com>
#
# Glances is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Glances is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

"""Docker plugin."""

import os
import threading
import time

from glances.logger import logger
from glances.compat import iterkeys, itervalues, nativestr
from glances.timer import getTimeSinceLastUpdate
from glances.plugins.glances_plugin import GlancesPlugin
from glances.processes import sort_stats as sort_stats_processes, weighted, glances_processes

# Docker-py library (optional and Linux-only)
# https://github.com/docker/docker-py
try:
    import docker
except Exception as e:
    import_error_tag = True
    # Display debu message if import KeyError
    logger.warning("Error loading Docker Python Lib. Docker plugin is disabled ({})".format(e))
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
items_history_list = [{'name': 'cpu_percent',
                       'description': 'Container CPU consumption in %',
                       'y_unit': '%'}]


class Plugin(GlancesPlugin):
    """Glances Docker plugin.

    stats is a dict: {'version': {...}, 'containers': [{}, {}]}
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args,
                                     config=config,
                                     items_history_list=items_history_list)

        # The plgin can be disable using: args.disable_docker
        self.args = args

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the Docker API
        self.docker_client = self.connect()

        # Dict of thread (to grab stats asynchroniously, one thread is created by container)
        # key: Container Id
        # value: instance of ThreadDockerGrabber
        self.thread_list = {}

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
        ret = []
        try:
            ret = self.stats['containers']
        except KeyError as e:
            logger.debug("docker plugin - Docker export error {}".format(e))
        return ret

    def connect(self):
        """Connect to the Docker server."""
        try:
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

        # The Docker-py lib is mandatory
        if import_error_tag:
            return self.stats

        if self.input_method == 'local':
            # Update stats

            # Docker version
            # Exemple: {
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
                    # Create it and add it to the internal dict
                    logger.debug("{} plugin - Create thread for container {}".format(self.plugin_name, container.id[:12]))
                    t = ThreadDockerGrabber(container)
                    self.thread_list[container.id] = t
                    t.start()

            # Stop threads for non-existing containers
            nonexisting_containers = set(iterkeys(self.thread_list)) - set([c.id for c in containers])
            for container_id in nonexisting_containers:
                # Stop the thread
                logger.debug("{} plugin - Stop thread for old container {}".format(self.plugin_name, container_id[:12]))
                self.thread_list[container_id].stop()
                # Delete the item from the dict
                del self.thread_list[container_id]

            # Get stats for all containers
            stats['containers'] = []
            for container in containers:
                # Init the stats for the current container
                container_stats = {}
                # The key is the container name and not the Id
                container_stats['key'] = self.get_key()
                # Export name (first name in the Names list, without the /)
                container_stats['name'] = nativestr(container.name)
                # Export global Names (used by the WebUI)
                container_stats['Names'] = [nativestr(container.name)]
                # Container Id
                container_stats['Id'] = container.id
                # Container Image
                container_stats['Image'] = container.image.tags
                # Global stats (from attrs)
                container_stats['Status'] = container.attrs['State']['Status']
                container_stats['Command'] = container.attrs['Config']['Entrypoint']
                # Standards stats
                if container_stats['Status'] in ('running', 'paused'):
                    container_stats['cpu'] = self.get_docker_cpu(container.id, self.thread_list[container.id].stats)
                    container_stats['cpu_percent'] = container_stats['cpu'].get('total', None)
                    container_stats['memory'] = self.get_docker_memory(container.id, self.thread_list[container.id].stats)
                    container_stats['memory_usage'] = container_stats['memory'].get('usage', None)
                    container_stats['io'] = self.get_docker_io(container.id, self.thread_list[container.id].stats)
                    container_stats['io_r'] = container_stats['io'].get('ior', None)
                    container_stats['io_w'] = container_stats['io'].get('iow', None)
                    container_stats['network'] = self.get_docker_network(container.id, self.thread_list[container.id].stats)
                    container_stats['network_rx'] = container_stats['network'].get('rx', None)
                    container_stats['network_tx'] = container_stats['network'].get('tx', None)
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
                # Add current container stats to the stats list
                stats['containers'].append(container_stats)

        elif self.input_method == 'snmp':
            # Update stats using SNMP
            # Not available
            pass

        # Sort and update the stats
        self.stats = sort_stats(stats)

        return self.stats

    def get_docker_cpu(self, container_id, all_stats):
        """Return the container CPU usage.

        Input: id is the full container id
               all_stats is the output of the stats method of the Docker API
        Output: a dict {'total': 1.49}
        """
        cpu_new = {}
        ret = {'total': 0.0}

        # Read the stats
        # For each container, you will find a pseudo-file cpuacct.stat,
        # containing the CPU usage accumulated by the processes of the container.
        # Those times are expressed in ticks of 1/USER_HZ of a second.
        # On x86 systems, USER_HZ is 100.
        try:
            cpu_new['total'] = all_stats['cpu_stats']['cpu_usage']['total_usage']
            cpu_new['system'] = all_stats['cpu_stats']['system_cpu_usage']
            cpu_new['nb_core'] = len(all_stats['cpu_stats']['cpu_usage']['percpu_usage'] or [])
        except KeyError as e:
            # all_stats do not have CPU information
            logger.debug("docker plugin - Cannot grab CPU usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
        else:
            # Previous CPU stats stored in the cpu_old variable
            if not hasattr(self, 'cpu_old'):
                # First call, we init the cpu_old variable
                self.cpu_old = {}
                try:
                    self.cpu_old[container_id] = cpu_new
                except (IOError, UnboundLocalError):
                    pass

            if container_id not in self.cpu_old:
                try:
                    self.cpu_old[container_id] = cpu_new
                except (IOError, UnboundLocalError):
                    pass
            else:
                #
                cpu_delta = float(cpu_new['total'] - self.cpu_old[container_id]['total'])
                system_delta = float(cpu_new['system'] - self.cpu_old[container_id]['system'])
                if cpu_delta > 0.0 and system_delta > 0.0:
                    ret['total'] = (cpu_delta / system_delta) * float(cpu_new['nb_core']) * 100

                # Save stats to compute next stats
                self.cpu_old[container_id] = cpu_new

        # Return the stats
        return ret

    def get_docker_memory(self, container_id, all_stats):
        """Return the container MEMORY.

        Input: id is the full container id
               all_stats is the output of the stats method of the Docker API
        Output: a dict {'rss': 1015808, 'cache': 356352,  'usage': ..., 'max_usage': ...}
        """
        ret = {}
        # Read the stats
        try:
            # Do not exist anymore with Docker 1.11 (issue #848)
            # ret['rss'] = all_stats['memory_stats']['stats']['rss']
            # ret['cache'] = all_stats['memory_stats']['stats']['cache']
            ret['usage'] = all_stats['memory_stats']['usage']
            ret['limit'] = all_stats['memory_stats']['limit']
            ret['max_usage'] = all_stats['memory_stats']['max_usage']
        except (KeyError, TypeError) as e:
            # all_stats do not have MEM information
            logger.debug("docker plugin - Cannot grab MEM usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
        # Return the stats
        return ret

    def get_docker_network(self, container_id, all_stats):
        """Return the container network usage using the Docker API (v1.0 or higher).

        Input: id is the full container id
        Output: a dict {'time_since_update': 3000, 'rx': 10, 'tx': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            rx: Number of byte received
            tx: Number of byte transmited
        """
        # Init the returned dict
        network_new = {}

        # Read the rx/tx stats (in bytes)
        try:
            netcounters = all_stats["networks"]
        except KeyError as e:
            # all_stats do not have NETWORK information
            logger.debug("docker plugin - Cannot grab NET usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
            # No fallback available...
            return network_new

        # Previous network interface stats are stored in the network_old variable
        if not hasattr(self, 'inetcounters_old'):
            # First call, we init the network_old var
            self.netcounters_old = {}
            try:
                self.netcounters_old[container_id] = netcounters
            except (IOError, UnboundLocalError):
                pass

        if container_id not in self.netcounters_old:
            try:
                self.netcounters_old[container_id] = netcounters
            except (IOError, UnboundLocalError):
                pass
        else:
            # By storing time data we enable Rx/s and Tx/s calculations in the
            # XML/RPC API, which would otherwise be overly difficult work
            # for users of the API
            try:
                network_new['time_since_update'] = getTimeSinceLastUpdate('docker_net_{}'.format(container_id))
                network_new['rx'] = netcounters["eth0"]["rx_bytes"] - self.netcounters_old[container_id]["eth0"]["rx_bytes"]
                network_new['tx'] = netcounters["eth0"]["tx_bytes"] - self.netcounters_old[container_id]["eth0"]["tx_bytes"]
                network_new['cumulative_rx'] = netcounters["eth0"]["rx_bytes"]
                network_new['cumulative_tx'] = netcounters["eth0"]["tx_bytes"]
            except KeyError as e:
                # all_stats do not have INTERFACE information
                logger.debug("docker plugin - Cannot grab network interface usage for container {} ({})".format(container_id, e))
                logger.debug(all_stats)

            # Save stats to compute next bitrate
            self.netcounters_old[container_id] = netcounters

        # Return the stats
        return network_new

    def get_docker_io(self, container_id, all_stats):
        """Return the container IO usage using the Docker API (v1.0 or higher).

        Input: id is the full container id
        Output: a dict {'time_since_update': 3000, 'ior': 10, 'iow': 65}.
        with:
            time_since_update: number of seconds elapsed between the latest grab
            ior: Number of byte readed
            iow: Number of byte written
        """
        # Init the returned dict
        io_new = {}

        # Read the ior/iow stats (in bytes)
        try:
            iocounters = all_stats["blkio_stats"]
        except KeyError as e:
            # all_stats do not have io information
            logger.debug("docker plugin - Cannot grab block IO usage for container {} ({})".format(container_id, e))
            logger.debug(all_stats)
            # No fallback available...
            return io_new

        # Previous io interface stats are stored in the io_old variable
        if not hasattr(self, 'iocounters_old'):
            # First call, we init the io_old var
            self.iocounters_old = {}
            try:
                self.iocounters_old[container_id] = iocounters
            except (IOError, UnboundLocalError):
                pass

        if container_id not in self.iocounters_old:
            try:
                self.iocounters_old[container_id] = iocounters
            except (IOError, UnboundLocalError):
                pass
        else:
            # By storing time data we enable IoR/s and IoW/s calculations in the
            # XML/RPC API, which would otherwise be overly difficult work
            # for users of the API
            try:
                # Read IOR and IOW value in the structure list of dict
                ior = [i for i in iocounters['io_service_bytes_recursive'] if i['op'] == 'Read'][0]['value']
                iow = [i for i in iocounters['io_service_bytes_recursive'] if i['op'] == 'Write'][0]['value']
                ior_old = [i for i in self.iocounters_old[container_id]['io_service_bytes_recursive'] if i['op'] == 'Read'][0]['value']
                iow_old = [i for i in self.iocounters_old[container_id]['io_service_bytes_recursive'] if i['op'] == 'Write'][0]['value']
            except (TypeError, IndexError, KeyError) as e:
                # all_stats do not have io information
                logger.debug("docker plugin - Cannot grab block IO usage for container {} ({})".format(container_id, e))
            else:
                io_new['time_since_update'] = getTimeSinceLastUpdate('docker_io_{}'.format(container_id))
                io_new['ior'] = ior - ior_old
                io_new['iow'] = iow - iow_old
                io_new['cumulative_ior'] = ior
                io_new['cumulative_iow'] = iow

                # Save stats to compute next bitrate
                self.iocounters_old[container_id] = iocounters

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

        # Add specifics informations
        # Alert
        for i in self.stats['containers']:
            # Init the views for the current container (key = container name)
            self.views[i[self.get_key()]] = {'cpu': {}, 'mem': {}}
            # CPU alert
            if 'cpu' in i and 'total' in i['cpu']:
                # Looking for specific CPU container threasold in the conf file
                alert = self.get_alert(i['cpu']['total'],
                                       header=i['name'] + '_cpu',
                                       action_key=i['name'])
                if alert == 'DEFAULT':
                    # Not found ? Get back to default CPU threasold value
                    alert = self.get_alert(i['cpu']['total'], header='cpu')
                self.views[i[self.get_key()]]['cpu']['decoration'] = alert
            # MEM alert
            if 'memory' in i and 'usage' in i['memory']:
                # Looking for specific MEM container threasold in the conf file
                alert = self.get_alert(i['memory']['usage'],
                                       maximum=i['memory']['limit'],
                                       header=i['name'] + '_mem',
                                       action_key=i['name'])
                if alert == 'DEFAULT':
                    # Not found ? Get back to default MEM threasold value
                    alert = self.get_alert(i['memory']['usage'],
                                           maximum=i['memory']['limit'],
                                           header='mem')
                self.views[i[self.get_key()]]['mem']['decoration'] = alert

        return True

    def msg_curse(self, args=None, max_width=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist (and non null) and display plugin enable...
        if not self.stats \
           or 'containers' not in self.stats or len(self.stats['containers']) == 0 \
           or self.is_disable():
            return ret

        # Build the string message
        # Title
        msg = '{}'.format('CONTAINERS')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {}'.format(len(self.stats['containers']))
        ret.append(self.curse_add_line(msg))
        msg = ' (served by Docker {})'.format(self.stats['version']["Version"])
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        # Header
        ret.append(self.curse_new_line())
        # Get the maximum containers name (cutted to 20 char max)
        name_max_width = min(20, len(max(self.stats['containers'], key=lambda x: len(x['name']))['name']))
        msg = ' {:{width}}'.format('Name', width=name_max_width)
        ret.append(self.curse_add_line(msg))
        msg = '{:>10}'.format('Status')
        ret.append(self.curse_add_line(msg))
        msg = '{:>6}'.format('CPU%')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('MEM')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('/MAX')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('IOR/s')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('IOW/s')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('Rx/s')
        ret.append(self.curse_add_line(msg))
        msg = '{:>7}'.format('Tx/s')
        ret.append(self.curse_add_line(msg))
        msg = ' {:8}'.format('Command')
        ret.append(self.curse_add_line(msg))
        # Data
        for container in self.stats['containers']:
            ret.append(self.curse_new_line())
            # Name
            ret.append(self.curse_add_line(self._msg_name(container=container,
                                                          max_width=name_max_width)))
            # Status
            status = self.container_alert(container['Status'])
            msg = '{:>10}'.format(container['Status'][0:10])
            ret.append(self.curse_add_line(msg, status))
            # CPU
            try:
                msg = '{:>6.1f}'.format(container['cpu']['total'])
            except KeyError:
                msg = '{:>6}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'],
                                                               key='cpu',
                                                               option='decoration')))
            # MEM
            try:
                msg = '{:>7}'.format(self.auto_unit(container['memory']['usage']))
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg, self.get_views(item=container['name'],
                                                               key='mem',
                                                               option='decoration')))
            try:
                msg = '{:>7}'.format(self.auto_unit(container['memory']['limit']))
            except KeyError:
                msg = '{:>7}'.format('_')
            ret.append(self.curse_add_line(msg))
            # IO R/W
            unit = 'B'
            for r in ['ior', 'iow']:
                try:
                    value = self.auto_unit(int(container['io'][r] // container['io']['time_since_update'])) + unit
                    msg = '{:>7}'.format(value)
                except KeyError:
                    msg = '{:>7}'.format('_')
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
            for r in ['rx', 'tx']:
                try:
                    value = self.auto_unit(int(container['network'][r] // container['network']['time_since_update'] * to_bit)) + unit
                    msg = '{:>7}'.format(value)
                except KeyError:
                    msg = '{:>7}'.format('_')
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
        name = container['name']
        if len(name) > max_width:
            name = '_' + name[-max_width + 1:]
        else:
            name = name[:max_width]
        return ' {:{width}}'.format(name, width=max_width)

    def container_alert(self, status):
        """Analyse the container status."""
        if status in ('running'):
            return 'OK'
        elif status in ('exited'):
            return 'WARNING'
        elif status in ('dead'):
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
        except:
            logger.debug("docker plugin - Exception thrown during run")
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
        return self._stopper.isSet()


def sort_stats(stats):
    # Sort Docker stats using the same function than processes
    sortedby = 'cpu_percent'
    sortedby_secondary = 'memory_usage'
    if glances_processes.sort_key.startswith('memory'):
        sortedby = 'memory_usage'
        sortedby_secondary = 'cpu_percent'
    sort_stats_processes(stats['containers'],
                         sortedby=sortedby,
                         sortedby_secondary=sortedby_secondary)
    return stats
