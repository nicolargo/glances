===============================
Glances - An eye on your system
===============================

.. image:: https://api.flattr.com/button/flattr-badge-large.png
        :target: https://flattr.com/thing/484466/nicolargoglances-on-GitHub
.. image:: https://scrutinizer-ci.com/g/nicolargo/glances/badges/quality-score.png?b=master
        :target: https://scrutinizer-ci.com/g/nicolargo/glances/
.. image:: https://travis-ci.org/nicolargo/glances.svg?branch=master
        :target: https://travis-ci.org/nicolargo/glances
.. image:: https://badge.fury.io/py/Glances.svg
        :target: http://badge.fury.io/py/Glances
.. image:: https://pypip.in/d/Glances/badge.svg
        :target: https://pypi.python.org/pypi/Glances/
        :alt: Downloads


Follow Glances on Twitter: `@nicolargo`_ or `@glances_system`_

**Glances** is a cross-platform curses-based system monitoring tool
written in Python.

.. image:: https://raw.github.com/nicolargo/glances/master/docs/images/screenshot-wide.png

Requirements
============

- ``python >= 2.6`` or ``>= 3.3`` (tested with version 2.6, 2.7, 3.3, 3.4)
- ``psutil >= 2.0.0``
- ``setuptools``

Optional dependencies:

- ``bottle`` (for Web server mode)
- ``py3sensors`` (for hardware monitoring support) [Linux-only]
- ``hddtemp`` (for HDD temperature monitoring support) [Linux-only]
- ``batinfo`` (for battery monitoring support) [Linux-only]
- ``pymdstat`` (for RAID support) [Linux-only]
- ``pysnmp`` (for SNMP support)
- ``zeroconf`` (for the autodiscover mode)
- ``netifaces`` (for the IP plugin)
- ``influxdb`` (for the InfluxDB export module)
- ``statsd`` (for the StatsD export module)
- ``pystache`` (for the action script feature)
- ``docker-py`` (for the Docker monitoring support) [Linux-only]
- ``matplotlib`` (for graphical/chart support)
- ``pika`` (for the RabbitMQ/ActiveMQ export module)

Installation
============

Glances Auto Install script
---------------------------

To install both dependencies and latest Glances production ready version
(aka *master* branch), just enter the following command line:

.. code-block:: console

    curl -L http://bit.ly/glances | /bin/bash

or

.. code-block:: console

    wget -O- http://bit.ly/glances | /bin/bash

*Note*: Only supported on some GNU/Linux distributions. If you want to
support other distributions, please contribute to `glancesautoinstall`_.

PyPI: The simple way
--------------------

Glances is on ``PyPI``. By using PyPI, you are sure to have the latest
stable version.

To install, simply use ``pip``:

.. code-block:: console

    pip install glances

*Note*: Python headers are required to install psutil. For example,
on Debian/Ubuntu you need to install first the *python-dev* package.

You can also install the following libraries in order to use optional
features:

.. code-block:: console

    pip install bottle batinfo https://bitbucket.org/gleb_zhulik/py3sensors/get/tip.tar.gz zeroconf netifaces pymdstat influxdb statsd pystache pika

To upgrade Glances to the latest version:

.. code-block:: console

    pip install --upgrade glances

If you need to install Glances in a specific user location, use:

.. code-block:: console

    export PYTHONUSERBASE=~/mylocalpath
    pip install --user glances

GNU/Linux
---------

At the moment, packages exist for the following GNU/Linux distributions:

- Arch Linux
- Debian
- Fedora/CentOS/RHEL
- Gentoo
- Slackware (SlackBuild)
- Ubuntu
- Void Linux

So you should be able to install it using your favorite package manager.

FreeBSD
-------

To install the binary package:

.. code-block:: console

    # pkg install py27-glances

To install Glances from ports:

.. code-block:: console

    # cd /usr/ports/sysutils/py-glances/
    # make install clean

OS X
----

OS X users can install Glances using ``Homebrew`` or ``MacPorts``.

Homebrew
````````

.. code-block:: console

    $ brew install python
    $ pip install glances

MacPorts
````````

.. code-block:: console

    $ sudo port install glances

Windows
-------

- Install Python for Windows (Python 2.7.9+ ship with Pip): http://www.python.org/getit/
- Install the psutil library (latest binary version): https://pypi.python.org/pypi/psutil
- Install the colorconsole library: https://pypi.python.org/pypi/colorconsole
- Install optionnals dependencies (see list bellow)
- Install Glances using pip

.. code-block:: console

    $ pip install glances

Source
------

To install Glances from source:

.. code-block:: console

    $ curl -L https://github.com/nicolargo/glances/archive/vX.Y.tar.gz -o glances-X.Y.tar.gz
    $ tar -zxvf glances-*.tar.gz
    $ cd glances-*
    # python setup.py install

*Note*: Python headers are required to install psutil. For example,
on Debian/Ubuntu you need to install first the *python-dev* package.

Puppet
------

You can install Glances using ``Puppet``: https://github.com/rverchere/puppet-glances

Usage
=====

For the standalone mode, just run:

.. code-block:: console

    $ glances

For the Web server mode, run:

.. code-block:: console

    $ glances -w

and enter the URL ``http://<ip>:61208`` in your favorite web browser.

For the client/server mode, run:

.. code-block:: console

    $ glances -s

on the server side and run:

.. code-block:: console

    $ glances -c <ip>

on the client one.

You can also detect and display all Glances servers available on your
network or defined in the configuration file:

.. code-block:: console

    $ glances --browser

and RTFM, always.

Documentation
=============

For complete documentation see `glances-doc`_.

If you have any question (after RTFM!), please post it on the official Q&A `forum`_.

Gateway to other services
=========================

Glances can export stats to: ``CSV`` file, ``InfluxDB``, ``StatsD`` and ``RabbitMQ`` server.

How to contribute ?
===================

If you want to contribute to the Glances project, read this `Wiki`_ page.

There is also a chat dedicated to the Glances developers:

.. image:: https://badges.gitter.im/Join%20Chat.svg
        :target: https://gitter.im/nicolargo/glances?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

Author
======

Nicolas Hennion (@nicolargo) <nicolas@nicolargo.com>

License
=======

LGPL. See ``COPYING`` for more details.

.. _psutil: https://github.com/giampaolo/psutil
.. _glancesautoinstall: https://github.com/nicolargo/glancesautoinstall
.. _@nicolargo: https://twitter.com/nicolargo
.. _@glances_system: https://twitter.com/glances_system
.. _glances-doc: https://github.com/nicolargo/glances/blob/master/docs/glances-doc.rst
.. _forum: https://groups.google.com/forum/?hl=en#!forum/glances-users
.. _Wiki: https://github.com/nicolargo/glances/wiki/How-to-contribute-to-Glances-%3F
