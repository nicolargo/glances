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
        'ChangeLog',
        'NEWS',
        'screenshot.png']),
    ('share/doc/glances/doc', glob('doc/*.png')),
    ('share/glances/html', glob('glances/html/*.html')),    
    ('share/glances/html/css', glob('glances/css/*.css')),
    ('share/glances/html/img', glob('glances/img/*.png')),
]
for mo in glob('i18n/*/LC_MESSAGES/*.mo'):
    data_files.append((dirname(mo).replace('i18n/', 'share/locale/'), [mo]))

setup(name='Glances',
    version='1.4b',
    download_url='https://github.com/downloads/nicolargo/glances/glances-1.4b.tar.gz',
    url='https://github.com/nicolargo/glances',
    description='CLI curses-based monitoring tool',
    author='Nicolas Hennion',
    author_email='nicolas@nicolargo.com',
    license="LGPL",
    keywords="cli curses monitoring system",
    long_description=open('README').read(),
    install_requires=['psutil>=0.4.1'],
    packages=['glances'],
     extras_require = {
        'HTML':  ['jinja2>=2.0'],
    },
    include_package_data=True,
    data_files=data_files,
    entry_points={"console_scripts": ["glances = glances.glances:main"]},
)
