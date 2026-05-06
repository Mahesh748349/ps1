from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Iterable

from .models import IngestionReport, SongMetadata

LOGGER = logging.getLogger(__name__)
SUPPORTED_AUDIO_EXTENSIONS = {".wav"}


class DatasetCatalog:
    """Loads song metadata from CSV, JSON, JSONL, Markdown tables, or folders."""

    def __init__(self) -> None:
        self.songs: dict[str, SongMetadata] = {}
        self.report = IngestionReport(loaded=0, skipped=0, errors=())

    def load(self, dataset_path: Path, audio_root: Path | None = None) -> IngestionReport:
        records: Iterable[dict[str, str]]
        if dataset_path.is_dir():
            records = self._records_from_directory(dataset_path)
            audio_root = dataset_path
        elif dataset_path.suffix.lower() == ".csv":
            records = self._records_from_csv(dataset_path)
        elif dataset_path.suffix.lower() in {".json", ".jsonl"}:
            records = self._records_from_json(dataset_path)
        elif dataset_path.suffix.lower() in {".md", ".markdown"}:
            records = self._records_from_markdown_table(dataset_path)
        else:
            raise ValueError(f"Unsupported dataset format: {dataset_path.suffix}")

        loaded = 0
        skipped = 0
        errors: list[str] = []
        for row_number, record in enumerate(records, start=1):
            try:
                song = self._parse_record(record, row_number, audio_root)
            except ValueError as exc:
                skipped += 1
                message = f"row {row_number}: {exc}"
                errors.append(message)
                LOGGER.warning("Skipping dataset record: %s", message)
                continue
            self.songs[song.song_id] = song
            loaded += 1

        self.report = IngestionReport(loaded=loaded, skipped=skipped, errors=tuple(errors))
        LOGGER.info("Loaded %s songs; skipped %s records", loaded, skipped)
        return self.report

    def _parse_record(
        self, record: dict[str, str], row_number: int, audio_root: Path | None
    ) -> SongMetadata:
        lowered = {str(key).strip().lower(): value for key, value in record.items()}
        song_id = str(lowered.get("song_id") or lowered.get("id") or "").strip()
        title = str(lowered.get("title") or "").strip()
        artist = str(lowered.get("artist") or "").strip()
        genre = str(lowered.get("genre") or "unknown").strip() or "unknown"
        duration_value = lowered.get("duration") or lowered.get("duration_seconds") or "0"
        path_value = str(lowered.get("audio_path") or lowered.get("path") or "").strip()

        if not song_id:
            raise ValueError("missing song_id")
        if not title:
            raise ValueError(f"missing title for song_id={song_id}")
        if not artist:
            raise ValueError(f"missing artist for song_id={song_id}")
        try:
            duration_seconds = float(duration_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid duration for song_id={song_id}") from exc

        audio_path = None
        if path_value:
            candidate = Path(path_value)
            audio_path = candidate if candidate.is_absolute() else (audio_root or Path.cwd()) / candidate
        return SongMetadata(
            song_id=song_id,
            title=title,
            artist=artist,
            duration_seconds=duration_seconds,
            genre=genre,
            audio_path=audio_path,
        )

    def _records_from_csv(self, path: Path) -> Iterable[dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            yield from csv.DictReader(handle)

    def _records_from_json(self, path: Path) -> Iterable[dict[str, str]]:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".jsonl":
            for line in text.splitlines():
                if line.strip():
                    yield json.loads(line)
            return
        payload = json.loads(text)
        if isinstance(payload, dict):
            payload = payload.get("songs", [])
        if not isinstance(payload, list):
            raise ValueError("JSON dataset must be a list or contain a songs list")
        for item in payload:
            yield item

    def _records_from_markdown_table(self, path: Path) -> Iterable[dict[str, str]]:
        rows = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
        table_rows = [line for line in rows if line.startswith("|") and line.endswith("|")]
        if len(table_rows) < 2:
            return
        headers = [cell.strip().lower() for cell in table_rows[0].strip("|").split("|")]
        for line in table_rows[2:]:
            values = [cell.strip() for cell in line.strip("|").split("|")]
            if len(values) == len(headers):
                yield dict(zip(headers, values, strict=True))

    def _records_from_directory(self, path: Path) -> Iterable[dict[str, str]]:
        for audio_file in path.rglob("*"):
            if audio_file.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
                continue
            song_id = audio_file.stem
            audio_path = audio_file.relative_to(path)
            yield {
                "song_id": song_id,
                "title": audio_file.stem.replace("_", " ").title(),
                "artist": "unknown",
                "duration": "0",
                "genre": "unknown",
                "audio_path": str(audio_path),
            }
