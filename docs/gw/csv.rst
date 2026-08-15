.. _csv:

CSV
===

It's possible to export stats to a CSV file.

.. code-block:: console

    $ glances --export csv --export-csv-file /tmp/glances.csv --quiet

CSV file description:

- first line: Stats description (header)
- others lines: Stats (data)

By default, data will be append any existing CSV file (if header are compliant).

If the header did not match with a previous one, an error is logged.

The --export-csv-overwrite tag should be used if you want to delete the existing CSV file when Glances starts.

It is possible to remove some exported data using the --disable-plugin tag:

  $ glances --export csv --export-csv-file /tmp/glances.csv --disable-plugin load,swap --quiet

or by only enable some plugins:

  $ glances --export csv --export-csv-file /tmp/glances.csv --disable-plugin all --enable-plugin cpu,mem,load --quiet
