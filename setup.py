#!/usr/bin/env python

import glob
import sys

from setuptools import setup


if sys.version_info < (2, 6) or (3, 0) <= sys.version_info < (3, 3):
    print('Glances requires at least Python 2.6 or 3.3 to run.')
    sys.exit(1)


def get_data_files():
    data_files = [
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS', 'README.rst',
                               'conf/glances.conf', 'docs/glances-doc.html']),
        ('share/doc/glances/images', glob.glob('docs/images/*.png')),
        ('share/man/man1', ['man/glances.1'])
    ]

    return data_files


def get_requires():
    requires = ['psutil>=2.0.0']
    if sys.platform.startswith('win'):
        requires += ['colorconsole']
    if sys.version_info == (2, 6):
        requires += ['argparse', 'logutils']

    return requires

setup(
    name='Glances',
    version='2.5',
    description="A cross-platform curses-based monitoring tool",
    long_description=open('README.rst').read(),
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    # download_url='https://s3.amazonaws.com/glances/glances-2.5.tar.gz',
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=get_requires(),
    extras_require={
        'WEB': ['bottle'],
        'SENSORS': ['py3sensors'],
        'BATINFO': ['batinfo'],
        'SNMP': ['pysnmp'],
        'CHART': ['matplotlib'],
        'BROWSER': ['zeroconf>=0.17'],
        'IP': ['netifaces'],
        'RAID': ['pymdstat'],
        'DOCKER': ['docker-py'],
        'EXPORT': ['influxdb>=1.0.0', 'potsdb' 'statsd', 'pika'],
        'ACTION': ['pystache'],
        'CPUINFO': ['py-cpuinfo']
    },
    packages=['glances'],
    include_package_data=True,
    data_files=get_data_files(),
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
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4'
    ]
)
