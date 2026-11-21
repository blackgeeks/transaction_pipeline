import time


def wait_for(client, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        job = client.get(f"/v1/transcriptions/{job_id}").json()
        if job["status"] in ("done", "failed"):
            return job
        time.sleep(0.2)
    raise AssertionError("job did not finish")


def upload(client, path):
    with open(path, "rb") as f:
        return client.post("/v1/transcriptions", files={"file": (path.name, f)})


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_wav_and_mp3(client, audio):
    for name in ("short.wav", "short.mp3"):
        r = upload(client, audio(name))
        assert r.status_code == 202
        job = wait_for(client, r.json()["job_id"])
        assert job["status"] == "done"
        segs = job["result"]["segments"]
        assert segs and segs[0]["start"] == 0.0
        assert all(s["end"] > s["start"] for s in segs)


def test_long_audio_is_chunked_with_correct_offsets(client, audio):
    r = upload(client, audio("long.wav", 12))
    job = wait_for(client, r.json()["job_id"])
    segs = job["result"]["segments"]
    starts = [s["start"] for s in segs]
    assert starts == sorted(starts)
    assert segs[-1]["end"] >= 11.5


def test_subtitle_formats(client, audio):
    job_id = upload(client, audio("subs.wav", 6)).json()["job_id"]
    wait_for(client, job_id)
    srt = client.get(f"/v1/transcriptions/{job_id}/segments?format=srt").text
    vtt = client.get(f"/v1/transcriptions/{job_id}/segments?format=vtt").text
    assert "00:00:00,000 -->" in srt
    assert vtt.startswith("WEBVTT")


def test_rejects_bad_extension(client, tmp_path):
    p = tmp_path / "notes.txt"
    p.write_text("hello")
    assert upload(client, p).status_code == 400


def test_corrupt_audio_fails_without_retry(client, tmp_path):
    p = tmp_path / "broken.mp3"
    p.write_bytes(b"this is not audio" * 100)
    job = wait_for(client, upload(client, p).json()["job_id"])
    assert job["status"] == "failed"
    assert job["attempts"] == 1


def test_unknown_job(client):
    assert client.get("/v1/transcriptions/nope").status_code == 404
