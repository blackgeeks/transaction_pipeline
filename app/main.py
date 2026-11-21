import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse

from app import config
from app.formats import to_srt, to_txt, to_vtt
from app.jobs import DONE, FAILED, QUEUED, JobStore, WorkerPool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(threadName)s %(message)s")

store = JobStore(config.DB_PATH)
workers = WorkerPool(store)


@asynccontextmanager
async def lifespan(app):
    workers.start()
    yield
    workers.stop()


app = FastAPI(title="Transcription Service", version="1.0.0", lifespan=lifespan)


def check_key(x_api_key: Optional[str] = Header(None)):
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(401, "invalid or missing API key")


async def save_upload(file: UploadFile):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in config.ALLOWED_EXT:
        raise HTTPException(400, f"unsupported format '{ext}', allowed: {sorted(config.ALLOWED_EXT)}")

    limit = config.MAX_UPLOAD_MB * 1024 * 1024
    path = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    size = 0
    with open(path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                f.close()
                path.unlink(missing_ok=True)
                raise HTTPException(413, f"file larger than {config.MAX_UPLOAD_MB}MB")
            f.write(chunk)

    if size == 0:
        path.unlink(missing_ok=True)
        raise HTTPException(400, "file is empty")
    return path


def load_job(job_id):
    job = store.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


def job_view(job):
    out = {
        "job_id": job["id"],
        "filename": job["filename"],
        "status": job["status"],
        "attempts": job["attempts"],
        "error": job["error"],
    }
    if job["status"] == DONE:
        out["result"] = json.loads(job["result"])
    return out


@app.get("/health")
def health():
    return {"status": "ok", "backend": config.BACKEND, "queue": workers.pending()}


@app.post("/v1/transcriptions", status_code=202, dependencies=[Depends(check_key)])
async def create_transcription(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    webhook_url: Optional[str] = Form(None),
):
    path = await save_upload(file)
    job_id = store.create(file.filename, path, language, webhook_url)
    workers.submit(job_id)
    return {"job_id": job_id, "status": QUEUED}


@app.get("/v1/transcriptions", dependencies=[Depends(check_key)])
def list_transcriptions(status: Optional[str] = None, limit: int = Query(50, le=200)):
    return store.list(limit, status)


@app.get("/v1/transcriptions/{job_id}", dependencies=[Depends(check_key)])
def get_transcription(job_id: str):
    return job_view(load_job(job_id))


@app.get("/v1/transcriptions/{job_id}/segments", dependencies=[Depends(check_key)])
def get_segments(job_id: str, format: str = Query("json", pattern="^(json|srt|vtt|txt)$")):
    job = load_job(job_id)
    if job["status"] != DONE:
        raise HTTPException(409, f"job is {job['status']}")

    segments = json.loads(job["result"])["segments"]
    if format == "srt":
        return PlainTextResponse(to_srt(segments))
    if format == "vtt":
        return PlainTextResponse(to_vtt(segments), media_type="text/vtt")
    if format == "txt":
        return PlainTextResponse(to_txt(segments))
    return {"job_id": job_id, "segments": segments}


@app.post("/v1/transcriptions/{job_id}/retry", status_code=202, dependencies=[Depends(check_key)])
def retry_transcription(job_id: str):
    job = load_job(job_id)
    if job["status"] != FAILED:
        raise HTTPException(409, "only failed jobs can be retried")
    if not os.path.exists(job["path"]):
        raise HTTPException(410, "original audio is gone, upload again")

    store.update(job_id, status=QUEUED, attempts=0, error=None)
    workers.submit(job_id)
    return {"job_id": job_id, "status": QUEUED}


@app.delete("/v1/transcriptions/{job_id}", status_code=204, dependencies=[Depends(check_key)])
def delete_transcription(job_id: str):
    job = load_job(job_id)
    if os.path.exists(job["path"]):
        os.remove(job["path"])
    store.delete(job_id)
