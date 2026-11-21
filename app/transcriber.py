import threading
from dataclasses import dataclass

from app import config
from app.audio import probe_duration


@dataclass
class Segment:
    start: float
    end: float
    text: str


class WhisperTranscriber:
    def __init__(self):
        from faster_whisper import WhisperModel
        self.model = WhisperModel(config.MODEL_SIZE, device=config.DEVICE, compute_type=config.COMPUTE_TYPE)

    def transcribe(self, path, language=None):
        segments, info = self.model.transcribe(str(path), language=language, beam_size=5, vad_filter=True)
        result = [Segment(s.start, s.end, s.text.strip()) for s in segments]
        return result, info.language


class MockTranscriber:
    lines = [
        "Hello and thanks for calling.",
        "I'd like to check the status of my booking.",
        "Sure, can I have the reference number please?",
        "It's A B C one two three.",
        "Thanks, give me a moment to look that up.",
    ]

    def transcribe(self, path, language=None):
        duration = probe_duration(path)
        out, t, i = [], 0.0, 0
        while t < duration:
            end = min(t + 4.0, duration)
            out.append(Segment(t, end, self.lines[i % len(self.lines)]))
            t, i = end, i + 1
        return out, language or "en"


_model = None
_lock = threading.Lock()


def get_transcriber():
    global _model
    with _lock:
        if _model is None:
            _model = MockTranscriber() if config.BACKEND == "mock" else WhisperTranscriber()
    return _model
