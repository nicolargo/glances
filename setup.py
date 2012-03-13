#!/usr/bin/env python

from glob import glob

from setuptools import setup

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
    include_package_data=True,
    data_files=[
        ('share/man/man1', ['man/glances.1']),
        ('share/doc/glances', ['README',
            'README-fr',
            'COPYING',
            'AUTHORS',
            'ChangeLog',
            'NEWS',
            'screenshot.png']),
        ('share/doc/glances/doc', glob('doc/*.png')),
    ],
    entry_points={"console_scripts": ["glances = glances.glances:main"]},
)
