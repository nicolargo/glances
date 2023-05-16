#!/usr/bin/env python

import glob
import os
import re
import sys
from io import open

from setuptools import setup, Command


if sys.version_info < (3, 4):
    print('Glances requires at least Python 3.4 to run.')
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
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS.rst', 'README.rst',
                               'CONTRIBUTING.md', 'conf/glances.conf']),
        ('share/man/man1', ['docs/man/glances.1'])
    ]

    return data_files


def get_install_requires():
    requires = [
        'psutil>=5.6.7',
        'defusedxml',
        'packaging',
        'ujson>=5.4.0',
    ]
    if sys.platform.startswith('win'):
        requires.append('bottle')
        requires.append('requests')

    return requires


def get_install_extras_require():
    extras_require = {
        'action': ['chevron'],
        'browser': ['zeroconf>=0.19.1'],
        'cloud': ['requests'],
        'containers': ['docker>=6.1.1', 'python-dateutil', 'six', 'podman', 'packaging'],
        'export': ['bernhard', 'cassandra-driver', 'couchdb', 'elasticsearch',
                   'graphitesender', 'influxdb>=1.0.0', 'influxdb-client', 'pymongo',
                   'kafka-python', 'pika', 'paho-mqtt', 'potsdb', 'prometheus_client',
                   'pyzmq', 'statsd'],
        'folders': ['scandir'],
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
    if sys.platform.startswith('linux'):
        extras_require['sensors'] = ['batinfo']

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
    python_requires=">=3.8",
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
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Topic :: System :: Monitoring'
    ]
)
