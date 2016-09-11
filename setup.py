#!/usr/bin/env python

import glob
import sys
import re

from setuptools import setup, Command


# Global functions
##################

def get_version():
    """Get version inside the __init__.py file"""
    init_file = open("glances/__init__.py").read()
    reg_version = r"^__version__ = ['\"]([^'\"]*)['\"]"
    find_version = re.search(reg_version, init_file, re.M)
    if find_version:
        return find_version.group(1)
    else:
        print("Can not retreive Glances version in the glances/__init__.py file.")
        sys.exit(1)


def get_data_files():
    data_files = [
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS', 'README.rst',
                               'conf/glances.conf']),
        ('share/man/man1', ['docs/man/glances.1'])
    ]

    return data_files


def get_requires():
    requires = ['psutil>=2.0.0']

    return requires


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

# Global vars
#############

glances_version = get_version()

if sys.version_info < (2, 7) or (3, 0) <= sys.version_info < (3, 3):
    print('Glances {0} require at least Python 2.7 or 3.3 to run.'.format(glances_version))
    print('Please install Glances 2.6.2 on your system.')
    sys.exit(1)

# Setup !

setup(
    name='Glances',
    version=glances_version,
    description="A cross-platform curses-based monitoring tool",
    long_description=open('README.rst').read(),
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=get_requires(),
    extras_require={
        'WEB': ['bottle', 'requests'],
        'SENSORS': ['py3sensors'],
        'BATINFO': ['batinfo'],
        'SNMP': ['pysnmp'],
        'CHART': ['matplotlib'],
        'BROWSER': ['zeroconf>=0.17'],
        'IP': ['netifaces'],
        'RAID': ['pymdstat'],
        'DOCKER': ['docker-py'],
        'EXPORT': ['influxdb>=1.0.0', 'elasticsearch', 'potsdb' 'statsd', 'pika', 'bernhard', 'cassandra-driver'],
        'ACTION': ['pystache'],
        'CPUINFO': ['py-cpuinfo'],
        'FOLDERS': ['scandir']
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
        'Programming Language :: Python :: 3.5'
    ]
)
