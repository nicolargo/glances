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
import tempfile

# Import Glances lib
from glances.core.glances_globals import logger

# Import specific lib
try:
    from matplotlib import __version__ as matplotlib_version
    import matplotlib.pyplot as plt
    import matplotlib.dates as dates
except:
    matplotlib_check = False
    logger.warning('Can not load Matplotlib library. Please install it using "pip install matplotlib"')
else:
    matplotlib_check = True
    logger.info('Load Matplotlib version %s' % matplotlib_version)


class GlancesHistory(object):

    """This class define the object to manage stats history"""

    def __init__(self, output_folder=tempfile.gettempdir()):
        # !!! MINUS: matplotlib footprint (mem/cpu) => Fork process ?
        # !!! MINUS: Mem used to store history
        # !!! TODO: sampling before graph => Usefull ?
        # !!! TODO: do not display first two point (glances is running)
        # !!! TODO: replace /tmp by a cross platform way to get /tmp folder
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

    def generate_graph(self, stats):
        """
        Generate graphs from plugins history
        """
        if not self.graph_enabled():
            return False

        for p in stats.getAllPlugins():
            h = stats.get_plugin(p).get_stats_history()
            if h is not None:
                # Build the graph
                # fig = plt.figure(dpi=72)
                ax = plt.subplot(1, 1, 1)

                # Label
                plt.title("%s stats" % p)
                
                handles = []
                for i in stats.get_plugin(p).get_items_history_list():
                    handles.append(plt.Rectangle((0, 0), 1, 1, fc=i['color'], ec=i['color'], linewidth=1))
                labels = [i['name'] for i in stats.get_plugin(p).get_items_history_list()]
                plt.legend(handles, labels, loc=1, prop={'size':9})
                formatter = dates.DateFormatter('%H:%M:%S')
                ax.xaxis.set_major_formatter(formatter)
                # ax.set_ylabel('%')

                # Draw the stats
                for i in stats.get_plugin(p).get_items_history_list():
                    ax.plot_date(h['date'], h[i['name']], 
                                 i['color'], 
                                 label='%s' % i['name'], 
                                 xdate=True, ydate=False)

                # Save and display
                plt.savefig(os.path.join(self.output_folder, 'glances_%s.png' % p), dpi=72)
                # plt.show()

        return True
