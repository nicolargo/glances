.. _elastic:

Elasticsearch
=============
.. note::
    You need to install the `elasticsearch`_ library on your system.

You can export statistics to an ``Elasticsearch`` server. The connection
should be defined in the Glances configuration file as following:

.. code-block:: ini

    [elasticsearch]
    host=localhost
    port=9200
    index=glances

and run Glances with:

.. code-block:: console

    $ glances --export elasticsearch

.. _elasticsearch: https://pypi.org/project/elasticsearch/
