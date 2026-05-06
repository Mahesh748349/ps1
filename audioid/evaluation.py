from __future__ import annotations

import csv
from pathlib import Path

from .service import AudioIdentificationService


def evaluate(service: AudioIdentificationService, manifest_path: Path) -> dict[str, float | int]:
    total = 0
    correct = 0
    false_positive = 0
    false_negative = 0
    with manifest_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            total += 1
            expected = row.get("expected_song_id", "").strip()
            query_path = Path(row["query_path"])
            result = service.identify_file(query_path)
            actual = result.song.song_id if result.song else ""
            if expected and actual == expected:
                correct += 1
            elif not expected and actual:
                false_positive += 1
            elif expected and not actual:
                false_negative += 1
    accuracy = correct / total if total else 0.0
    return {
        "total": total,
        "correct": correct,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "accuracy": round(accuracy, 4),
    }
