from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .evaluation import evaluate
from .http_api import run_server
from .service import AudioIdentificationService, dumps_json, result_to_dict
from .tools import import_song, make_query_clip


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audio identification and source detection")
    parser.add_argument("--dataset", type=Path, default=Path("data/catalog.csv"), help="CSV/JSON/Markdown catalog or audio folder")
    parser.add_argument("--audio-root", type=Path, default=None, help="Base folder for relative audio paths")
    parser.add_argument("--threshold", type=float, default=0.18, help="Minimum confidence for a match")
    parser.add_argument("--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("health", help="Load dataset and print service health")

    import_parser = subparsers.add_parser("import-song", help="Copy a WAV into data/songs and update catalog.csv")
    import_parser.add_argument("source", type=Path, help="Downloaded PCM .wav song file")
    import_parser.add_argument("--songs-dir", type=Path, default=Path("data/songs"))
    import_parser.add_argument("--song-id", default=None)
    import_parser.add_argument("--title", default=None)
    import_parser.add_argument("--artist", default="unknown")
    import_parser.add_argument("--genre", default="unknown")
    import_parser.add_argument("--replace", action="store_true", help="Overwrite an existing copied file/catalog row")

    query_parser = subparsers.add_parser("make-query", help="Cut a short WAV query clip from a song")
    query_parser.add_argument("source", type=Path)
    query_parser.add_argument("destination", type=Path)
    query_parser.add_argument("--start", type=float, default=0.0, help="Start time in seconds")
    query_parser.add_argument("--duration", type=float, default=5.0, help="Clip length in seconds")

    identify = subparsers.add_parser("identify", help="Identify one query wav file")
    identify.add_argument("query", type=Path)

    serve = subparsers.add_parser("serve", help="Run HTTP API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a CSV manifest")
    eval_parser.add_argument("manifest", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(message)s")

    if args.command == "import-song":
        try:
            record = import_song(
                args.source,
                args.dataset,
                args.songs_dir,
                song_id=args.song_id,
                title=args.title,
                artist=args.artist,
                genre=args.genre,
                replace=args.replace,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(dumps_json({"status": "imported", "song": record}))
        return

    if args.command == "make-query":
        try:
            clip = make_query_clip(args.source, args.destination, args.start, args.duration)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(dumps_json({"status": "created", "query": clip}))
        return

    service = AudioIdentificationService(args.dataset, audio_root=args.audio_root, threshold=args.threshold)
    service.start()

    if args.command == "health":
        print(dumps_json(service.health()))
    elif args.command == "identify":
        print(dumps_json(result_to_dict(service.identify_file(args.query))))
    elif args.command == "evaluate":
        print(dumps_json(evaluate(service, args.manifest)))
    elif args.command == "serve":
        run_server(service, args.host, args.port)


if __name__ == "__main__":
    main()
