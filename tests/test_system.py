from __future__ import annotations

import csv
import math
import wave
from pathlib import Path

from audioid.service import AudioIdentificationService


def test_identifies_clean_partial_query(tmp_path: Path) -> None:
    song_a = tmp_path / "song_a.wav"
    song_b = tmp_path / "song_b.wav"
    query = tmp_path / "query.wav"
    _write_tone(song_a, 330.0, seconds=4.0)
    _write_tone(song_b, 660.0, seconds=4.0)
    _write_tone(query, 330.0, seconds=2.0)

    catalog = tmp_path / "catalog.csv"
    with catalog.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["song_id", "title", "artist", "duration_seconds", "genre", "audio_path"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "song_id": "a",
                "title": "Song A",
                "artist": "Tester",
                "duration_seconds": "4",
                "genre": "tone",
                "audio_path": str(song_a),
            }
        )
        writer.writerow(
            {
                "song_id": "b",
                "title": "Song B",
                "artist": "Tester",
                "duration_seconds": "4",
                "genre": "tone",
                "audio_path": str(song_b),
            }
        )

    service = AudioIdentificationService(catalog)
    service.start()
    result = service.identify_file(query)

    assert result.status == "matched"
    assert result.song is not None
    assert result.song.song_id == "a"
    assert result.confidence > 0.5


def test_rejects_silent_query(tmp_path: Path) -> None:
    song = tmp_path / "song.wav"
    query = tmp_path / "silent.wav"
    _write_tone(song, 440.0, seconds=2.0)
    _write_tone(query, 440.0, seconds=1.5, amplitude=0.0)
    catalog = tmp_path / "catalog.csv"
    catalog.write_text(
        "song_id,title,artist,duration_seconds,genre,audio_path\n"
        f"s,Song,Tester,2,tone,{song}\n",
        encoding="utf-8",
    )

    service = AudioIdentificationService(catalog)
    service.start()
    result = service.identify_file(query)

    assert result.status == "rejected"
    assert "silent" in result.message


def _write_tone(path: Path, frequency: float, seconds: float, amplitude: float = 0.5) -> None:
    sample_rate = 8000
    frame_count = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            value = int(amplitude * 32767 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.extend(value.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(frames))
