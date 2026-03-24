# Qwen3-TTS Skill (AI-callable)

English | [简体中文](./README.zh-CN.md)

This repository is an **AI/Agent-callable Skill** for **Qwen3-TTS (`qwen-tts`)**. The intended usage is that the AI runs the bundled script via `uv run` to produce wav outputs (CustomVoice / VoiceDesign / VoiceClone / Tokenizer).

- **Full usage**: [`SKILL.md`](./SKILL.md)
- **Python integration examples**: [`references/python_api.md`](./references/python_api.md)
- **Script entry**: [`scripts/run_qwen3_tts.py`](./scripts/run_qwen3_tts.py)

## How an AI should call it (prompt template)

Have the AI execute the script directly (recommended: `uv run`). Common templates:

- **CustomVoice (custom speaker + optional instruction)**:
  - `custom-voice --language <LANG> --text <TEXT> --out-dir <DIR>`
  - Optional: `--speaker <NAME>` (if omitted, a default speaker may be chosen based on language; see `SKILL.md`)
  - Optional: `--instruct <STYLE>`, `--output <PATH>`
- **VoiceDesign (design a voice from natural language)**:
  - `voice-design --language <LANG> --text <TEXT> --instruct <DESC> --out-dir <DIR>`
- **VoiceClone (clone from reference audio)**:
  - `voice-clone --language <LANG> --ref-audio <URL_OR_PATH> --ref-text <TRANSCRIPT> --text <TEXT> --out-dir <DIR>`
  - Optional: `--x-vector-only-mode` (can omit `--ref-text`, quality may degrade)
- **Tokenizer roundtrip (encode -> decode)**:
  - `tokenizer-roundtrip --audio <URL_OR_PATH> --out-dir <DIR>`

Windows path note: if you pass absolute paths like `C:/Users/...` in commands, wrap them in **double quotes** (see the Windows section in `SKILL.md`).

## Demo video

<video src="./qwen3tts%20skill-1769369939100.mp4" controls playsinline style="max-width: 100%;"></video>

## Quick start (recommended: uv run)

Help:

```bash
uv run scripts/run_qwen3_tts.py -h
```

CustomVoice (generate wav):

```bash
uv run scripts/run_qwen3_tts.py custom-voice --language Chinese --text "其实我真的有发现，我是一个特别善于观察别人情绪的人。" --out-dir outputs
```

VoiceDesign:

```bash
uv run scripts/run_qwen3_tts.py voice-design --language Chinese --text "哥哥，你回来啦，人家等了你好久好久了，要抱抱！" --instruct "体现撒娇稚嫩的萝莉女声，音调偏高且起伏明显。" --out-dir outputs
```

VoiceClone:

```bash
uv run scripts/run_qwen3_tts.py voice-clone --language English --ref-audio "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/clone.wav" --ref-text "Okay. Yeah. I resent you. I love you. I respect you. But you know what? You blew it! And thanks to you." --text "Sentence A." --out-dir outputs
```

Tokenizer roundtrip:

```bash
uv run scripts/run_qwen3_tts.py tokenizer-roundtrip --audio "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/tokenizer_demo_1.wav" --out-dir outputs
```

## Common flags

See `-h` for details. Common performance-related flags:

- `--device-map`: e.g. `cuda:0` / `cpu`
- `--dtype`: `auto` / `bfloat16` / `float16` / `float32`
- `--attn`: `auto` / `flash_attention_2` (if installed & supported)

