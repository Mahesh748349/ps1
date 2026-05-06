# Architecture

This project implements a dependency-light baseline for audio identification and source detection. It is designed for hackathon review: easy to run, clear to inspect, and structured so stronger DSP or ML models can replace the baseline extractor later.

## Flow

1. Dataset metadata is loaded by `DatasetCatalog` from CSV, JSON, JSONL, Markdown tables, or a folder of `.wav` files.
2. Each valid audio file is decoded into mono floating-point samples.
3. `FeatureExtractor` converts audio into standardized `(hash, time_offset)` fingerprints.
4. `FingerprintIndex` builds an inverted index from each hash to matching song/time occurrences.
5. Query clips pass through the same decoder, validation, and feature extractor.
6. `MatchingEngine` uses hash lookups and offset voting to find the strongest aligned song candidate.
7. The service returns status, song metadata, confidence, top candidates, and end-to-end latency.

## Key Choices

- Metadata and fingerprints are separate but linked by `song_id`.
- The index is immutable after startup, so concurrent HTTP requests can read it safely.
- The baseline extractor uses coarse waveform features and hashes so it can run without external packages.
- Matching is fuzzy by design: it counts consistent time-offset votes instead of requiring every hash to match.
- Unknown results are returned when confidence is below a threshold to reduce false positives.

## Scaling

For a few thousand songs, the in-memory inverted index is fast and simple. Each query only touches postings for hashes present in the snippet, avoiding full database scans. For larger datasets, the same schema can move to SQLite, Redis, RocksDB, or an approximate nearest-neighbor vector index while keeping the `FeatureExtractor` and `MatchingEngine` contracts stable.

## Supported Audio

The current baseline supports PCM `.wav` files using the Python standard library. MP3, FLAC, and neural embeddings can be added behind the same interfaces with optional dependencies such as ffmpeg, librosa, or a model runtime.
