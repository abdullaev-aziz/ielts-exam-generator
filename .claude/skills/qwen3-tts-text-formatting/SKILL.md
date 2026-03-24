---
name: qwen3-tts-text-formatting
description: Best practices for formatting spoken text for Qwen3-TTS to produce natural, realistic audio. Use when writing or reviewing TTS input text, especially for IELTS listening audio, dialogue scripts, narrator lines, or any speech synthesis with Qwen3-TTS. Triggers on: "format text for TTS", "qwen3 tts text", "tts naturalness", "spelling sequences", "tts pauses", "IELTS audio text", "voice instruction".
license: MIT
metadata:
  author: local
  version: "1.0.0"
---

# Qwen3-TTS Text Formatting Best Practices

Guidelines for producing natural, realistic audio from Qwen3-TTS — especially for IELTS Listening test generation.

---

## How Qwen3-TTS Reads Text

Qwen3-TTS uses **two separate inputs**:

| Field | Purpose |
|-------|---------|
| `text` | The spoken script — what actually gets voiced |
| `instruct` | Voice instruction — how to say it (gender, emotion, pace, pauses) |

The model reads punctuation as prosody cues automatically. It does **not** support SSML or markup tags.

---

## Punctuation for Pauses and Rhythm

| Symbol | Effect | Use for |
|--------|--------|---------|
| `…` | Hesitation / thinking pause | Trailing thoughts, fillers, uncertainty |
| `—` | Abrupt break / thought shift | Self-corrections, interruptions |
| `,` | Short breath | Clause boundaries, lists |
| `?` / `!` | Intonation rise / energy | Questions, emphasis |
| Paragraph break | Longer pause | Section transitions in long-form |

**Good examples:**
```
The price is… let me check… forty-seven pounds fifty.
It's the fourteenth — no, sorry, the twenty-first.
Um… I'm not sure about that one.
So that's on the third floor — well, actually the second floor.
```

**Never use:**
- SSML tags: `<break time="1s"/>`, `<prosody rate="slow">`
- Explicit markers: `[pause:2s]`, `[breath]`, `[silence]`
- ALL-CAPS emphasis: `the answer is FORTY-FIVE`
- Speaker labels inside text: `NARRATOR: ...`

The model ignores these and they degrade output quality.

---

## Fillers and Natural Speech

Fillers are **critical** for TTS naturalness. Never strip them.

Preserve all of: `um`, `er`, `erm`, `well`, `right`, `you know`, `I mean`, `let me see`, `hang on`, `oh actually`

When a filler opens a phrase, follow it with `…`:
```
Er… I think it's around forty pounds.
Um… we've got a few options actually.
Well… it depends on the day, really.
```

Limit added fillers to **1–4 per section** to avoid overuse.

---

## Letter-by-Letter Spelling Sequences

For phone calls where someone spells out a name, postcode, or address:

| Before (Agent 2 output) | After (reformatted for TTS) |
|-------------------------|----------------------------|
| `K-O-W-A-L-S-K-I` | `K — O — W — A — L — S — K — I` |
| `P-E-M-B-E-R-T-O-N` | `P — E — M — B — E — R — T — O — N` |

**Rule:** Separate each letter with ` — ` (space, em-dash, space). This creates a brief inter-letter pause in TTS, mimicking how people actually spell things out on phone calls.

Apply to: surnames, postcodes, street names, email handles, usernames, reference codes.

**Example:**
```
Before: "The surname is Kowalski. That's K-O-W-A-L-S-K-I."
After:  "The surname is Kowalski. That's K — O — W — A — L — S — K — I."
```

---

## Numbers, Dates, and Times

Always write as words in the spoken text field:

| Avoid | Use instead |
|-------|------------|
| `45` | `forty-five` |
| `£12.50` | `twelve pounds fifty` |
| `2:30 pm` | `half past two` |
| `15/03` | `the fifteenth of March` |
| `07845 332901` | `zero seven eight four five, three three two nine zero one` |
| `Q1–5` | `questions one to five` |

---

## Voice Instruction Prompt (`instruct` field)

The `instruct` field controls voice characteristics. Structure it as 1–3 sentences covering:

1. Voice basics (gender, age, accent, timbre)
2. Personality / context
3. Pacing, pauses, emotion

**IELTS Narrator (examiner voice):**
```
Clear, neutral mid-30s British female voice in professional IELTS examiner style — calm, articulate, slightly formal but natural conversational rhythm. Moderate pace with realistic short pauses after each question or key phrase, very occasional 'um' or 'er' hesitations, natural breathing, precise pronunciation of numbers and spellings, friendly yet neutral tone.
```

**IELTS Dialogue — Male speaker:**
```
Clear mid-30s British male voice, natural conversational pace, warm and approachable. Slight hesitations and realistic breathing between sentences, natural intonation rises on questions, occasional fillers like 'um' and 'er', friendly and helpful tone.
```

**IELTS Dialogue — Female speaker:**
```
Clear mid-30s British female voice, natural conversational pace, warm and engaged. Realistic short pauses at clause boundaries, occasional fillers, slight intonation variation, friendly and professional tone.
```

**Realism boosters** — add these phrases to any instruction:
- `"with natural short pauses and breaths"`
- `"slight hesitations and fillers when appropriate"`
- `"human-like prosody and intonation rises/falls"`
- `"clear enunciation of numbers, spellings, and dates"`

---

## IELTS Section 1 — Full Example

```
Woman: Hello… good morning. Um, I'm looking for information about boat trips on the river?

Man: Oh, right — yes, we've got a few actually. Are you after the short sightseeing one or the longer dinner cruise?

Woman: Probably the short one, I think. How long does it take?

Man: It's about forty-five minutes… yeah, forty-five to fifty, depending on the water traffic, you know.

Woman: And the price?

Man: Adults are twelve pounds fifty, children under twelve six pounds seventy-five.

Woman: Okay… and do we need to book ahead?

Man: It's a good idea at weekends, but during the week you can usually just turn up. Er… what date were you thinking of?
```

Key patterns shown:
- `…` after fillers (`Um,`, `Er…`)
- `—` for thought shifts (`right — yes`)
- Numbers as words (`forty-five`, `twelve pounds fifty`)
- Short, natural sentence lengths

---

## Quick Reference Checklist

Before finalising TTS text:

- [ ] All numbers written as words
- [ ] Spelling sequences use `X — Y — Z` format
- [ ] Fillers preserved and followed by `…`
- [ ] No SSML tags or `[pause]` markers
- [ ] No ALL-CAPS emphasis
- [ ] No speaker labels inside text fields
- [ ] Commas used freely at natural breath points
- [ ] Long sentences split at `…` or `,` boundaries
