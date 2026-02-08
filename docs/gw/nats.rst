.. _nats:

NATS
====

NATS is a message broker.

You can export statistics to a ``NATS`` server.

The connection should be defined in the Glances configuration file as
following:

.. code-block:: ini

    [nats]
    host=nats://localhost:4222
    prefix=glances

and run Glances with:

.. code-block:: console

    $ glances --export nats

Data model
-----------

Glances stats are published as JSON messagesto the following subjects:

    <prefix>.<plugin>

Example:

    CPU stats are published to glances.cpu

So a simple Python client will subscribe to this subject with:


    import asyncio

    import nats


    async def main():
        nc = nats.NATS()

        await nc.connect(servers=["nats://localhost:4222"])

        future = asyncio.Future()

        async def cb(msg):
            nonlocal future
            future.set_result(msg)

        await nc.subscribe("glances.cpu", cb=cb)

        # Wait for message to come in
        print("Waiting (max 30 seconds) for a message on 'glances' subject...")
        msg = await asyncio.wait_for(future, 30)
        print(msg.subject, msg.data)

    if __name__ == '__main__':
        asyncio.run(main())

To subscribe to all Glannces stats use wildcard:

        await nc.subscribe("glances.*", cb=cb)

