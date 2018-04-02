.. _restful:

RESTful
=======

You can export statistics to a ``RESTful`` JSON server. All the available stats
will be exported in one big (~15 KB) POST request to the RESTful endpoint.

The RESTful endpoint should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [restful]
    # Configuration for the --export-restful option
    # Example, export to http://localhost:6789/
    host=localhost
    port=6789
    protocol=http
    path=/

URL Syntax:

.. code-block:: ini

    http://localhost:6789/
    |      |         |   |
    |      |         |   path
    |      |         port
    |      host
    protocol

and run Glances with:

.. code-block:: console

    $ glances --export restful

Glances will generate stats as a big JSON dictionary (see example `here`_).


.. _here: https://pastebin.com/7U3vXqvF
