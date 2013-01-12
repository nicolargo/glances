#!/usr/bin/env python

from glob import glob
from os.path import dirname

from setuptools import setup

data_files = [
    ('share/man/man1', ['man/glances.1']),
    ('share/doc/glances', ['README',
                           'README-fr',
                           'COPYING',
                           'AUTHORS',
                           'NEWS',
                           'screenshot.png',
                           'glances/conf/glances.conf']),
    ('share/doc/glances/doc', glob('doc/*.png')),
    ('etc/glances', ['glances/conf/glances.conf']),
    ('share/glances/html', glob('glances/html/*.html')),
    ('share/glances/css', glob('glances/css/*.css')),
    ('share/glances/img', glob('glances/img/*.png')),
]

for mo in glob('i18n/*/LC_MESSAGES/*.mo'):
    data_files.append((dirname(mo).replace('i18n/', 'share/locale/'), [mo]))

setup(
    name='Glances',
    version='1.6b',
    download_url='https://s3.amazonaws.com/glances/glances-1.6b.tar.gz',
    url='https://github.com/nicolargo/glances',
    description='CLI curses-based monitoring tool',
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    license="LGPL",
    keywords="cli curses monitoring system",
    long_description=open('README').read(),
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
