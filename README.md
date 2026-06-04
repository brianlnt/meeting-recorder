# Meeting Recorder

Record meetings in the browser, transcribe them locally with
[faster-whisper](https://github.com/SYSTRAN/faster-whisper), and summarize them
with a local LLM via [Ollama](https://ollama.com). Everything runs on your
machine — no audio or transcripts leave the box.

## Stack

- **Backend:** FastAPI (`app.py`), SQLite storage in `data/meetings.db`
- **Transcription:** faster-whisper (`base` model, CPU/int8)
- **Summarization:** Ollama running `llama3.2:3b`
- **Frontend:** single static page (`static/index.html`), MediaRecorder API

## One-time setup

```bash
# Python deps
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Ollama — use the official app/cask, NOT `brew install ollama`
# (the plain formula ships without the llama-server binary and 500s on generate)
brew install --cask ollama-app
ollama pull llama3.2:3b

# ffmpeg is required by faster-whisper
brew install ffmpeg
```

## Run

```bash
# 1. Start Ollama (or just open Ollama.app once so it auto-starts on login)
ollama serve

# 2. Start the app
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000, click the red button to record, click again to stop.
Transcription + summary take ~30s–2min depending on length.

## Config (env vars)

| Variable        | Default                  | Notes                          |
|-----------------|--------------------------|--------------------------------|
| `WHISPER_MODEL` | `base`                   | `tiny`/`small`/`medium`/`large`|
| `OLLAMA_MODEL`  | `llama3.2:3b`            | any pulled Ollama model        |
| `OLLAMA_URL`    | `http://localhost:11434` | Ollama server address          |
```
