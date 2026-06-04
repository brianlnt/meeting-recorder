# Meeting Recorder — project context

Local-first meeting recorder: record in the browser → transcribe locally →
summarize with a local LLM. **Nothing leaves the machine** (no cloud APIs); this
privacy property is intentional — keep it that way unless the user asks.

## Architecture
- `app.py` — FastAPI backend. Endpoints: `POST /api/process` (transcribe +
  summarize + store), `GET /api/meetings`, `GET /api/meetings/{id}`,
  `DELETE /api/meetings/{id}`. Serves the frontend at `/`.
- `static/index.html` — single-page UI (vanilla JS, MediaRecorder API).
- Storage: SQLite at `data/meetings.db`; audio files in `data/audio/`.
- Transcription: faster-whisper (`base`, CPU/int8).
- Summarization: Ollama running `llama3.2:3b` at `localhost:11434`.

## Running it
```bash
ollama serve   # or open Ollama.app
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000. See README.md for full setup.

## Gotchas
- Use the Ollama **cask** (`brew install --cask ollama-app`), NOT the brew
  formula — the formula lacks the `llama-server` binary and `/api/generate` 500s.
- Mic access only works on `localhost`/`127.0.0.1` (secure-context requirement).

## Status (as of 2026-06-04)
App is fully working end-to-end and verified. Not yet a git repo. `.gitignore`
and `README.md` exist. No tests yet.

## Ideas discussed / not yet built
Editable titles, search, audio playback, bigger Whisper/LLM models for quality.
