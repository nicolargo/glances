.. _faq:

F.A.Q
=====

Any encoding issue ?
--------------------

Try to run Glances with the following command line:

    LANG=en_US.UTF-8 LC_ALL= glances

Container memory stats not displayed ?
--------------------------------------

On ARM64, Docker needs to be configured to allow access to the memory stats.

Edit the /boot/firmware/cmdline.txt and add the following configuration key:

    cgroup_enable=memory

On Debian/Ubuntu Operating Systems, Webserver display a blank screen ?
----------------------------------------------------------------------

Some distribution packages do not include the Web UI static files. In this case, the Glances server
logs a ``WebUI assets not found`` warning and only serves the REST API.

Please install Glances from PyPI (``pip install 'glances[web]'``) or use the Docker images, which
include the Web UI.

I can not reach the Web UI from another machine ?
-------------------------------------------------

Glances v5 listens on ``127.0.0.1`` by default. Start the server with ``-B 0.0.0.0`` (or set
``bind_address=0.0.0.0`` in the ``[outputs]`` section of the configuration file) to listen on all the
interfaces.

A server bound to ``127.0.0.1`` also rejects requests whose ``Host`` header is not ``localhost``,
``127.0.0.1`` or ``[::1]`` (DNS rebinding protection). Behind a local reverse proxy that forwards its own
``Host``, list the accepted names in ``webui_allowed_hosts`` (``[outputs]`` section).

Glances said that my computer has no free memory, is it normal ?
----------------------------------------------------------------

On Linux, Glances shows by default the free memory.

Free memory can be low, it's a "normal" behavior because Linux uses free memory for disk caching
to improve performance. More information can be found here: https://linuxatemyram.com/.

If you want to display the "available" memory instead of the "free" memory, you can uses the
the following configuration key in the Glances configuration file:

.. code-block:: ini

    [mem]
    # Display available memory instead of used memory
    available=True
