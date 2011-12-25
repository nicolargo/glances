#!/usr/bin/python
#
# Glances is a simple CLI monitoring tool based on libstatgrab
#
# Pre-requisites: python-statgrab 0.5 or >
#
# Copyright (C) Nicolargo 2011 <nicolas@nicolargo.com>
# 
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# glances is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.";
#

import os
import getopt
import sys
import signal
import time
import datetime
import curses
import statgrab
import multiprocessing


# Globals variables
#==================

# The glances version id
__version__ = "1.3.4"		

# Class
#======

class Timer():
	"""
	The timer class
	"""
	
	def __init__(self, duration):
		self.target = time.time() + duration
	
	def finished(self):
		return time.time() > self.target


class glancesGrabFs():
	"""
	Get FS stats: idem as structure http://www.i-scream.org/libstatgrab/docs/sg_get_fs_stats.3.html
	"""

	def __init__(self):
		self.__update__()
	
	
	def __update__(self):
		"""
		Update the stats
		"""
		
		# Reset the list
		self.fs_list = []
		
		# Ignore the following fs
		ignore_fsname = ('none', 'gvfs-fuse-daemon', 'fusectl', 'cgroup')
		ignore_fstype = ('binfmt_misc', 'devpts', 'iso9660', 'none', 'proc', 'sysfs', 'usbfs')
		
		# Open the current mounted FS
		mtab = open("/etc/mtab", "r")
		for line in mtab.readlines():
			if line.split()[0] in ignore_fsname: continue
			if line.split()[2] in ignore_fstype: continue
			# Get FS stats
			fs_current = {}
			fs_name = self.__getmount__(line.split()[1])
			fs_stats = os.statvfs(fs_name)
			# Build the list
			fs_current['device_name'] = str(line.split()[0])
			fs_current['fs_type'] = str(line.split()[2])
			fs_current['mnt_point'] = str(fs_name)
			fs_current['size'] = float(fs_stats.f_blocks) * long(fs_stats.f_frsize)
			fs_current['used'] = float(fs_stats.f_blocks - fs_stats.f_bfree) * long(fs_stats.f_frsize)
			fs_current['avail'] = float(fs_stats.f_bfree) * long(fs_stats.f_frsize)
			self.fs_list.append(fs_current)
		mtab.close()
				
		
	def __getmount__(self, path):
		"""
		Return the real root path of a file
		Exemple: /home/nicolargo can return /home or /
		"""
		path = os.path.realpath(os.path.abspath(path))
		while path != os.path.sep:
			if os.path.ismount(path):
				return path
			path = os.path.abspath(os.path.join(path, os.pardir))
		return path		


	def get(self):
		self.__update__()
		return self.fs_list


class glancesStats():
	"""
	This class store, update and give the libstatgrab stats
	"""

	def __init__(self):
		"""
		Init the libstatgrab and process to the first update
		"""
		
		# Init libstatgrab
		if not statgrab.sg_init():
			print "Error: Can not init the libstatgrab library.\n"
		
		# Init the interfac fs stats
		self.glancesgrabfs = glancesGrabFs()
			
		# Do the first update
		self.__update__()

	def __update__(self):
		"""
		Update the stats
		"""

		# Get informations from libstatgrab and others...
		try:
			self.host = statgrab.sg_get_host_info()
		except:
			self.host = {}
		self.system = self.host
		try:
			self.cpu = statgrab.sg_get_cpu_percents()
		except:
			self.cpu = {}
		try:
			self.load = statgrab.sg_get_load_stats()
		except:
			self.load = {}
		try:
			self.mem = statgrab.sg_get_mem_stats()
		except:
			self.mem = {}
		try:
			self.memswap = statgrab.sg_get_swap_stats()
		except:
			self.memswap = {}
		try:
			self.networkinterface = statgrab.sg_get_network_iface_stats()
		except:
			self.networkinterface = {}
		try:
			self.network = statgrab.sg_get_network_io_stats_diff()
		except:
			self.network = {}
		try:
			self.diskio = statgrab.sg_get_disk_io_stats_diff()
		except:
			self.diskio = {}
		try:
			# Replace the bugged self.fs = statgrab.sg_get_fs_stats()
			self.fs = self.glancesgrabfs.get()
		except:
			self.fs = {}
		try:
			self.processcount = statgrab.sg_get_process_count()
		except:
			self.processcount = {}
		try:
			self.process = statgrab.sg_get_process_stats()
		except:
			self.process = {}

		# Get the current date/time
		self.now = datetime.datetime.now()
				
		# Get the number of core (CPU)
		# Used to display load alerts
		self.core_number = multiprocessing.cpu_count()

		
	def end(self):
		# Shutdown the libstatgrab
		statgrab.sg_shutdown()

		
	def update(self):
		# Update the stats
		self.__update__()

		
	def getHost(self):
		return self.host

		
	def getSystem(self):
		return self.system

		
	def getCpu(self):
		return self.cpu


	def getCore(self):
		return self.core_number
		
		
	def getLoad(self):
		return self.load

		
	def getMem(self):
		return self.mem

		
	def getMemSwap(self):
		return self.memswap


	def getNetworkInterface(self):
		return self.networkinterface
		
		
	def getNetwork(self):
		return self.network

		
	def getDiskIO(self):
		return self.diskio


	def getFs(self):
		return self.fs

		
	def getProcessCount(self):
		return self.processcount

		
	def getProcessList(self, sortedby = 'auto'):
		"""
		Return the sorted process list		
		"""
		
		if sortedby == 'auto':
			# If global Mem > 70% sort by process size
			# Else sort by cpu comsoption
			sortedby = 'cpu_percent'
			if ( self.mem['total'] != 0):
				if ( ( (self.mem['used'] - self.mem['cache']) * 100 / self.mem['total']) > 70):
					sortedby = 'proc_size'
		return sorted(self.process, key=lambda process: process[sortedby], reverse=True)

		
	def getNow(self):
		return self.now	

		
class glancesScreen():
	"""
	This class manage the screen (display and key pressed)
	"""

	# By default the process list is automaticaly sorted
	# If global CPU > 75% 		=> Sorted by process Cpu consomption
	# If global used MEM > 75% 	=> Sorted by process size 
	__process_sortedby = 'auto'
	
	def __init__(self, refresh_time = 1):
		# Global information to display
		self.__version = __version__

		# Init windows positions
		self.term_h = 		24 ; 		self.term_w = 		80
		self.host_x = 		0 ; 		self.host_y = 		0
		self.system_x = 	0 ; 		self.system_y = 	1
		self.cpu_x = 		0 ; 		self.cpu_y = 		3
		self.load_x = 		20; 		self.load_y = 		3
		self.mem_x = 		41; 		self.mem_y = 		3
		self.network_x = 	0 ; 		self.network_y = 	9
		self.diskio_x = 	0 ; 		self.diskio_y = 	-1
		self.fs_x = 		0 ; 		self.fs_y = 		-1
		self.process_x = 	30;			self.process_y = 	9
		self.now_x = 		79;			self.now_y = 		3
		self.caption_x = 	0 ;			self.caption_y = 	3

		# Init the curses screen
		self.screen = curses.initscr() 
		if not self.screen:
			print "Error: Can not init the curses library.\n"
		curses.start_color()
		curses.use_default_colors()
		curses.noecho() ; curses.cbreak() ; curses.curs_set(0)
		
		# Init colors
		self.hascolors = False
		if curses.has_colors():
			self.hascolors = True
			#Init				FG color				BG color
			curses.init_pair(1, curses.COLOR_WHITE, 	curses.COLOR_BLACK)
			curses.init_pair(2, curses.COLOR_WHITE, 	curses.COLOR_RED)
			curses.init_pair(3, curses.COLOR_WHITE, 	curses.COLOR_GREEN)
			curses.init_pair(4, curses.COLOR_WHITE, 	curses.COLOR_BLUE)
			curses.init_pair(5, curses.COLOR_WHITE, 	curses.COLOR_MAGENTA)
			curses.init_pair(6, curses.COLOR_WHITE, 	curses.COLOR_CYAN)
			curses.init_pair(7, curses.COLOR_BLACK, 	curses.COLOR_YELLOW)

			# Text colors/styles
			self.title_color = curses.A_BOLD|curses.A_UNDERLINE
			self.no_color = curses.color_pair(1)
			self.default_color = curses.color_pair(3)|curses.A_BOLD
			self.if50pc_color = curses.color_pair(4)|curses.A_BOLD
			self.if70pc_color = curses.color_pair(5)|curses.A_BOLD
			self.if90pc_color = curses.color_pair(2)|curses.A_BOLD

		# By default all the stats are displayed
		self.network_tag = True
		self.diskio_tag = True
		self.fs_tag = True

		# Init window		
		self.term_window = self.screen.subwin(0, 0)

		# Init refresh time
		self.__refresh_time = refresh_time

		# Catch key pressed with non blocking mode
		self.term_window.keypad(1) ; self.term_window.nodelay(1) ; self.pressedkey = -1

		
	def setProcessSortedBy(self, sorted):
		self.__process_sortedautoflag = False
		self.__process_sortedby = sorted

		
	def getProcessSortedBy(self):
		return self.__process_sortedby


	def __autoUnit(self, val):
		"""
		Convert val to string and concatenate the good unit
		Exemples:
			960 -> 960
			142948 -> 143K
			560745673 -> 561M
			...
		"""
		if val >= 1073741824L:
			return "%.1fG" % (val / 1073741824L)
		elif val >= 1048576L:
			return "%.1fM" % (val / 1048576L)
		elif val >= 1024:
			return "%.1fK" % (val / 1024)
		else:
			return str(int(val))
		
	def __getColor(self, current = 0, max = 100):
		# If current > 50% of max then color = self.if50pc_color / A_DIM
		# If current > 70% of max then color = self.if70pc_color / A_BOLD
		# If current > 90% of max then color = self.if90pc_color / A_REVERSE
		# By default: color = self.default_color / 0
		try:
			(current * 100) / max
		except ZeroDivisionError:
			return 0

		variable = (current * 100) / max

		if variable > 90:
			if self.hascolors:
				return self.if90pc_color
			else:
				return curses.A_REVERSE
		elif variable > 70:
			if self.hascolors:
				return self.if70pc_color
			else:
				return curses.A_BOLD
		elif variable > 50:
			if self.hascolors:
				return self.if50pc_color
			else:
				return curses.A_DIM
		else:
			if self.hascolors:
				return self.default_color
			else:
				return 0


	def __getLoadColor(self, current = 0, core = 1):
		# core is the number of CPU core
		# If current > 0.7*core then color = self.if50pc_color / A_DIM
		# If current > 1.0*core then color = self.if70pc_color / A_BOLD
		# If current > 5.0*core then color = self.if90pc_color / A_REVERSE
		# By default: color = self.default_color / 0

		if current > (5.0 * core):
			if self.hascolors:
				return self.if90pc_color
			else:
				return curses.A_REVERSE
		elif current > (1.0 * core):
			if self.hascolors:
				return self.if70pc_color
			else:
				return curses.A_BOLD
		elif current > (0.7 * core):
			if self.hascolors:
				return self.if50pc_color
			else:
				return curses.A_DIM
		else:
			if self.hascolors:
				return self.default_color
			else:
				return 0

				
	def __catchKey(self):
		# Get key
		self.pressedkey = self.term_window.getch();

		# Actions...
		if (self.pressedkey == 27) or (self.pressedkey == 113):
			# 'ESC'|'q' > Exit
			end()
		#elif (self.pressedkey == curses.KEY_RESIZE):
			# Resize event
		elif (self.pressedkey == 97):
			# 'a' > Sort process list automaticaly
			self.setProcessSortedBy('auto')
		elif (self.pressedkey == 99):
			# 'c' > Sort process list by Cpu usage
			self.setProcessSortedBy('cpu_percent')
		elif (self.pressedkey == 100):
			# 'n' > Enable/Disable diskio stats
			self.diskio_tag = not self.diskio_tag
		elif (self.pressedkey == 102):
			# 'n' > Enable/Disable fs stats
			self.fs_tag = not self.fs_tag
		elif (self.pressedkey == 109):
			# 'm' > Sort process list by Mem usage
			self.setProcessSortedBy('proc_size')
		elif (self.pressedkey == 110):
			# 'n' > Enable/Disable network stats
			self.network_tag = not self.network_tag
		
		# Return the key code
		return self.pressedkey

			
	def end(self):
		# Shutdown the curses window
		curses.echo() ; curses.nocbreak() ; curses.curs_set(1)
		curses.endwin()
		

	def display(self, stats):
		# Display all
		screen.displayHost(stats.getHost())
		screen.displaySystem(stats.getSystem())	
		screen.displayCpu(stats.getCpu())
		screen.displayLoad(stats.getLoad(), stats.getCore())
		screen.displayMem(stats.getMem(), stats.getMemSwap())
		network_count = screen.displayNetwork(stats.getNetwork(), stats.getNetworkInterface())
		diskio_count = screen.displayDiskIO(stats.getDiskIO(), self.network_y + network_count)
		screen.displayFs(stats.getFs(), self.network_y + network_count + diskio_count)		
		screen.displayProcess(stats.getProcessCount(), stats.getProcessList(screen.getProcessSortedBy()))
		screen.displayCaption()
		screen.displayNow(stats.getNow())
		
		
	def erase(self):
		# Erase the content of the screen
		self.term_window.erase()


	def update(self, stats):		
		# Erase and display
		self.erase()
		self.display(stats) 
		
		# Wait
		countdown = Timer(self.__refresh_time)
		while (not countdown.finished()):
			# Refresh the screen
			self.term_window.refresh()
			# Getkey
			if (self.__catchKey() > -1):
				# Erase and display
				self.erase()
				self.display(stats) 				
			# Wait 100ms...
			curses.napms(100)
		
		
	def displayHost(self, host):
		# Host information
		if (not host):
			return 0
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.host_y) 
			and (screen_x > self.host_x+79)):
			host_msg = "Glances v"+self.__version+" running on "+host['hostname']+" "+str(self.pressedkey) 
			self.term_window.addnstr(self.host_y, self.host_x+int(screen_x/2)-len(host_msg)/2, host_msg, 80, self.title_color if self.hascolors else 0)

		
	def displaySystem(self, system):
		# System information
		if (not system):
			return 0		
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.system_y) 
			and (screen_x > self.system_x+79)):
			system_msg = system['os_name']+" "+system['platform']+" "+system['os_version']
			self.term_window.addnstr(self.system_y, self.system_x+int(screen_x/2)-len(system_msg)/2, system_msg, 80)

		
	def displayCpu(self, cpu):		
		# CPU %
		if (not cpu):
			return 0
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.cpu_y+6) 
			and (screen_x > self.cpu_x+18)):
			self.term_window.addnstr(self.cpu_y, self.cpu_x, 	"Cpu", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.cpu_y, self.cpu_x+10,"%", 8)
			self.term_window.addnstr(self.cpu_y+1, self.cpu_x, "User:", 8)
			self.term_window.addnstr(self.cpu_y+2, self.cpu_x, "Kernel:", 8)
			self.term_window.addnstr(self.cpu_y+3, self.cpu_x, "Nice:", 8)
			self.term_window.addnstr(self.cpu_y+4, self.cpu_x, "Idle:", 8)
			self.term_window.addnstr(self.cpu_y+1, self.cpu_x+10, "%.1f" % cpu['user'], 8, self.__getColor(cpu['user']))
			self.term_window.addnstr(self.cpu_y+2, self.cpu_x+10, "%.1f" % cpu['kernel'], 8, self.__getColor(cpu['kernel']))
			self.term_window.addnstr(self.cpu_y+3, self.cpu_x+10, "%.1f" % cpu['nice'], 8, self.__getColor(cpu['nice']))
			self.term_window.addnstr(self.cpu_y+4, self.cpu_x+10, "%.1f" % cpu['idle'], 8)

		
	def displayLoad(self, load, core):
		# Load %
		if (not load):
			return 0		
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.load_y+5) 
			and (screen_x > self.load_x+18)):
			self.term_window.addnstr(self.load_y, self.load_x, "Load", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.load_y, self.load_x+10, str(core)+"-Core", 8)
			self.term_window.addnstr(self.load_y+1, self.load_x, "1 min:", 8)
			self.term_window.addnstr(self.load_y+2, self.load_x, "5 mins:", 8)
			self.term_window.addnstr(self.load_y+3, self.load_x, "15 mins:", 8)
			self.term_window.addnstr(self.load_y+1, self.load_x+10, str(load['min1']), 8)
			self.term_window.addnstr(self.load_y+2, self.load_x+10, str(load['min5']), 8, self.__getLoadColor(load['min5'], core))
			self.term_window.addnstr(self.load_y+3, self.load_x+10, str(load['min15']), 8, self.__getLoadColor(load['min15'], core))

		
	def displayMem(self, mem, memswap):
		# MEM
		if (not mem or not memswap):
			return 0		
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.mem_y+5) 
			and (screen_x > self.mem_x+38)):
			self.term_window.addnstr(self.mem_y, self.mem_x, 	"Mem MB", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.mem_y, self.mem_x+10,"Mem", 8)
			self.term_window.addnstr(self.mem_y, self.mem_x+20,"Swap", 8)
			self.term_window.addnstr(self.mem_y, self.mem_x+30,"Real", 8)
			self.term_window.addnstr(self.mem_y+1, self.mem_x, "Total:", 8)
			self.term_window.addnstr(self.mem_y+2, self.mem_x, "Used:", 8)
			self.term_window.addnstr(self.mem_y+3, self.mem_x, "Free:", 8)
			self.term_window.addnstr(self.mem_y+1, self.mem_x+10, str(mem['total']/1048576), 8)
			self.term_window.addnstr(self.mem_y+2, self.mem_x+10, str(mem['used']/1048576), 8)
			self.term_window.addnstr(self.mem_y+3, self.mem_x+10, str(mem['free']/1048576), 8)
			self.term_window.addnstr(self.mem_y+1, self.mem_x+20, str(memswap['total']/1048576), 8)
			self.term_window.addnstr(self.mem_y+2, self.mem_x+20, str(memswap['used']/1048576), 8, self.__getColor(memswap['used'], memswap['total']))
			self.term_window.addnstr(self.mem_y+3, self.mem_x+20, str(memswap['free']/1048576), 8)
			self.term_window.addnstr(self.mem_y+1, self.mem_x+30, "-", 8)
			self.term_window.addnstr(self.mem_y+2, self.mem_x+30, str((mem['used']-mem['cache'])/1048576), 8, self.__getColor(mem['used']-mem['cache'], mem['total']))
			self.term_window.addnstr(self.mem_y+3, self.mem_x+30, str((mem['free']+mem['cache'])/1048576), 8)

		
	def displayNetwork(self, network, networkinterface):
		"""
		Display the network interface bitrate
		Return the number of interfaces
		"""
		# Network interfaces bitrate
		if (not network or not networkinterface or not self.network_tag):
			return 0				
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.network_y+3) 
			and (screen_x > self.network_x+28)):
			# Get the speed of the network interface
			# TODO: optimize...
			speed = {}
			for i in range(0, len(networkinterface)):
				# Strange think, on Ubuntu, libstatgrab return 65525 for my ethernet card...
				if networkinterface[i]['speed'] == 65535:
					speed[networkinterface[i]['interface_name']] = 0
				else:
					speed[networkinterface[i]['interface_name']] = networkinterface[i]['speed']*1000000
			# Network interfaces bitrate
			self.term_window.addnstr(self.network_y, self.network_x,    "Net rate", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.network_y, self.network_x+10, "Rx/ps", 8)
			self.term_window.addnstr(self.network_y, self.network_x+20, "Tx/ps", 8)
			# Adapt the maximum interface to the screen
			for i in range(0, min(screen_y-self.network_y-3, len(network))):
				elapsed_time = max (1, network[i]['systime'])
				self.term_window.addnstr(self.network_y+1+i, self.network_x, network[i]['interface_name']+':', 8)
				self.term_window.addnstr(self.network_y+1+i, self.network_x+10, self.__autoUnit(network[i]['rx']/elapsed_time*8) + "b", 8, self.__getColor(network[i]['rx']/elapsed_time*8, speed[network[i]['interface_name']]))
				self.term_window.addnstr(self.network_y+1+i, self.network_x+20, self.__autoUnit(network[i]['tx']/elapsed_time*8) + "b", 8, self.__getColor(network[i]['tx']/elapsed_time*8, speed[network[i]['interface_name']]))
			return i+3
		return 0

			
	def displayDiskIO(self, diskio, offset_y = 0):
		# Disk input/output rate
		if (not diskio or not self.diskio_tag):
			return 0						
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		self.diskio_y = offset_y
		if ((screen_y > self.diskio_y+3) 
			and (screen_x > self.diskio_x+28)):
			self.term_window.addnstr(self.diskio_y, self.diskio_x,    "Disk I/O", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.diskio_y, self.diskio_x+10, "In/ps", 8)
			self.term_window.addnstr(self.diskio_y, self.diskio_x+20, "Out/ps", 8)
			# Adapt the maximum disk to the screen
			disk = 0
			for disk in range(0, min(screen_y-self.diskio_y-3, len(diskio))):
				elapsed_time = max(1, diskio[disk]['systime'])			
				self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x, diskio[disk]['disk_name']+':', 8)
				self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x+10, self.__autoUnit(diskio[disk]['write_bytes']/elapsed_time) + "B", 8)
				self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x+20, self.__autoUnit(diskio[disk]['read_bytes']/elapsed_time) + "B", 8)
			return disk+3
		return 0


	def displayFs(self, fs, offset_y = 0):
		# Filesystem stats
		if (not fs or not self.fs_tag):
			return 0						
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		self.fs_y = offset_y
		if ((screen_y > self.fs_y+3) 
			and (screen_x > self.fs_x+28)):
			self.term_window.addnstr(self.fs_y, self.fs_x,    "Mount", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.fs_y, self.fs_x+10, "Total", 8)
			self.term_window.addnstr(self.fs_y, self.fs_x+20, "Used", 8)
			# Adapt the maximum disk to the screen
			mounted = 0
			for mounted in range(0, min(screen_y-self.fs_y-3, len(fs))):
				self.term_window.addnstr(self.fs_y+1+mounted, self.fs_x, fs[mounted]['mnt_point'], 8)
				self.term_window.addnstr(self.fs_y+1+mounted, self.fs_x+10, self.__autoUnit(fs[mounted]['size']), 8)
				self.term_window.addnstr(self.fs_y+1+mounted, self.fs_x+20, self.__autoUnit(fs[mounted]['used']), 8, self.__getColor(fs[mounted]['used'], fs[mounted]['size']))
			return mounted+3
		return 0			


	def displayProcess(self, processcount, processlist):
		# Process
		if (not processcount or not processlist):
			return 0						
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		# If there is no (network&diskio&fs) stats
		# then increase process window
		if (not self.network_tag and not self.diskio_tag and not self.fs_tag):
			process_x = 0
		else:
			process_x = self.process_x
		# Display the process summary
		if ((screen_y > self.process_y+3) 
			and (screen_x > process_x+48)):
			# Processes sumary
			self.term_window.addnstr(self.process_y, process_x, "Process", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
			self.term_window.addnstr(self.process_y, process_x+10,"Total", 8)
			self.term_window.addnstr(self.process_y, process_x+20,"Running", 8)
			self.term_window.addnstr(self.process_y, process_x+30,"Sleeping", 8)
			self.term_window.addnstr(self.process_y, process_x+40,"Other", 8)
			self.term_window.addnstr(self.process_y+1, process_x, "Number:", 8)
			self.term_window.addnstr(self.process_y+1, process_x+10,str(processcount['total']), 8)
			self.term_window.addnstr(self.process_y+1, process_x+20,str(processcount['running']), 8)
			self.term_window.addnstr(self.process_y+1, process_x+30,str(processcount['sleeping']), 8)
			self.term_window.addnstr(self.process_y+1, process_x+40,str(processcount['stopped']+stats.getProcessCount()['zombie']), 8)
		# Display the process detail
		if ((screen_y > self.process_y+6) 
			and (screen_x > process_x+49)):
			# Processes detail
			if (self.getProcessSortedBy() == 'cpu_percent'):
				sortchar = '^'
			else:
				sortchar = ' '
			self.term_window.addnstr(self.process_y+3, process_x,"Cpu %"+sortchar, 8)
			if (self.getProcessSortedBy() == 'proc_size'):
				sortchar = '^'
			else:
				sortchar = ' '
			self.term_window.addnstr(self.process_y+3, process_x+10,"Size MB"+sortchar, 8)
			self.term_window.addnstr(self.process_y+3, process_x+20,"Res MB", 8)
			self.term_window.addnstr(self.process_y+3, process_x+30,"Name", 8)
			for processes in range(0, min(screen_y-self.term_h+self.process_y, len(processlist))):
				self.term_window.addnstr(self.process_y+4+processes, process_x, "%.1f" % processlist[processes]['cpu_percent'], 8, self.__getColor(processlist[processes]['cpu_percent']))
				self.term_window.addnstr(self.process_y+4+processes, process_x+10, str((processlist[processes]['proc_size'])/1048576), 8)
				self.term_window.addnstr(self.process_y+4+processes, process_x+20, str((processlist[processes]['proc_resident'])/1048576), 8)
				maxprocessname = screen_x-process_x-30
				# If screen space is available then display long name
				if ((len(processlist[processes]['proctitle']) > maxprocessname) 
				   or (len(processlist[processes]['proctitle']) == 0)):
					processname = processlist[processes]['process_name']
				else:	
					processname = processlist[processes]['proctitle']		
				self.term_window.addnstr(self.process_y+4+processes, process_x+30, processname, maxprocessname)


	def displayCaption(self):
		# Caption
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.caption_y) 
			and (screen_x > self.caption_x+32)):
			self.term_window.addnstr(max(self.caption_y, screen_y-1), self.caption_x,    "   OK   ", 8, self.default_color)
			self.term_window.addnstr(max(self.caption_y, screen_y-1), self.caption_x+8,  "CAREFUL ", 8, self.if50pc_color)
			self.term_window.addnstr(max(self.caption_y, screen_y-1), self.caption_x+16,  "WARNING ", 8, self.if70pc_color)
			self.term_window.addnstr(max(self.caption_y, screen_y-1), self.caption_x+24, "CRITICAL", 8, self.if90pc_color)
	
			
	def displayNow(self, now):
		# Display the current date and time (now...) - Center
		if (not now):
			return 0						
		screen_x = self.screen.getmaxyx()[1]
		screen_y = self.screen.getmaxyx()[0]
		if ((screen_y > self.now_y)
			and (screen_x > self.now_x)):
			now_msg = now.strftime("%Y-%m-%d %H:%M:%S")
			self.term_window.addnstr(max(self.now_y, screen_y-1), max(self.now_x, screen_x-1)-len(now_msg), now_msg, len(now_msg))

		
# Global def
#===========

def printVersion():
	print "Glances version "+__version__

	
def printSyntax():
	printVersion()
	print "Usage: glances.py [-t|--time sec] [-h|--help] [-v|--version]"
	print ""
	print "\t-h:\tDisplay the syntax and exit"
	print "\t-t sec:\tSet the refresh time in second default is 1"
	print "\t-v:\tDisplay the version and exit"

	
def init():
	global stats, screen
	global refresh_time

	refresh_time = 1

	# Manage args
	try:
		opts, args = getopt.getopt(sys.argv[1:], "ht:v", ["help", "time", "version"])
	except getopt.GetoptError, err:
		# Print help information and exit:
		print str(err)
		printSyntax()
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("-v", "--version"):
			printVersion()
			sys.exit(0)
		elif opt in ("-t", "--time"):
			if int(arg) >= 1:
				refresh_time = int(arg)
			else:
				print "Error: Refresh time should be a positive non-null integer"
				sys.exit(2)				
		else:
			printSyntax()
			sys.exit(0)
	
	# Catch CTRL-C
	signal.signal(signal.SIGINT, signal_handler)	

	# Init stats
	stats = glancesStats()
	
	# Init screen
	screen = glancesScreen(refresh_time)


def main():
	# Init stuff
	init()

	# Main loop
	while True:
		# Get informations from libstatgrab and others...
		stats.update()
	
		# Update the screen
		screen.update(stats)

		
def end():
	stats.end()
	screen.end()
	sys.exit(0)

	
def signal_handler(signal, frame):
	end()

# Main
#=====

if __name__ == "__main__":
	main()
	
# The end...
