.. image:: https://api.flattr.com/button/flattr-badge-large.png
        :target: https://flattr.com/thing/484466/nicolargoglances-on-GitHub
.. image:: https://travis-ci.org/nicolargo/glances.png?branch=master
        :target: https://travis-ci.org/nicolargo/glances

===============================
Glances - An eye on your system
===============================

.. image:: https://raw.github.com/nicolargo/glances/master/docs/images/glances-white-256.png
        :width: 128

**Glances** is a cross-platform curses-based monitoring tool written in Python.

It uses the `psutil`_ library to get information from your system.

.. image:: https://raw.github.com/nicolargo/glances/master/docs/images/screenshot-wide.png

Requirements
============

- ``python >= 2.6`` (tested with version 2.6, 2.7, 3.2, 3.3)
- ``psutil >= 0.4.1`` (recommended version >= 0.6)
- ``jinja`` (optional for HTML output)
- ``pysensors`` (optional for HW monitoring support) [Linux-only]
- ``hddtemp`` (optional for HDD temperature monitoring support)
- ``batinfo`` (optional for battery monitoring support) [Linux-only]
- ``setuptools``

Installation
============

Glances is on `PyPI`_. To install, simply use `pip`_:

.. code-block:: console

    pip install Glances

*Note*: On Debian/Ubuntu, you need to install first the `python-dev` package.

Linux
-----

Actually, packages exist for Arch Linux, Fedora / CentOS / RHEL,
Debian (Sid/Testing) and Ubuntu (13.04+), so you should be able to
install it using your favorite package manager.

FreeBSD
-------

To install the precompiled binary package:

.. code-block:: console

    # pkg_add -r py27-glances

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

    $ brew install brew-pip
    $ export PYTHONPATH=$(brew --prefix)/lib/python2.7/site-packages
    $ brew pip Glances

If you get the following error:

.. code-block:: console

    Error: Failed executing: pip install glances==X.X --install-option=--prefix=/usr/local/XXX/glances/X.X (.rb:)

Try to run:

.. code-block:: console

    $ pip install glances==X.X --install-option=--prefix=/usr/local/XXX/glances/X.X
    $ brew link Glances

MacPorts
````````

.. code-block:: console

    $ sudo port install glances

Windows
-------

Windows only support Glances in server mode. Glances will automatically run in server mode on it.

Thanks to `Nicolas Bourges`, Glances can be easily installed using a Windows installer:

- glances-1.6.1-x86.exe_ (32-bit, md5sum: 13d5be664599f80152f8f1ae47400576)
- glances-1.6.1-x64.exe_ (64-bit, md5sum: a347ec5097d6d4d5039c7233872757a8)

Otherwise, you have to follow these steps:

- Install `Python for Windows`: http://www.python.org/getit/
- Install the `psutil` library: https://code.google.com/p/psutil/downloads/list
- Download `Glances` from here: http://nicolargo.github.io/glances/

Source
------

To install Glances from source:

.. code-block:: console

    $ curl -L https://github.com/nicolargo/glances/archive/vX.X.tar.gz -o glances-X.X.tar.gz
    $ tar -zxvf glances-*.tar.gz
    $ cd glances-*
    # python setup.py install

*Note*: On Debian/Ubuntu, you need to install first the `python-dev` package.

Puppet
------

You can install Glances using `Puppet`_: https://github.com/rverchere/puppet-glances

Usage
=====

Just run:

.. code-block:: console

    $ glances

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
.. _PyPI: https://pypi.python.org/pypi
.. _pip: http://www.pip-installer.org/
.. _Homebrew: http://mxcl.github.com/homebrew/
.. _MacPorts: https://www.macports.org/
.. _glances-1.6.1-x86.exe: https://s3.amazonaws.com/glances/glances-1.6.1-x86.exe
.. _glances-1.6.1-x64.exe: https://s3.amazonaws.com/glances/glances-1.6.1-x64.exe
.. _Puppet: https://puppetlabs.com/puppet/what-is-puppet/
.. _glances-doc: https://github.com/nicolargo/glances/blob/master/docs/glances-doc.rst
