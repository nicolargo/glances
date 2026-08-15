import asyncio

import nats


async def main():
    duration = 30
    subject = "glances.*"

    nc = nats.NATS()

    await nc.connect(servers=["nats://localhost:4222"])

    future = asyncio.Future()

    async def cb(msg):
        subject = msg.subject
        reply = msg.reply
        data = msg.data.decode()
        print(f"Received a message on '{subject} {reply}': {data}")

    print(f"Receiving message from {subject} during {duration} seconds...")
    await nc.subscribe(subject, cb=cb)
    await asyncio.wait_for(future, duration)

    await nc.close()


if __name__ == '__main__':
    asyncio.run(main())

# To run this test script, make sure you have a NATS server running locally.
