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


# Globals variables
#==================

# The glances version id
__version__ = "1.1"		

# Class
#======

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
		# Do the first update
		self.__update__()

	def __update__(self):
		"""
		Update the stats
		"""

		# Get informations from libstatgrab and others...
		self.host = statgrab.sg_get_host_info()
		self.system = statgrab.sg_get_host_info()
		self.cpu = statgrab.sg_get_cpu_percents()
		self.load = statgrab.sg_get_load_stats()
		self.mem = statgrab.sg_get_mem_stats()
		self.memswap = statgrab.sg_get_swap_stats()
		self.network = statgrab.sg_get_network_io_stats_diff()
		self.diskio = statgrab.sg_get_disk_io_stats_diff()
		# BUG: https://bugs.launchpad.net/ubuntu/+source/libstatgrab/+bug/886783
		# TODO: self.fs = statgrab.sg_get_fs_stats()
		self.processcount = statgrab.sg_get_process_count()
		self.process = statgrab.sg_get_process_stats()
		self.now = datetime.datetime.now()		

		
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

		
	def getLoad(self):
		return self.load

		
	def getMem(self):
		return self.mem

		
	def getMemSwap(self):
		return self.memswap

		
	def getNetwork(self):
		return self.network

		
	def getDiskIO(self):
		return self.diskio

		
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
		self.diskio_x = 	0 ; 		self.diskio_y = 	16
		self.process_x = 	30;			self.process_y = 	9
		self.now_x = 		79;			self.now_y = 		23	 # Align right
		self.caption_x = 	0 ;			self.caption_y = 	23

		# Init the curses screen
		self.screen = curses.initscr() 
		if not self.screen:
			print "Error: Can not init the curses library.\n"
		curses.resizeterm( self.term_h, self.term_w )
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

		# Init window		
		self.term_window = curses.newwin(self.term_h, self.term_w, 0, 0)

		# Init refresh time
		self.__refresh_time = refresh_time

		# Catch key pressed with non blocking mode
		self.term_window.keypad(1) ; self.term_window.nodelay(1) ; self.pressedkey = -1

		
	def setProcessSortedBy(self, sorted):
		self.__process_sortedautoflag = False
		self.__process_sortedby = sorted

		
	def getProcessSortedBy(self):
		return self.__process_sortedby

		
	def __getColor(self, current = 0, max = 100):
		# If current > 50% of max then color = self.if50pc_color / A_DIM
		# If current > 70% of max then color = self.if70pc_color / A_BOLD
		# If current > 90% of max then color = self.if90pc_color / A_REVERSE
		# By default: color = self.default_color / 0
		try:
			(current * 100) / max
		except ZeroDivisionError:
			return self.no_color

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

				
	def __catchKey(self):
		# Get key
		self.pressedkey = self.term_window.getch();

		# Actions...
		if (self.pressedkey == 27) or (self.pressedkey == 113):
			# 'ESC'|'q' > Exit
			end()
		elif (self.pressedkey == 97):
			# 'a' > Sort process list automaticaly
			self.setProcessSortedBy('auto')
		elif (self.pressedkey == 99):
			# 'c' > Sort process list by Cpu usage
			self.setProcessSortedBy('cpu_percent')
		elif (self.pressedkey == 109):
			# 'm' > Sort process list by Mem usage
			self.setProcessSortedBy('proc_size')

			
	def end(self):
		# Shutdown the curses window
		curses.echo() ; curses.nocbreak() ; curses.curs_set(1)
		curses.endwin()

		
	def update(self):
		# Refresh the screen
		self.term_window.refresh()

		# Sleep
		#curses.napms(self.__refresh_time*1000)
		time.sleep(self.__refresh_time)

		# Getkey
		self.__catchKey()

		
	def erase(self):
		# Erase the content of the screen
		self.term_window.erase()

		
	def displayHost(self, host):
		# Host information
		host_msg = "Glances v"+self.__version+" running on "+host['hostname'] #+" "+str(pressed_key)
		self.term_window.addnstr(self.host_y, self.host_x+40-len(host_msg)/2, host_msg, 80, self.title_color if self.hascolors else 0)

		
	def displaySystem(self, system):
		# System information
		system_msg = system['os_name']+" "+system['platform']+" "+system['os_version']
		self.term_window.addnstr(self.system_y, self.system_x+40-len(system_msg)/2, system_msg, 80)

		
	def displayCpu(self, cpu):
		# CPU %
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

		
	def displayLoad(self, load):
		# Load %
		self.term_window.addnstr(self.load_y, self.load_x, 	"Load", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
		self.term_window.addnstr(self.load_y, self.load_x+10,"%", 8)
		self.term_window.addnstr(self.load_y+1, self.load_x, "1 min:", 8)
		self.term_window.addnstr(self.load_y+2, self.load_x, "5 mins:", 8)
		self.term_window.addnstr(self.load_y+3, self.load_x, "15 mins:", 8)
		self.term_window.addnstr(self.load_y+1, self.load_x+10, str(load['min1']), 8, self.__getColor(load['min1']))
		self.term_window.addnstr(self.load_y+2, self.load_x+10, str(load['min5']), 8, self.__getColor(load['min5']))
		self.term_window.addnstr(self.load_y+3, self.load_x+10, str(load['min15']), 8, self.__getColor(load['min15']))

		
	def displayMem(self, mem, memswap):
		# MEM
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

		
	def displayNetwork(self, network):
		# Network interfaces bitrate
		self.term_window.addnstr(self.network_y, self.network_x,    "Net rate", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
		self.term_window.addnstr(self.network_y, self.network_x+10, "Rx Kbps", 8)
		self.term_window.addnstr(self.network_y, self.network_x+20, "Tx Kbps", 8)
		# A maximum of 5 interfaces could be monitored
		for interface in range(0, min(4, len(network))):
			elapsed_time = max (1, network[interface]['systime'])
			self.term_window.addnstr(self.network_y+1+interface, self.network_x, network[interface]['interface_name']+':', 8)
			self.term_window.addnstr(self.network_y+1+interface, self.network_x+10, str(network[interface]['rx']/elapsed_time/1000), 8)
			self.term_window.addnstr(self.network_y+1+interface, self.network_x+20, str(network[interface]['tx']/elapsed_time/1000), 8)

			
	def displayDiskIO(self, diskio):
		# Disk input/output rate
		self.term_window.addnstr(self.diskio_y, self.diskio_x,    "Disk I/O", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
		self.term_window.addnstr(self.diskio_y, self.diskio_x+10, "In KBps", 8)
		self.term_window.addnstr(self.diskio_y, self.diskio_x+20, "Out KBps", 8)
		# A maximum of 5 disks could be monitored
		for disk in range(0, min(4, len(diskio))):
			elapsed_time = max(1, diskio[disk]['systime'])			
			self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x, diskio[disk]['disk_name']+':', 8)
			self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x+10, str(diskio[disk]['read_bytes']/elapsed_time/1000), 8)
			self.term_window.addnstr(self.diskio_y+1+disk, self.diskio_x+20, str(diskio[disk]['write_bytes']/elapsed_time/1000), 8)
			

	def displayProcess(self, processcount, processlist):
		# Process
		self.term_window.addnstr(self.process_y, self.process_x, "Process", 8, self.title_color if self.hascolors else curses.A_UNDERLINE)
		self.term_window.addnstr(self.process_y, self.process_x+10,"Total", 8)
		self.term_window.addnstr(self.process_y, self.process_x+20,"Running", 8)
		self.term_window.addnstr(self.process_y, self.process_x+30,"Sleeping", 8)
		self.term_window.addnstr(self.process_y, self.process_x+40,"Other", 8)
		self.term_window.addnstr(self.process_y+1, self.process_x, "Number:", 8)
		self.term_window.addnstr(self.process_y+1, self.process_x+10,str(processcount['total']), 8)
		self.term_window.addnstr(self.process_y+1, self.process_x+20,str(processcount['running']), 8)
		self.term_window.addnstr(self.process_y+1, self.process_x+30,str(processcount['sleeping']), 8)
		self.term_window.addnstr(self.process_y+1, self.process_x+40,str(processcount['stopped']+stats.getProcessCount()['zombie']), 8)
		#term_window.addnstr(process_y+2, process_x,"List:", 8)
		if (self.getProcessSortedBy() == 'cpu_percent'):
			sortchar = '^'
		else:
			sortchar = ' '
		self.term_window.addnstr(self.process_y+3, self.process_x,"Cpu %"+sortchar, 8)
		if (self.getProcessSortedBy() == 'proc_size'):
			sortchar = '^'
		else:
			sortchar = ' '
		self.term_window.addnstr(self.process_y+3, self.process_x+10,"Size MB"+sortchar, 8)
		self.term_window.addnstr(self.process_y+3, self.process_x+20,"Res MB", 8)
		self.term_window.addnstr(self.process_y+3, self.process_x+30,"Name", 8)
		for processes in range(0, min(9, len(processlist))):
			self.term_window.addnstr(self.process_y+4+processes, self.process_x, "%.1f" % processlist[processes]['cpu_percent'], 8, self.__getColor(processlist[processes]['cpu_percent']))
			self.term_window.addnstr(self.process_y+4+processes, self.process_x+10, str((processlist[processes]['proc_size'])/1048576), 8)
			self.term_window.addnstr(self.process_y+4+processes, self.process_x+20, str((processlist[processes]['proc_resident'])/1048576), 8)
			self.term_window.addnstr(self.process_y+4+processes, self.process_x+30, processlist[processes]['process_name'], 20)


	def displayCaption(self):
		# Caption
		self.term_window.addnstr(self.caption_y, self.caption_x, "<50%", 4, self.default_color)
		self.term_window.addnstr(self.caption_y, self.caption_x+4, ">50%", 4, self.if50pc_color)
		self.term_window.addnstr(self.caption_y, self.caption_x+8, ">70%", 4, self.if70pc_color)
		self.term_window.addnstr(self.caption_y, self.caption_x+12, ">90%", 4, self.if90pc_color)

			
	def displayNow(self, now):
		# Display the current date and time (now...) - Center
		now_msg = now.strftime("%Y-%m-%d %H:%M:%S")
		self.term_window.addnstr(self.now_y, self.now_x-len(now_msg), now_msg, len(now_msg))

		
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

		# Clean the screen
		screen.erase()
	
		# Display stats
		screen.displayHost(stats.getHost())
		screen.displaySystem(stats.getSystem())	
		screen.displayCpu(stats.getCpu())
		screen.displayLoad(stats.getLoad())
		screen.displayMem(stats.getMem(), stats.getMemSwap())
		screen.displayNetwork(stats.getNetwork())
		screen.displayDiskIO(stats.getDiskIO())		
		screen.displayProcess(stats.getProcessCount(), stats.getProcessList(screen.getProcessSortedBy()))
		screen.displayCaption()
		screen.displayNow(stats.getNow())
	
		# Update and sleep... bzzz... bzzz...
		screen.update()

		
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
