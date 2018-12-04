# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2017 Nicolargo <nicolas@nicolargo.com>
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
- AWS EC2 (class ThreadAwsEc2Grabber, see bellow)
"""

try:
    import requests
except ImportError:
    cloud_tag = False
else:
    cloud_tag = True

import json
import threading

from glances.compat import iteritems, to_ascii
from glances.plugins.glances_plugin import GlancesPlugin
from glances.logger import logger


class Plugin(GlancesPlugin):

    """Glances' cloud plugin.

    The goal of this plugin is to retreive additional information
    concerning the datacenter where the host is connected.

    See https://github.com/nicolargo/glances/issues/1029

    stats is a dict
    """

    def __init__(self, args=None):
        """Init the plugin."""
        super(Plugin, self).__init__(args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

        # Init thread to grab AWS EC2 stats asynchroniously
        self.aws_ec2 = ThreadAwsEc2Grabber()

        # Run the thread
        self.aws_ec2. start()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

    def exit(self):
        """Overwrite the exit method to close threads"""
        self.aws_ec2.stop()
        # Call the father class
        super(Plugin, self).exit()

    @GlancesPlugin._check_decorator
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update the cloud stats.

        Return the stats (dict)
        """
        # Reset stats
        self.reset()

        # Requests lib is needed to get stats from the Cloud API
        if not cloud_tag:
            return self.stats

        # Update the stats
        if self.input_method == 'local':
            self.stats = self.aws_ec2.stats
            # self.stats = {'ami-id': 'ami-id',
            #                         'instance-id': 'instance-id',
            #                         'instance-type': 'instance-type',
            #                         'region': 'placement/availability-zone'}

        return self.stats

    def msg_curse(self, args=None):
        """Return the string to display in the curse interface."""
        # Init the return message
        ret = []

        if not self.stats or self.stats == {} or self.is_disable():
            return ret

        # Generate the output
        if 'ami-id' in self.stats and 'region' in self.stats:
            msg = 'AWS EC2'
            ret.append(self.curse_add_line(msg, "TITLE"))
            msg = ' {} instance {} ({})'.format(to_ascii(self.stats['instance-type']),
                                                to_ascii(self.stats['instance-id']),
                                                to_ascii(self.stats['region']))
            ret.append(self.curse_add_line(msg))

        # Return the message with decoration
        logger.info(ret)
        return ret


class ThreadAwsEc2Grabber(threading.Thread):
    """
    Specific thread to grab AWS EC2 stats.

    stats is a dict
    """

    # AWS EC2
    AWS = 'aws'
    AZURE = 'azure'
    GCP = 'gcp'

    # http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html
    AWS_EC2_API_URL = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
    AWS_EC2_API_URL_CHECK = 'http://169.254.169.254/latest/dynamic/instance-identity/document'

    # https://docs.microsoft.com/en-us/azure/virtual-machines/windows/instance-metadata-service
    AZURE_VM_API_URL = 'http://169.254.169.254/metadata/instance?api-version=2017-12-01'
    AZURE_VM_API_URL_CHECK = 'http://169.254.169.254/metadata/instance?api-version=2017-12-01'

    # https://cloud.google.com/compute/docs/storing-retrieving-metadata#querying
    GCP_VM_API_URL = 'http://metadata.google.internal/computeMetadata/v1/instance'
    GCP_VM_API_URL_CHECK = 'http://metadata.google.internal/computeMetadata/v1/instance/id'
    GCP_VM_API_METADATA = {'cpu-platform': 'cpu-platform',
                           'description' : 'description',
                           'hostname' : 'hostname',
                           'id' : 'id',
                           'machine-type' : 'machine-type',
                           'name' : 'name',
                           'tags' : 'tags',
                           'zone' : 'zone'
                           }

    def __init__(self):
        """Init the class"""
        logger.debug("cloud plugin - Create thread for AWS EC2")
        super(ThreadAwsEc2Grabber, self).__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The class return the stats as a dict
        self._stats = {}

    def run(self):
        """Function called to grab stats.
        Infinite loop, should be stopped by calling the stop() method"""

        if not cloud_tag:
            logger.debug("cloud plugin - Requests lib is not installed")
            self.stop()
            return False

        cloud = self.determine_cloud_provider()

        if cloud == self.AWS:
            r_url = self.AWS_EC2_API_URL
            try:
                r = requests.get(r_url, timeout=3)
                if r.ok:
                    document = json.loads(r.content)
                    self._stats['privateIp'] = document['privateIp']
                    self._stats['devpayProductCodes'] = document['devpayProductCodes']
                    self._stats['marketplaceProductCodes'] = document['marketplaceProductCodes']
                    self._stats['version'] = document['version']
                    self._stats['instanceId'] = document['instanceId']
                    self._stats['billingProducts'] = document['billingProducts']
                    self._stats['instanceType'] = document['instanceType']
                    self._stats['availabilityZone'] = document['availabilityZone']
                    self._stats['kernelId'] = document['kernelId']
                    self._stats['ramdiskId'] = document['ramdiskId']
                    self._stats['accountId'] = document['accountId']
                    self._stats['architecture'] = document['architecture']
                    self._stats['imageId'] = document['imageId']
                    self._stats['pendingTime'] = document['pendingTime']
                    self._stats['region'] = document['region']
                    self._stats['type'] = self.AWS
            except Exception as e:
                logger.debug('cloud plugin - Cannot connect to the AWS EC2 API {}: {}'.format(r_url, e))
        elif cloud == self.AZURE:
            r_url = self.AZURE_VM_API_URL
            try:
                headers = {}
                headers['Metadata'] = "true"
                r = requests.get(r_url, headers=headers, timeout=3)
                if r.ok:
                    document = json.loads(r.content)
                    self._stats['compute'] = document['compute']
                    self._stats['network'] = document['network']
                    self._stats['type'] = self.AZURE
            except Exception as e:
                logger.debug('cloud plugin - Cannot connect to the AZURE VM API {}: {}'.format(r_url, e))
        elif cloud == self.GCP:
            self._stats['type'] = self.GCP
            for k, v in iteritems(self.GCP_VM_API_METADATA):
                r_url = '{}/{}'.format(self.GCP_VM_API_URL, v)
                try:
                    headers = {}
                    headers['Metadata-Flavor'] = "Google"
                    # Local request, a timeout of 3 seconds is OK
                    r = requests.get(r_url, headers=headers, timeout=3)
                    if r.ok:
                        self._stats[k] = r.content
                except Exception as e:
                    logger.debug('cloud plugin - Cannot connect to the GCP VM API {}: {}'.format(r_url, e))


        return True

    @property
    def stats(self):
        """Stats getter"""
        return self._stats

    @stats.setter
    def stats(self, value):
        """Stats setter"""
        self._stats = value

    def stop(self, timeout=None):
        """Stop the thread"""
        logger.debug("cloud plugin - Close thread for AWS EC2")
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped"""
        return self._stopper.isSet()

    def determine_cloud_provider(self):
        for url in [self.AWS_EC2_API_URL_CHECK, self.AZURE_VM_API_URL_CHECK, self.GCP_VM_API_URL_CHECK]:
            headers = {}
            if url == self.AZURE_VM_API_URL_CHECK:
                headers['Metadata'] = "true"
            elif url == self.GCP_VM_API_URL_CHECK:
                headers['Metadata-Flavor'] = "Google"
            r = requests.get(url, headers=headers)
            if r.ok:
                if url == self.AWS_EC2_API_URL_CHECK:
                    return self.AWS
                elif url == self.AZURE_VM_API_URL_CHECK:
                    return self.AZURE
                elif url == self.GCP_VM_API_URL_CHECK:
                    return self.GCP
        return None
