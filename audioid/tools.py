from __future__ import annotations

import csv
import re
import shutil
import wave
from pathlib import Path


CATALOG_FIELDS = ["song_id", "title", "artist", "duration_seconds", "genre", "audio_path"]


def import_song(
    source: Path,
    catalog_path: Path,
    songs_dir: Path,
    song_id: str | None = None,
    title: str | None = None,
    artist: str = "unknown",
    genre: str = "unknown",
    replace: bool = False,
) -> dict[str, str]:
    source = source.expanduser().resolve()
    if source.suffix.lower() != ".wav":
        raise ValueError("only PCM .wav files can be imported; convert MP3/M4A/FLAC to WAV first")
    duration = wav_duration_seconds(source)
    if duration <= 0:
        raise ValueError("audio file is empty")

    song_id = _clean_song_id(song_id or source.stem)
    if not song_id:
        raise ValueError("song_id cannot be empty")
    title = (title or source.stem.replace("_", " ").title()).strip()
    artist = artist.strip() or "unknown"
    genre = genre.strip() or "unknown"

    songs_dir.mkdir(parents=True, exist_ok=True)
    destination = (songs_dir / f"{song_id}.wav").resolve()
    if destination.exists() and destination != source and not replace:
        raise ValueError(f"{destination} already exists; pass --replace to overwrite it")
    if destination != source:
        shutil.copy2(source, destination)

    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    rows = _read_catalog(catalog_path)
    if any(row.get("song_id") == song_id for row in rows) and not replace:
        raise ValueError(f"song_id {song_id!r} already exists in {catalog_path}; pass --replace to update it")

    audio_path = _display_path(destination)
    record = {
        "song_id": song_id,
        "title": title,
        "artist": artist,
        "duration_seconds": f"{duration:.2f}",
        "genre": genre,
        "audio_path": audio_path,
    }
    rows = [row for row in rows if row.get("song_id") != song_id]
    rows.append(record)
    _write_catalog(catalog_path, rows)
    return record


def make_query_clip(source: Path, destination: Path, start_seconds: float, duration_seconds: float) -> dict[str, str]:
    if duration_seconds <= 0:
        raise ValueError("duration must be greater than 0")
    if start_seconds < 0:
        raise ValueError("start must be 0 or greater")

    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()
    if source.suffix.lower() != ".wav" or destination.suffix.lower() != ".wav":
        raise ValueError("source and destination must both be .wav files")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source), "rb") as src:
        frame_rate = src.getframerate()
        total_frames = src.getnframes()
        start_frame = min(total_frames, int(start_seconds * frame_rate))
        clip_frames = min(total_frames - start_frame, int(duration_seconds * frame_rate))
        if clip_frames <= 0:
            raise ValueError("start is beyond the end of the source audio")
        src.setpos(start_frame)
        frames = src.readframes(clip_frames)
        params = src.getparams()

    with wave.open(str(destination), "wb") as out:
        out.setparams(params)
        out.writeframes(frames)

    return {
        "source": _display_path(source),
        "query": _display_path(destination),
        "start_seconds": f"{start_seconds:.2f}",
        "duration_seconds": f"{clip_frames / frame_rate:.2f}",
    }


def wav_duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav:
            frame_rate = wav.getframerate()
            frame_count = wav.getnframes()
            if frame_rate <= 0:
                raise ValueError("invalid WAV sample rate")
            return frame_count / frame_rate
    except (EOFError, OSError, wave.Error) as exc:
        detail = str(exc) or "file is empty or corrupt"
        raise ValueError(f"invalid WAV file: {detail}") from exc


def _read_catalog(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CATALOG_FIELDS})


def _clean_song_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return cleaned.strip("_").lower()


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)
