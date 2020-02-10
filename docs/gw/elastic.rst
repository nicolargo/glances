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

The stats are available through the elasticsearch API. For example, to
get the CPU system stats:

.. code-block:: console

    $ curl http://172.17.0.2:9200/glances/cpu/system
    {
        "_index": "glances",
        "_type": "cpu",
        "_id": "system",
        "_version": 28,
        "found": true,"
        _source": {
            "timestamp": "2016-02-04T14:11:02.362232",
            "value": "2.2"
        }
    }

.. _elasticsearch: https://pypi.org/project/elasticsearch/
