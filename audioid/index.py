from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType

from .models import Fingerprint


class FingerprintIndex:
    """Read-optimized inverted index: fingerprint hash -> song/time occurrences."""

    def __init__(self) -> None:
        self._postings: dict[str, tuple[tuple[str, int], ...]] = {}
        self._fingerprints: dict[str, Fingerprint] = {}
        self.ready = False

    @property
    def song_count(self) -> int:
        return len(self._fingerprints)

    @property
    def hash_count(self) -> int:
        return len(self._postings)

    @property
    def fingerprints(self) -> MappingProxyType:
        return MappingProxyType(self._fingerprints)

    def build(self, fingerprints: list[Fingerprint]) -> None:
        postings: dict[str, list[tuple[str, int]]] = defaultdict(list)
        compact_fingerprints: dict[str, Fingerprint] = {}
        for fingerprint in fingerprints:
            compact_fingerprints[fingerprint.song_id] = fingerprint
            for digest, offset in fingerprint.hashes:
                postings[digest].append((fingerprint.song_id, offset))
        self._postings = {digest: tuple(values) for digest, values in postings.items()}
        self._fingerprints = compact_fingerprints
        self.ready = True

    def lookup(self, digest: str) -> tuple[tuple[str, int], ...]:
        return self._postings.get(digest, ())
