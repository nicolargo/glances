#!/usr/bin/env python

import os
import sys
import glob

from setuptools import setup

data_files = [
    ('share/doc/glances', ['AUTHORS', 'COPYING', 'NEWS', 'README.rst',
                           'docs/glances-doc.html',
                           'glances/conf/glances.conf']),
    ('share/doc/glances/images', glob.glob('docs/images/*.png')),
    ('share/glances/css', glob.glob('glances/data/css/*.css')),
    ('share/glances/html', glob.glob('glances/data/html/*.html')),
    ('share/glances/img', glob.glob('glances/data/img/*.png')),
    ('share/man/man1', ['docs/man/glances.1'])
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
    description="A cross-platform curses-based monitoring tool",
    long_description=open('README.rst').read(),
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    download_url='https://s3.amazonaws.com/glances/glances-1.7a.tar.gz',
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=['psutil>=0.4.1'],
    extras_require={
        'HTML': ['jinja2>=2.0'],
        'SENSORS': ['pysensors>=0.0.2']
    },
    packages=['glances'],
    include_package_data=True,
    data_files=data_files,
    test_suite="glances.tests",
    entry_points={"console_scripts": ["glances=glances.glances:main"]},
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
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3'
    ]
)
