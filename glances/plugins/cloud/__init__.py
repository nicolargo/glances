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

"""Cloud plugin.

Supported Cloud API:
- OpenStack meta data (class ThreadOpenStack, see bellow): AWS, OVH...
"""

import threading

from glances.compat import iteritems, to_ascii
from glances.plugins.glances_plugin import GlancesPlugin
from glances.logger import logger

# Import plugin specific dependency
try:
    import requests
except ImportError as e:
    import_error_tag = True
    # Display debu message if import KeyError
    logger.warning("Missing Python Lib ({}), Cloud plugin is disabled".format(e))
else:
    import_error_tag = False


class Plugin(GlancesPlugin):
    """Glances' cloud plugin.

    The goal of this plugin is to retreive additional information
    concerning the datacenter where the host is connected.

    See https://github.com/nicolargo/glances/issues/1029

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

        # Init thread to grab OpenStack stats asynchroniously
        self.OPENSTACK = ThreadOpenStack()

        # Run the thread
        self.OPENSTACK.start()

    def exit(self):
        """Overwrite the exit method to close threads."""
        self.OPENSTACK.stop()
        # Call the father class
        super(Plugin, self).exit()

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the cloud stats.

        Return the stats (dict)
        """
        # Init new stats
        stats = self.get_init_value()

        # Requests lib is needed to get stats from the Cloud API
        if import_error_tag:
            return stats

        # Update the stats
        if self.input_method == 'local':
            stats = self.OPENSTACK.stats
            # Example:
            # Uncomment to test on physical computer
            # stats = {'ami-id': 'ami-id',
            #                    'instance-id': 'instance-id',
            #                    'instance-type': 'instance-type',
            #                    'region': 'placement/availability-zone'}

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        if not self.stats or self.stats == {} or self.is_disable():
            return ret

        # Generate the output
        if 'instance-type' in self.stats \
           and 'instance-id' in self.stats \
           and 'region' in self.stats:
            msg = 'Cloud '
            ret.append(self.curse_add_line(msg, "TITLE"))
            msg = '{} instance {} ({})'.format(self.stats['instance-type'],
                                               self.stats['instance-id'],
                                               self.stats['region'])
            ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        # logger.info(ret)
        return ret


class ThreadOpenStack(threading.Thread):
    """
    Specific thread to grab OpenStack stats.

    stats is a dict
    """

    # https://docs.openstack.org/nova/latest/user/metadata-service.html
    OPENSTACK_API_URL = 'http://169.254.169.254/latest/meta-data'
    OPENSTACK_API_METADATA = {'ami-id': 'ami-id',
                              'instance-id': 'instance-id',
                              'instance-type': 'instance-type',
                              'region': 'placement/availability-zone'}

    def __init__(self):
        """Init the class."""
        logger.debug("cloud plugin - Create thread for OpenStack metadata")
        super(ThreadOpenStack, self).__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The class return the stats as a dict
        self._stats = {}

    def run(self):
        """Grab plugin's stats.

        Infinite loop, should be stopped by calling the stop() method
        """
        if import_error_tag:
            self.stop()
            return False

        for k, v in iteritems(self.OPENSTACK_API_METADATA):
            r_url = '{}/{}'.format(self.OPENSTACK_API_URL, v)
            try:
                # Local request, a timeout of 3 seconds is OK
                r = requests.get(r_url, timeout=3)
            except Exception as e:
                logger.debug('cloud plugin - Cannot connect to the OpenStack metadata API {}: {}'.format(r_url, e))
                break
            else:
                if r.ok:
                    self._stats[k] = to_ascii(r.content)

        return True

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
        logger.debug("cloud plugin - Close thread for OpenStack metadata")
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.isSet()
