import asyncio

import nats


async def main():
    nc = nats.NATS()

    await nc.connect(servers=["nats://localhost:4222"])

    await nc.publish("glances.test", b'A test')
    await nc.flush()


if __name__ == '__main__':
    asyncio.run(main())

# To run this test script, make sure you have a NATS server running locally.
