import asyncio
import nats

async def main():
    nc = await nats.connect("nats://localhost:4222")
    print("✅ Publisher connected")

    # Publish a message
    await nc.publish("agent.task", b"Analyze this product description")
    print("📤 Message sent!")

    await nc.drain()

asyncio.run(main())