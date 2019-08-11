.. _csv:

CSV
===

It's possible to export stats to a CSV file.

.. code-block:: console

    $ glances --export csv --export-csv-file /tmp/glances.csv

CSV file description:

- first line: Stats description (header)
- others lines: Stats (data)

By default, data will be append any existing CSV file.

If the header did not match with a previous one, an error is logged.

The --export-csv-overwrite tag should be used if you want to delete the existing CSV file when Glances starts.

It is possible to remove some exported data using the --disable-plugin tag:

  $ glances --export csv --export-csv-file /tmp/glances.csv --disable-plugin load,swap
