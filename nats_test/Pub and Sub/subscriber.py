import asyncio
import nats

async def main():
    # Connect to NATS server
    nc = await nats.connect("nats://localhost:4222")
    print("✅ Subscriber connected")

    # Define message handler
    async def handler(msg):
        data = msg.data.decode()
        print(f"📨 Received on [{msg.subject}]: {data}")

    # Subscribe to subject
    await nc.subscribe("agent.task", cb=handler)
    print("👂 Listening on 'agent.task' ...")

    # Keep alive
    await asyncio.sleep(30)
    await nc.drain()

asyncio.run(main())