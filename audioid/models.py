from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class SongMetadata:
    song_id: str
    title: str
    artist: str
    duration_seconds: float
    genre: str = "unknown"
    audio_path: Path | None = None


@dataclass(frozen=True, slots=True)
class AudioSignal:
    samples: tuple[float, ...]
    sample_rate: int
    duration_seconds: float
    source_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Fingerprint:
    song_id: str
    hashes: tuple[tuple[str, int], ...]
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class CandidateScore:
    song_id: str
    votes: int
    aligned_offset: int
    raw_overlap: int
    confidence: float


@dataclass(frozen=True, slots=True)
class IdentificationResult:
    status: str
    song: SongMetadata | None
    confidence: float
    candidates: tuple[CandidateScore, ...]
    latency_ms: float
    message: str = ""


@dataclass(frozen=True, slots=True)
class IngestionReport:
    loaded: int
    skipped: int
    errors: tuple[str, ...]
