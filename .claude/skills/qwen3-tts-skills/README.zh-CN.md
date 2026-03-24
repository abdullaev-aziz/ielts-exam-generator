# Qwen3-TTS Skill（本地 TTS 工作流）

[English](./README.md) | 简体中文

这是一个**给 AI/Agent 调用的 Skill 仓库**：围绕 **Qwen3-TTS（`qwen-tts`）** 提供可复制运行的本地 TTS 工作流。AI 的主要动作是用 `uv run` 调用内置脚本生成 wav（CustomVoice / VoiceDesign / VoiceClone / Tokenizer）。

- **完整用法**：[`SKILL.md`](./SKILL.md)
- **Python 集成示例**：[`references/python_api.md`](./references/python_api.md)
- **脚本入口**：[`scripts/run_qwen3_tts.py`](./scripts/run_qwen3_tts.py)

## 给 AI 的调用方式（Prompt 模板）

让 AI 直接执行本 Skill 的脚本即可（推荐 `uv run`）。常用模板如下：

- **CustomVoice（自定义音色 + 可选指令）**：
  - `custom-voice --language <LANG> --text <TEXT> --out-dir <DIR>`
  - 可选：`--speaker <NAME>`（不填时会按语言自动选默认 speaker；详见 `SKILL.md`）
  - 可选：`--instruct <STYLE>`、`--output <PATH>`
- **VoiceDesign（自然语言描述“设计”音色）**：
  - `voice-design --language <LANG> --text <TEXT> --instruct <DESC> --out-dir <DIR>`
- **VoiceClone（克隆音色）**：
  - `voice-clone --language <LANG> --ref-audio <URL_OR_PATH> --ref-text <TRANSCRIPT> --text <TEXT> --out-dir <DIR>`
  - 可选：`--x-vector-only-mode`（可不传 `--ref-text`，但质量可能下降）
- **Tokenizer roundtrip（编码→解码还原）**：
  - `tokenizer-roundtrip --audio <URL_OR_PATH> --out-dir <DIR>`

Windows 路径要点：命令里出现 `C:/Users/...` 这类绝对路径时，用**双引号**包起来（详见 `SKILL.md` 的 Windows 章节）。

## 演示视频

<video src="./qwen3tts%20skill-1769369939100.mp4" controls playsinline style="max-width: 100%;"></video>

## 快速开始（推荐：uv run）

查看帮助：

```bash
uv run scripts/run_qwen3_tts.py -h
```

CustomVoice（生成 wav）：

```bash
uv run scripts/run_qwen3_tts.py custom-voice --language Chinese --text "其实我真的有发现，我是一个特别善于观察别人情绪的人。" --out-dir outputs
```

VoiceDesign（用自然语言“设计”音色）：

```bash
uv run scripts/run_qwen3_tts.py voice-design --language Chinese --text "哥哥，你回来啦，人家等了你好久好久了，要抱抱！" --instruct "体现撒娇稚嫩的萝莉女声，音调偏高且起伏明显。" --out-dir outputs
```

VoiceClone（克隆音色）：

```bash
uv run scripts/run_qwen3_tts.py voice-clone --language English --ref-audio "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/clone.wav" --ref-text "Okay. Yeah. I resent you. I love you. I respect you. But you know what? You blew it! And thanks to you." --text "Sentence A." --out-dir outputs
```

Tokenizer roundtrip（编码→解码还原）：

```bash
uv run scripts/run_qwen3_tts.py tokenizer-roundtrip --audio "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen3-TTS-Repo/tokenizer_demo_1.wav" --out-dir outputs
```

## 常用参数

脚本支持这些通用性能参数（详见 `-h`）：

- `--device-map`：如 `cuda:0` / `cpu`
- `--dtype`：`auto` / `bfloat16` / `float16` / `float32`
- `--attn`：`auto` / `flash_attention_2`（已安装且硬件兼容时）

