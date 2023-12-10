.. _install:

Install
=======

Glances is available on ``PyPI``. By using PyPI, you are sure to have the
latest stable version.

To install, simply use ``pip``:

.. code-block:: console

    pip install glances

*Note*: Python headers are required to install `psutil`_. For instance,
on Debian/Ubuntu, you must first install the *python-dev* package.
On Fedora/CentOS/RHEL, first, install the *python-devel* package. For Windows,
psutil can be installed from the binary installation file.

You can also install the following libraries to use the optional
features (such as the web interface, export modules, etc.):

.. code-block:: console

    pip install glances[all]

To upgrade Glances and all its dependencies to the latest versions:

.. code-block:: console

    pip install --upgrade glances
    pip install --upgrade psutil
    pip install --upgrade glances[all]

For additional installation methods, read the official `README`_ file.

.. _psutil: https://github.com/giampaolo/psutil
.. _README: https://github.com/nicolargo/glances/blob/master/README.rst
