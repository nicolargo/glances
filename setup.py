#!/usr/bin/env python

import glob
import os
import re
import sys
from io import open

from setuptools import setup, Command


if sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 4):
    print('Glances requires at least Python 2.7 or 3.4 to run.')
    sys.exit(1)

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3


# Global functions
##################

with open(os.path.join('glances', '__init__.py'), encoding='utf-8') as f:
    version = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M).group(1)

if not version:
    raise RuntimeError('Cannot find Glances version information.')

with open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


def get_data_files():
    data_files = [
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS.rst', 'README.rst',
                               'CONTRIBUTING.md', 'conf/glances.conf']),
        ('share/man/man1', ['docs/man/glances.1'])
    ]

    return data_files


def get_install_requires():
    requires = ['psutil>=5.3.0', 'future']
    if sys.platform.startswith('win'):
        requires.append('bottle')
        requires.append('requests')

    return requires


def get_install_extras_require():
    extras_require = {
        'action': ['pystache'],
        # Zeroconf 0.19.1 is the latest one compatible with Python 2 (issue #1293)
        'browser': ['zeroconf==0.19.1' if PY2 else 'zeroconf>=0.19.1'],
        'cloud': ['requests'],
        'cpuinfo': ['py-cpuinfo<=4.0.0'],
        'docker': ['docker>=2.0.0'],
        'export': ['bernhard', 'cassandra-driver', 'couchdb', 'elasticsearch',
                   'influxdb>=1.0.0', 'kafka-python', 'pika', 'paho-mqtt', 'potsdb',
                   'prometheus_client', 'pyzmq', 'statsd'],
        'folders': ['scandir'],  # python_version<"3.5"
        'gpu': ['py3nvml'],
        'graph': ['pygal'],
        'ip': ['netifaces'],
        'raid': ['pymdstat'],
        'smart': ['pySMART.smartx'],
        'snmp': ['pysnmp'],
        'sparklines': ['sparklines'],
        'web': ['bottle', 'requests'],
        'wifi': ['wifi']
    }
    # Add automatically the 'all' target
    extras_require.update({'all': [i[0] for i in extras_require.values()]})

    return extras_require


class tests(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        import sys
        for t in glob.glob('unitest.py'):
            ret = subprocess.call([sys.executable, t]) != 0
            if ret != 0:
                raise SystemExit(ret)
        raise SystemExit(0)


# Setup !

setup(
    name='Glances',
    version=version,
    description="A cross-platform curses-based monitoring tool",
    long_description=long_description,
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    license='LGPLv3',
    keywords="cli curses monitoring system",
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
    install_requires=get_install_requires(),
    extras_require=get_install_extras_require(),
    packages=['glances'],
    include_package_data=True,
    data_files=get_data_files(),
    cmdclass={'test': tests},
    test_suite="unitest.py",
    entry_points={"console_scripts": ["glances=glances:main"]},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console :: Curses',
        'Environment :: Web Environment',
        'Framework :: Bottle',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: System :: Monitoring'
    ]
)
