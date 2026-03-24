---
paths:
  - "src/listening/**"
---

# Agent Pipeline

The system uses a **sequential agent pipeline** orchestrated by `src/listening/agents/part1/main_agent.py`:

1. **Agent 1** (`agent1.py`) — Blueprint/skeleton generator. Creates an `IELTSBlueprint` Pydantic model with scenario, speakers, question groups, and planned answer fields. This is the most complete agent with a detailed prompt.
2. **Agent 2** (`agent2.py`) — Question & answer writer. Takes the `IELTSBlueprint` from Agent 1 and generates 10 concrete questions, answers with distractors, and a full natural dialogue. Outputs an `IELTSQuestionSet` Pydantic model. Uses Cambridge distractor techniques (correction traps, spelling protocol, number confusion, decoy alternatives).
3. **Agent 3** (`agent3.py`) — TTS script generator. Takes the `IELTSQuestionSet` from Agent 2 and blueprint speaker info from Agent 1, and produces an `IELTSTTSScript` — a complete ordered list of speech and silence events matching the IELTS Part 1 audio structure. Uses semantic `SilenceType` labels (not hardcoded durations). Applies Qwen3-TTS text formatting (ellipsis for pauses, em-dash spelling sequences, filler preservation). The `to_events()` method converts the Pydantic output to the `[(speaker, text), (None, duration)]` tuple format consumed by the audio generator.
4. **Agent 4** (`agent4.py`) — Quality checker/validator. Validates IELTS compliance against Cambridge standards. Returns an `IELTSValidation` Pydantic model with `valid` (bool), `issues` (list of strings), and `summary`.

## Pipeline Execution

Agents use the OpenAI SDK (configured in `config.py`) via the `agents` framework (`await Runner.run()`). The pipeline is split into 4 stage functions in `main_agent.py`: `run_qna_stage`, `run_tts_stage`, `run_audio_stage`, `run_qa_stage`. A convenience wrapper `run_pipeline()` calls all 4 sequentially for standalone use. Each stage function accepts an `on_progress` callback. `run_audio_stage` calls `asyncio.to_thread(generate_and_upload_to_s3, ...)` to offload blocking GPU work. Prompts live in `prompts.py`.

## Timeouts & Retries

Each pipeline step runs with a timeout and auto-retry (up to `MAX_RETRIES=2`). Timeouts are configured via `AGENT_TIMEOUTS` in `main_agent.py`: agent1=3min, agent2=4min, agent3=3min, audio=60min, agent4=2min. On timeout, a status event is published and the step retries; on final failure, an error is raised.

## Data Models

Pydantic models in `agent1.py`: `IELTSBlueprint`, `QuestionGroup`, `PlannedAnswerField`, `Gender`, `QuestionType`. The blueprint always generates exactly 10 questions, uses British English, requires different speaker genders, and enforces IELTS Part 1 format (Group 1 is always form_completion, no MCQ in Part 1).

Pydantic models in `agent2.py`: `IELTSQuestionSet`, `Question`, `AnswerKeyEntry`, `DialogueLine`, `AnswerType`, `QuestionFormat`, `DistractorTechnique`, `Speaker`. The question set contains exactly 10 questions, 10 answer key entries (each with a distractor), and a full dialogue (35-50 lines) with Cambridge distractor techniques.

Pydantic models in `agent3.py`: `IELTSTTSScript`, `TTSEvent`, `EventType` (speech/silence), `SilenceType` (8 labels). `SILENCE_DURATIONS` maps silence labels to durations in seconds. `to_events()` converts the structured output to `[(speaker, text), (None, duration)]` tuples for the audio generator.

Pydantic models in `agent4.py`: `IELTSValidation` with `valid` (bool), `issues` (list[str]), `summary` (str). Validates structure, answer quality, dialogue quality, distractor correctness, and TTS script formatting.
