import json
import logging
import queue
import sqlite3
import threading
import time
import urllib.request
import uuid
from contextlib import contextmanager
from pathlib import Path

from app import config, pipeline
from app.audio import AudioError

log = logging.getLogger(__name__)

QUEUED, PROCESSING, DONE, FAILED = "queued", "processing", "done", "failed"


class JobStore:
    def __init__(self, db_path):
        self.db_path = db_path
        with self._db() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    path TEXT,
                    language TEXT,
                    webhook_url TEXT,
                    status TEXT,
                    attempts INTEGER DEFAULT 0,
                    error TEXT,
                    result TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def create(self, filename, path, language=None, webhook_url=None):
        job_id = uuid.uuid4().hex
        now = time.time()
        with self._db() as db:
            db.execute(
                "INSERT INTO jobs (id, filename, path, language, webhook_url, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, filename, str(path), language, webhook_url, QUEUED, now, now),
            )
        return job_id

    def get(self, job_id):
        with self._db() as db:
            row = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return dict(row) if row else None

    def update(self, job_id, **fields):
        fields["updated_at"] = time.time()
        cols = ", ".join(f"{k} = ?" for k in fields)
        with self._db() as db:
            db.execute(f"UPDATE jobs SET {cols} WHERE id = ?", (*fields.values(), job_id))

    def list(self, limit=50, status=None):
        sql, args = "SELECT id, filename, status, attempts, error, created_at FROM jobs", []
        if status:
            sql += " WHERE status = ?"
            args.append(status)
        sql += " ORDER BY created_at DESC LIMIT ?"
        args.append(limit)
        with self._db() as db:
            return [dict(r) for r in db.execute(sql, args)]

    def unfinished(self):
        with self._db() as db:
            rows = db.execute("SELECT id FROM jobs WHERE status IN (?, ?)", (QUEUED, PROCESSING))
            return [r["id"] for r in rows]

    def delete(self, job_id):
        with self._db() as db:
            db.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


class WorkerPool:
    def __init__(self, store, size=config.WORKERS):
        self.store = store
        self.size = size
        self.q = queue.Queue()
        self.threads = []

    def start(self):
        # anything left over from a crash or restart gets picked up again
        for job_id in self.store.unfinished():
            self.store.update(job_id, status=QUEUED)
            self.q.put(job_id)

        for i in range(self.size):
            t = threading.Thread(target=self._loop, name=f"worker-{i}", daemon=True)
            t.start()
            self.threads.append(t)
        log.info("started %d workers", self.size)

    def stop(self):
        for _ in self.threads:
            self.q.put(None)
        for t in self.threads:
            t.join(timeout=5)
        self.threads = []
        self.q = queue.Queue()

    def submit(self, job_id):
        self.q.put(job_id)

    def pending(self):
        return self.q.qsize()

    def _loop(self):
        while True:
            job_id = self.q.get()
            if job_id is None:
                break
            try:
                self._process(job_id)
            except Exception:
                log.exception("unexpected error on job %s", job_id)

    def _process(self, job_id):
        job = self.store.get(job_id)
        if not job or job["status"] in (DONE, FAILED):
            return

        attempt = job["attempts"] + 1
        self.store.update(job_id, status=PROCESSING, attempts=attempt)
        log.info("job %s attempt %d", job_id, attempt)

        try:
            result = pipeline.run(job["path"], job["language"])
        except AudioError as e:
            self._fail(job, str(e))
            return
        except Exception as e:
            log.warning("job %s failed: %s", job_id, e)
            if attempt >= config.MAX_ATTEMPTS:
                self._fail(job, f"gave up after {attempt} attempts: {e}")
            else:
                delay = 2 ** attempt
                self.store.update(job_id, status=QUEUED, error=str(e))
                threading.Timer(delay, self.q.put, args=(job_id,)).start()
            return

        self.store.update(job_id, status=DONE, result=json.dumps(result), error=None)
        Path(job["path"]).unlink(missing_ok=True)
        self._notify(job_id, job["webhook_url"])

    def _fail(self, job, error):
        self.store.update(job["id"], status=FAILED, error=error)
        self._notify(job["id"], job["webhook_url"])

    def _notify(self, job_id, url):
        if not url:
            return
        job = self.store.get(job_id)
        body = json.dumps({"job_id": job_id, "status": job["status"], "error": job["error"]}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            log.warning("webhook for %s failed: %s", job_id, e)
