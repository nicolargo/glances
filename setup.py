#!/usr/bin/env python

import os
import sys
import glob

from setuptools import setup

data_files = [
    ('share/man/man1', ['man/glances.1']),
    ('share/doc/glances', ['AUTHORS',
                           'COPYING',
                           'NEWS',
                           'README',
                           'glances/conf/glances.conf']),
    ('share/doc/glances/doc', glob.glob('doc/*.png')),
    ('share/glances/css', glob.glob('glances/data/css/*.css')),
    ('share/glances/html', glob.glob('glances/data/html/*.html')),
    ('share/glances/img', glob.glob('glances/data/img/*.png')),
]

if hasattr(sys, 'real_prefix') or ('bsd' or 'darwin' in sys.platform):
    etc_path = os.path.join(sys.prefix, 'etc', 'glances')
if not hasattr(sys, 'real_prefix') and 'linux' in sys.platform:
    etc_path = os.path.join('/etc', 'glances')
data_files.append((etc_path, ['glances/conf/glances.conf']))

for mo in glob.glob('i18n/*/LC_MESSAGES/*.mo'):
    data_files.append((os.path.dirname(mo).replace('i18n/', 'share/locale/'), [mo]))

setup(
    name='Glances',
    version='1.7a',
    download_url='https://s3.amazonaws.com/glances/glances-1.7a.tar.gz',
    url='https://github.com/nicolargo/glances',
    description='CLI curses-based monitoring tool',
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    license="LGPL",
    keywords="cli curses monitoring system",
    long_description=open('README').read(),
    test_suite="glances.tests",
    install_requires=['psutil>=0.4.1'],
    packages=['glances'],
    extras_require={
        'HTML': ['jinja2>=2.0'],
        'SENSORS': ['pysensors>=0.0.2'],
    },
    include_package_data=True,
    data_files=data_files,
    entry_points={"console_scripts": ["glances=glances.glances:main"]},
)
