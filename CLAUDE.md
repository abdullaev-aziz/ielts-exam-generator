# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered IELTS Listening Test Generator. Uses a multi-agent pipeline to generate realistic IELTS listening exams with structured blueprints, dialogue scripts, and TTS audio output. Currently Part 1 is implemented; Parts 2-4 are planned.

## Running the Code

```bash
# Activate virtual environment
source .venv/bin/activate

# REQUIRED: narrator_ref.wav must exist in the project root before running.
# It is a 3–10s clean audio sample of a British narrator voice used for voice cloning.
# See "narrator_ref.wav" section below.

# Run the full Part 1 pipeline — generates content AND audio in one command (requires GPU)
python "listening/agents/part1/main agent.py"
# Outputs: tts_events.json (backup) + ielts_part1.wav

# Retry audio generation from a saved JSON (skip agents, GPU only)
python ielts_audio_generator.py tts_events.json

# Run individual agents
python listening/agents/part1/agent1.py   # Blueprint generator
python listening/agents/part1/agent2.py   # Question writer
python listening/agents/part1/agent3.py   # TTS script generator
python listening/agents/part1/agent4.py   # Quality validator
```

### narrator_ref.wav

This file is a required asset committed to git. It is a short (3–10s) clean audio recording of a British narrator/examiner voice used to clone the narrator's timbre for all IELTS audio output. If you need to replace it:
1. Record or source a 3–10s clip of a clear, neutral British voice
2. Save as `narrator_ref.wav` in the project root
3. Optionally create `narrator_ref.txt` with the transcript of that clip (improves clone quality)

### Generated files (gitignored)

`*.wav` (except `narrator_ref.wav`) and `tts_events.json` are gitignored. They are produced by the pipeline and should not be committed.

## Architecture

The system uses a **sequential agent pipeline** orchestrated by `listening/agents/part1/main agent.py`:

1. **Agent 1** (`agent1.py`) — Blueprint/skeleton generator. Creates an `IELTSBlueprint` Pydantic model with scenario, speakers, question groups, and planned answer fields. This is the most complete agent with a detailed prompt.
2. **Agent 2** (`agent2.py`) — Question & answer writer. Takes the `IELTSBlueprint` from Agent 1 and generates 10 concrete questions, answers with distractors, and a full natural dialogue. Outputs an `IELTSQuestionSet` Pydantic model. Uses Cambridge distractor techniques (correction traps, spelling protocol, number confusion, decoy alternatives).
3. **Agent 3** (`agent3.py`) — TTS script generator. Takes the `IELTSQuestionSet` from Agent 2 and blueprint speaker info from Agent 1, and produces an `IELTSTTSScript` — a complete ordered list of speech and silence events matching the IELTS Part 1 audio structure. Uses semantic `SilenceType` labels (not hardcoded durations). Applies Qwen3-TTS text formatting (ellipsis for pauses, em-dash spelling sequences, filler preservation). The `to_events()` method converts the Pydantic output to the `[(speaker, text), (None, duration)]` tuple format consumed by the audio generator.
4. **Agent 4** (`agent4.py`) — Quality checker/validator. Validates IELTS compliance. (Stub.)

Agents use the OpenAI SDK (configured in `config.py`) via the `agents` framework (`await Runner.run()`). The pipeline is async — `main agent.py` runs via `asyncio.run(main())` and calls `asyncio.to_thread(generate_audio, ...)` to offload blocking GPU work without blocking the event loop. Prompts live in `prompts.py`.

**TTS audio generator** (`ielts_audio_generator.py`): Exposes `generate_audio(script: IELTSTTSScript, out_wav: str)` — called directly by `main agent.py` after the pipeline so no JSON round-trip is needed. Can also run standalone: `python ielts_audio_generator.py tts_events.json`. Uses Qwen3-TTS with voice cloning, speaker-specific voice design, silence trimming, and micro-pauses. TTS models are **lazy-loaded** on first use (not at import time) via `_ensure_initialized()` — importing the module does not allocate GPU memory.

## Key Configuration

- `listening/agents/part1/config.py` — API key (from `OPENAI_API_KEY` env var), model name (`gpt-5-mini-2025-08-07`), retry settings
- `.env` — Environment variables for API keys (gitignored)
- `listening/agents/part1/prompts.py` — All agent system prompts (Agents 1, 2, and 3 are populated)

## Data Models

Pydantic models in `agent1.py`: `IELTSBlueprint`, `QuestionGroup`, `PlannedAnswerField`, `Gender`, `QuestionType`. The blueprint always generates exactly 10 questions, uses British English, requires different speaker genders, and enforces IELTS Part 1 format (Group 1 is always form_completion, no MCQ in Part 1).

Pydantic models in `agent2.py`: `IELTSQuestionSet`, `Question`, `AnswerKeyEntry`, `DialogueLine`, `AnswerType`, `QuestionFormat`, `DistractorTechnique`, `Speaker`. The question set contains exactly 10 questions, 10 answer key entries (each with a distractor), and a full dialogue (35-50 lines) with Cambridge distractor techniques.

Pydantic models in `agent3.py`: `IELTSTTSScript`, `TTSEvent`, `EventType` (speech/silence), `SilenceType` (8 labels). `SILENCE_DURATIONS` maps silence labels to durations in seconds. `to_events()` converts the structured output to `[(speaker, text), (None, duration)]` tuples for the audio generator.

## Dependencies

Key packages: `openai`, `openai-agents` (agent orchestration framework), `qwen-tts`, `torch`, `soundfile`, `numpy`, `pydantic`. Python 3.13.3. Pinned versions are in `requirements.txt`.

```bash
pip install -r requirements.txt
```

Note: `torch==2.2.2` in `requirements.txt` is the CPU build. For GPU inference (required for TTS), install the matching CUDA build from [pytorch.org](https://pytorch.org/get-started/locally/) instead.

## Installed Skills

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
