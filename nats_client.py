import asyncio
import json
import nats


async def main():
    nc = await nats.connect("nats://localhost:4222")

    response = await nc.request("ielts.generate", b"{}", timeout=5)
    job = json.loads(response.data)
    job_id = job["job_id"]
    print(f"Job started: {job_id}")
    print(f"Subscribing to ielts.result.{job_id} ...\n")

    done = asyncio.Event()

    async def handle_progress(msg):
        data = json.loads(msg.data)
        type_ = data.get("type")
        if type_ == "status":
            print(f"[status] {data.get('data', {}).get('message')}")
        elif type_ == "questions":
            print(f"[questions] Questions and answers received")
            print(json.dumps(data.get("data", {}), indent=2))
        elif type_ == "audio":
            print(f"[audio] Audio ready: {data.get('data', {}).get('cdn_url')}")
        elif type_ == "validation":
            print(f"[validation] QA result: {data.get('data', {}).get('result')}")
        elif type_ == "error":
            print(f"[error] Pipeline failed: {data.get('error')}")
        if data.get("done"):
            done.set()

    sub = await nc.subscribe(f"ielts.result.{job_id}", cb=handle_progress)
    await done.wait()
    await sub.unsubscribe()
    await nc.close()


asyncio.run(main())
