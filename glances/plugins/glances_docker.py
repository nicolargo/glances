# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

# Import Glances libs
from glances.core.glances_logging import logger
from glances.plugins.glances_plugin import GlancesPlugin

# Docker-py library (optional and Linux-only)
# https://github.com/docker/docker-py
try:
    import docker
    import requests
except ImportError as e:
    logger.debug("Docker library not found (%s). Glances cannot grab Docker info." % e)
    docker_tag = False
else:
    docker_tag = True
import os
import re
import numbers


class Plugin(GlancesPlugin):

    """Glances' Docker plugin.

    stats is a list
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # The plgin can be disable using: args.disable_docker
        self.args = args

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the Docker API
        self.docker_client = False

    def connect(self, version=None):
        """Connect to the Docker server"""
        # Init connection to the Docker API
        try:
            if version is None:
                ret = docker.Client(base_url='unix://var/run/docker.sock')
            else:
                ret = docker.Client(base_url='unix://var/run/docker.sock',
                                    version=version)
        except NameError:
            # docker lib not found
            return None
        try:
            ret.version()
        except requests.exceptions.ConnectionError as e:
            # Connexion error (Docker not detected)
            # Let this message in debug mode
            logger.debug("Can't connect to the Docker server (%s)" % e)
            return None
        except docker.errors.APIError as e:
            if version is None:
                # API error (Version mismatch ?)
                logger.debug("Docker API error (%s)" % e)
                # Try the connection with the server version
                import re
                version = re.search('server\:\ (.*)\)\".*\)', str(e))
                if version:
                    logger.debug("Try connection with Docker API version %s" % version.group(1))
                    ret = self.connect(version=version.group(1))
                else:
                    logger.debug("Can not retreive Docker server version")
                    ret = None
            else:
                # API error
                logger.error("Docker API error (%s)" % e)
                ret = None
        except Exception as e:
            # Others exceptions...
            # Connexion error (Docker not detected)
            logger.error("Can't connect to the Docker server (%s)" % e)
            ret = None

        # Log an info if Docker plugin is disabled
        if ret is None:
            logger.debug("Docker plugin is disable because an error has been detected")

        return ret

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update Docker stats using the input method.
        """
        # Reset stats
        self.reset()

        # Get the current Docker API client
        if not self.docker_client:
            # First time, try to connect to the server
            self.docker_client = self.connect()
            if self.docker_client is None:
                global docker_tag
                docker_tag = False

        # The Docker-py lib is mandatory
        if not docker_tag or (self.args is not None and self.args.disable_docker):
            return self.stats

        if self.get_input() == 'local':
            # Update stats
            # Exemple: {
            #     "KernelVersion": "3.16.4-tinycore64",
            #     "Arch": "amd64",
            #     "ApiVersion": "1.15",
            #     "Version": "1.3.0",
            #     "GitCommit": "c78088f",
            #     "Os": "linux",
            #     "GoVersion": "go1.3.3"
            # }
            self.stats['version'] = self.docker_client.version()
            # Example: [{u'Status': u'Up 36 seconds',
            #            u'Created': 1420378904,
            #            u'Image': u'nginx:1',
            #            u'Ports': [{u'Type': u'tcp', u'PrivatePort': 443},
            #                       {u'IP': u'0.0.0.0', u'Type': u'tcp', u'PublicPort': 8080, u'PrivatePort': 80}],
            #            u'Command': u"nginx -g 'daemon off;'",
            #            u'Names': [u'/webstack_nginx_1'],
            #            u'Id': u'b0da859e84eb4019cf1d965b15e9323006e510352c402d2f442ea632d61faaa5'}]
            self.stats['containers'] = self.docker_client.containers()
            # Get CPU and MEMORY stats for containers
            for c in self.stats['containers']:
                c['cpu'] = self.get_docker_cpu(c['Id'])
                c['memory'] = self.get_docker_memory(c['Id'])

        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            # Not available
            pass

        return self.stats

    def get_docker_cpu(self, id):
        """Return the container CPU usage by reading /sys/fs/cgroup/...
        Input: id is the full container id
        Output: a dict {'total': 1.49, 'user': 0.65, 'system': 0.84}"""
        ret = {}
        # Read the stats
        try:
            with open('/sys/fs/cgroup/cpuacct/docker/' + id + '/cpuacct.stat', 'r') as f:
                for line in f:
                    m = re.search(r"(system|user)\s+(\d+)", line)
                    if m:
                        ret[m.group(1)] = int(m.group(2))
        except IOError as e:
            logger.error("Can not grab container CPU stat ({0})".format(e))
            return ret
        # Get the user ticks
        ticks = self.get_user_ticks()        
        if isinstance(ret["system"], numbers.Number) and isinstance(ret["user"], numbers.Number):
            ret["total"] = ret["system"] + ret["user"]
            for k in ret.keys():
                ret[k] = float(ret[k]) / ticks
        # Return the stats
        return ret

    def get_docker_memory(self, id):
        """Return the container MEMORY usage by reading /sys/fs/cgroup/...
        Input: id is the full container id
        Output: a dict {'rss': 1015808, 'cache': 356352}"""
        ret = {}
        # Read the stats
        try:
            with open('/sys/fs/cgroup/memory/docker/' + id + '/memory.stat', 'r') as f:
                for line in f:
                    m = re.search(r"(rss|cache)\s+(\d+)", line)
                    if m:
                        ret[m.group(1)] = int(m.group(2))
        except IOError as e:
            logger.error("Can not grab container MEM stat ({0})".format(e))
            return ret
        # Return the stats
        return ret

    def get_user_ticks(self):
        """return the user ticks by reading the environment variable"""
        return os.sysconf(os.sysconf_names['SC_CLK_TCK'])

    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist (and non null) and display plugin enable...
        if self.stats == {} or args.disable_docker or len(self.stats['containers']) == 0:
            return ret

        # Build the string message
        # Title
        msg = '{0}'.format(_("CONTAINERS"))
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {0}'.format(len(self.stats['containers']))
        ret.append(self.curse_add_line(msg))
        msg = ' ({0} {1})'.format(_("served by Docker"),
                                  self.stats['version']["Version"])
        ret.append(self.curse_add_line(msg))
        ret.append(self.curse_new_line())
        # Header
        ret.append(self.curse_new_line())
        msg = '{0:>14}'.format(_("Id"))
        ret.append(self.curse_add_line(msg))
        msg = ' {0:20}'.format(_("Name"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>26}'.format(_("Status"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6}'.format(_("CPU%"))
        ret.append(self.curse_add_line(msg))
        msg = '{0:>6}'.format(_("MEM"))
        ret.append(self.curse_add_line(msg))
        msg = ' {0:8}'.format(_("Command"))
        ret.append(self.curse_add_line(msg))
        # Data
        for container in self.stats['containers']:
            ret.append(self.curse_new_line())
            # Id
            msg = '{0:>14}'.format(container['Id'][0:12])
            ret.append(self.curse_add_line(msg))
            # Name
            name = container['Names'][0]
            if len(name) > 20:
                name = '_' + name[:-19]
            else:
                name[0:20]
            msg = ' {0:20}'.format(name)
            ret.append(self.curse_add_line(msg))
            # Status
            status = self.container_alert(container['Status'])
            msg = container['Status'].replace("minute", "min")
            msg = '{0:>26}'.format(msg[0:25])
            ret.append(self.curse_add_line(msg, status))
            # CPU
            try:
                msg = '{0:>6.1f}'.format(container['cpu']['total'])
            except KeyError:
                msg = '{0:>6}'.format('?')
            ret.append(self.curse_add_line(msg))
            # MEM
            try:
                msg = '{0:>6}'.format(self.auto_unit(container['memory']['rss']))
            except KeyError:
                msg = '{0:>6}'.format('?')
            ret.append(self.curse_add_line(msg))
            # Command
            msg = ' {0}'.format(container['Command'])
            ret.append(self.curse_add_line(msg))

        return ret

    def container_alert(self, status):
        """Analyse the container status"""
        if "Paused" in status:
            return 'CAREFUL'
        else:
            return 'OK'
