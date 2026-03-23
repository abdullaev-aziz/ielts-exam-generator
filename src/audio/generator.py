import io
import os
import numpy as np
import torch
import soundfile as sf
import boto3
from botocore.config import Config
from qwen_tts import Qwen3TTSModel
from listening.agents.part1.agent3 import IELTSTTSScript

# ---------------------------
# Qwen3-TTS setup
# ---------------------------
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
VOICE_DESIGN_MODEL_ID = os.getenv("QWEN3_TTS_VOICE_DESIGN_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign")
VOICE_CLONE_MODEL_ID = os.getenv("QWEN3_TTS_VOICE_CLONE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
NARRATOR_REF_AUDIO = os.getenv("QWEN3_TTS_NARRATOR_REF_AUDIO", "narrator_ref.wav")
NARRATOR_REF_TEXT = os.getenv("QWEN3_TTS_NARRATOR_REF_TEXT", """You will hear four different recordings.
                                                                And vou will have to answer questions on what you hear. There will be
                                                                time for you to read the instructions and questions. And you will have
                                                                a chance to check your work. You will hear each recording once only.
                                                                The test is in four parts. At the end of the test, you will be given two
                                                                minutes to check all of your answers""")


def load_tts_model(model_id: str) -> Qwen3TTSModel:
    return Qwen3TTSModel.from_pretrained(
        model_id,
        dtype=torch.float32,
        attn_implementation="eager",
        low_cpu_mem_usage=False,
    )


def resolve_project_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


voice_design_model = None
voice_clone_model = None

OUT_WAV = "ielts_part4.wav"
REFERENCE_TEXT = "Hello, this is a test."

# Micro-pauses for realism (kept short between adjacent speech turns)
PAUSE_TURN = 0.25
PAUSE_NARR = 0.30

# Speaker instructions used for non-narrator reference generation.
INSTR = {
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

def build_reference_assets():
    print("Generating reference voices...")
    reference_prompts = {}
# I deleted the man and woman
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
            reference_prompts[speaker] = voice_clone_model.create_voice_clone_prompt(
                ref_audio=narrator_ref_audio,
                ref_text=ref_text if ref_text else None,
                x_vector_only_mode=use_xvector_only,
            )
            mode = "x-vector only" if use_xvector_only else "full clone"
            print(f"  Prepared reusable prompt for {speaker} from {narrator_ref_audio} ({mode})")
            continue

        wavs, sr = voice_design_model.generate_voice_design(
            text=REFERENCE_TEXT,
            language="English",
            instruct=INSTR[speaker],
            do_sample=False,
        )
        reference_prompts[speaker] = voice_clone_model.create_voice_clone_prompt(
            ref_audio=(wavs[0], sr),
            ref_text=REFERENCE_TEXT,
            x_vector_only_mode=False,
        )
        print(f"  Prepared reusable prompt for {speaker}")

    return reference_prompts


reference_prompts = None


def _ensure_initialized():
    global voice_design_model, voice_clone_model, reference_prompts
    if reference_prompts is not None:
        return
    voice_design_model = load_tts_model(VOICE_DESIGN_MODEL_ID)
    voice_clone_model = load_tts_model(VOICE_CLONE_MODEL_ID)
    reference_prompts = build_reference_assets()


def tts_line(text: str, speaker: str):
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


def silence(sr: int, sec: float):
    """Generate silence of specified duration."""
    return np.zeros(int(round(sr * sec)), dtype=np.float32)


def trim_audio_edges(
    wav: np.ndarray,
    sr: int,
    threshold: float = 0.006,
    min_keep_ms: float = 80.0,
):
    """
    Trim excessive leading/trailing silence from generated TTS audio.
    Keeps a tiny margin to avoid cutting consonants.
    """
    if wav.size == 0:
        return wav

    abs_wav = np.abs(wav)
    peak = float(abs_wav.max())
    # Adaptive threshold suppresses low-amplitude model noise that can fake long tails.
    effective_threshold = max(threshold, peak * 0.02)
    idx = np.where(abs_wav > effective_threshold)[0]
    if idx.size == 0:
        return wav

    pad = int(round(sr * (min_keep_ms / 1000.0)))
    start = max(0, int(idx[0]) - pad)
    end = min(wav.size, int(idx[-1]) + pad + 1)
    return wav[start:end]


def _render_audio(script: IELTSTTSScript):
    """Render all TTS events and return (combined_array, sample_rate)."""
    _ensure_initialized()
    events = script.to_events()

    print("Starting audio generation...")
    print(f"Total events: {len(events)}\n")

    tmp_wav, sr = tts_line("Test.", NARRATOR)
    print(f"Sample rate: {sr} Hz\n")

    segments = []

    for idx, event in enumerate(events, 1):
        if event[0] is None:
            duration = event[1]
            segments.append(silence(sr, duration))
            print(f"[{idx}/{len(events)}] Silence: {duration:.1f}s")
            continue

        speaker, text = event
        print(f"[{idx}/{len(events)}] {speaker}: {text[:60]}{'...' if len(text) > 60 else ''}")

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
    print(f"\n✓ Uploaded to S3: {cdn_url}  ({duration_min:.2f} min)")
    return cdn_url
