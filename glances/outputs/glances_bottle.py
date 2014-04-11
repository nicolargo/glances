#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Glances - An eye on your system
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

# Import system lib
import os
import sys
try:
    from bottle import Bottle, template, static_file, TEMPLATE_PATH
except ImportError:
    print('Bottle module not found. Glances cannot start in web server mode.')
    sys.exit(1)

# Import Glances lib
from glances.core.glances_timer import Timer
from glances.core.glances_globals import glances_logs, glances_processes


class glancesBottle:
    """
    This class manage the Bottle Web Server
    """

    def __init__(self, args=None):

        # Init args
        self.args = args

        # Init stats
        # Will be updated within Bottle route
        self.stats = None

        # Init Bottle
        self._host = 'localhost'
        self._port = 8080
        self._app = Bottle()
        self._route()

        # Update the template path (glances/outputs/bottle)
        TEMPLATE_PATH.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'bottle'))

        # Path where the statics files are stored
        self.STATIC_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static')

        # Define the style (CSS) list (hash table) for stats
        self.__style_list = {
            'DEFAULT': '',
            'UNDERLINE': 'underline',
            'BOLD': 'bold',
            'SORT': 'sort',
            'OK': 'ok',
            'TITLE': 'title',
            'CAREFUL': 'careful',
            'WARNING': 'warning',
            'CRITICAL': 'critical',
            'OK_LOG': 'ok_log',
            'CAREFUL_LOG': 'careful_log',
            'WARNING_LOG': 'warning_log',
            'CRITICAL_LOG': 'critical_log'
        }


    def _route(self):
        """
        Define route
        """
        self._app.route('/', method="GET", callback=self._index)
        self._app.route('/<refresh_time:int>', method=["GET", "POST"], callback=self._index)
        self._app.route('/<filename:re:.*\.css>', method="GET", callback=self._css)

    def start(self, stats):
        # Init stats
        self.stats = stats

        # Start the Bottle
        self._app.run(host=self._host, port=self._port)

    def end(self):
        # End the Bottle
        pass

    def _index(self, refresh_time=None):
        """
        Bottle callback for index.html (/) file
        """
        # Manage parameter
        if (refresh_time is None):
            refresh_time = self.args.time

        # Update the stat
        self.stats.update()
        
        # Display
        return self.display(self.stats, refresh_time=refresh_time)

    def _css(self, filename):
        """
        Bottle callback for *.css files
        """
        # Return the static file
        return static_file(filename, root=os.path.join(self.STATIC_PATH, 'css'))

    def display(self, stats, refresh_time=None):
        """
        Display stats on the Webpage

        stats: Stats database to display
        """

        html = template('header', refresh_time=refresh_time)
        html += "<header>"
        html += self.display_plugin('system', self.stats.get_plugin('system').get_curse(args=self.args))
        html += self.display_plugin('uptime', self.stats.get_plugin('uptime').get_curse(args=self.args))
        html += "</header>"
        html += template('newline')
        html += "<section>"
        html += self.display_plugin('cpu', self.stats.get_plugin('cpu').get_curse(args=self.args))
        html += self.display_plugin('load', self.stats.get_plugin('load').get_curse(args=self.args))
        html += self.display_plugin('mem', self.stats.get_plugin('mem').get_curse(args=self.args))
        html += self.display_plugin('memswap', self.stats.get_plugin('memswap').get_curse(args=self.args))
        html += "</section>"
        html += template('newline')
        html += "<section>"
        html += "<aside>"
        html += self.display_plugin('network', self.stats.get_plugin('network').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('diskio', self.stats.get_plugin('diskio').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('fs', self.stats.get_plugin('fs').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('sensors', self.stats.get_plugin('sensors').get_curse(args=self.args))
        html += "</aside>"
        html += "<aside>"
        html += self.display_plugin('alert', self.stats.get_plugin('alert').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('processcount', self.stats.get_plugin('processcount').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('monitor', self.stats.get_plugin('monitor').get_curse(args=self.args))
        html += template('newline')
        html += self.display_plugin('processlist', self.stats.get_plugin('processlist').get_curse(args=self.args))
        html += "</aside>"
        html += "</section>"
        html += template('footer')

        return html

    def display_plugin(self, plugin_name, plugin_stats):
        """
        Generate the Bootle template for the plugin_stats
        """

        # Template header
        tpl = """ \
                %#Template for Bottle
              """
        tpl += '<article class="plugin" id="%s">' % plugin_name

        tpl += '<div id="table">'
        tpl += '<div class="row">'
        for m in plugin_stats['msgdict']:
            # New line
            if (m['msg'].startswith('\n')):
                tpl += '</div>'
                tpl += '<div class="row">'
                continue
            tpl += '<span class="cell" id="%s">%s</span>' % (self.__style_list[m['decoration']] , 
                                                                               m['msg'].replace(' ', '&nbsp;'))
        tpl += '</div>'
        tpl += '</div>'
        
        tpl += """ \
                </article>   
                %#End Template for Bottle
               """
        return template(tpl)        