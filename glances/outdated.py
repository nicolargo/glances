#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""Manage Glances update."""

import json
import os
import pickle
import threading
from datetime import datetime, timedelta
from ssl import CertificateError

from glances import __version__
from glances.config import user_cache_dir
from glances.globals import HTTPError, URLError, nativestr, safe_makedirs, urlopen
from glances.logger import logger

try:
    from packaging.version import Version

    PACKAGING_IMPORT = True
except Exception as e:
    logger.warning(f"Unable to import 'packaging' module ({e}). Glances cannot check for updates.")
    PACKAGING_IMPORT = False

PYPI_API_URL = 'https://pypi.python.org/pypi/Glances/json'


class Outdated:
    """
    This class aims at providing methods to warn the user when a new Glances
    version is available on the PyPI repository (https://pypi.python.org/pypi/Glances/).
    """

    def __init__(self, args, config):
        """Init the Outdated class"""
        self.args = args
        self.config = config
        self.cache_dir = user_cache_dir()[0]
        self.cache_file = os.path.join(self.cache_dir, 'glances-version.db')

        # Set default value...
        self.data = {'installed_version': __version__, 'latest_version': '0.0', 'refresh_date': datetime.now()}

        # Disable update check if `packaging` is not installed
        if not PACKAGING_IMPORT:
            self.args.disable_check_update = True

        # Read the configuration file only if update check is not explicitly disabled
        if not self.args.disable_check_update:
            self.load_config(config)

        logger.debug(f"Check Glances version up-to-date: {not self.args.disable_check_update}")

        # And update !
        self.get_pypi_version()

    def load_config(self, config):
        """Load outdated parameter in the global section of the configuration file."""

        global_section = 'global'
        if hasattr(config, 'has_section') and config.has_section(global_section):
            self.args.disable_check_update = config.get_value(global_section, 'check_update').lower() == 'false'
        else:
            logger.debug(f"Cannot find section {global_section} in the configuration file")
            return False

        return True

    def installed_version(self):
        return self.data['installed_version']

    def latest_version(self):
        return self.data['latest_version']

    def refresh_date(self):
        return self.data['refresh_date']

    def get_pypi_version(self):
        """Wrapper to get the latest PyPI version (async)

        The data are stored in a cached file
        Only update online once a week
        """
        if self.args.disable_check_update:
            return

        # If the cached file exist, read-it
        cached_data = self._load_cache()

        if cached_data == {}:
            # Update needed
            # Update and save the cache
            thread = threading.Thread(target=self._update_pypi_version)
            thread.start()
        else:
            # Update not needed
            self.data['latest_version'] = cached_data['latest_version']
            logger.debug("Get Glances version from cache file")

    def is_outdated(self):
        """Return True if a new version is available"""
        if self.args.disable_check_update:
            # Check is disabled by configuration
            return False

        logger.debug(f"Check Glances version (installed: {self.installed_version()} / latest: {self.latest_version()})")
        return Version(self.latest_version()) > Version(self.installed_version())

    def _load_cache(self):
        """Load cache file and return cached data"""
        # If the cached file exist, read-it
        max_refresh_date = timedelta(days=7)
        cached_data = {}
        try:
            with open(self.cache_file, 'rb') as f:
                cached_data = pickle.load(f)
        except Exception as e:
            logger.debug(f"Cannot read version from cache file: {self.cache_file} ({e})")
        else:
            logger.debug("Read version from cache file")
            if (
                cached_data['installed_version'] != self.installed_version()
                or datetime.now() - cached_data['refresh_date'] > max_refresh_date
            ):
                # Reset the cache if:
                # - the installed version is different
                # - the refresh_date is > max_refresh_date
                cached_data = {}
        return cached_data

    def _save_cache(self):
        """Save data to the cache file."""
        # Create the cache directory
        safe_makedirs(self.cache_dir)

        # Create/overwrite the cache file
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.data, f)
        except Exception as e:
            logger.error(f"Cannot write version to cache file {self.cache_file} ({e})")

    def _update_pypi_version(self):
        """Get the latest PyPI version (as a string) via the RESTful JSON API"""
        logger.debug(f"Get latest Glances version from the PyPI RESTful API ({PYPI_API_URL})")

        # Update the current time
        self.data['refresh_date'] = datetime.now()

        try:
            res = urlopen(PYPI_API_URL, timeout=3).read()
        except (HTTPError, URLError, CertificateError) as e:
            logger.debug(f"Cannot get Glances version from the PyPI RESTful API ({e})")
        else:
            self.data['latest_version'] = json.loads(nativestr(res))['info']['version']
            logger.debug("Save Glances version to the cache file")

        # Save result to the cache file
        # Note: also saved if the Glances PyPI version cannot be grabbed
        self._save_cache()

        return self.data
