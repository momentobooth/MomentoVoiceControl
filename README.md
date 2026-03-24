# MomentoBooth Voice Control Service

Local, offline, low-latency voice control for MomentoBooth using the MQTT protocol.

> [!Note]
> Initially vibe-coded with Claude

## Architecture

```
Microphone → Silero VAD → [utterance queue] → Faster-Whisper STT
  → Layer 1: rapidfuzz  (< 1 ms)
  → Layer 2: MiniLM embeddings  (~30 ms)
  → Layer 3: small LLM  (~500 ms, CPU)
  → executor (your app dispatch)
```

## Setup

```bash
# 1. System dependencies
sudo apt install portaudio19-dev python3-dev

# 2. Python dependencies
pip install -r requirements.txt

# 3. (Optional) LLM model for Layer 3
pip install huggingface-hub
huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf \
    Phi-3-mini-4k-instruct-q4.gguf --local-dir ./models

# 4. Run
python main.py
```

## Swapping to real LLM (Layer 3)

In `main.py`, change:
```python
from llm.interface import MockLLM
llm = MockLLM()
```
to:
```python
from llm.interface import LlamaCppLLM
llm = LlamaCppLLM("./models/Phi-3-mini-4k-instruct-q4.gguf")
```

## Dynamic command updates

From your application:
```python
registry.update_commands({
    "screen": "PrintScreen",
    "commands": [
        {"name": "confirm_print", "examples": ["confirm", "yes", "print now"]},
        {"name": "cancel",        "examples": ["cancel", "no", "stop"]},
        {
            "name": "set_copies",
            "parameters": ["count"],
            "examples": ["set copies to {count}", "{count} copies"],
        },
    ]
})
```

## Tuning for your environment

### VAD (`audio/vad_loop.py`)
| Setting | Default | Quieter room | Noisy room |
|---|---|---|---|
| `VAD_THRESHOLD` | 0.5 | 0.4 | 0.65 |
| `SILENCE_GRACE_MS` | 600 | 500 | 800 |
| `MIN_SPEECH_MS` | 300 | 200 | 400 |

### STT (`stt/transcriber.py`)
| Model | Size | CPU latency | Use when |
|---|---|---|---|
| `tiny.en` | 80 MB | ~80 ms | Very fast, quiet room |
| `small.en` | 240 MB | ~300 ms | **Default — best CPU trade-off** |
| `medium.en` | 760 MB | ~900 ms | Noisy/accented speech |

### Matching (`matching/resolver.py`)
| Setting | Default | More permissive | Stricter |
|---|---|---|---|
| `FUZZY_THRESHOLD` | 82 | 70 | 90 |
| `EMBED_THRESHOLD` | 0.72 | 0.65 | 0.80 |

## Running tests (no microphone required)

```bash
python -m pytest tests/ -v
```

## Adding GPU support later

In `stt/transcriber.py`, change:
```python
self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
```
to:
```python
self._model = WhisperModel(model_size, device="cuda", compute_type="float16")
```
And switch to `large-v3` for best accuracy.
