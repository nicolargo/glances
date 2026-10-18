.. _elastic:

Elasticsearch
=============
.. note::
    You need to install the `elasticsearch`_ library on your system.

You can export statistics to an ``Elasticsearch`` server. The connection
should be defined in the Glances configuration file as following:

.. code-block:: ini

    [elasticsearch]
    # https or http
    scheme=http
    host=localhost
    port=9200
    index=glances

All the keys are mandatory. Stats are stored in a daily index named
``<index>-YYYY.MM.DD``.

and run Glances with:

.. code-block:: console

    $ glances --export elasticsearch

.. _elasticsearch: https://pypi.org/project/elasticsearch/
