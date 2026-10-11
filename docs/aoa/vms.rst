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
    # Thresholds for CPU (per-second rate of the VM CPU time), MEM (in % of
    # the VM memory) and LOAD (1 min load, if reported by the engine)
    # No default: leave commented to keep the VM table uncoloured
    #cpu_careful=50
    #cpu_warning=70
    #cpu_critical=90
    #mem_careful=20
    #mem_warning=50
    #mem_critical=70
    #load_careful=70
    #load_warning=100
    #load_critical=500
    # Per-VM override
    #vmname_mem_careful=10
    # Define the maximum VMs size name (default is 20 chars)
    max_name_size=20
    # By default, Glances only display running VMs with states:
    # 'Running', 'Paused', 'Starting' or 'Restarting'
    # Set the following key to True to display all VMs regarding their states
    all=False

.. note::

    The ``vms`` plugin is **disabled by default** (``disable=True``). CPU,
    MEM and LOAD thresholds are optional: without them, VM rows are
    informational only (the status is colour-coded: running is OK,
    starting/restarting is warning). When thresholds are defined, the
    values are coloured and alerts are raised (``warning`` and above).
    The TUI shows, per VM: engine (when more than one is active), name, status,
    core count, CPU%, memory used / total, load (1/5/15 min, only when
    available) and release.

You can use all the variables ({{foo}}) available in the vms plugin.

Filtering (for hide or show) is based on regular expression. Please be sure that your regular
expression works as expected. You can use an online tool like `regex101`_ in
order to test your regular expression.

.. _Multipass: https://canonical.com/multipass
.. _Virsh: https://www.libvirt.org/manpages/virsh.html
.. _regex101: https://regex101.com/
