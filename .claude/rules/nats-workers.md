---
paths:
  - "src/workers/**"
---

# NATS Workers

The primary runtime mode. The pipeline is split into 4 independent stage workers that chain through JetStream subjects. Different workers can run on different devices.

## Worker Components

- `src/workers/common.py` — **shared NATS infrastructure**. Contains stream definitions, `ensure_streams()`, `make_progress_callback()`, and the generic `run_worker()` loop. All workers and the dispatcher import from here — no duplicated stream/loop code.
- `src/common/log_config.py` — shared logging setup. All processes call `setup_logging()` at startup for consistent structured console output.
- `src/workers/subscriber.py` — **dispatcher only**. Subscribes to `ielts.generate`; responds with `{"job_id": "..."}` and publishes `{"job_id": "..."}` to `ielts.stage.qna`. No agents run here.
- `src/workers/worker_qna.py` — durable pull consumer on `ielts.stage.qna`. Runs Agent 1 + Agent 2 (`ack_wait=600s`). Publishes blueprint + question_set to `ielts.stage.tts`.
- `src/workers/worker_tts.py` — durable pull consumer on `ielts.stage.tts`. Runs Agent 3 (`ack_wait=300s`). Publishes tts_script to `ielts.stage.audio`.
- `src/workers/worker_audio.py` — durable pull consumer on `ielts.stage.audio`. Runs TTS + S3 upload (`ack_wait=3600s` for long GPU jobs). Publishes cdn_url to `ielts.stage.qa`.
- `src/workers/worker_qa.py` — durable pull consumer on `ielts.stage.qa`. Runs Agent 4 (`ack_wait=300s`). Publishes final `validation` event with `done: true` to `ielts.result.{job_id}`.
- `src/workers/publisher.py` — sends a request to `ielts.generate`, then subscribes via JetStream ordered consumer (replays all stored events from the beginning). Resume: re-run with no args (queries the last job_id from the `IELTS_RESULTS` stream) or pass an explicit job_id.

## Streams & Delivery

All workers create both streams on startup (idempotent via `workers.common.ensure_streams()`): `IELTS_STAGES` on `ielts.stage.*` and `IELTS_RESULTS` on `ielts.result.*`, both with 2-hour retention. Durable consumers provide at-least-once delivery — crashed workers get redelivery on restart.

## Progress Events

Event types: `status`, `questions`, `audio`, `validation`, `error`. Final event always includes `"done": true`.
