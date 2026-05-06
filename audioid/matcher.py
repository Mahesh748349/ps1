from __future__ import annotations

import time
from collections import Counter, defaultdict

from .index import FingerprintIndex
from .models import CandidateScore, Fingerprint, IdentificationResult, SongMetadata


class MatchingEngine:
    def __init__(self, index: FingerprintIndex, catalog: dict[str, SongMetadata], threshold: float = 0.18) -> None:
        self.index = index
        self.catalog = catalog
        self.threshold = threshold

    def identify(self, query: Fingerprint, started_at: float | None = None) -> IdentificationResult:
        started = started_at or time.perf_counter()
        if not self.index.ready:
            return self._result("error", None, 0.0, (), started, "index is not ready")
        if not query.hashes:
            return self._result("rejected", None, 0.0, (), started, "query produced no fingerprints")

        offset_votes: dict[str, Counter[int]] = defaultdict(Counter)
        raw_overlap = Counter()
        for digest, query_offset in query.hashes:
            for song_id, song_offset in self.index.lookup(digest):
                raw_overlap[song_id] += 1
                offset_votes[song_id][song_offset - query_offset] += 1

        candidates: list[CandidateScore] = []
        query_size = max(1, len(query.hashes))
        for song_id, votes_by_offset in offset_votes.items():
            aligned_offset, votes = votes_by_offset.most_common(1)[0]
            song_size = max(1, len(self.index.fingerprints[song_id].hashes))
            coverage = votes / min(query_size, song_size)
            support = raw_overlap[song_id] / query_size
            confidence = min(1.0, coverage * 0.75 + min(1.0, support) * 0.25)
            candidates.append(
                CandidateScore(
                    song_id=song_id,
                    votes=votes,
                    aligned_offset=aligned_offset,
                    raw_overlap=raw_overlap[song_id],
                    confidence=round(confidence, 4),
                )
            )

        candidates.sort(key=lambda item: (item.confidence, item.votes, item.raw_overlap), reverse=True)
        top = candidates[0] if candidates else None
        if not top or top.confidence < self.threshold:
            return self._result(
                "unknown",
                None,
                top.confidence if top else 0.0,
                tuple(candidates[:5]),
                started,
                "no candidate passed confidence threshold",
            )
        return self._result("matched", self.catalog.get(top.song_id), top.confidence, tuple(candidates[:5]), started)

    def _result(
        self,
        status: str,
        song: SongMetadata | None,
        confidence: float,
        candidates: tuple[CandidateScore, ...],
        started: float,
        message: str = "",
    ) -> IdentificationResult:
        return IdentificationResult(
            status=status,
            song=song,
            confidence=round(confidence, 4),
            candidates=candidates,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            message=message,
        )
