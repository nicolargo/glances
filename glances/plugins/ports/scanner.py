#
# This file is part of Glances.
#
# SPDX-FileCopyrightText: 2026 Nicolas Hennion <nicolas@nicolargo.com>
#
# SPDX-License-Identifier: LGPL-3.0-only
#

"""The ports plugin's scanner thread: TCP / ICMP port checks and URL checks.

Moved out of the v4 plugin module at the v5 cutover; the v5 ports model
runs it.
"""

import os
import socket
import subprocess
import threading
import time

from glances.globals import BSD, MACOS, WINDOWS
from glances.logger import logger
from glances.timer import Counter

try:
    import requests

    requests_tag = True
except ImportError as e:
    requests_tag = False
    logger.warning(f"Missing Python Lib ({e}), Ports plugin is limited to port scanning")


class ThreadScanner(threading.Thread):
    """
    Specific thread for the port/web scanner.

    stats is a list of dict
    """

    def __init__(self, stats, web_secrets):
        """Init the class."""
        logger.debug(f"ports plugin - Create thread for scan list {stats}")
        super().__init__()
        # Event needed to stop properly the thread
        self._stopper = threading.Event()
        # The class return the stats as a list of dict
        self._stats = stats
        # Scan credentials (URL userinfo and proxies), indexed by indice.
        # They are deliberately not part of stats, which is published.
        self._web_secrets = web_secrets
        # Is part of Ports plugin
        self.plugin_name = "ports"

    def get_key(self):
        """Return the key of the list."""
        return 'indice'

    def run(self):
        """Grab the stats.

        Infinite loop, should be stopped by calling the stop() method.
        """
        for p in self._stats:
            # End of the thread has been asked
            if self.stopped():
                break
            # Scan a port (ICMP or TCP)
            if 'port' in p:
                self._port_scan(p)
                # Had to wait between two scans
                # If not, result are not ok
                time.sleep(1)
            # Scan an URL
            elif 'url' in p and requests_tag:
                self._web_scan(p)
            # Add the key for every element
            p['key'] = self.get_key()

    @property
    def stats(self):
        """Stats getter."""
        return self._stats

    @stats.setter
    def stats(self, value):
        """Stats setter."""
        self._stats = value

    def stop(self, timeout=None):
        """Stop the thread."""
        logger.debug(f"ports plugin - Close thread for scan list {self._stats}")
        self._stopper.set()

    def stopped(self):
        """Return True is the thread is stopped."""
        return self._stopper.is_set()

    def _web_scan(self, web):
        """Scan the  Web/URL (dict) and update the status key."""
        secrets = self._web_secrets[web['indice']]
        try:
            req = requests.head(
                secrets['url'],
                allow_redirects=True,
                verify=web['ssl_verify'],
                proxies=secrets['proxies'],
                timeout=web['timeout'],
            )
        except Exception as e:
            logger.debug(e)
            web['status'] = 'Error'
            web['elapsed'] = 0
        else:
            web['status'] = req.status_code
            web['elapsed'] = req.elapsed.total_seconds()
        return web

    def _port_scan(self, port):
        """Scan the port structure (dict) and update the status key."""
        if int(port['port']) == 0:
            return self._port_scan_icmp(port)
        return self._port_scan_tcp(port)

    def _resolv_name(self, hostname):
        """Convert hostname to IP address."""
        ip = hostname
        try:
            ip = socket.gethostbyname(hostname)
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Cannot convert {hostname} to IP address ({e})")
        return ip

    def _port_scan_icmp(self, port):
        """Scan the (ICMP) port structure (dict) and update the status key."""
        ret = None

        # Create the ping command
        # Use the system ping command because it already have the sticky bit set
        # Python can not create ICMP packet with non root right
        if WINDOWS:
            timeout_opt = '-w'
            count_opt = '-n'
            # Windows ping takes the reply timeout in milliseconds
            timeout_value = str(int(float(port['timeout']) * 1000))
        elif MACOS or BSD:
            timeout_opt = '-t'
            count_opt = '-c'
            timeout_value = str(port['timeout'])
        else:
            # Linux and co...
            timeout_opt = '-W'
            count_opt = '-c'
            timeout_value = str(port['timeout'])
        # Build the command line
        # Note: Only string are allowed
        cmd = [
            'ping',
            count_opt,
            '1',
            timeout_opt,
            timeout_value,
            self._resolv_name(port['host']),
        ]
        fnull = open(os.devnull, 'w')

        try:
            counter = Counter()
            ret = subprocess.check_call(cmd, stdout=fnull, stderr=fnull, close_fds=True)
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        except subprocess.CalledProcessError:
            # Correct issue #1084: No Offline status for timed-out ports
            port['status'] = False
        except Exception as e:
            logger.debug("{}: Error while pinging host {} ({})".format(self.plugin_name, port['host'], e))

        fnull.close()

        return ret

    def _port_scan_tcp(self, port):
        """Scan the (TCP) port structure (dict) and update the status key."""
        ret = None

        # Create and configure the scanning socket.
        #
        # The timeout belongs to this socket, not to the process:
        # socket.setdefaulttimeout() is global and was never restored, so once
        # a port had been scanned every socket built afterwards anywhere in
        # Glances silently inherited the last scanned port's timeout.
        #
        # Returning here also matters: if the socket cannot be created, the
        # code below used to run anyway and _socket was unbound, so the
        # connect_ex raised UnboundLocalError into the "Error while scanning
        # port" handler and the finally clause then raised it again, this time
        # with nothing to catch it.
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.settimeout(port['timeout'])
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Error while creating scanning socket ({e})")
            return ret

        # Scan port
        ip = self._resolv_name(port['host'])
        counter = Counter()
        try:
            ret = _socket.connect_ex((ip, int(port['port'])))
        except Exception as e:
            logger.debug(f"{self.plugin_name}: Error while scanning port {port} ({e})")
        else:
            if ret == 0:
                port['status'] = counter.get()
            else:
                port['status'] = False
        finally:
            _socket.close()

        return ret
