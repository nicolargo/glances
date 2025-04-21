.. _vms:

VMs
===

Glances ``vms`` plugin is designed to display stats about VMs ran on the host.

It's actually support two engines: `Multipass` and `Virsh`.

No Python dependency is needed but Multipass and Virsh binary should be available:
- multipass should be executable from /snap/bin/multipass
- virsh should be executable from /usr/bin/virsh

Note: CPU information is not availble for Multipass VM. Load is not available for Virsh VM.

Configuration file options:

.. code-block:: ini

    [vms]
    disable=True
    # Define the maximum VMs size name (default is 20 chars)
    max_name_size=20
    # By default, Glances only display running VMs with states:
    # 'Running', 'Paused', 'Starting' or 'Restarting'
    # Set the following key to True to display all VMs regarding their states
    all=False

You can use all the variables ({{foo}}) available in the containers plugin.

Filtering (for hide or show) is based on regular expression. Please be sure that your regular
expression works as expected. You can use an online tool like `regex101`_ in
order to test your regular expression.

.. _Multipass: https://canonical.com/multipass
.. _Virsh: https://www.libvirt.org/manpages/virsh.html
