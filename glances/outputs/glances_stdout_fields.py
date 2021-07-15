# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2021 Nicolargo <nicolas@nicolargo.com>
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

"""Fields description interface class."""

from pprint import pformat

from glances.logger import logger
from glances.compat import iteritems


class GlancesStdoutFieldsDescription(object):

    """
    This class manages the fields description display.
    """

    def __init__(self, config=None, args=None):
        # Init
        self.config = config
        self.args = args

    def end(self):
        pass

    def update(self,
               stats,
               duration=3):
        """Display issue
        """
        print('.. _apidoc:')
        print('')
        print('Restfull/API plugins documentation')
        print('==================================')
        print('')
        print('The Glances Restfull/API server could be ran using the following command line:')
        print('')
        print('.. code-block:: bash')
        print('')
        print('    # glances -w --disable-webui')
        print('')
        for plugin in sorted(stats._plugins):
            if stats._plugins[plugin].fields_description:
                print('{}'.format(plugin))
                print('-' * len(plugin))
                print('')
                for field, description in iteritems(stats._plugins[plugin].fields_description):
                    print('* **{}**: {} (unit is *{}*)'.format(field,
                            description['description'][:-1] if description['description'].endswith('.') else description['description'],
                            description['unit']))
                print('')
                print('GET {} plugin stats:'.format(plugin))
                print('')
                print('.. code-block:: json')
                print('')
                print('    # curl http://localhost:61208/api/3/{}'.format(plugin))
                stat = stats._plugins[plugin].get_export()
                if isinstance(stat, list) and len(stat) > 1:
                    # Only display two first items
                    print('    ' + pformat(stat[0:2]).replace('\n', '\n    '))
                else:
                    print('    ' + pformat(stat).replace('\n', '\n    '))
                print('')
            else:
                logger.error('No fields_description variable defined for plugin {}'.format(plugin))

        # Return True to exit directly (no refresh)
        return True
