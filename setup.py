#!/usr/bin/env python

import glob
import os
import re
import sys
from io import open

from setuptools import setup, Command


if sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 3):
    print('Glances requires at least Python 2.7 or 3.3 to run.')
    sys.exit(1)


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
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS', 'README.rst',
                               'CONTRIBUTING.md', 'conf/glances.conf']),
        ('share/man/man1', ['docs/man/glances.1'])
    ]

    return data_files


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
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=['psutil>=2.0.0'],
    extras_require={
        'ACTION': ['pystache'],
        'BATINFO': ['batinfo'],
        'BROWSER': ['zeroconf>=0.17'],
        'CPUINFO': ['py-cpuinfo'],
        'CHART': ['matplotlib'],
        'DOCKER': ['docker-py'],
        'EXPORT': ['bernhard', 'cassandra-driver', 'couchdb', 'elasticsearch', 'influxdb>=1.0.0', 'pika', 'potsdb', 'pyzmq', 'statsd'],
        'FOLDERS': ['scandir'],
        'GPU': ['nvidia-ml-py'],
        'IP': ['netifaces'],
        'RAID': ['pymdstat'],
        'SENSORS': ['py3sensors'],
        'SNMP': ['pysnmp'],
        'WEB': ['bottle', 'requests'],
        'WIFI': ['wifi']
    },
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
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: System :: Monitoring'
    ]
)
