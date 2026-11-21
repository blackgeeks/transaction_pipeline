import os
import subprocess
import tempfile

import pytest

os.environ["TRANSCRIBER"] = "mock"
os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["CHUNK_SEC"] = "5"
os.environ["WORKERS"] = "2"


def make_audio(path, seconds, fmt=None):
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    subprocess.run(cmd + [str(path)], check=True)
    return path


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def audio(tmp_path):
    return lambda name, seconds=3: make_audio(tmp_path / name, seconds)
