from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().with_name(".env"))

import asyncio
import json
import traceback
import uuid
import nats

from listening.agents.part1.main_agent import run_pipeline


async def main():
    nc = await nats.connect("nats://localhost:4222")

    async def handle_generate(msg):
        job_id = str(uuid.uuid4())
        await msg.respond(json.dumps({"job_id": job_id}).encode())
        asyncio.create_task(run_job(nc, job_id))

    await nc.subscribe("ielts.generate", cb=handle_generate)
    print("IELTS server listening on 'ielts.generate'... (Ctrl+C to stop)")

    try:
        await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

    await nc.close()


async def run_job(nc, job_id):
    result_subject = f"ielts.result.{job_id}"

    async def publish(type_, data, done=False):
        msg = {"type": type_, "job_id": job_id, "data": data}
        if done:
            msg["done"] = True
        await nc.publish(result_subject, json.dumps(msg).encode())

    try:
        await run_pipeline(on_progress=publish)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[job {job_id}] ERROR:\n{tb}")
        await nc.publish(result_subject, json.dumps({
            "type": "error",
            "job_id": job_id,
            "error": str(e),
            "done": True,
        }).encode())


asyncio.run(main())
