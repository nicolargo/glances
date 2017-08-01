.. _json:

JSON
====

It's possible to export stats to a JSON file to be processed later by an
external system.

.. code-block:: console

    $ glances --export-json /tmp/glances.json

JSON file description:

Each line would contain a JSON glance of the system. If this file needs to be
processed it should be processed in a line by line basis.
