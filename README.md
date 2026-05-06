# Audio Identification & Source Detection System

## Team Information
- **Team Name**: [Team Name]
- **Year**: [Year]
- **All-Female Team**: [Yes/No]

## Architecture Overview

#### Describe your approach here. Keep it short and clear.

    - The system loads song metadata from CSV/JSON/Markdown/folders into typed records, decodes WAV audio, and links every generated fingerprint back to the song_id.
    - A baseline FeatureExtractor creates compact hash/time-offset fingerprints from coarse waveform energy and zero-crossing features; the extractor is abstract so spectrogram or neural embeddings can be swapped in later.
    - Fingerprints are stored in an in-memory inverted index: hash -> [(song_id, offset)]. Query matching uses fast hash lookup plus offset voting to identify partial clips without brute-forcing every song.
    - The HTTP API uses Python's ThreadingHTTPServer with an immutable read-only index after startup, supports concurrent queries, reports health, rejects invalid/silent/short inputs, and returns confidence plus latency metrics.

**Note:** Please do not change the format or spelling of anything in this README. The fields are extracted using a script, so any changes to the structure or formatting may break the extraction process.
