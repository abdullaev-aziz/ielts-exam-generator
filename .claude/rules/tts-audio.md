---
paths:
  - "src/audio/**"
---

# TTS Audio Generator

`src/audio/generator.py` has two public entry points:
- `_render_audio(script)` — private helper, renders TTS events to a numpy array in memory
- `generate_and_upload_to_s3(script, s3_key) → str` — renders in memory via `BytesIO`, uploads directly to S3 via `put_object`, returns the CDN URL. Called by `main_agent.py` — no local files written.

Uses Qwen3-TTS with voice cloning, speaker-specific voice design, silence trimming, and micro-pauses. TTS models are **lazy-loaded** on first use (not at import time) via `_ensure_initialized()` — importing the module does not allocate GPU memory.

## Generated Files

The pipeline no longer writes local WAV or JSON files. Audio is rendered in memory and uploaded directly to S3. The S3 key format is `dev/ielts/part1/ielts_part1_{YYYYMMDD_HHMMSS}.wav` — each run gets a unique timestamped name.

## narrator_ref.wav

Required asset committed to git. A short (3–10s) clean audio recording of a British narrator/examiner voice used to clone the narrator's timbre for all IELTS audio output. If you need to replace it:
1. Record or source a 3–10s clip of a clear, neutral British voice
2. Save as `narrator_ref.wav` in the project root
3. Optionally create `narrator_ref.txt` with the transcript of that clip (improves clone quality)

## TTS Text Formatting Rules

- Use `…` for hesitations, `—` for thought breaks, commas for breath points
- Reformat spelling sequences: `K-O-W-A-L-S-K-I` → `K — O — W — A — L — S — K — I`
- Preserve all fillers (um, er, erm) — critical for TTS naturalness
- Write all numbers as words; no SSML or markup tags
