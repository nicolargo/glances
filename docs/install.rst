.. _install:

Install
=======

Glances is on ``PyPI``. By using PyPI, you are sure to have the latest
stable version.

To install, simply use ``pip``:

.. code-block:: console

    pip install glances

*Note*: Python headers are required to install `psutil`_. For example,
on Debian/Ubuntu you need to install first the *python-dev* package.
For Fedora/CentOS/RHEL install first *python-devel* package. For Windows,
just install psutil from the binary installation file.

You can also install the following libraries in order to use optional
features (like the Web interface, export modules...):

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
