Follow Glances on Twitter: `@nicolargo`_ or `@glances_system`_

===============================
Glances - An eye on your system
===============================

.. image:: https://api.flattr.com/button/flattr-badge-large.png
        :target: https://flattr.com/thing/484466/nicolargoglances-on-GitHub
.. image:: https://travis-ci.org/nicolargo/glances.png?branch=master
        :target: https://travis-ci.org/nicolargo/glances
.. image:: https://badge.fury.io/py/Glances.png
        :target: http://badge.fury.io/py/Glances
.. image:: https://pypip.in/d/Glances/badge.png
        :target: https://pypi.python.org/pypi/Glances/
        :alt: Downloads
.. image:: https://d2weczhvl823v0.cloudfront.net/nicolargo/glances/trend.png
        :target: https://bitdeli.com/nicolargo
.. image:: https://raw.github.com/nicolargo/glances/master/docs/images/glances-white-256.png
        :width: 128

**Glances** is a cross-platform curses-based monitoring tool written in Python.

It uses the `psutil`_ library to get information from your system.

.. image:: https://raw.github.com/nicolargo/glances/master/docs/images/screenshot-wide.png

Requirements
============

- ``python >= 2.6`` (tested with version 2.6, 2.7, 3.2, 3.3)
- ``psutil >= 0.5.1`` (recommended version >= 1.2.1)
- ``setuptools``

Optional dependencies:

- ``jinja2`` (for HTML output)
- ``pysensors`` (for HW monitoring support) [Linux-only]
- ``hddtemp`` (for HDD temperature monitoring support)
- ``batinfo`` (for battery monitoring support) [Linux-only]

Installation
============

PyPI: The simple way
--------------------

Glances is on `PyPI`_. To install, simply use `pip`_:

.. code-block:: console

    pip install Glances

To upgrade Glances to the latest version:

.. code-block:: console

    pip install --upgrade Glances

Linux
-----

At the moment, packages exist for the following distributions:

- Arch Linux
- Debian (Testing/Sid)
- Fedora/CentOS/RHEL
- Gentoo
- Ubuntu (13.04+)
- Void Linux

So you should be able to install it using your favorite package manager.

FreeBSD
-------

To install the binary package:

.. code-block:: console

    # pkg_add -r py27-glances

Using pkgng:

.. code-block:: console

    # pkg install py27-glances

To install Glances from ports:

.. code-block:: console

    # cd /usr/ports/sysutils/py-glances/
    # make install clean

OS X
----

OS X users can also install Glances using `Homebrew`_ or `MacPorts`_.

Homebrew
````````

.. code-block:: console

    $ brew install python
    $ pip install Glances

MacPorts
````````

.. code-block:: console

    $ sudo port install glances

Windows
-------

Glances proposes a Windows client based on the `colorconsole`_ Python library.
Glances version < 1.7.2 only works in server mode.

Thanks to Nicolas Bourges, a Windows installer is available:

- Glances-1.7.2-win32.msi_ (32-bit, MD5: dba4f6cc9f47b6806ffaeb665c093270)

Otherwise, you have to follow these steps:

- Install Python for Windows: http://www.python.org/getit/
- Install the psutil library: https://pypi.python.org/pypi?:action=display&name=psutil#downloads
- Install the colorconsole library: http://code.google.com/p/colorconsole/downloads/list
- Download Glances from here: http://nicolargo.github.io/glances/

Source
------

To install Glances from source:

.. code-block:: console

    $ curl -L https://github.com/nicolargo/glances/archive/vX.X.tar.gz -o glances-X.X.tar.gz
    $ tar -zxvf glances-*.tar.gz
    $ cd glances-*
    # python setup.py install

*Note*: Python headers are required to install psutil. For example, you need to install first:

* On Debian/Ubuntu, the *python-dev* package
* On CentOS/Fedora, the *python-devel* package (from the EPEL repository)
* On openSUSE/SLES/SLED, the *python-devel* package (from Oss repository)

Puppet
------

You can install Glances using `Puppet`_: https://github.com/rverchere/puppet-glances

Usage
=====

Just run:

.. code-block:: console

    $ glances

and RTFM, always.

Documentation
=============

For complete documentation see `glances-doc`_.

Author
======

Nicolas Hennion (@nicolargo) <nicolas@nicolargo.com>

License
=======

LGPL. See ``COPYING`` for more details.

.. _psutil: https://code.google.com/p/psutil/
.. _@nicolargo: https://twitter.com/nicolargo
.. _@glances_system: https://twitter.com/glances_system
.. _PyPI: https://pypi.python.org/pypi
.. _pip: http://www.pip-installer.org/
.. _Homebrew: http://brew.sh/
.. _MacPorts: https://www.macports.org/
.. _Glances-1.7.2-win32.msi: http://glances.s3.amazonaws.com/Glances-1.7.2-win32.msi
.. _colorconsole: https://pypi.python.org/pypi/colorconsole
.. _Puppet: https://puppetlabs.com/puppet/what-is-puppet/
.. _glances-doc: https://github.com/nicolargo/glances/blob/master/docs/glances-doc.rst
