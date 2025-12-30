import asyncio

import nats


async def main():
    nc = nats.NATS()

    await nc.connect(servers=["nats://localhost:4222"])

    future = asyncio.Future()

    async def cb(msg):
        nonlocal future
        future.set_result(msg)

    await nc.subscribe("glances.*", cb=cb)

    # Wait for message to come in
    print("Waiting (max 30s) for a message on 'glances' subject...")
    msg = await asyncio.wait_for(future, 30)
    print(msg.subject, msg.data)

if __name__ == '__main__':
    asyncio.run(main())

# To run this test script, make sure you have a NATS server running locally.
