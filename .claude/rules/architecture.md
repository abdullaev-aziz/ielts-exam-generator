# Architecture

The project uses a `src/` layout with `pyproject.toml` for packaging. Install with `pip install -e .`.

```
src/
├── listening/agents/part1/     # Agent pipeline
│   ├── config.py, prompts.py   # Configuration & prompts
│   ├── agent1-4.py             # Individual agents
│   └── main_agent.py           # Pipeline orchestrator
├── audio/
│   └── generator.py            # TTS rendering + S3 upload
├── workers/                    # NATS workers & dispatcher
│   ├── common.py               # Shared NATS infrastructure
│   ├── subscriber.py           # Dispatcher
│   ├── publisher.py            # Client
│   └── worker_*.py             # Stage workers
└── common/
    └── log_config.py           # Shared logging setup
```

## Package Structure

The `src/` directory contains all Python packages. `listening/`, `audio/`, `workers/`, and `common/` are proper Python packages with `__init__.py` files. All imports are absolute (e.g., `from listening.agents.part1.config import MODEL`, `from workers.common import run_worker`). No `sys.path` hacks.

## Key Configuration

- `src/listening/agents/part1/config.py` — API key (from `OPENAI_API_KEY` env var), model name (`gpt-5.4-2026-03-05`)
- `.env` — Environment variables for API keys, NATS, and S3 config (gitignored). Required NATS var:
  - `NATS_URL` — NATS server URL (e.g. `nats://localhost:4222`)
- Required S3 vars:
  - `S3_ENDPOINT_URL` — custom S3-compatible endpoint
  - `S3_REGION` — storage region
  - `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` — credentials
  - `S3_BUCKET_NAME` — target bucket
  - `S3_BASE_FOLDER` — key prefix (default: `dev/ielts`)
  - `S3_CDN_BASE_URL` — CDN base for returned URLs
- `src/listening/agents/part1/prompts.py` — All agent system prompts (Agents 1–4 are populated)
- `pyproject.toml` — Project packaging config. Defines CLI entry points (`ielts-dispatcher`, `ielts-publisher`, `ielts-worker-*`).
