.. _zfs:

ZFS
===

This plugin monitors `ZFS <https://openzfs.org/>`_ pools and datasets.

It requires OpenZFS 2.3 or newer, which provides JSON output for the
``zpool`` and ``zfs`` commands. On older ZFS versions, or on systems
without ZFS, the plugin disables itself automatically.

.. note::
    This plugin is disabled by default. Enable it with ``disable=False``
    in the ``[zfs]`` section.

.. note::
    The plugin runs the ``zpool list``, ``zpool status`` and ``zfs list``
    commands. Pools are identified by their GUID, so data stays consistent
    even if a pool is renamed.

Fields
------

Per pool:

- **state**: pool state (``ONLINE``, ``DEGRADED``, ``FAULTED``, ...).
- **health**: pool health.
- **size / allocated / free**: space usage, in bytes.
- **capacity**: pool usage in percent.
- **fragmentation**: pool fragmentation in percent.
- **read_errors / write_errors / checksum_errors**: total device errors.
- **error_count**: pool data error count.
- **status**: status message reported by ``zpool status``. The TUI shows its
  first sentence, truncated to fit.
- **scan_function / scan_state / scan_errors / scan_progress**: last or
  running scrub/resilver.
- **vdevs**: per-device list.
- **datasets**: per-dataset list (name, used, available, referenced,
  mountpoint, used_percent).

Alerts
------

- Pool state other than ``ONLINE`` (``DEGRADED``/``OFFLINE``/``REMOVED`` ->
  WARNING, ``FAULTED``/``UNAVAIL`` -> CRITICAL).
- Pool capacity above ``capacity_warning``/``capacity_critical`` (defaults
  80/90 percent).
- Any device READ/WRITE/CKSUM error.
- Any scrub/resilver error.

Configuration
-------------

See the ``[zfs]`` section in ``glances.conf``. Notable options:
``refresh``, ``max_depth``, ``max_datasets``, ``show_datasets``.
