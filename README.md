# Transcription Service

Upload an audio file, get back text with timestamps per segment.
Built with FastAPI + faster-whisper, jobs processed in background workers.

## Setup (macOS)

```bash
brew install ffmpeg
cd ~/Desktop/transcribe-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

or just `./run.sh` (creates the venv on first run).

Docs: http://localhost:8000/docs

First request downloads the Whisper model (`base` is ~150MB). For better accuracy
use `WHISPER_MODEL=small uvicorn app.main:app`.

To run without downloading a model (fake text, real timestamps):

```bash
TRANSCRIBER=mock uvicorn app.main:app --reload
```

## Try it

```bash
say "Hello, I want to check the status of my booking. The reference is A B C one two three." -o sample.aiff
ffmpeg -i sample.aiff sample.mp3

curl -F "file=@sample.mp3" http://localhost:8000/v1/transcriptions
# {"job_id":"<id>","status":"queued"}

curl http://localhost:8000/v1/transcriptions/<id>
curl "http://localhost:8000/v1/transcriptions/<id>/segments?format=srt"
```

## Endpoints

| Method | Path | |
|---|---|---|
| POST | /v1/transcriptions | upload (file, language?, webhook_url?) → 202 + job_id |
| GET | /v1/transcriptions | list jobs |
| GET | /v1/transcriptions/{id} | status + result |
| GET | /v1/transcriptions/{id}/segments?format=json\|srt\|vtt\|txt | segments |
| POST | /v1/transcriptions/{id}/retry | retry a failed job |
| DELETE | /v1/transcriptions/{id} | delete job and audio |
| GET | /health | health + queue size |

## Tests

```bash
pytest -q
```

Tests use the mock backend, so no model download needed.

## Config

See `.env.example`. Copy it to `.env` and `run.sh` picks it up.
Set `API_KEY` to require an `X-API-Key` header.
