===============
Glances experts
===============

This is the Glances exporters folder.

A Glances exporter is a Python module hosted in a folder.

The name of the foo Glances exporter folder is foo (glances_foo).

The exporter is a Python class named Export inherits the GlancesExport object:

.. code-block:: python

    class Export(GlancesExport):
        """Glances foo exporter."""

        def __init__(self, args=None, config=None):
            super(Export, self).__init__(config=config, args=args)
            pass

A plugin should implement the following methods:

- export(): export the self.stats variable to the exporter destination.

Have a look of all Glances exporter's methods in the export.py file.
