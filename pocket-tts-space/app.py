"""Gradio demo for Kyutai's Pocket TTS (https://huggingface.co/kyutai/pocket-tts).

Pocket TTS is a 100M-parameter text-to-speech model built to run on CPU, so all
inference here happens on CPU. The Space sits on ZeroGPU only because that is the
hardware tier available to free accounts; ZeroGPU requires at least one
`@spaces.GPU` function, so a no-op one is declared and never called.
"""

import spaces  # must be imported before torch

import tempfile
import threading
import time
from collections import OrderedDict
from pathlib import Path

import gradio as gr
import numpy as np
import scipy.io.wavfile
import torch
from pocket_tts import TTSModel
from pocket_tts.default_parameters import (
    DEFAULT_TEMPERATURE,
    DEFAULT_TEXT_FOR_LANGUAGE,
    get_default_voice_for_language,
)

torch.set_num_threads(2)  # Pocket TTS is tuned for ~2 CPU cores


@spaces.GPU(duration=1)
def _noop():  # ZeroGPU requires >= 1 decorated function; never called
    pass


LANGUAGES = {
    "English": "english",
    "French": "french",
    "German": "german",
    "Spanish": "spanish",
    "Italian": "italian",
    "Portuguese": "portuguese",
    "Dutch": "dutch",
}

# Pre-made voices (all are available for every language). Native language in brackets.
VOICES = {
    "alba": "en",
    "anna": "en",
    "azelma": "en",
    "bill_boerst": "en",
    "caro_davy": "en",
    "charles": "en",
    "cosette": "en",
    "eponine": "en",
    "eve": "en",
    "fantine": "en",
    "george": "en",
    "jane": "en",
    "javert": "en",
    "jean": "en",
    "marius": "en",
    "mary": "en",
    "michael": "en",
    "paul": "en",
    "peter_yearsley": "en",
    "stuart_bell": "en",
    "vera": "en",
    "estelle": "fr",
    "juergen": "de",
    "lola": "es",
    "giovanni": "it",
    "rafael": "pt",
    "daan": "nl",
}
VOICE_CHOICES = [(f"{name} ({lang})", name) for name, lang in VOICES.items()]

MAX_CHARS = 2000
MAX_LOADED_MODELS = 3  # keep RAM bounded: each language is a separate ~100M model

_lock = threading.Lock()  # generation is not thread-safe; also guards the caches
_models: "OrderedDict[str, TTSModel]" = OrderedDict()
_voice_states: dict[tuple[str, str], object] = {}


def _get_model(language: str) -> TTSModel:
    if language in _models:
        _models.move_to_end(language)
        return _models[language]
    model = TTSModel.load_model(language=language)
    _models[language] = model
    while len(_models) > MAX_LOADED_MODELS:
        evicted, _ = _models.popitem(last=False)
        for key in [k for k in _voice_states if k[0] == evicted]:
            del _voice_states[key]
    return model


def _get_voice_state(model: TTSModel, language: str, voice: str, reference_audio: str | None):
    if reference_audio:
        if not model.has_voice_cloning:
            raise gr.Error(
                "Voice cloning is not enabled on this Space: the gated voice-cloning weights "
                "could not be downloaded. Pick a pre-made voice instead."
            )
        return model.get_state_for_audio_prompt(Path(reference_audio))
    if voice not in VOICES:
        raise gr.Error(f"Unknown voice {voice!r}.")
    key = (language, voice)
    if key not in _voice_states:
        _voice_states[key] = model.get_state_for_audio_prompt(voice)
    return _voice_states[key]


def _validate(text: str, language_label: str) -> tuple[str, str]:
    text = (text or "").strip()
    if not text:
        raise gr.Error("Please enter some text.")
    if len(text) > MAX_CHARS:
        raise gr.Error(f"Text is limited to {MAX_CHARS} characters in this demo ({len(text)} given).")
    if language_label not in LANGUAGES:
        raise gr.Error(f"Unsupported language {language_label!r}.")
    return text, LANGUAGES[language_label]


def _to_int16(chunk: torch.Tensor) -> np.ndarray:
    audio = chunk.detach().cpu().float().clamp(-1.0, 1.0).numpy()
    return (audio * 32767.0).astype(np.int16)


def _stats(audio_seconds: float, elapsed: float, first_chunk: float | None) -> str:
    rtf = audio_seconds / elapsed if elapsed > 0 else 0.0
    parts = [f"**{audio_seconds:.1f}s** of audio in **{elapsed:.1f}s** on CPU ({rtf:.1f}x real-time)"]
    if first_chunk is not None:
        parts.append(f"first audio after **{first_chunk * 1000:.0f} ms**")
    return " · ".join(parts)


def stream_speech(
    text: str,
    language: str = "English",
    voice: str = "alba",
    reference_audio: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
):
    """Stream speech for `text`, yielding audio chunks as soon as they are decoded.

    Args:
        text: The text to speak.
        language: One of English, French, German, Spanish, Italian, Portuguese, Dutch.
        voice: Name of a pre-made voice (e.g. "alba"). Ignored when `reference_audio` is set.
        reference_audio: Optional path to a short, clean voice sample to clone.
        temperature: Sampling temperature; higher is more expressive, lower is more stable.
    """
    text, lang = _validate(text, language)
    with _lock:
        yield gr.skip(), ("Loading model…" if lang not in _models else "Generating…")
        model = _get_model(lang)
        state = _get_voice_state(model, lang, voice, reference_audio)
        model.temp = float(temperature)
        sr = model.sample_rate
        start = time.perf_counter()
        first_chunk, n_samples = None, 0
        for chunk in model.generate_audio_stream(state, text):
            if first_chunk is None:
                first_chunk = time.perf_counter() - start
            n_samples += chunk.shape[-1]
            yield (sr, _to_int16(chunk)), "Generating…"
        elapsed = time.perf_counter() - start
    yield gr.skip(), _stats(n_samples / sr, elapsed, first_chunk)


def synthesize(
    text: str,
    language: str = "English",
    voice: str = "alba",
    temperature: float = DEFAULT_TEMPERATURE,
) -> str:
    """Convert text to speech with Kyutai's Pocket TTS and return the path to a WAV file.

    Args:
        text: The text to speak (up to 2000 characters).
        language: One of English, French, German, Spanish, Italian, Portuguese, Dutch.
        voice: Name of a pre-made voice, e.g. "alba", "marius", "estelle", "juergen", "lola".
        temperature: Sampling temperature; higher is more expressive, lower is more stable.
    """
    text, lang = _validate(text, language)
    with _lock:
        model = _get_model(lang)
        state = _get_voice_state(model, lang, voice, None)
        model.temp = float(temperature)
        audio = model.generate_audio(state, text)
        sr = model.sample_rate
    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    scipy.io.wavfile.write(out.name, sr, _to_int16(audio))
    return out.name


def on_language_change(language_label: str):
    lang = LANGUAGES.get(language_label, "english")
    return (
        gr.update(value=get_default_voice_for_language(lang)),
        gr.update(value=DEFAULT_TEXT_FOR_LANGUAGE.get(lang, DEFAULT_TEXT_FOR_LANGUAGE["english"])),
    )


# Load English eagerly so the first request is fast, and learn whether the gated
# voice-cloning weights are reachable with this Space's token.
with _lock:
    _get_model("english")
    _get_voice_state(_models["english"], "english", "alba", None)
CLONING_AVAILABLE = _models["english"].has_voice_cloning

CLONING_NOTE = (
    "Upload or record a few seconds of clean speech; the model will speak in that voice. "
    "Only clone voices you have permission to use."
    if CLONING_AVAILABLE
    else "⚠️ Voice cloning is off on this Space: its gated weights require accepting the terms at "
    "[kyutai/pocket-tts](https://huggingface.co/kyutai/pocket-tts) and adding an `HF_TOKEN` secret. "
    "The pre-made voices above work without it."
)

EXAMPLES = [
    ["Hello world. I am Kyutai's Pocket TTS. I'm fast enough to run on small CPUs. I hope you'll like me.", "English", "alba"],
    ["The quick brown fox jumps over the lazy dog, and then takes a well-deserved nap in the sun.", "English", "marius"],
    [DEFAULT_TEXT_FOR_LANGUAGE["french"], "French", "estelle"],
    [DEFAULT_TEXT_FOR_LANGUAGE["german"], "German", "juergen"],
    [DEFAULT_TEXT_FOR_LANGUAGE["spanish"], "Spanish", "lola"],
    [DEFAULT_TEXT_FOR_LANGUAGE["italian"], "Italian", "giovanni"],
    [DEFAULT_TEXT_FOR_LANGUAGE["portuguese"], "Portuguese", "rafael"],
    [DEFAULT_TEXT_FOR_LANGUAGE["dutch"], "Dutch", "daan"],
]

with gr.Blocks(title="Pocket TTS") as demo:
    gr.Markdown(
        "# 🔊 Pocket TTS\n"
        "Kyutai's 100M-parameter text-to-speech model that runs faster than real-time on a CPU, "
        "in 7 languages, with streaming and voice cloning. "
        "[Model](https://huggingface.co/kyutai/pocket-tts) · "
        "[Code](https://github.com/kyutai-labs/pocket-tts) · "
        "[Tech report](https://kyutai.org/blog/2026-01-13-pocket-tts)"
    )
    with gr.Row():
        with gr.Column(scale=3):
            text = gr.Textbox(
                label="Text",
                value=DEFAULT_TEXT_FOR_LANGUAGE["english"],
                lines=5,
                max_length=MAX_CHARS,
            )
            with gr.Row():
                language = gr.Dropdown(list(LANGUAGES), value="English", label="Language")
                voice = gr.Dropdown(VOICE_CHOICES, value="alba", label="Voice")
            with gr.Accordion("Clone a voice", open=False):
                gr.Markdown(CLONING_NOTE)
                reference_audio = gr.Audio(
                    label="Reference voice (overrides the voice above)",
                    sources=["upload", "microphone"],
                    type="filepath",
                    interactive=CLONING_AVAILABLE,
                )
            with gr.Accordion("Advanced", open=False):
                temperature = gr.Slider(0.0, 1.0, value=DEFAULT_TEMPERATURE, step=0.05, label="Temperature")
            generate = gr.Button("Generate", variant="primary")
        with gr.Column(scale=2):
            audio_out = gr.Audio(label="Speech", streaming=True, autoplay=True, interactive=False)
            stats = gr.Markdown()

    gr.Examples(examples=EXAMPLES, inputs=[text, language, voice])

    language.input(on_language_change, inputs=language, outputs=[voice, text], api_visibility="private")
    generate.click(
        stream_speech,
        inputs=[text, language, voice, reference_audio, temperature],
        outputs=[audio_out, stats],
        concurrency_limit=1,
        api_visibility="private",
    )
    gr.api(synthesize, api_name="synthesize", concurrency_limit=1)

if __name__ == "__main__":
    demo.queue(max_size=32).launch(mcp_server=True)
