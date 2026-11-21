def _ts(seconds, sep):
    ms = int(round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02}{sep}{ms:03}"


def to_srt(segments):
    blocks = []
    for i, s in enumerate(segments, 1):
        blocks.append(f"{i}\n{_ts(s['start'], ',')} --> {_ts(s['end'], ',')}\n{s['text']}\n")
    return "\n".join(blocks)


def to_vtt(segments):
    lines = ["WEBVTT", ""]
    for s in segments:
        lines.append(f"{_ts(s['start'], '.')} --> {_ts(s['end'], '.')}")
        lines.append(s["text"])
        lines.append("")
    return "\n".join(lines)


def to_txt(segments):
    return "\n".join(f"[{_ts(s['start'], '.')}] {s['text']}" for s in segments)
