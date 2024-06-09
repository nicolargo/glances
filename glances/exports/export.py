#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2022 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""
I am your father...

...for all Glances exports IF.
"""

from glances.globals import NoOptionError, NoSectionError, iteritems, iterkeys, json_dumps
from glances.logger import logger
from glances.timer import Counter


class GlancesExport:
    """Main class for Glances export IF."""

    # List of non exportable plugins
    # @TODO: remove this part and make all plugins exportable (see issue #1556)
    # @TODO: also make this list configurable by the user (see issue #1443)
    non_exportable_plugins = [
        'alert',
        'amps',
        'help',
        'now',
        'plugin',
        'psutilversion',
        'quicklook',
        'version',
    ]

    def __init__(self, config=None, args=None):
        """Init the export class."""
        # Export name
        self.export_name = self.__class__.__module__
        logger.debug(f"Init export module {self.export_name}")

        # Init the config & args
        self.config = config
        self.args = args

        # By default export is disabled
        # Needs to be set to True in the __init__ class of child
        self.export_enable = False

        # Mandatory for (most of) the export module
        self.host = None
        self.port = None

        # Save last export list
        self._last_exported_list = None

    def _log_result_decorator(fct):
        """Log (DEBUG) the result of the function fct."""

        def wrapper(*args, **kw):
            counter = Counter()
            ret = fct(*args, **kw)
            duration = counter.get()
            class_name = args[0].__class__.__name__
            class_module = args[0].__class__.__module__
            logger.debug(f"{class_name} {class_module} {fct.__name__} return {ret} in {duration} seconds")
            return ret

        return wrapper

    def exit(self):
        """Close the export module."""
        logger.debug(f"Finalise export interface {self.export_name}")

    def load_conf(self, section, mandatories=['host', 'port'], options=None):
        """Load the export <section> configuration in the Glances configuration file.

        :param section: name of the export section to load
        :param mandatories: a list of mandatory parameters to load
        :param options: a list of optional parameters to load

        :returns: Boolean -- True if section is found
        """
        options = options or []

        if self.config is None:
            return False

        # By default read the mandatory host:port items
        try:
            for opt in mandatories:
                setattr(self, opt, self.config.get_value(section, opt))
        except NoSectionError:
            logger.error(f"No {section} configuration found")
            return False
        except NoOptionError as e:
            logger.error(f"Error in the {section} configuration ({e})")
            return False

        # Load options
        for opt in options:
            try:
                setattr(self, opt, self.config.get_value(section, opt))
            except NoOptionError:
                pass

        logger.debug(f"Load {section} from the Glances configuration file")
        logger.debug(f"{section} parameters: {({opt: getattr(self, opt) for opt in mandatories + options})}")

        return True

    def get_item_key(self, item):
        """Return the value of the item 'key'."""
        ret = None
        try:
            ret = item[item['key']]
        except KeyError:
            logger.error(f"No 'key' available in {item}")
        if isinstance(ret, list):
            return ret[0]
        return ret

    def parse_tags(self, tags):
        """Parse tags into a dict.

        :param tags: a comma-separated list of 'key:value' pairs. Example: foo:bar,spam:eggs
        :return: a dict of tags. Example: {'foo': 'bar', 'spam': 'eggs'}
        """
        d_tags = {}
        if tags:
            try:
                d_tags = dict([x.split(':') for x in tags.split(',')])
            except ValueError:
                # one of the 'key:value' pairs was missing
                logger.info('Invalid tags passed: %s', tags)
                d_tags = {}

        return d_tags

    def plugins_to_export(self, stats):
        """Return the list of plugins to export.

        :param stats: the stats object
        :return: a list of plugins to export
        """
        return [p for p in stats.getPluginsList() if p not in self.non_exportable_plugins]

    def last_exported_list(self):
        """Return the list of plugins last exported."""
        return self._last_exported_list

    def update(self, stats):
        """Update stats to a server.

        The method builds two lists: names and values and calls the export method to export the stats.

        Note: this class can be overwritten (for example in CSV and Graph).
        """
        if not self.export_enable:
            return False

        # Get all the stats & limits
        self._last_exported_list = self.plugins_to_export(stats)
        all_stats = stats.getAllExportsAsDict(plugin_list=self.last_exported_list())
        all_limits = stats.getAllLimitsAsDict(plugin_list=self.last_exported_list())

        # Loop over plugins to export
        for plugin in self.last_exported_list():
            if isinstance(all_stats[plugin], dict):
                all_stats[plugin].update(all_limits[plugin])
            elif isinstance(all_stats[plugin], list):
                # TypeError: string indices must be integers (Network plugin) #1054
                for i in all_stats[plugin]:
                    i.update(all_limits[plugin])
            else:
                continue
            export_names, export_values = self.build_export(all_stats[plugin])
            self.export(plugin, export_names, export_values)

        return True

    def build_export(self, stats):
        """Build the export lists."""
        export_names = []
        export_values = []

        if isinstance(stats, dict):
            # Stats is a dict
            # Is there a key ?
            if 'key' in iterkeys(stats) and stats['key'] in iterkeys(stats):
                pre_key = '{}.'.format(stats[stats['key']])
            else:
                pre_key = ''
            # Walk through the dict
            for key, value in sorted(iteritems(stats)):
                if isinstance(value, bool):
                    value = json_dumps(value)

                if isinstance(value, list):
                    value = ' '.join([str(v) for v in value])

                if isinstance(value, dict):
                    item_names, item_values = self.build_export(value)
                    item_names = [pre_key + key.lower() + str(i) for i in item_names]
                    export_names += item_names
                    export_values += item_values
                else:
                    export_names.append(pre_key + key.lower())
                    export_values.append(value)
        elif isinstance(stats, list):
            # Stats is a list (of dict)
            # Recursive loop through the list
            for item in stats:
                item_names, item_values = self.build_export(item)
                export_names += item_names
                export_values += item_values
        return export_names, export_values

    def export(self, name, columns, points):
        # This method should be implemented by each exporter
        pass
