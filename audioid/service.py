from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from .audio import QueryValidationError, load_wav, validate_query
from .features import BaselineFingerprintExtractor, FeatureExtractor
from .index import FingerprintIndex
from .ingestion import DatasetCatalog
from .matcher import MatchingEngine
from .models import Fingerprint, IdentificationResult

LOGGER = logging.getLogger(__name__)


class AudioIdentificationService:
    def __init__(
        self,
        dataset_path: Path,
        audio_root: Path | None = None,
        extractor: FeatureExtractor | None = None,
        threshold: float = 0.18,
    ) -> None:
        self.dataset_path = dataset_path
        self.audio_root = audio_root
        self.extractor = extractor or BaselineFingerprintExtractor()
        self.catalog = DatasetCatalog()
        self.index = FingerprintIndex()
        self.engine: MatchingEngine | None = None
        self.errors: list[str] = []
        self.threshold = threshold
        self.started_at: float | None = None

    def start(self) -> None:
        self.started_at = time.perf_counter()
        self.catalog.load(self.dataset_path, self.audio_root)
        fingerprints: list[Fingerprint] = []
        for song in self.catalog.songs.values():
            if not song.audio_path:
                self.errors.append(f"{song.song_id}: missing audio_path")
                continue
            try:
                signal = load_wav(song.audio_path)
                fingerprints.append(self.extractor.extract(signal, song.song_id))
            except (OSError, QueryValidationError, ValueError) as exc:
                message = f"{song.song_id}: {exc}"
                self.errors.append(message)
                LOGGER.warning("Could not fingerprint song: %s", message)
        self.index.build(fingerprints)
        self.engine = MatchingEngine(self.index, self.catalog.songs, threshold=self.threshold)

    def identify_file(self, path: Path, metadata: dict[str, Any] | None = None) -> IdentificationResult:
        started = time.perf_counter()
        try:
            signal = load_wav(path, metadata=metadata)
            validate_query(signal)
            fingerprint = self.extractor.extract(signal, "query")
        except QueryValidationError as exc:
            return IdentificationResult("rejected", None, 0.0, (), round((time.perf_counter() - started) * 1000, 2), str(exc))
        if self.engine is None:
            return IdentificationResult("error", None, 0.0, (), round((time.perf_counter() - started) * 1000, 2), "service not started")
        result = self.engine.identify(fingerprint, started_at=started)
        LOGGER.info("identified %s confidence=%s latency_ms=%s", result.status, result.confidence, result.latency_ms)
        return result

    def health(self) -> dict[str, Any]:
        uptime_ms = round((time.perf_counter() - self.started_at) * 1000, 2) if self.started_at else 0.0
        dataset_loaded = self.catalog.report.loaded > 0
        return {
            "status": "ok" if dataset_loaded and self.index.ready and not self.errors else "degraded",
            "dataset_loaded": dataset_loaded,
            "index_ready": self.index.ready,
            "songs_loaded": self.catalog.report.loaded,
            "songs_indexed": self.index.song_count,
            "hashes_indexed": self.index.hash_count,
            "skipped_records": self.catalog.report.skipped,
            "errors": [*self.catalog.report.errors[:10], *self.errors[:10]],
            "uptime_ms": uptime_ms,
        }


def result_to_dict(result: IdentificationResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
        "message": result.message,
        "song": None
        if result.song is None
        else {
            "song_id": result.song.song_id,
            "title": result.song.title,
            "artist": result.song.artist,
            "duration_seconds": result.song.duration_seconds,
            "genre": result.song.genre,
        },
        "candidates": [
            {
                "song_id": item.song_id,
                "votes": item.votes,
                "aligned_offset": item.aligned_offset,
                "raw_overlap": item.raw_overlap,
                "confidence": item.confidence,
            }
            for item in result.candidates
        ],
    }


def dumps_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)
