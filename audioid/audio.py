from __future__ import annotations

import math
import wave
from pathlib import Path

from .models import AudioSignal


class QueryValidationError(ValueError):
    pass


def load_wav(path: Path, metadata: dict | None = None) -> AudioSignal:
    if path.suffix.lower() != ".wav":
        raise QueryValidationError("unsupported audio format; please provide a PCM .wav file")
    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            sample_rate = wav.getframerate()
            frame_count = wav.getnframes()
            raw = wav.readframes(frame_count)
    except (EOFError, OSError, wave.Error) as exc:
        detail = str(exc) or "file is empty or corrupt"
        raise QueryValidationError(f"invalid wav file: {detail}") from exc

    if sample_width not in {1, 2, 4}:
        raise QueryValidationError(f"unsupported sample width: {sample_width} bytes")
    if frame_count == 0:
        raise QueryValidationError("audio file is empty")

    samples = _decode_pcm(raw, sample_width, channels)
    duration = len(samples) / sample_rate if sample_rate else 0.0
    return AudioSignal(
        samples=tuple(samples),
        sample_rate=sample_rate,
        duration_seconds=duration,
        source_path=path,
        metadata=metadata or {},
    )


def validate_query(signal: AudioSignal, min_seconds: float = 1.0) -> None:
    if signal.duration_seconds < min_seconds:
        raise QueryValidationError(f"query is too short; minimum is {min_seconds:.1f}s")
    if not signal.samples:
        raise QueryValidationError("query contains no samples")
    rms = math.sqrt(sum(sample * sample for sample in signal.samples) / len(signal.samples))
    if rms < 0.002:
        raise QueryValidationError("query is silent or too quiet to identify")


def _decode_pcm(raw: bytes, sample_width: int, channels: int) -> list[float]:
    max_value = float((1 << (8 * sample_width - 1)) - 1)
    samples: list[float] = []
    frame_size = sample_width * channels
    for index in range(0, len(raw), frame_size):
        channel_values = []
        for channel in range(channels):
            start = index + channel * sample_width
            chunk = raw[start : start + sample_width]
            if sample_width == 1:
                value = chunk[0] - 128
                divisor = 128.0
            else:
                value = int.from_bytes(chunk, "little", signed=True)
                divisor = max_value
            channel_values.append(value / divisor)
        samples.append(sum(channel_values) / len(channel_values))
    return samples
