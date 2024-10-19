#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Cloud plugin.

Supported Cloud API:
- OpenStack meta data (class ThreadOpenStack) - Vanilla OpenStack
- OpenStackEC2 meta data (class ThreadOpenStackEC2) - Amazon EC2 compatible
"""

import threading

from glances.globals import iteritems, to_ascii
from glances.logger import logger
from glances.plugins.plugin.model import GlancesPluginModel

# Import plugin specific dependency
try:
    import requests
except ImportError as e:
    import_error_tag = True
    # Display debug message if import error
    logger.warning(f"Missing Python Lib ({e}), Cloud plugin is disabled")
else:
    import_error_tag = False


class PluginModel(GlancesPluginModel):
    """Glances' cloud plugin.

    The goal of this plugin is to retrieve additional information
    concerning the datacenter where the host is connected.

    See https://github.com/nicolargo/glances/issues/1029

    stats is a dict
    """

    def __init__(self, args=None, config=None):
        """Init the plugin."""
        super().__init__(args=args, config=config)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

        # Init thread to grab OpenStack stats asynchronously
        self.OPENSTACK = ThreadOpenStack()
        self.OPENSTACKEC2 = ThreadOpenStackEC2()

        # Run the thread
        self.OPENSTACK.start()
        self.OPENSTACKEC2.start()

    def exit(self):
        """Overwrite the exit method to close threads."""
        self.OPENSTACK.stop()
        self.OPENSTACKEC2.stop()
        # Call the father class
        super().exit()

    @GlancesPluginModel._check_decorator
    @GlancesPluginModel._log_result_decorator
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
            if not stats:
                stats = self.OPENSTACKEC2.stats
            # Example:
            # Uncomment to test on physical computer (only for test purpose)
            # stats = {'id': 'ami-id', 'name': 'My VM', 'type': 'Gold', 'region': 'France', 'platform': 'OpenStack'}

        # Update the stats
        self.stats = stats

        return self.stats

    def msg_curse(self, args=None, max_width=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        if not self.stats or self.stats == {} or self.is_disabled():
            return ret

        # Do not display Unknown information in the cloud plugin #2485
        if not self.stats.get('platform') or not self.stats.get('name'):
            return ret

        # Generate the output
        msg = self.stats.get('platform', 'Unknown')
        ret.append(self.curse_add_line(msg, "TITLE"))
        msg = ' {} instance {} ({})'.format(
            self.stats.get('type', 'Unknown'), self.stats.get('name', 'Unknown'), self.stats.get('region', 'Unknown')
        )
        ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        # logger.info(ret)
        return ret


class ThreadOpenStack(threading.Thread):
    """
    Specific thread to grab OpenStack stats.

    stats is a dict
    """

    # The metadata service provides a way for instances to retrieve
    # instance-specific data via a REST API. Instances access this
    # service at 169.254.169.254 or at fe80::a9fe:a9fe.
    # All types of metadata, be it user-, nova- or vendor-provided,
    # can be accessed via this service.
    # https://docs.openstack.org/nova/latest/user/metadata-service.html
    OPENSTACK_PLATFORM = "OpenStack"
    OPENSTACK_API_URL = 'http://169.254.169.254/openstack/latest/meta-data'
    OPENSTACK_API_METADATA = {
        'id': 'project_id',
        'name': 'name',
        'type': 'meta/role',
        'region': 'availability_zone',
    }

    def __init__(self):
        """Init the class."""
        logger.debug("cloud plugin - Create thread for OpenStack metadata")
        super().__init__()
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
            r_url = f'{self.OPENSTACK_API_URL}/{v}'
            try:
                # Local request, a timeout of 3 seconds is OK
                r = requests.get(r_url, timeout=3)
            except Exception as e:
                logger.debug(f'cloud plugin - Cannot connect to the OpenStack metadata API {r_url}: {e}')
                break
            else:
                if r.ok:
                    self._stats[k] = to_ascii(r.content)
        else:
            # No break during the loop, so we can set the platform
            self._stats['platform'] = self.OPENSTACK_PLATFORM

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
        return self._stopper.is_set()


class ThreadOpenStackEC2(ThreadOpenStack):
    """
    Specific thread to grab OpenStack EC2 (Amazon cloud) stats.

    stats is a dict
    """

    # The metadata service provides a way for instances to retrieve
    # instance-specific data via a REST API. Instances access this
    # service at 169.254.169.254 or at fe80::a9fe:a9fe.
    # All types of metadata, be it user-, nova- or vendor-provided,
    # can be accessed via this service.
    # https://docs.openstack.org/nova/latest/user/metadata-service.html
    OPENSTACK_PLATFORM = "Amazon EC2"
    OPENSTACK_API_URL = 'http://169.254.169.254/latest/meta-data'
    OPENSTACK_API_METADATA = {
        'id': 'ami-id',
        'name': 'instance-id',
        'type': 'instance-type',
        'region': 'placement/availability-zone',
    }
