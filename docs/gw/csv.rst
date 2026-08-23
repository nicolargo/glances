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

If the column set changes — at startup, because the header did not match a previous
one, or mid-run, because a network interface, disk or container appeared or
disappeared — a warning is logged and Glances rolls over to a new file rather than
losing data. The new file is named after the original path with ``-NNN`` inserted
before the extension, zero-padded to 3 digits and starting at ``001``
(``/tmp/glances.csv`` becomes ``/tmp/glances-001.csv``, then ``/tmp/glances-002.csv``,
and so on), and its first line is the new header. The --export-csv-overwrite tag
governs what happens if the rotation target already exists: overwrite it, or (default)
skip to the next free index.

The --export-csv-overwrite tag should be used if you want to delete the existing CSV file when Glances starts.

It is possible to remove some exported data using the --disable-plugin tag:

  $ glances --export csv --export-csv-file /tmp/glances.csv --disable-plugin load,swap --quiet

or by only enable some plugins:

  $ glances --export csv --export-csv-file /tmp/glances.csv --disable-plugin all --enable-plugin cpu,mem,load --quiet
