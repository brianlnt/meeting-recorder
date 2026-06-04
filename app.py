import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

import requests
from faster_whisper import WhisperModel
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "meetings.db"

DATA_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL", "base")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

app = FastAPI()
_whisper = None


def get_whisper() -> WhisperModel:
    global _whisper
    if _whisper is None:
        _whisper = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    return _whisper


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meetings (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            title TEXT,
            transcript TEXT,
            summary TEXT,
            audio_path TEXT
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


SUMMARY_PROMPT = """You summarize meeting transcripts.
Read the transcript and return ONLY a JSON object with these fields:
- "title": short 3-7 word title
- "summary": 2-4 sentence overview
- "key_points": array of 3-7 important takeaways
- "action_items": array of follow-up tasks or decisions (may be empty)

TRANSCRIPT:
{transcript}
"""


def summarize(transcript: str) -> dict:
    resp = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": SUMMARY_PROMPT.format(transcript=transcript),
            "stream": False,
            "format": "json",
        },
        timeout=600,
    )
    resp.raise_for_status()
    raw = resp.json().get("response", "")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "title": "Untitled meeting",
            "summary": raw[:500] or "(summary unavailable)",
            "key_points": [],
            "action_items": [],
        }


@app.post("/api/process")
async def process_audio(file: UploadFile = File(...)):
    meeting_id = uuid.uuid4().hex[:12]
    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    audio_path = AUDIO_DIR / f"{meeting_id}{suffix}"
    audio_path.write_bytes(await file.read())

    model = get_whisper()
    segments, _info = model.transcribe(str(audio_path), beam_size=1, vad_filter=True)
    transcript = " ".join(seg.text.strip() for seg in segments).strip()

    if not transcript:
        audio_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="No speech detected in recording")

    summary_data = summarize(transcript)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO meetings (id, created_at, title, transcript, summary, audio_path) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            meeting_id,
            datetime.utcnow().isoformat(),
            summary_data.get("title", "Untitled"),
            transcript,
            json.dumps(summary_data),
            str(audio_path.relative_to(BASE_DIR)),
        ),
    )
    conn.commit()
    conn.close()

    return {
        "id": meeting_id,
        "title": summary_data.get("title"),
        "transcript": transcript,
        "summary": summary_data,
    }


@app.get("/api/meetings")
def list_meetings():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, created_at, title FROM meetings ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [{"id": r[0], "created_at": r[1], "title": r[2]} for r in rows]


@app.get("/api/meetings/{meeting_id}")
def get_meeting(meeting_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, created_at, title, transcript, summary FROM meetings WHERE id = ?",
        (meeting_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {
        "id": row[0],
        "created_at": row[1],
        "title": row[2],
        "transcript": row[3],
        "summary": json.loads(row[4]) if row[4] else {},
    }


@app.delete("/api/meetings/{meeting_id}")
def delete_meeting(meeting_id: str):
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT audio_path FROM meetings WHERE id = ?", (meeting_id,)
    ).fetchone()
    if row and row[0]:
        path = BASE_DIR / row[0]
        if path.exists():
            path.unlink()
    conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


app.mount("/", StaticFiles(directory=str(BASE_DIR / "static"), html=True), name="static")
