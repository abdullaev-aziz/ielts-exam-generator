# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered IELTS Listening Test Generator. Uses a multi-agent pipeline to generate realistic IELTS listening exams with structured blueprints, dialogue scripts, and TTS audio output. Currently Part 1 is implemented; Parts 2-4 are planned.

## Running the Code

```bash
# Activate virtual environment
source .venv/bin/activate

# One-time setup (makes src/ packages importable):
pip install -e .

# REQUIRED: narrator_ref.wav must exist in the project root before running.
# It is a 3–10s clean audio sample of a British narrator voice used for voice cloning.
# See "narrator_ref.wav" section below.

# --- NATS mode (primary way to run) ---
# Start NATS server in Docker (JetStream enabled, persisted volume):
docker compose -f nats.yml up -d

# Stop NATS server:
docker compose -f nats.yml down

# Start dispatcher (receives ielts.generate, dispatches to stage workers):
python -m workers.subscriber        # or: ielts-dispatcher

# Start stage workers — each can run on a different device:
python -m workers.worker_qna        # or: ielts-worker-qna   (needs: OpenAI API key)
python -m workers.worker_tts        # or: ielts-worker-tts   (needs: OpenAI API key)
python -m workers.worker_audio      # or: ielts-worker-audio  (needs: GPU + S3 credentials)
python -m workers.worker_qa         # or: ielts-worker-qa    (needs: OpenAI API key)

# Send a job and stream results:
python -m workers.publisher          # or: ielts-publisher
# Resumes the last incomplete job from NATS; starts a new one if the last job finished or none exist.

# Resume a specific job (replay all events from the beginning):
python -m workers.publisher <job_id>
# Events are persisted in JetStream for 2 hours.

# --- Standalone pipeline (no NATS) ---
# run_pipeline() in main_agent.py can be called directly from Python:
#   from listening.agents.part1.main_agent import run_pipeline
#   cdn_url = asyncio.run(run_pipeline())

# Run individual agents
python src/listening/agents/part1/agent1.py   # Blueprint generator
python src/listening/agents/part1/agent2.py   # Question writer
python src/listening/agents/part1/agent3.py   # TTS script generator
python src/listening/agents/part1/agent4.py   # Quality validator
```

### narrator_ref.wav

This file is a required asset committed to git. It is a short (3–10s) clean audio recording of a British narrator/examiner voice used to clone the narrator's timbre for all IELTS audio output. If you need to replace it:
1. Record or source a 3–10s clip of a clear, neutral British voice
2. Save as `narrator_ref.wav` in the project root
3. Optionally create `narrator_ref.txt` with the transcript of that clip (improves clone quality)

### Generated files

The pipeline no longer writes local WAV or JSON files. Audio is rendered in memory and uploaded directly to S3. The S3 key format is `dev/ielts/part1/ielts_part1_{YYYYMMDD_HHMMSS}.wav` — each run gets a unique timestamped name.

## Architecture

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

The system uses a **sequential agent pipeline** orchestrated by `src/listening/agents/part1/main_agent.py`:

1. **Agent 1** (`agent1.py`) — Blueprint/skeleton generator. Creates an `IELTSBlueprint` Pydantic model with scenario, speakers, question groups, and planned answer fields. This is the most complete agent with a detailed prompt.
2. **Agent 2** (`agent2.py`) — Question & answer writer. Takes the `IELTSBlueprint` from Agent 1 and generates 10 concrete questions, answers with distractors, and a full natural dialogue. Outputs an `IELTSQuestionSet` Pydantic model. Uses Cambridge distractor techniques (correction traps, spelling protocol, number confusion, decoy alternatives).
3. **Agent 3** (`agent3.py`) — TTS script generator. Takes the `IELTSQuestionSet` from Agent 2 and blueprint speaker info from Agent 1, and produces an `IELTSTTSScript` — a complete ordered list of speech and silence events matching the IELTS Part 1 audio structure. Uses semantic `SilenceType` labels (not hardcoded durations). Applies Qwen3-TTS text formatting (ellipsis for pauses, em-dash spelling sequences, filler preservation). The `to_events()` method converts the Pydantic output to the `[(speaker, text), (None, duration)]` tuple format consumed by the audio generator.
4. **Agent 4** (`agent4.py`) — Quality checker/validator. Validates IELTS compliance against Cambridge standards. Returns an `IELTSValidation` Pydantic model with `valid` (bool), `issues` (list of strings), and `summary`.

Agents use the OpenAI SDK (configured in `config.py`) via the `agents` framework (`await Runner.run()`). The pipeline is split into 4 stage functions in `main_agent.py`: `run_qna_stage`, `run_tts_stage`, `run_audio_stage`, `run_qa_stage`. A convenience wrapper `run_pipeline()` calls all 4 sequentially for standalone use. Each stage function accepts an `on_progress` callback. `run_audio_stage` calls `asyncio.to_thread(generate_and_upload_to_s3, ...)` to offload blocking GPU work. Prompts live in `prompts.py`.

**Package structure**: The `src/` directory contains all Python packages. `listening/`, `audio/`, `workers/`, and `common/` are proper Python packages with `__init__.py` files. All imports are absolute (e.g., `from listening.agents.part1.config import MODEL`, `from workers.common import run_worker`). No `sys.path` hacks.

**Logging**: All modules use Python's `logging` module (no `print()` for operational output). `common.log_config.setup_logging()` configures structured console output. Logger names follow the `ielts.*` namespace (`ielts.pipeline`, `ielts.audio`, `ielts.nats`, `ielts.dispatcher`, `ielts.publisher`).

Each pipeline step runs with a timeout and auto-retry (up to `MAX_RETRIES=2`). Timeouts are configured via `AGENT_TIMEOUTS` in `main_agent.py`: agent1=3min, agent2=4min, agent3=3min, audio=60min, agent4=2min. On timeout, a status event is published and the step retries; on final failure, an error is raised.

**NATS interface**: The primary runtime mode. The pipeline is split into 4 independent stage workers that chain through JetStream subjects. Different workers can run on different devices.

- `src/workers/common.py` — **shared NATS infrastructure**. Contains stream definitions, `ensure_streams()`, `make_progress_callback()`, and the generic `run_worker()` loop. All workers and the dispatcher import from here — no duplicated stream/loop code.
- `src/common/log_config.py` — shared logging setup. All processes call `setup_logging()` at startup for consistent structured console output.
- `src/workers/subscriber.py` — **dispatcher only**. Subscribes to `ielts.generate`; responds with `{"job_id": "..."}` and publishes `{"job_id": "..."}` to `ielts.stage.qna`. No agents run here.
- `src/workers/worker_qna.py` — durable pull consumer on `ielts.stage.qna`. Runs Agent 1 + Agent 2 (`ack_wait=600s`). Publishes blueprint + question_set to `ielts.stage.tts`.
- `src/workers/worker_tts.py` — durable pull consumer on `ielts.stage.tts`. Runs Agent 3 (`ack_wait=300s`). Publishes tts_script to `ielts.stage.audio`.
- `src/workers/worker_audio.py` — durable pull consumer on `ielts.stage.audio`. Runs TTS + S3 upload (`ack_wait=3600s` for long GPU jobs). Publishes cdn_url to `ielts.stage.qa`.
- `src/workers/worker_qa.py` — durable pull consumer on `ielts.stage.qa`. Runs Agent 4 (`ack_wait=300s`). Publishes final `validation` event with `done: true` to `ielts.result.{job_id}`.
- `src/workers/publisher.py` — sends a request to `ielts.generate`, then subscribes via JetStream ordered consumer (replays all stored events from the beginning). Resume: re-run with no args (queries the last job_id from the `IELTS_RESULTS` stream) or pass an explicit job_id.
- All workers create both streams on startup (idempotent via `workers.common.ensure_streams()`): `IELTS_STAGES` on `ielts.stage.*` and `IELTS_RESULTS` on `ielts.result.*`, both with 2-hour retention. Durable consumers provide at-least-once delivery — crashed workers get redelivery on restart.
- Progress event types: `status`, `questions`, `audio`, `validation`, `error`. Final event always includes `"done": true`.

**TTS audio generator** (`src/audio/generator.py`): Two public entry points:
- `_render_audio(script)` — private helper, renders TTS events to a numpy array in memory
- `generate_and_upload_to_s3(script, s3_key) → str` — renders in memory via `BytesIO`, uploads directly to S3 via `put_object`, returns the CDN URL. Called by `main_agent.py` — no local files written.

Uses Qwen3-TTS with voice cloning, speaker-specific voice design, silence trimming, and micro-pauses. TTS models are **lazy-loaded** on first use (not at import time) via `_ensure_initialized()` — importing the module does not allocate GPU memory.

## Key Configuration

- `src/listening/agents/part1/config.py` — API key (from `OPENAI_API_KEY` env var), model name (`gpt-5.4-2026-03-05`)
- `.env` — Environment variables for API keys and S3 config (gitignored). Required S3 vars:
  - `S3_ENDPOINT_URL` — custom S3-compatible endpoint
  - `S3_REGION` — storage region
  - `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` — credentials
  - `S3_BUCKET_NAME` — target bucket
  - `S3_BASE_FOLDER` — key prefix (default: `dev/ielts`)
  - `S3_CDN_BASE_URL` — CDN base for returned URLs
- `src/listening/agents/part1/prompts.py` — All agent system prompts (Agents 1–4 are populated)
- `pyproject.toml` — Project packaging config. Defines CLI entry points (`ielts-dispatcher`, `ielts-publisher`, `ielts-worker-*`).

## Data Models

Pydantic models in `agent1.py`: `IELTSBlueprint`, `QuestionGroup`, `PlannedAnswerField`, `Gender`, `QuestionType`. The blueprint always generates exactly 10 questions, uses British English, requires different speaker genders, and enforces IELTS Part 1 format (Group 1 is always form_completion, no MCQ in Part 1).

Pydantic models in `agent2.py`: `IELTSQuestionSet`, `Question`, `AnswerKeyEntry`, `DialogueLine`, `AnswerType`, `QuestionFormat`, `DistractorTechnique`, `Speaker`. The question set contains exactly 10 questions, 10 answer key entries (each with a distractor), and a full dialogue (35-50 lines) with Cambridge distractor techniques.

Pydantic models in `agent3.py`: `IELTSTTSScript`, `TTSEvent`, `EventType` (speech/silence), `SilenceType` (8 labels). `SILENCE_DURATIONS` maps silence labels to durations in seconds. `to_events()` converts the structured output to `[(speaker, text), (None, duration)]` tuples for the audio generator.

Pydantic models in `agent4.py`: `IELTSValidation` with `valid` (bool), `issues` (list[str]), `summary` (str). Validates structure, answer quality, dialogue quality, distractor correctness, and TTS script formatting.

## Dependencies

Key packages: `openai`, `openai-agents` (agent orchestration framework), `qwen-tts`, `torch`, `soundfile`, `numpy`, `pydantic`, `boto3` (S3 uploads), `nats-py` (NATS messaging), `python-dotenv` (env loading). Python 3.13.3. Pinned versions are in `requirements.txt`.

All dependencies including `nats-py` and `python-dotenv` are listed in `requirements.txt`.

```bash
pip install -e .               # installs project + dependencies from pyproject.toml
# or:
pip install -r requirements.txt  # dependencies only (no editable install)
```

Note: `torch==2.2.2` in `requirements.txt` is the CPU build. For GPU inference (required for TTS), install the matching CUDA build from [pytorch.org](https://pytorch.org/get-started/locally/) instead.

## Installed Skills

### NATS (`nats`)

Location: `.agents/skills/nats/`

Core NATS and JetStream reference — subjects, request/reply, persistence, consumers. Python, Node.js, Go, and Java examples. Also covers security (TLS, auth) and clustering.

**Usage**: Reference `SKILL.md` for quick patterns and `advanced.md` for JetStream consumer setup, security config, and clustering when working on `src/workers/subscriber.py`, `src/workers/publisher.py`, or any NATS-related code.

### OpenAI Agents SDK Guidelines (`openai-agents-sdk-guidelines`)

Location: `.agents/skills/openai-agents-sdk-guidelines/`

30+ implementation rules for the OpenAI Agents Python SDK, organized by priority:

| Priority | Category | Prefix | Key Rules |
|----------|----------|--------|-----------|
| 1 (CRITICAL) | Agent Design | `agent-` | basic-config, output-type, dynamic-instructions, tool-choice, tool-use-behavior |
| 2 (CRITICAL) | Multi-Agent Patterns | `multi-agent-` | manager-pattern, handoffs, handoff-description, handoff-inputs, input-filter |
| 3 (HIGH) | Tools | `tool-` | function-decorator, docstrings, context-parameter, error-handling, agents-as-tools |
| 4 (MEDIUM-HIGH) | Guardrails | `guardrail-` | input-validation, output-validation, execution-mode |
| 5 (MEDIUM) | Context Management | `context-` | local-context, type-consistency, llm-visibility |
| 6 (MEDIUM) | Running Agents | `runner-` | async-vs-sync, max-turns, run-config, exception-handling |
| 7 (MEDIUM) | Conversation Mgmt | `conversation-` | manual-history, sessions, server-managed |
| 8 (LOW-MEDIUM) | Streaming | `streaming-` | run-streamed, item-events |

**Usage**: When working on agent code, read the relevant rule file at `.agents/skills/openai-agents-sdk-guidelines/rules/<prefix>-<description>.md` for correct/incorrect examples and best practices.

### Qwen3-TTS Skills (`qwen3-tts-skills`)

Location: `.agents/skills/qwen3-tts-skills/`

CLI and Python API reference for Qwen3-TTS model usage — CustomVoice, VoiceDesign, VoiceClone modes, batch dubbing workflow.

**Usage**: Reference `references/python_api.md` for Python API examples and `scripts/` for CLI tools.

### Qwen3-TTS Text Formatting (`qwen3-tts-text-formatting`)

Location: `.agents/skills/qwen3-tts-text-formatting/`

Best practices for formatting spoken text to produce natural, realistic Qwen3-TTS audio — specifically tuned for IELTS Listening test generation.

Key rules:
- Use `…` for hesitations, `—` for thought breaks, commas for breath points
- Reformat spelling sequences: `K-O-W-A-L-S-K-I` → `K — O — W — A — L — S — K — I`
- Preserve all fillers (um, er, erm) — critical for TTS naturalness
- Write all numbers as words; no SSML or markup tags

**Usage**: Reference when writing or reviewing any TTS `text` field or `instruct` voice instruction prompt.

### Superpowers (`superpowers`)

Location: `.agents/skills/brainstorming/`, `.agents/skills/writing-plans/`, `.agents/skills/executing-plans/`, etc.

14 workflow skills from the [superpowers plugin](https://github.com/obra/superpowers-marketplace), installed locally into `.agents/skills/`. These are **not** loaded via the plugin system — skills live directly in the repo.

| Skill | When to use |
|-------|-------------|
| `using-superpowers` | Start of any conversation — establishes skill discovery |
| `brainstorming` | Before any creative work / new feature |
| `writing-plans` | Before touching code on multi-step tasks |
| `executing-plans` | Executing a written plan with review checkpoints |
| `subagent-driven-development` | Parallel independent tasks in current session |
| `dispatching-parallel-agents` | 2+ independent tasks for parallel agents |
| `test-driven-development` | Before writing implementation code |
| `systematic-debugging` | Before proposing fixes for any bug/failure |
| `verification-before-completion` | Before claiming work is complete or tests pass |
| `using-git-worktrees` | Isolated feature work / before executing plans |
| `finishing-a-development-branch` | When implementation is complete, deciding how to integrate |
| `requesting-code-review` | After completing a feature or before merging |
| `receiving-code-review` | When processing code review feedback |
| `writing-skills` | When creating or editing skills |
