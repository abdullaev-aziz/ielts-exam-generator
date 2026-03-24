# Logging Conventions

- All modules use Python's `logging` module — no `print()` for operational output
- `common.log_config.setup_logging()` configures structured console output
- Logger names follow the `ielts.*` namespace:
  - `ielts.pipeline` — main agent pipeline
  - `ielts.audio` — TTS rendering and S3 upload
  - `ielts.nats` — NATS connection and messaging
  - `ielts.dispatcher` — dispatcher/subscriber
  - `ielts.publisher` — publisher/client
- Never log secrets (API keys, S3 credentials, tokens)
