#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2024 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

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

from glances.globals import u
from glances.logger import logger
from glances.timer import Timer


class GlancesAmp:
    """Main class for Glances AMP."""

    NAME = '?'
    VERSION = '?'
    DESCRIPTION = '?'
    AUTHOR = '?'
    EMAIL = '?'

    def __init__(self, name=None, args=None):
        """Init AMP class."""
        logger.debug(f"AMP - Init {self.NAME} version {self.VERSION}")

        # AMP name (= module name without glances_)
        if name is None:
            self.amp_name = self.__class__.__module__
        else:
            self.amp_name = name

        # Init the args
        self.args = args

        # Init the configs
        self.configs = {}

        # A timer is needed to only update every refresh seconds
        # Init to 0 in order to update the AMP on startup
        self.timer = Timer(0)

    def load_config(self, config):
        """Load AMP parameters from the configuration file."""

        # Read AMP configuration.
        # For ex, the AMP foo should have the following section:
        #
        # [foo]
        # enable=true
        # regex=\/usr\/bin\/nginx
        # refresh=60
        #
        # and optionally:
        #
        # one_line=false
        # option1=opt1

        amp_section = 'amp_' + self.amp_name
        if hasattr(config, 'has_section') and config.has_section(amp_section):
            logger.debug(f"AMP - {self.NAME}: Load configuration")
            for param, _ in config.items(amp_section):
                try:
                    self.configs[param] = config.get_float_value(amp_section, param)
                except ValueError:
                    self.configs[param] = config.get_value(amp_section, param).split(',')
                    if len(self.configs[param]) == 1:
                        self.configs[param] = self.configs[param][0]
                logger.debug(f"AMP - {self.NAME}: Load parameter: {param} = {self.configs[param]}")
        else:
            logger.debug(f"AMP - {self.NAME}: Can not find section {self.amp_name} in the configuration file")
            return False

        if self.enable():
            # Refresh option is mandatory
            for k in ['refresh']:
                if k not in self.configs:
                    logger.warning(
                        f"AMP - {self.NAME}: Can not find configuration key {k} in section {self.amp_name} "
                        f"(the AMP will be disabled)"
                    )
                    self.configs['enable'] = 'false'
        else:
            logger.debug(f"AMP - {self.NAME} is disabled")

        # Init the count to 0
        self.configs['count'] = 0

        return self.enable()

    def get(self, key):
        """Generic method to get the item in the AMP configuration"""
        if key in self.configs:
            return self.configs[key]
        return None

    def enable(self):
        """Return True|False if the AMP is enabled in the configuration file (enable=true|false)."""
        ret = self.get('enable')
        if ret is None:
            return False
        return ret.lower().startswith('true')

    def regex(self):
        """Return regular expression used to identified the current application."""
        return self.get('regex')

    def refresh(self):
        """Return refresh time in seconds for the current application monitoring process."""
        return self.get('refresh')

    def one_line(self):
        """Return True|False if the AMP should be displayed in one line (one_line=true|false)."""
        ret = self.get('one_line')
        if ret is None:
            return False
        return ret.lower().startswith('true')

    def time_until_refresh(self):
        """Return time in seconds until refresh."""
        return self.timer.get()

    def should_update(self):
        """Return True is the AMP should be updated

        Conditions for update:
        - AMP is enable
        - only update every 'refresh' seconds
        """
        if self.timer.finished():
            self.timer.set(self.refresh())
            self.timer.reset()
            return self.enable()
        return False

    def set_count(self, count):
        """Set the number of processes matching the regex"""
        self.configs['count'] = count

    def count(self):
        """Get the number of processes matching the regex"""
        return self.get('count')

    def count_min(self):
        """Get the minimum number of processes"""
        return self.get('countmin')

    def count_max(self):
        """Get the maximum number of processes"""
        return self.get('countmax')

    def set_result(self, result, separator=''):
        """Store the result (string) into the result key of the AMP

        If one_line is true then it replaces `\n` by the separator
        """
        if self.one_line():
            self.configs['result'] = u(result).replace('\n', separator)
        else:
            self.configs['result'] = u(result)

    def result(self):
        """Return the result of the AMP (as a string)"""
        ret = self.get('result')
        if ret is not None:
            ret = u(ret)
        return ret

    def update_wrapper(self, process_list):
        """Wrapper for the children update"""
        # Set the number of running process
        self.set_count(len(process_list))
        # Call the children update method
        if self.should_update():
            return self.update(process_list)
        return self.result()
