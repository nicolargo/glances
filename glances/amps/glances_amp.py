# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2016 Nicolargo <nicolas@nicolargo.com>
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

"""
I am your father...

...for all Glances Application Monitoring Processes (AMP).

AMP (Application Monitoring Process)
A Glances AMP is a Python script called (every *refresh* seconds) if:
- the AMP is *enabled* in the Glances configuration file
- a process is running (match the *regex* define in the configuration file)
The script should define a Amp (GlancesAmp) class with, at least, an update method.
The update method should call the set_result method to set the AMP return string.
The return string is a string with one or more line (\n between lines).
If the *one_line* var is true then the AMP will be displayed in one line.
"""

from glances.compat import u
from glances.timer import Timer
from glances.logger import logger


class GlancesAmp(object):
    """Main class for Glances AMP."""

    NAME = '?'
    VERSION = '?'
    DESCRIPTION = '?'
    AUTHOR = '?'
    EMAIL = '?'

    def __init__(self, args=None):
        """Init AMP classe."""
        logger.debug("Init {0} version {1}".format(self.NAME, self.VERSION))

        # AMP name (= module name without glances_)
        self.amp_name = self.__class__.__module__[len('glances_'):]

        # Init the args
        self.args = args

        # Init the configs
        self.configs = {}

        # A timer is needed to only update every refresh seconds
        # Init to 0 in order to update the AMP on startup
        self.timer = Timer(0)

    def load_config(self, config):
        """Load AMP parameters from the configuration file."""

        # Read AMP confifuration.
        # For ex, the AMP foo should have the following section:
        #
        # [foo]
        # enable=true
        # regex=\/usr\/bin\/nginx
        # refresh=60
        #
        # and optionnaly:
        #
        # one_line=false
        # option1=opt1
        # ...
        #
        if (hasattr(config, 'has_section') and
                config.has_section(self.amp_name)):
            logger.debug("{0}: Load configuration".format(self.NAME))
            for param, _ in config.items(self.amp_name):
                try:
                    self.configs[param] = config.get_float_value(self.amp_name, param)
                except ValueError:
                    self.configs[param] = config.get_value(self.amp_name, param).split(',')
                    if len(self.configs[param]) == 1:
                        self.configs[param] = self.configs[param][0]
                logger.debug("{0}: Load parameter: {1} = {2}".format(self.NAME, param, self.configs[param]))
        else:
            logger.warning("{0}: Can not find section {1} in the configuration file {2}".format(self.NAME, self.amp_name, config))

        # enable, regex and refresh are mandatories
        # if not configured then AMP is disabled
        for k in ['enable', 'regex', 'refresh']:
            if k not in self.configs:
                logger.warning("{0}: Can not find configuration key {1} in section {2}".format(self.NAME, k, self.amp_name))
                self.configs['enable'] = 'false'

        if not self.enable():
            logger.warning("{0} is disabled".format(self.NAME))

    def get(self, key):
        """Generic method to get the item in the AMP configuration"""
        if key in self.configs:
            return self.configs[key]
        else:
            return None

    def enable(self):
        """Return True|False if the AMP is enabled in the configuration file (enable=true|false)."""
        return self.get('enable').lower().startswith('true')

    def regex(self):
        """Return regular expression used to identified the current application."""
        return self.get('regex')

    def refresh(self):
        """Return refresh time in seconds for the current application monitoring process."""
        return self.get('refresh')

    def time_until_refresh(self):
        """Return time in seconds until refresh."""
        return self.timer.get()

    def should_update(self):
        """Return True is the AMP should be updated:
        - AMP is enable
        - only update every 'refresh' seconds
        """
        if self.timer.finished():
            self.timer.set(self.refresh())
            self.timer.reset()
            return self.enable()
        return False

    def set_result(self, result):
        """Store the result (string) into the result key of the AMP"""
        self.configs['result'] = str(result)

    def result(self):
        """ Return the result of the AMP (as a string)"""
        ret = self.get('result')
        if ret is not None:
            ret = u(ret)
        return ret
