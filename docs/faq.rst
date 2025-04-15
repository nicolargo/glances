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
