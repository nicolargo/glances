===============
Glances experts
===============

This is the Glances exporters folder.

A Glances exporter is a Python package hosted in a folder: the foo exporter
lives in ``glances_foo/`` and its code in ``glances_foo/export.py``.

The exporter is a Python class named Export that inherits the
GlancesExportBase class (``export_base.py``):

.. code-block:: python

    from glances.exports.export_base import GlancesExportBase


    class Export(GlancesExportBase):
        """Glances foo exporter."""

        export_name = "foo"

        def export(self, name, columns, points):
            """Write one plugin's flattened stats to the backend."""

An exporter should implement the following methods:

- export(name, columns, points): write one plugin's stats to the exporter
  destination.
- exit() (optional): release the backend resources.

Have a look of all Glances exporter's methods in the export_base.py file.
