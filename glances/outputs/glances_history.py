# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2014 Nicolargo <nicolas@nicolargo.com>
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

"""History class."""

# Import system lib
import os

# Import Glances lib
from glances.core.glances_globals import logger

# Import specific lib
try:
    from matplotlib import __version__ as matplotlib_version
    import matplotlib.pyplot as plt
except:
    matplotlib_check = False
    logger.warning(
        'Can not load Matplotlib library. Please install it using "pip install matplotlib"')
else:
    matplotlib_check = True
    logger.info('Load Matplotlib version %s' % matplotlib_version)


class GlancesHistory(object):

    """This class define the object to manage stats history"""

    def __init__(self, output_folder):
        self.output_folder = output_folder

    def get_output_folder(self):
        """Return the output folder where the graph are generated"""
        return self.output_folder

    def graph_enabled(self):
        """Return True if Glances can generaate history graphs"""
        return matplotlib_check

    def reset(self, stats):
        """
        Reset all the history
        """
        if not self.graph_enabled():
            return False
        for p in stats.getAllPlugins():
            h = stats.get_plugin(p).get_stats_history()
            if h is not None:
                stats.get_plugin(p).reset_stats_history()
        return True

    def get_graph_color(self, item):
        """
        Get the item's color
        """
        try:
            ret = item['color']
        except KeyError:
            return '#FFFFFF'
        else:
            return ret

    def get_graph_ylegend(self, item):
        """
        Get the item's Y legend
        """
        try:
            ret = item['label_y']
        except KeyError:
            return ''
        else:
            return ' ' + ret

    def generate_graph(self, stats):
        """
        Generate graphs from plugins history
        """
        if not self.graph_enabled():
            return False

        for p in stats.getAllPlugins():
            h = stats.get_plugin(p).get_stats_history()
            # Init graph
            plt.clf()
            fig = plt.gcf()
            fig.set_size_inches(20, 10)
            # Data
            if h is None:
                # History (h) not available for plugin (p)
                continue
            index_graph = 0
            for i in stats.get_plugin(p).get_items_history_list():
                if i['name'] in h.keys():
                    # The key exist
                    # Add the curve in the current chart
                    logger.debug("Generate graph: %s %s" % (p, i['name']))
                    index_graph += 1
                    plt.title(p.capitalize())
                    plt.subplot(len(stats.get_plugin(p).get_items_history_list()), 1, index_graph)
                    plt.ylabel(i['name'] + self.get_graph_ylegend(i))
                    plt.grid(True)
                    plt.plot_date(h['date'], h[i['name']],
                                  fmt='', drawstyle='default', linestyle='-',
                                  color=self.get_graph_color(i),
                                  xdate=True, ydate=False)
                else:
                    # The key did not exist
                    # Find if anothers key ends with the key
                    # Ex: key='tx' => 'ethernet_tx'
                    stats_history_filtered = sorted([key for key in h.keys() if key.endswith(i['name'])])
                    logger.debug("Generate graphs: %s %s" % (p, stats_history_filtered))
                    if len(stats_history_filtered) > 0:
                        # Create 'n' graph
                        # Each graph iter through the stats
                        plt.clf()
                        index_item = 0
                        for k in stats_history_filtered:
                            index_item += 1
                            plt.title(p.capitalize())
                            plt.subplot(len(stats_history_filtered), 1, index_item)
                            plt.ylabel(k + self.get_graph_ylegend(i))
                            plt.grid(True)
                            plt.plot_date(h['date'], h[k],
                                          fmt='', drawstyle='default', linestyle='-',
                                          color=self.get_graph_color(i),
                                          xdate=True, ydate=False)
                        # Save the graph to output file
                        plt.xlabel('Date')
                        plt.savefig(os.path.join(self.output_folder, 'glances_%s_%s.png' % (p, i['name'])), dpi=72)

            if index_graph > 0:
                # Save the graph to output file
                plt.xlabel('Date')
                plt.savefig(os.path.join(self.output_folder, 'glances_%s.png' % (p)), dpi=72)

            plt.close()

        return True


def generate_graph_OLD(self, stats):
        """
        Generate graphs from plugins history
        """
        if not self.graph_enabled():
            return False

        for p in stats.getAllPlugins():
            h = stats.get_plugin(p).get_stats_history()
            # Generate graph (init)
            plt.clf()
            # Title and axis
            plt.title(p.capitalize())
            plt.grid(True)
            if h is not None:
                # History (h) available for plugin (p)
                index = 1
                for k, v in h.iteritems():
                    if k != 'date':
                        plt.subplot(len(h), 1, index)
                        index += 1
                        plt.xlabel('Date')
                        plt.ylabel(self.get_graph_ylegend(stats, p, k))
                        # Data
                        plt.plot_date(h['date'], h[k],
                                      fmt='', drawstyle='default', linestyle='-',
                                      color=self.get_graph_color(stats, p, k),
                                      xdate=True, ydate=False)
                        # Save the graph to output file
                        plt.savefig(os.path.join(self.output_folder, 'glances_%s_%s.png' % (p, k)), dpi=72)
        return True
