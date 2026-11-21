import json
import subprocess
from pathlib import Path


class AudioError(Exception):
    """Bad input audio. Retrying won't fix it."""


def probe_duration(path):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        return float(json.loads(out.stdout)["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError) as e:
        raise AudioError("could not read audio file") from e


def normalize(src, dst):
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-ac", "1", "-ar", "16000", str(dst)],
            check=True, capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise AudioError("could not decode audio file") from e
    return Path(dst)


def split(path, chunk_sec):
    path = Path(path)
    out_dir = path.parent / f"{path.stem}_chunks"
    out_dir.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(path), "-f", "segment",
         "-segment_time", str(chunk_sec), "-c", "copy", str(out_dir / "%04d.wav")],
        check=True, capture_output=True,
    )
    return sorted(out_dir.glob("*.wav"))
