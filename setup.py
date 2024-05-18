#!/usr/bin/env python

import builtins
import glob
import os
import re
import sys

from setuptools import Command, setup

# If the minimal Python version is changed then do not forget to change it in:
# - ./pyproject.toml
# - .github/workflows/test.yml
if not (sys.version_info >= (3, 8)):
    print('Glances requires at least Python 3.8 to run.')
    sys.exit(1)

# Global functions
##################

with builtins.open(os.path.join('glances', '__init__.py'), encoding='utf-8') as f:
    version = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", f.read(), re.M).group(1)

if not version:
    raise RuntimeError('Cannot find Glances version information.')

with builtins.open('README.rst', encoding='utf-8') as f:
    long_description = f.read()


def get_data_files():
    return [
        (
            'share/doc/glances',
            ['AUTHORS', 'COPYING', 'NEWS.rst', 'README.rst', "SECURITY.md", 'CONTRIBUTING.md', 'conf/glances.conf'],
        ),
        ('share/man/man1', ['docs/man/glances.1']),
    ]


def get_install_requires():
    required = []
    with open('requirements.txt') as f:
        required = f.read().splitlines()

    # On Windows, install WebUI by default
    if sys.platform.startswith('win'):
        required.append('fastapi')
        required.append('uvicorn')
        required.append('jinja2')
        required.append('requests')

    return required


def get_install_extras_require():
    extras_require = {
        'action': ['chevron'],
        'browser': ['zeroconf>=0.19.1'],
        'cloud': ['requests'],
        'containers': ['docker>=6.1.1', 'python-dateutil', 'six', 'podman', 'packaging'],
        'export': [
            'bernhard',
            'cassandra-driver',
            'elasticsearch',
            'graphitesender',
            'ibmcloudant',
            'influxdb>=1.0.0',
            'influxdb-client',
            'pymongo',
            'kafka-python',
            'pika',
            'paho-mqtt',
            'potsdb',
            'prometheus_client',
            'pyzmq',
            'statsd',
        ],
        'gpu': ['nvidia-ml-py'],
        'graph': ['pygal'],
        'ip': ['netifaces'],
        'raid': ['pymdstat'],
        'smart': ['pySMART.smartx'],
        'snmp': ['pysnmp'],
        'sparklines': ['sparklines'],
        'web': ['fastapi', 'uvicorn', 'jinja2', 'requests'],
        'wifi': ['wifi'],
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

        for t in glob.glob('unittest-core.py'):
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
    test_suite="unittest-core.py",
    entry_points={"console_scripts": ["glances=glances:main"]},
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console :: Curses',
        'Environment :: Web Environment',
        'Framework :: FastAPI',
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
        'Programming Language :: Python :: 3.12',
        'Topic :: System :: Monitoring',
    ],
)
