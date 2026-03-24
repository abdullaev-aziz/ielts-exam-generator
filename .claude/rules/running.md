# Running the Code

```bash
# Activate virtual environment
source .venv/bin/activate

# One-time setup (makes src/ packages importable):
pip install -e .

# REQUIRED: narrator_ref.wav must exist in the project root before running.
```

## NATS mode (primary)

```bash
# Start/stop NATS server in Docker (JetStream enabled, persisted volume):
docker compose -f nats.yml up -d
docker compose -f nats.yml down

# Start dispatcher:
python -m workers.subscriber        # or: ielts-dispatcher

# Start stage workers (each can run on a different device):
python -m workers.worker_qna        # or: ielts-worker-qna   (needs: OpenAI API key)
python -m workers.worker_tts        # or: ielts-worker-tts   (needs: OpenAI API key)
python -m workers.worker_audio      # or: ielts-worker-audio  (needs: GPU + S3 credentials)
python -m workers.worker_qa         # or: ielts-worker-qa    (needs: OpenAI API key)

# Send a job and stream results:
python -m workers.publisher          # or: ielts-publisher
# Resumes the last incomplete job; starts new one if last job finished or none exist.

# Resume a specific job (replay all events from the beginning):
python -m workers.publisher <job_id>
# Events are persisted in JetStream for 2 hours.
```

## Standalone pipeline (no NATS)

```bash
# run_pipeline() in main_agent.py can be called directly from Python:
#   from listening.agents.part1.main_agent import run_pipeline
#   cdn_url = asyncio.run(run_pipeline())

# Run individual agents:
python src/listening/agents/part1/agent1.py   # Blueprint generator
python src/listening/agents/part1/agent2.py   # Question writer
python src/listening/agents/part1/agent3.py   # TTS script generator
python src/listening/agents/part1/agent4.py   # Quality validator
```

## Dependencies

Key packages: `openai`, `openai-agents`, `qwen-tts`, `torch`, `soundfile`, `numpy`, `pydantic`, `boto3`, `nats-py`, `python-dotenv`. Python 3.13.3. Pinned versions in `requirements.txt`.

```bash
pip install -e .               # installs project + dependencies from pyproject.toml
pip install -r requirements.txt  # dependencies only (no editable install)
```

Note: `torch==2.2.2` in `requirements.txt` is the CPU build. For GPU inference (required for TTS), install the matching CUDA build from pytorch.org instead.
