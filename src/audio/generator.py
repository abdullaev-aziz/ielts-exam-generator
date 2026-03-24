"""IELTS audio generator — renders TTS events to WAV and uploads to S3.

Public entry points:
- ``generate_and_upload_to_s3(script, s3_key) -> str``  (CDN URL)
- ``_render_audio(script) -> (np.ndarray, int)``        (raw audio + sample rate)

TTS models are lazy-loaded on first use via ``_ensure_initialized()``.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Any

import boto3
import numpy as np
import soundfile as sf
import torch
from botocore.config import Config
from qwen_tts import Qwen3TTSModel

from listening.agents.part1.agent3 import IELTSTTSScript

logger = logging.getLogger("ielts.audio")

# ── Model configuration ──────────────────────────────────────────────────────

PROJECT_ROOT = str(Path(__file__).resolve().parents[2])
VOICE_DESIGN_MODEL_ID = os.getenv("QWEN3_TTS_VOICE_DESIGN_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
VOICE_CLONE_MODEL_ID = os.getenv("QWEN3_TTS_VOICE_CLONE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
NARRATOR_REF_AUDIO = os.getenv("QWEN3_TTS_NARRATOR_REF_AUDIO", "narrator_ref.wav")
NARRATOR_REF_TEXT = os.getenv("QWEN3_TTS_NARRATOR_REF_TEXT", """You will hear four different recordings.
                                                                And vou will have to answer questions on what you hear. There will be
                                                                time for you to read the instructions and questions. And you will have
                                                                a chance to check your work. You will hear each recording once only.
                                                                The test is in four parts. At the end of the test, you will be given two
                                                                minutes to check all of your answers""")

REFERENCE_TEXT = "Hello, this is a test. Now you are hearring me."

# Micro-pauses for realism (kept short between adjacent speech turns)
PAUSE_TURN = 0.25
PAUSE_NARR = 0.30

# Speaker voice design instructions
INSTR: dict[str, str] = {
    "MAN": """gender: Male.
    pitch: Mid-range, slightly deep.
    speed: Slightly slowed (0.92x), natural conversational pace with gentle pauses for thought.
    volume: Balanced, relaxed.
    age: Young Adult.
    clarity: High.
    fluency: High, with natural flow.
    accent: British.
    texture: Warm, natural.
    emotion: Friendly, engaged.
    tone: Casual yet thoughtful, as if discussing ideas with a close friend.
    personality: Approachable, genuine, conversational.
    """,
    "SPEAKER": """gender: Male. pitch: Low. speed: Normal (slower for numbers and letters). volume: Strong. age: Middle-aged. clarity: Very High. fluency: Very High. accent: Neutral British. texture: Rich. emotion: Authoritative. tone: Confident. personality: Commanding.""",
    "WOMAN": """
    gender: Female.
    pitch: Mid-range.
    speed: Slightly slowed (0.92x), natural conversational pace with gentle pauses for thought.
    volume: Balanced, intimate.
    age: Young Adult.
    clarity: High.
    fluency: High, with natural flow.
    accent: British.
    texture: Warm, natural.
    emotion: Friendly, engaged.
    tone: Casual yet thoughtful, as if sharing ideas with a close friend.
    personality: Approachable, genuine, conversational.
    """,
}

NARRATOR = "NARRATOR"
MAN = "MAN"
WOMAN = "WOMAN"

# ── Lazy-loaded globals ──────────────────────────────────────────────────────

voice_design_model: Qwen3TTSModel | None = None
voice_clone_model: Qwen3TTSModel | None = None
reference_prompts: dict[str, Any] | None = None


DEVICE = "cuda:0" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if DEVICE.startswith("cuda") else torch.float32


def load_tts_model(model_id: str) -> Qwen3TTSModel:
    """Load a Qwen3-TTS model from HuggingFace."""
    logger.info("Loading TTS model %s on %s (%s)", model_id, DEVICE, DTYPE)
    return Qwen3TTSModel.from_pretrained(
        model_id,
        dtype=DTYPE,
        device_map=DEVICE,
        attn_implementation="flash_attention_2" if DEVICE.startswith("cuda") else "eager",
    )


def resolve_project_path(path: str) -> str:
    """Resolve *path* relative to PROJECT_ROOT if not already absolute."""
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def build_reference_assets() -> dict[str, Any]:
    """Generate reusable voice clone prompts for NARRATOR, MAN, and WOMAN."""
    logger.info("Generating reference voices…")
    prompts: dict[str, Any] = {}

    for speaker in [NARRATOR, WOMAN, MAN]:
        if speaker == NARRATOR:
            narrator_ref_audio = resolve_project_path(NARRATOR_REF_AUDIO)
            if not os.path.exists(narrator_ref_audio):
                raise FileNotFoundError(
                    f"Narrator reference audio not found: {narrator_ref_audio}. "
                    "Place your sample as narrator_ref.wav in the project root, "
                    "or set QWEN3_TTS_NARRATOR_REF_AUDIO to its path."
                )

            ref_text = NARRATOR_REF_TEXT.strip()
            narrator_ref_text_path = resolve_project_path("narrator_ref.txt")
            if not ref_text and os.path.exists(narrator_ref_text_path):
                with open(narrator_ref_text_path, "r", encoding="utf-8") as f:
                    ref_text = f.read().strip()

            use_xvector_only = not bool(ref_text)
            prompts[speaker] = voice_clone_model.create_voice_clone_prompt(
                ref_audio=narrator_ref_audio,
                ref_text=ref_text if ref_text else None,
                x_vector_only_mode=use_xvector_only,
            )
            mode = "x-vector only" if use_xvector_only else "full clone"
            logger.info("  Prepared reusable prompt for %s from %s (%s)", speaker, narrator_ref_audio, mode)
            continue

        wavs, sr = voice_design_model.generate_voice_design(
            text=REFERENCE_TEXT,
            language="English",
            instruct=INSTR[speaker],
            do_sample=False,
        )
        prompts[speaker] = voice_clone_model.create_voice_clone_prompt(
            ref_audio=(wavs[0], sr),
            ref_text=REFERENCE_TEXT,
            x_vector_only_mode=False,
        )
        logger.info("  Prepared reusable prompt for %s", speaker)

    return prompts


def _ensure_initialized() -> None:
    """Lazy-load TTS models and build reference assets on first call."""
    global voice_design_model, voice_clone_model, reference_prompts
    if reference_prompts is not None:
        return
    voice_design_model = load_tts_model(VOICE_DESIGN_MODEL_ID)
    voice_clone_model = load_tts_model(VOICE_CLONE_MODEL_ID)
    reference_prompts = build_reference_assets()


def tts_line(text: str, speaker: str) -> tuple[np.ndarray, int]:
    """Generate speech with a fixed speaker reference for stable voice consistency."""
    _ensure_initialized()
    if speaker not in reference_prompts:
        raise ValueError(f"Unknown speaker: {speaker}")

    wavs, sr = voice_clone_model.generate_voice_clone(
        text=text,
        language="English",
        voice_clone_prompt=reference_prompts[speaker],
        do_sample=False,
    )
    return wavs[0], sr


def silence(sr: int, sec: float) -> np.ndarray:
    """Generate silence of specified duration."""
    return np.zeros(int(round(sr * sec)), dtype=np.float32)


def trim_audio_edges(
    wav: np.ndarray,
    sr: int,
    threshold: float = 0.006,
    min_keep_ms: float = 80.0,
) -> np.ndarray:
    """Trim excessive leading/trailing silence from generated TTS audio."""
    if wav.size == 0:
        return wav

    abs_wav = np.abs(wav)
    peak = float(abs_wav.max())
    effective_threshold = max(threshold, peak * 0.02)
    idx = np.where(abs_wav > effective_threshold)[0]
    if idx.size == 0:
        return wav

    pad = int(round(sr * (min_keep_ms / 1000.0)))
    start = max(0, int(idx[0]) - pad)
    end = min(wav.size, int(idx[-1]) + pad + 1)
    return wav[start:end]


def _render_audio(script: IELTSTTSScript) -> tuple[np.ndarray, int]:
    """Render all TTS events and return (combined_array, sample_rate)."""
    _ensure_initialized()
    events = script.to_events()

    logger.info("Starting audio generation… (%d events)", len(events))

    tmp_wav, sr = tts_line("Test.", NARRATOR)
    logger.info("Sample rate: %d Hz", sr)

    segments: list[np.ndarray] = []

    for idx, event in enumerate(events, 1):
        if event[0] is None:
            duration = event[1]
            segments.append(silence(sr, duration))
            logger.debug("[%d/%d] Silence: %.1fs", idx, len(events), duration)
            continue

        speaker, text = event
        preview = text[:60] + ("…" if len(text) > 60 else "")
        logger.info("[%d/%d] %s: %s", idx, len(events), speaker, preview)

        wav, _ = tts_line(text, speaker)
        wav = trim_audio_edges(wav, sr)
        segments.append(wav)

        if idx < len(events):
            next_event = events[idx]
            if next_event[0] is not None:
                pause = PAUSE_NARR if speaker == NARRATOR else PAUSE_TURN
                segments.append(silence(sr, pause))

    return np.concatenate(segments), sr


def generate_and_upload_to_s3(script: IELTSTTSScript, s3_key: str) -> str:
    """Render audio in memory and upload directly to S3. Returns the CDN URL."""
    combined, sr = _render_audio(script)

    buf = io.BytesIO()
    sf.write(buf, combined, sr, format="WAV")
    wav_bytes = buf.getvalue()

    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("S3_ENDPOINT_URL"),
        region_name=os.getenv("S3_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        config=Config(s3={"addressing_style": "path"}),
    )
    bucket = os.getenv("S3_BUCKET_NAME")
    client.put_object(Bucket=bucket, Key=s3_key, Body=wav_bytes, ContentType="audio/wav")

    cdn_base = os.getenv("S3_CDN_BASE_URL", "").rstrip("/")
    cdn_url = f"{cdn_base}/{s3_key}"

    duration_min = combined.shape[0] / sr / 60
    logger.info("Uploaded to S3: %s  (%.2f min)", cdn_url, duration_min)
    return cdn_url
