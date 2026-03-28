# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered IELTS Listening Test Generator. Uses a multi-agent pipeline to generate realistic IELTS listening exams with structured blueprints, dialogue scripts, and TTS audio output. Currently Part 1 is implemented; Parts 2-4 are planned.

## Quick Reference

- **Setup**: `source .venv/bin/activate && pip install -e .`
- **Run (NATS)**: `docker compose -f nats.yml up -d` then start workers (see `.claude/rules/running.md`)
- **Run (standalone)**: `from listening.agents.part1.main_agent import run_pipeline`
- **Python**: 3.13.3 | **Model**: `gpt-5.4`
- **All imports are absolute** — no `sys.path` hacks
- **All logging via `logging` module** — no `print()`, `ielts.*` namespace
- **No local file writes** — audio rendered in memory, uploaded to S3
- **Blueprint history** in PostgreSQL (`DATABASE_URL` env var) — Agent 1 exclusion list for variety

## Rules

Detailed instructions are split into `.claude/rules/`:

| Rule file | Scope | Content |
|-----------|-------|---------|
| `architecture.md` | Global | Project structure, package layout, config |
| `agents-pipeline.md` | `src/listening/**` | Agent 1-4, pipeline flow, data models, timeouts |
| `nats-workers.md` | `src/workers/**` | Worker architecture, streams, consumers, events |
| `tts-audio.md` | `src/audio/**` | TTS generator, S3 upload, voice cloning, formatting |
| `logging.md` | Global | Logger conventions, namespace, no-print rule |
| `running.md` | Global | How to run: venv, NATS, workers, standalone |
| `skills.md` | Global | Installed skills reference |

Path-scoped rules (with `paths:` frontmatter) only load when working on matching files. Global rules load every session.
