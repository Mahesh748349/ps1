from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod

from .models import AudioSignal, Fingerprint


class FeatureExtractor(ABC):
    @abstractmethod
    def extract(self, signal: AudioSignal, song_id: str = "query") -> Fingerprint:
        raise NotImplementedError


class BaselineFingerprintExtractor(FeatureExtractor):
    """Spectral peak fingerprinting without external dependencies."""

    def __init__(self, window_seconds: float = 0.45, hop_seconds: float = 0.12) -> None:
        self.window_seconds = window_seconds
        self.hop_seconds = hop_seconds
        self.frequency_bins = (
            80,
            110,
            150,
            205,
            280,
            380,
            520,
            700,
            950,
            1300,
            1750,
            2350,
            3150,
            4200,
            5600,
        )

    def extract(self, signal: AudioSignal, song_id: str = "query") -> Fingerprint:
        window = max(512, int(signal.sample_rate * self.window_seconds))
        hop = max(256, int(signal.sample_rate * self.hop_seconds))
        hashes: list[tuple[str, int]] = []
        samples = signal.samples
        if len(samples) < window:
            return Fingerprint(song_id=song_id, hashes=(), duration_seconds=signal.duration_seconds)

        offset = 0
        for start in range(0, len(samples) - window + 1, hop):
            frame = samples[start : start + window]
            rms = math.sqrt(sum(value * value for value in frame) / len(frame))
            if rms < 0.002:
                offset += 1
                continue

            peaks = self._spectral_peaks(frame, signal.sample_rate)
            for left_index, left_peak in enumerate(peaks):
                for right_peak in peaks[left_index + 1 :]:
                    spread = right_peak - left_peak
                    payload = f"{left_peak}|{right_peak}|{spread}"
                    digest = hashlib.blake2s(payload.encode("ascii"), digest_size=6).hexdigest()
                    hashes.append((digest, offset))
            offset += 1

        return Fingerprint(song_id=song_id, hashes=tuple(hashes), duration_seconds=signal.duration_seconds)

    def _spectral_peaks(self, frame: tuple[float, ...], sample_rate: int) -> tuple[int, ...]:
        compact = _compact_frame(frame, target_size=1536)
        energies: list[tuple[float, int]] = []
        for bin_index, frequency in enumerate(self.frequency_bins):
            if frequency >= sample_rate / 2:
                continue
            energy = _goertzel_energy(compact, sample_rate, frequency)
            energies.append((energy, bin_index))
        if not energies:
            return ()
        energies.sort(reverse=True)
        return tuple(sorted(bin_index for _, bin_index in energies[:5]))


def _clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def _compact_frame(frame: tuple[float, ...], target_size: int) -> tuple[float, ...]:
    if len(frame) <= target_size:
        return frame
    stride = len(frame) / target_size
    compact: list[float] = []
    for index in range(target_size):
        start = int(index * stride)
        end = max(start + 1, int((index + 1) * stride))
        chunk = frame[start:end]
        compact.append(sum(chunk) / len(chunk))
    return tuple(compact)


def _goertzel_energy(samples: tuple[float, ...], sample_rate: int, frequency: int) -> float:
    normalized = frequency / sample_rate
    coefficient = 2.0 * math.cos(2.0 * math.pi * normalized)
    previous = 0.0
    previous_2 = 0.0
    for sample in samples:
        value = sample + coefficient * previous - previous_2
        previous_2 = previous
        previous = value
    return previous_2 * previous_2 + previous * previous - coefficient * previous * previous_2
