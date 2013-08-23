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

if hasattr(sys, 'real_prefix') or 'bsd' in sys.platform:
    etc_path = os.path.join(sys.prefix, 'etc', 'glances')
if not hasattr(sys, 'real_prefix') and 'linux' in sys.platform:
    etc_path = os.path.join('/etc', 'glances')
elif 'darwin' in sys.platform:
    etc_path = os.path.join('/usr/local', 'etc', 'glances')
data_files.append((etc_path, ['glances/conf/glances.conf']))

for mo in glob.glob('i18n/*/LC_MESSAGES/*.mo'):
    data_files.append((os.path.dirname(mo).replace('i18n/', 'share/locale/'), [mo]))

if sys.platform.startswith('win'):
    requires = ['psutil>=0.5.1', 'colorconsole==0.6']
else:
    requires = ['psutil>=0.5.1']
    
setup(
    name='Glances',
    version='1.7.1',
    description="A cross-platform curses-based monitoring tool",
    long_description=open('README.rst').read(),
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    url='https://github.com/nicolargo/glances',
    # Alternative download_url='https://s3.amazonaws.com/glances/glances-1.7.1.tar.gz',
    license="LGPL",
    keywords="cli curses monitoring system",
    install_requires=requires,
    extras_require={
        'HTML': ['jinja2'],
        'SENSORS': ['pysensors'],
        'BATINFO': ['batinfo']
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
