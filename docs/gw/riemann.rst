.. _riemann:

Riemann
=======

You can export statistics to a ``Riemann`` server (using TCP protocol).
The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [riemann]
    host=localhost
    port=5555

and run Glances with:

.. code-block:: console

    $ glances --export riemann
