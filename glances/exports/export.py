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

from glances.globals import NoOptionError, NoSectionError, json_dumps
from glances.logger import logger
from glances.timer import Counter


class GlancesExport:
    """Main class for Glances export IF."""

    # List of non exportable internal plugins
    non_exportable_plugins = [
        "alert",
        "help",
        "plugin",
        "psutilversion",
        "quicklook",
        "version",
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

        # Fields description
        self._fields_description = None

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

    def load_conf(self, section, mandatories=["host", "port"], options=None):
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
        logger.debug(f"{section} parameters: { ({opt: getattr(self, opt) for opt in mandatories + options}) }")

        return True

    def get_item_key(self, item):
        """Return the value of the item 'key'."""
        ret = None
        try:
            ret = item[item["key"]]
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
                d_tags = dict([x.split(":") for x in tags.split(",")])
            except ValueError:
                # one of the 'key:value' pairs was missing
                logger.info("Invalid tags passed: %s", tags)
                d_tags = {}

        return d_tags

    def normalize_for_influxdb(self, name, columns, points):
        """Normalize data for the InfluxDB's data model.

        :return: a list of measurements.
        """
        FIELD_TO_TAG = ["name", "cmdline", "type"]
        ret = []

        # Build initial dict by crossing columns and point
        data_dict = dict(zip(columns, points))

        # issue1871 - Check if a key exist. If a key exist, the value of
        # the key should be used as a tag to identify the measurement.
        keys_list = [k.split(".")[0] for k in columns if k.endswith(".key")]
        if not keys_list:
            keys_list = [None]

        for measurement in keys_list:
            # Manage field
            if measurement is not None:
                fields = {
                    k.replace(f"{measurement}.", ""): data_dict[k] for k in data_dict if k.startswith(f"{measurement}.")
                }
            else:
                fields = data_dict
            # Transform to InfluxDB data model
            # https://docs.influxdata.com/influxdb/v1.8/write_protocols/line_protocol_reference/
            for k in fields:
                #  Do not export empty (None) value
                if fields[k] is None:
                    continue
                # Convert numerical to float
                try:
                    fields[k] = float(fields[k])
                except (TypeError, ValueError):
                    # Convert others to string
                    try:
                        fields[k] = str(fields[k])
                    except (TypeError, ValueError):
                        pass
            # Manage tags
            tags = self.parse_tags(self.tags)
            # Add the hostname as a tag
            tags["hostname"] = self.hostname
            if "hostname" in fields:
                fields.pop("hostname")
            # Others tags...
            if "key" in fields and fields["key"] in fields:
                # Create a tag from the key
                # Tag should be an string (see InfluxDB data model)
                tags[fields["key"]] = str(fields[fields["key"]])
                # Remove it from the field list (can not be a field and a tag)
                fields.pop(fields["key"])
            # Add name as a tag (example for the process list)
            for k in FIELD_TO_TAG:
                if k in fields:
                    tags[k] = str(fields[k])
                    # Remove it from the field list (can not be a field and a tag)
                    fields.pop(k)
            # Add the measurement to the list
            ret.append({"measurement": name, "tags": tags, "fields": fields})
        return ret

    def plugins_to_export(self, stats):
        """Return the list of plugins to export.

        :param stats: the stats object
        :return: a list of plugins to export
        """
        return [p for p in stats.getPluginsList() if p not in self.non_exportable_plugins]

    def last_exported_list(self):
        """Return the list of plugins last exported."""
        return self._last_exported_list

    def init_fields(self, stats):
        """Return fields description in order to init stats in a server."""
        if not self.export_enable:
            return False

        self._last_exported_list = self.plugins_to_export(stats)
        self._fields_description = stats.getAllFieldsDescriptionAsDict(plugin_list=self.last_exported_list())
        return self._fields_description

    def update(self, stats):
        """Update stats to a server.

        The method builds two lists: names and values and calls the export method to export the stats.

        Note: if needed this class can be overwritten.
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
                # Remove the <plugin>_disable field
                all_stats[plugin].pop(f"{plugin}_disable", None)
            elif isinstance(all_stats[plugin], list):
                # TypeError: string indices must be integers (Network plugin) #1054
                for i in all_stats[plugin]:
                    i.update(all_limits[plugin])
                    # Remove the <plugin>_disable field
                    i.pop(f"{plugin}_disable", None)
            else:
                continue
            export_names, export_values = self.build_export(all_stats[plugin])
            self.export(plugin, export_names, export_values)

        return True

    def build_export(self, stats):
        """Build the export lists.
        This method builds two lists: names and values.
        """

        # Initialize export lists
        export_names = []
        export_values = []

        if isinstance(stats, dict):
            # Stats is a dict
            # Is there a key ?
            if "key" in stats.keys() and stats["key"] in stats.keys():
                pre_key = "{}.".format(stats[stats["key"]])
            else:
                pre_key = ""
            # Walk through the dict
            for key, value in sorted(stats.items()):
                if isinstance(value, bool):
                    value = json_dumps(value).decode()

                if isinstance(value, list):
                    value = " ".join([str(v) for v in value])

                if isinstance(value, dict):
                    item_names, item_values = self.build_export(value)
                    item_names = [pre_key + key.lower() + str(i) for i in item_names]
                    export_names += item_names
                    export_values += item_values
                else:
                    # We are on a simple value
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
