# Audio Identification & Source Detection System

## Team Information
- **Team Name**: HackOrbit
- **Year**: 2nd year
- **All-Female Team**: no

## Architecture Overview

#### Describe your approach here. Keep it short and clear.

    - The system loads song metadata from CSV/JSON/Markdown/folders into typed records, decodes WAV audio, and links every generated fingerprint back to the song_id.
    - A baseline FeatureExtractor creates compact hash/time-offset fingerprints from coarse waveform energy and zero-crossing features; the extractor is abstract so spectrogram or neural embeddings can be swapped in later.
    - Fingerprints are stored in an in-memory inverted index: hash -> [(song_id, offset)]. Query matching uses fast hash lookup plus offset voting to identify partial clips without brute-forcing every song.
    - The HTTP API uses Python's ThreadingHTTPServer with an immutable read-only index after startup, supports concurrent queries, reports health, rejects invalid/silent/short inputs, and returns confidence plus latency metrics.

**Note:** Please do not change the format or spelling of anything in this README. The fields are extracted using a script, so any changes to the structure or formatting may break the extraction process.

## Project Status

This project is a working dependency-light audio identification app. It can load a WAV catalog, fingerprint known songs, identify short WAV query clips, show confidence and latency, expose HTTP endpoints, and provide a browser UI for testing.

Implemented areas:

- Dataset metadata ingestion from CSV, JSON, JSONL, Markdown tables, or folders of `.wav` files.
- PCM WAV decoding with mono conversion for multi-channel audio.
- Query validation for unsupported formats, corrupt files, empty files, very short clips, and silent or very quiet audio.
- Baseline spectral fingerprint extraction using compact peak hashes.
- In-memory inverted fingerprint index for fast lookup.
- Offset-voting matcher with confidence scores and top candidate reporting.
- Health reporting for loaded songs, indexed songs, hash count, skipped records, and startup errors.
- CLI commands for health checks, identifying files, importing songs, making query clips, evaluating accuracy, and serving the UI/API.
- HTTP API with concurrent request handling through `ThreadingHTTPServer`.
- Browser UI for checking system status, browsing catalog entries, selecting bundled query files, typing a query path, uploading a WAV query, and viewing match details.

## Folder Layout

```text
audioid/
  audio.py        WAV loading and query validation
  cli.py          Command-line entry point
  evaluation.py   Batch accuracy evaluation helpers
  features.py     Feature extraction interface and baseline fingerprinting
  http_api.py     HTTP API and browser UI
  index.py        In-memory inverted fingerprint index
  ingestion.py    Dataset metadata loaders
  matcher.py      Matching and confidence scoring
  models.py       Shared dataclasses
  service.py      Main orchestration service
  tools.py        Song import and query clip utilities
data/
  catalog.csv     Active song catalog
  songs/          Full WAV songs
  queries/        Query WAV snippets
  demo_wav/       Generated demo tones and sample clips
tests/
  test_system.py  End-to-end service tests
```

## Current Dataset

The active catalog is `data/catalog.csv`. It currently includes the bundled demo tones and `bak.wav`:

- `demo_low` - Demo Low Tone
- `demo_mid` - Demo Mid Tone
- `demo_high` - Demo High Tone
- `bak` - BAK

Important data note: `data/songs/song1.wav` is currently a 0-byte file, so it is not valid audio yet. Replace it with a real PCM `.wav` file or import a valid song before expecting it to identify.

## Requirements

- Python 3.11 or newer.
- No runtime third-party packages are required for the main app.
- Optional: install `pytest` if you want to run the test suite.
- Audio files must be valid PCM `.wav` files. MP3, M4A, FLAC, empty files, and corrupt WAV files are rejected.

## Quick Start

Run these commands from PowerShell:

```powershell
cd "c:\Users\ml907\OneDrive\Desktop\audio on code 2 force\ps1"
python -m audioid --dataset data/catalog.csv health
python -m audioid --dataset data/catalog.csv identify data/queries/bak_query.wav
python -m audioid --dataset data/catalog.csv serve --host 127.0.0.1 --port 8010
```

After the server starts, keep that terminal open and visit:

```text
http://127.0.0.1:8010/
```

## Run The App

From the project folder:

```powershell
cd "c:\Users\ml907\OneDrive\Desktop\audio on code 2 force\ps1"
python -m audioid --dataset data/catalog.csv serve --host 127.0.0.1 --port 8010
```

Then open:

```text
http://127.0.0.1:8010/
```

If port `8010` is busy, choose another port:

```powershell
python -m audioid --dataset data/catalog.csv serve --host 127.0.0.1 --port 8020
```

The server runs in the foreground. Stop it with `Ctrl+C`.

## Browser UI

The UI supports:

- Viewing service health and index status.
- Viewing the loaded catalog.
- Clicking bundled sample query buttons.
- Typing a WAV query path such as `data/queries/bak_query.wav`.
- Uploading a local `.wav` query file.
- Seeing the final status, matched song, confidence, latency, top candidates, and raw JSON response.

## CLI Commands

Check service health:

```powershell
python -m audioid --dataset data/catalog.csv health
```

Identify a query:

```powershell
python -m audioid --dataset data/catalog.csv identify data/queries/bak_query.wav
```

Create a short query clip from a full song:

```powershell
python -m audioid make-query data/songs/bak.wav data/queries/bak_new_query.wav --start 10 --duration 5
```

Import a valid PCM WAV into `data/songs` and update `data/catalog.csv`:

```powershell
python -m audioid import-song "C:\path\to\song.wav" --song-id song1 --title "Song 1" --artist "Unknown Artist" --genre unknown --replace
```

If your source song is not a WAV file, convert it to PCM WAV first. Example with FFmpeg:

```powershell
ffmpeg -i "C:\path\to\song.mp3" -ac 1 -ar 44100 "C:\path\to\song.wav"
```

Evaluate a batch manifest:

```powershell
python -m audioid --dataset data/catalog.csv evaluate data/evaluation.csv
```

The evaluation CSV should contain:

```csv
query_path,expected_song_id
data/queries/bak_query.wav,bak
```

## HTTP API

Health check:

```text
GET /health
```

Loaded songs:

```text
GET /songs
```

Bundled query files for the UI:

```text
GET /queries
```

Identify by server-side file path:

```text
GET /identify?file=data/queries/bak_query.wav
```

Identify by JSON body:

```text
POST /identify
Content-Type: application/json

{"file": "data/queries/bak_query.wav"}
```

Upload and identify a WAV file:

```text
POST /identify-upload
Content-Type: audio/wav
```

## Response Format

Successful match example:

```json
{
  "status": "matched",
  "confidence": 0.7,
  "latency_ms": 250.54,
  "message": "",
  "song": {
    "song_id": "bak",
    "title": "BAK",
    "artist": "Unknown Artist",
    "duration_seconds": 8.33,
    "genre": "unknown"
  },
  "candidates": [
    {
      "song_id": "bak",
      "votes": 132,
      "aligned_offset": 8,
      "raw_overlap": 6034,
      "confidence": 0.7
    }
  ]
}
```

Possible statuses:

- `matched` - a candidate passed the confidence threshold.
- `unknown` - candidates were found, but none passed the threshold.
- `rejected` - the query was invalid, unsupported, silent, too short, empty, or corrupt.
- `error` - the service was not ready or the index could not be used.

## Validation Performed

The following commands were checked successfully:

```powershell
python -m audioid --dataset data\catalog.csv health
python -m audioid --dataset data\catalog.csv identify data\queries\bak_query.wav
python -m audioid --dataset data\catalog.csv identify data\queries\demo_low_query.wav
python -m audioid --dataset data\catalog.csv identify data\songs\song1.wav
```

Observed behavior:

- `data/catalog.csv` loads cleanly with status `ok`.
- `data/queries/bak_query.wav` matches `bak`.
- `data/queries/demo_low_query.wav` matches `demo_low`.
- `data/songs/song1.wav` is rejected cleanly because it is an empty or corrupt WAV file.

The Python environment used during this update did not have `pytest` installed, so `python -m pytest` could not be run until the optional test dependency is installed.

## Run Tests

The app itself has no third-party runtime dependencies, but tests need `pytest`:

```powershell
python -m pip install pytest
python -m pytest
```

If package installation is not allowed in your environment, use the CLI validation commands above to verify the main workflow.

## Troubleshooting

If the UI does not open:

- Make sure the `serve` command is still running.
- Try a different port, for example `--port 8020`.
- Open the exact URL printed by the server.
- Check that you started the command from the `ps1` project folder.

If a song or query is rejected:

- Confirm the file is not 0 bytes.
- Confirm the file extension is `.wav`.
- Confirm it is a valid PCM WAV file, not an MP3 renamed to `.wav`.
- Confirm the query is at least 1 second long and not silent.

If matching returns `unknown`:

- Use a query clip cut from a song already listed in `data/catalog.csv`.
- Use a 3-10 second query for better results.
- Re-run `health` and confirm `songs_indexed` is greater than 0.

If `song1.wav` does not work:

- Replace `data/songs/song1.wav` with a real WAV file.
- Or import a real song with `python -m audioid import-song ... --replace`.

## Recent Fixes

- Folder-based datasets now resolve audio paths correctly without double-prefixing the folder path.
- Invalid or empty WAV files now return clean rejection errors instead of uncaught exceptions.
- The browser UI now has a `/queries` endpoint and quick-select buttons for bundled sample WAV files.
- JSON request bodies now return a clear `invalid JSON request body` message when malformed.
