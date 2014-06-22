#!/usr/bin/env python

import glob
import os
import sys

from setuptools import setup


def get_data_files():
    data_files = [
        ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS', 'README.rst',
                               'conf/glances.conf', 'docs/glances-doc.html']),
        ('share/doc/glances/images', glob.glob('docs/images/*.png')),
        ('share/man/man1', ['man/glances.1'])
    ]

    if hasattr(sys, 'real_prefix') or 'bsd' in sys.platform:
        conf_path = os.path.join(sys.prefix, 'etc', 'glances')
    elif not hasattr(sys, 'real_prefix') and 'linux' in sys.platform:
        conf_path = os.path.join('/etc', 'glances')
    elif 'darwin' in sys.platform:
        conf_path = os.path.join('/usr/local', 'etc', 'glances')
    elif 'win32' in sys.platform:
        conf_path = os.path.join(os.environ.get('APPDATA'), 'glances')
    data_files.append((conf_path, ['conf/glances.conf']))

    for mo in glob.glob('i18n/*/LC_MESSAGES/*.mo'):
        data_files.append((os.path.dirname(mo).replace('i18n/', 'share/locale/'), [mo]))

    return data_files


def get_requires():
    requires = ['psutil>=2.0.0']
    if sys.platform.startswith('win'):
        requires += ['colorconsole']
    if sys.version_info < (2, 7):
        requires += ['argparse']

    return requires

setup(
    name='Glances',
    version='2.0.1',
    description="A cross-platform curses-based monitoring tool",
    long_description=open('README.rst').read(),
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    # download_url='https://s3.amazonaws.com/glances/glances-2.0.1.tar.gz',
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=get_requires(),
    extras_require={
        'WEB': ['bottle'],
        'SENSORS': ['py3sensors'],
        'BATINFO': ['batinfo'],
        'SNMP': ['pysnmp']
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
