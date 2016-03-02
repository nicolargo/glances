.. _quickstart:

Quickstart
==========

This page gives a good introduction in how to get started with Glances.
Glances offers 3 modes:

- Standalone
- Client/Server
- Web server

Standalone Mode
---------------

Simply run:

.. code-block:: console

    $ glances

Client/Server Mode
------------------

If you want to remotely monitor a machine, called ``server``, from
another one, called ``client``, just run on the server:

.. code-block:: console

    server$ glances -s

and on the client:

.. code-block:: console

    client$ glances -c @server

where ``@server`` is the IP address or hostname of the server.

Glances can centralize available Glances servers using the ``--browser``
option. The server list can be statically defined via the configuration
file (section ``[serverlist]``).

In server mode, you can set the bind address with ``-B ADDRESS`` and
the listening TCP port with ``-p PORT``.

In client mode, you can set the TCP port of the server with ``-p PORT``.

Default binding address is ``0.0.0.0`` (Glances will listen on all the
available network interfaces) and TCP port is ``61209``.

In client/server mode, limits are set by the server side.

You can set a password to access to the server ``--password``. By
default, the username is ``glances`` but you can change it with
``--username``.

If you ask it, the SHA password will be stored in ``username.pwd`` file.

Glances is ``IPv6`` compatible. Just use the ``-B ::`` option to bind to
all IPv6 addresses.

Autodiscover
^^^^^^^^^^^^

Glances can also detect and display all Glances servers available on
your network via the ``zeroconf`` protocol (not available on Windows):

.. code-block:: console

    client$ glances --browser

Use ``--disable-autodiscover`` to disable it.

SNMP
^^^^

As an experimental feature, if Glances server is not detected by the
client, the latter will try to grab stats using the ``SNMP`` protocol:

.. code-block:: console

    client$ glances -c @snmpserver

.. note::
    Stats grabbed by SNMP request are limited and OS dependent.

Web Server Mode
---------------

.. image:: _static/screenshot-web.png

If you want to remotely monitor a machine, called ``server``, from any
device with a web browser, just run the server with the ``-w`` option:

.. code-block:: console

    server$ glances -w

then on the client enter the following URL in your favorite web browser:

::

    http://@server:61208

where ``@server`` is the IP address or hostname of the server.

To change the refresh rate of the page, just add the period in seconds
at the end of the URL. For example, to refresh the page every ``10``
seconds:

::

    http://@server:61208/10

The Glances web interface follows responsive web design principles.

Here's a screenshot from Chrome on Android:

.. image:: _static/screenshot-web2.png
