import logging
import shutil
from pathlib import Path

from app import config
from app.audio import AudioError, normalize, probe_duration, split
from app.transcriber import get_transcriber

log = logging.getLogger(__name__)


def run(src_path, language=None):
    src = Path(src_path)
    wav = src.with_name(f"{src.stem}_16k.wav")
    normalize(src, wav)

    try:
        duration = probe_duration(wav)
        if duration > config.MAX_DURATION_SEC:
            raise AudioError(f"audio is {duration:.0f}s, limit is {config.MAX_DURATION_SEC}s")

        model = get_transcriber()
        if duration <= config.CHUNK_SEC:
            segments, lang = model.transcribe(wav, language)
        else:
            segments, lang = _transcribe_chunked(model, wav, language)
    finally:
        wav.unlink(missing_ok=True)
        shutil.rmtree(wav.parent / f"{wav.stem}_chunks", ignore_errors=True)

    segs = [
        {"id": i, "start": round(s.start, 2), "end": round(s.end, 2), "text": s.text}
        for i, s in enumerate(s for s in segments if s.text)
    ]
    return {
        "language": lang,
        "duration": round(duration, 2),
        "text": " ".join(s["text"] for s in segs),
        "segments": segs,
    }


def _transcribe_chunked(model, wav, language):
    chunks = split(wav, config.CHUNK_SEC)
    log.info("split %s into %d chunks", wav.name, len(chunks))

    segments, offset, lang = [], 0.0, language
    for chunk in chunks:
        part, detected = model.transcribe(chunk, lang)
        lang = lang or detected
        for s in part:
            s.start += offset
            s.end += offset
        segments.extend(part)
        offset += probe_duration(chunk)
    return segments, lang
