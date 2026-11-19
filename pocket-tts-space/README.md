---
title: Pocket TTS
emoji: 🔊
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.32.0
app_file: app.py
python_version: "3.12"
short_description: Kyutai's 100M CPU text-to-speech in 7 languages
models:
  - kyutai/pocket-tts
  - kyutai/pocket-tts-without-voice-cloning
tags:
  - text-to-speech
  - mcp-server
license: mit
---

# Pocket TTS demo

Try [Kyutai's Pocket TTS](https://huggingface.co/kyutai/pocket-tts): a 100M-parameter text-to-speech model that
runs faster than real-time on a CPU. Pick one of 27 voices in English, French, German, Spanish, Italian,
Portuguese or Dutch, and hear the audio stream in as it is generated.

- [Model card](https://huggingface.co/kyutai/pocket-tts) · [Code](https://github.com/kyutai-labs/pocket-tts) ·
  [Tech report](https://kyutai.org/blog/2026-01-13-pocket-tts) · [Paper](https://arxiv.org/abs/2509.06926)
- The `synthesize` endpoint is also exposed over the Gradio API and as an MCP tool.
- **Voice cloning** needs the gated weights: accept the terms on the
  [model page](https://huggingface.co/kyutai/pocket-tts), then add an `HF_TOKEN` secret to this Space.
