# Setup and Execution

## Run Locally

The project uses only the Python standard library for the main application.

```powershell
python -m audioid --dataset data/catalog.csv health
python -m audioid --dataset data/catalog.csv identify path\to\query.wav
python -m audioid --dataset data/catalog.csv serve --host 127.0.0.1 --port 8000
```

After starting the server, open this in your browser:

```text
http://127.0.0.1:8000/
```

The browser UI shows system health, loaded songs, and an identification form. Use a query WAV path such as:

```text
data/queries/bak_query.wav
```

## Dataset Catalog

Create `data/catalog.csv` with these columns:

```csv
song_id,title,artist,duration_seconds,genre,audio_path
song-1,Example Song,Example Artist,185,pop,C:\path\to\song.wav
```

The app also accepts JSON, JSONL, Markdown tables, or a directory of `.wav` files as the dataset input.

## Add Real Songs

This baseline reads PCM `.wav` files. If your downloaded file is MP3/M4A/FLAC, convert it to WAV first, then import it.

```powershell
python -m audioid import-song "$env:USERPROFILE\Downloads\your-song.wav" --title "Your Song" --artist "Artist Name" --genre pop
python -m audioid health
```

The import command copies the file into `data/songs/` and adds/updates the row in `data/catalog.csv`.

To create a 5-second query snippet for testing:

```powershell
python -m audioid make-query data/songs/your-song.wav data/queries/your-song-query.wav --start 30 --duration 5
python -m audioid identify data/queries/your-song-query.wav
```

If you already have a WAV named `song1.wav`, you can import it like this:

```powershell
python -m audioid import-song "$env:USERPROFILE\Downloads\song1.wav" --song-id song1 --title "Song 1" --artist "Unknown Artist" --replace
```

## API Examples

```powershell
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/identify?file=C:\path\to\query.wav"
```

POST requests are also supported:

```powershell
curl -X POST http://127.0.0.1:8000/identify -H "Content-Type: application/json" -d "{\"file\":\"C:\\path\\to\\query.wav\"}"
```

## Accuracy Evaluation

Create a CSV with `query_path,expected_song_id`, then run:

```powershell
python -m audioid --dataset data/catalog.csv evaluate data/evaluation.csv
```

The output includes total queries, correct identifications, false positives, false negatives, and accuracy.
