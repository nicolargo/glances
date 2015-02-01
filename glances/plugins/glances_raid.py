# -*- coding: utf-8 -*-
#
# This file is part of Glances.
#
# Copyright (C) 2015 Nicolargo <nicolas@nicolargo.com>
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

"""RAID plugin."""

# Import Glances libs
from glances.core.glances_logging import logger
from glances.plugins.glances_plugin import GlancesPlugin

# pymdstat only available on GNU/Linux OS
try:
    from pymdstat import MdStat
except ImportError:
    logger.debug("pymdstat library not found. Glances cannot grab RAID info.")
    pass


class Plugin(GlancesPlugin):

    """Glances' RAID plugin.

    stats is a dict (see pymdstat documentation)
    """

    def __init__(self, args=None):
        """Init the plugin."""
        GlancesPlugin.__init__(self, args=args)

        # We want to display the stat in the curse interface
        self.display_curse = True

        # Init the stats
        self.reset()

    def reset(self):
        """Reset/init the stats."""
        self.stats = {}

        # init view data
        self.view_data = {}
                
    @GlancesPlugin._log_result_decorator
    def update(self):
        """Update RAID stats using the input method."""
        # Reset stats
        self.reset()

        if self.get_input() == 'local':
            # Update stats using the PyMDstat lib (https://github.com/nicolargo/pymdstat)
            try:
                if self.args.debug_json:
                    mds = MdStatMock()
                else:
                    mds = MdStat()
                self.stats = mds.get_stats()['arrays']
            except Exception as e:
                logger.debug("Can not grab RAID stats (%s)" % e)
                return self.stats

        elif self.get_input() == 'snmp':
            # Update stats using SNMP
            # No standard way for the moment...
            pass

        # Update the view
        self.update_views()

        self.generate_view_data()
        
        return self.stats

    def generate_view_data(self):
        self.view_data['title'] = '{0:11}'.format(_('RAID disks'))
        self.view_data['title_used'] = '{0:>6}'.format(_("Used"))
        self.view_data['title_avail'] = '{0:>6}'.format(_("Avail"))
        
        self.view_data['raid'] = []
        # Data
        arrays = list(self.stats.keys())
        arrays.sort()
        for array in arrays:
            # Display the current status
            status = self.raid_alert(self.stats[array]['status'], self.stats[array]['used'], self.stats[array]['available'])
            
            raid = {}
            raid['status_label'] = status
            raid['current_status'] = self.stats[array]['status']
            raid['current_used'] = self.stats[array]['used']
            raid['current_available'] = self.stats[array]['available']
            
            # Data: RAID type name | disk used | disk available
            array_type = self.stats[array]['type'].upper() if self.stats[array]['type'] is not None else _('UNKNOWN')
            
            raid['type'] = '{0:<5}{1:>6}'.format(array_type, array)
            
            if raid['current_status'] == 'active':
                raid['used'] = '{0:>6}'.format(self.stats[array]['used'])
                raid['available'] = '{0:>6}'.format(self.stats[array]['available'])
            elif raid['current_status'] == 'inactive':
                raid['status'] = '└─ Status {}'.format(self.stats[array]['status'])
                components = self.stats[array]['components'].keys()
                components.sort()
                
                raid['components'] = []
                for i, component in enumerate(components):
                    if i == len(components) - 1:
                        tree_char = '└─'
                    else:
                        tree_char = '├─'
                    compo = {}
                    compo['treechar'] = '   {0} disk {1}: '.format(tree_char, self.stats[array]['components'][component])
                    compo['component'] = '{0}'.format(component)
                    raid['components'].append(compo)
                    
            if raid['current_used'] < raid['current_available']:
                # Display current array configuration
                raid['degraded_mode'] = '└─ Degraded mode'
                if len(self.stats[array]['config']) < 17:
                    raid['config'] = '   └─ {0}'.format(self.stats[array]['config'].replace('_', 'A'))
        
        
            self.view_data['raid'].append(raid)


    def get_view_data(self, args=None):        
        return self.view_data
    
    def msg_curse(self, args=None):
        """Return the dict to display in the curse interface."""
        # Init the return message
        ret = []

        # Only process if stats exist and display plugin enable...
        if not self.stats or args.disable_raid or not self.view_data:
            return ret

        # Build the string message
        # Header
        ret.append(self.curse_add_line(self.view_data['title'], "TITLE"))
        ret.append(self.curse_add_line(self.view_data['title_used']))
        ret.append(self.curse_add_line(self.view_data['title_avail']))
        
        for raid in self.view_data['raid']:
            # New line
            ret.append(self.curse_new_line())
            # Display the current status

            # Data: RAID type name | disk used | disk available
            ret.append(self.curse_add_line(raid['type']))
            
            if raid['current_status'] == 'active':
                ret.append(self.curse_add_line(raid['used'], raid['status_label']))
                ret.append(self.curse_add_line(raid['available'], raid['status_label']))
            elif raid['current_status'] == 'inactive':
                ret.append(self.curse_new_line())
                ret.append(self.curse_add_line(raid['status'], raid['status_label']))
                
                components = raid['components']
                for component in components:
                    ret.append(self.curse_new_line())
                    ret.append(self.curse_add_line(component['treechar']))
                    ret.append(self.curse_add_line(component['component']))
                    
            if raid['current_used'] < raid['current_available']:
                ret.append(self.curse_new_line())
                ret.append(self.curse_add_line(raid['degraded_mode'], raid['status_label']))
                if 'config' in raid:
                    ret.append(self.curse_add_line(raid['config']))

        return ret

    def raid_alert(self, status, used, available):
        """
        [available/used] means that ideally the array would have _available_ devices however, _used_ devices are in use.
        Obviously when used >= available then things are good.
        """
        if status == 'inactive':
            return 'CRITICAL'
        if used < available:
            return 'WARNING'
        return 'OK'


class MdStatMock:
    
    def __init__(self):
        self.personalities = ['raid1', 'raid6', 'raid5', 'raid4']
        self.arrays = ['md2', 'md3', 'md0', 'md1']
        
    def get_stats(self):
        return {'arrays': {'md0': {'available': '2',
           'components': {'sda1': '0', 'sdb1': '1'},
           'config': 'UU',
           'status': 'active',
           'type': 'raid1',
           'used': '2'},
          'md1': {'available': '2',
           'components': {'sda2': '0', 'sdb2': '1'},
           'config': 'UU',
           'status': 'active',
           'type': 'raid1',
           'used': '2'},
          'md2': {'available': '2',
           'components': {'sda3': '0', 'sdb3': '1'},
           'config': 'UU',
           'status': 'active',
           'type': 'raid1',
           'used': '2'},
          'md3': {'available': '10',
           'components': {'sdc1': '0',
            'sdd1': '1',
            'sde1': '2',
            'sdf1': '3',
            'sdg1': '4',
            'sdh1': '5',
            'sdi1': '6',
            'sdj1': '7',
            'sdk1': '8',
            'sdl1': '9'},
           'config': 'UUUUUUUUUU',
           'status': 'active',
           'type': 'raid5',
           'used': '10'}},
         'personalities': ['raid1', 'raid6', 'raid5', 'raid4']}
        
        
    def personalities(self):
        return self.personalities

    def arrays(self):
        return self.arrays
    
    def type(self, label):
        pos = self.personalities.index(label)
        if (pos >= 0):
            return self.arrays[pos]
        
    def status(self, label):
        return 'active'

    def components(self, label):
        return ['sdk1', 'sdj1', 'sde1', 'sdl1', 'sdg1', 'sdf1', 'sdh1', 'sdc1', 'sdd1', 'sdi1']
    
    def available(self, label):
        return 10
    
    def used(self, label):
        return 10
    
    def config(self, label):
        return 'UUUUUUUUUU'

    