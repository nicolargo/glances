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

Netifaces issue ?
-----------------

Previously, Glances uses Netifaces to get network interfaces information.

Now, Glances uses Netifaces2.

Please uninstall Netifaces and install Netifaces2 instead.

Extra note: Glances 4.5 or higher do not use Netifaces/Netifaces2 anymore.

On Debian/Ubuntu Operating Systems, Webserver display a blank screen ?
----------------------------------------------------------------------

For some reason, the Glances Debian/Ubuntu packages do not include the Web UI static files.

Please read: https://github.com/nicolargo/glances/issues/2021 for workaround and more information.

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
