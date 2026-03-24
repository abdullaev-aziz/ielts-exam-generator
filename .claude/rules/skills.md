# Installed Skills

## NATS (`nats`)

Location: `.claude/skills/nats/`

Core NATS and JetStream reference — subjects, request/reply, persistence, consumers. Reference `SKILL.md` for quick patterns and `advanced.md` for JetStream consumer setup, security config, and clustering.

## OpenAI Agents SDK Guidelines (`openai-agents-sdk-guidelines`)

Location: `.claude/skills/openai-agents-sdk-guidelines/`

30+ implementation rules for the OpenAI Agents Python SDK. When working on agent code, read the relevant rule file at `.claude/skills/openai-agents-sdk-guidelines/rules/<prefix>-<description>.md`.

| Priority | Category | Prefix |
|----------|----------|--------|
| 1 (CRITICAL) | Agent Design | `agent-` |
| 2 (CRITICAL) | Multi-Agent Patterns | `multi-agent-` |
| 3 (HIGH) | Tools | `tool-` |
| 4 (MEDIUM-HIGH) | Guardrails | `guardrail-` |
| 5 (MEDIUM) | Context Management | `context-` |
| 6 (MEDIUM) | Running Agents | `runner-` |
| 7 (MEDIUM) | Conversation Mgmt | `conversation-` |
| 8 (LOW-MEDIUM) | Streaming | `streaming-` |

## Qwen3-TTS Skills (`qwen3-tts-skills`)

Location: `.claude/skills/qwen3-tts-skills/`

CLI and Python API reference. See `references/python_api.md` for Python API examples.

## Qwen3-TTS Text Formatting (`qwen3-tts-text-formatting`)

Location: `.claude/skills/qwen3-tts-text-formatting/`

Best practices for formatting spoken text for natural Qwen3-TTS audio output.

## Superpowers (`superpowers`)

14 workflow skills installed locally into `.claude/skills/`. Key ones: `brainstorming`, `writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`, `verification-before-completion`, `requesting-code-review`.
