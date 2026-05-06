from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .service import AudioIdentificationService, result_to_dict


def run_server(service: AudioIdentificationService, host: str, port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path in {"/", "/index.html"}:
                self._html(200, _index_html())
                return
            if parsed.path == "/health":
                self._json(200, service.health())
                return
            if parsed.path == "/songs":
                self._json(200, {"songs": [_song_to_dict(song) for song in service.catalog.songs.values()]})
                return
            if parsed.path == "/queries":
                self._json(200, {"queries": _query_files()})
                return
            if parsed.path == "/identify":
                query = parse_qs(parsed.query)
                file_value = query.get("file", [""])[0]
                if not file_value:
                    self._json(400, {"status": "rejected", "message": "missing ?file= path"})
                    return
                result = service.identify_file(Path(file_value))
                code = 200 if result.status in {"matched", "unknown"} else 400
                self._json(code, result_to_dict(result))
                return
            self._json(404, {"message": "not found"})

        def do_POST(self) -> None:
            parsed_path = urlparse(self.path).path
            if parsed_path == "/identify-upload":
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    self._json(400, {"status": "rejected", "message": "empty upload"})
                    return
                upload_dir = Path("data/queries/uploads")
                upload_dir.mkdir(parents=True, exist_ok=True)
                path = upload_dir / f"query_{int(time.time() * 1000)}.wav"
                path.write_bytes(self.rfile.read(length))
                result = service.identify_file(path, metadata={"upload": True})
                code = 200 if result.status in {"matched", "unknown"} else 400
                payload = result_to_dict(result)
                payload["uploaded_path"] = str(path)
                self._json(code, payload)
                return

            if parsed_path != "/identify":
                self._json(404, {"message": "not found"})
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._json(400, {"status": "rejected", "message": "invalid JSON request body"})
                return
            file_value = payload.get("file")
            if not file_value:
                self._json(400, {"status": "rejected", "message": "missing JSON field: file"})
                return
            result = service.identify_file(Path(file_value), metadata=payload.get("metadata") or {})
            code = 200 if result.status in {"matched", "unknown"} else 400
            self._json(code, result_to_dict(result))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _html(self, status: int, html: str) -> None:
            body = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Listening on http://{host}:{port}")
    server.serve_forever()


def _song_to_dict(song: object) -> dict:
    return {
        "song_id": song.song_id,
        "title": song.title,
        "artist": song.artist,
        "duration_seconds": song.duration_seconds,
        "genre": song.genre,
        "audio_path": str(song.audio_path) if song.audio_path else "",
    }


def _query_files() -> list[dict[str, str]]:
    roots = [Path("data/queries"), Path("data/demo_wav")]
    files: list[dict[str, str]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.wav")):
            files.append({"name": path.stem.replace("_", " ").title(), "path": str(path)})
    return files


def _index_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Audio Identification</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f4ef;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #667085;
      --line: #d7dce2;
      --accent: #176b87;
      --accent-2: #2f7d57;
      --warn: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    header {
      padding: 22px 28px;
      background: #0f2f3a;
      color: white;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 0; }
    main {
      width: min(1180px, calc(100% - 32px));
      margin: 24px auto;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      gap: 20px;
    }
    section, aside {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    h2 { margin: 0 0 14px; font-size: 18px; letter-spacing: 0; }
    label { display: block; margin-bottom: 8px; color: var(--muted); font-size: 14px; }
    .row { display: flex; gap: 10px; align-items: end; }
    .query-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0 2px;
    }
    input {
      width: 100%;
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 15px;
    }
    button {
      min-height: 42px;
      border: 0;
      border-radius: 6px;
      background: var(--accent);
      color: white;
      padding: 0 16px;
      font-size: 15px;
      cursor: pointer;
      white-space: nowrap;
    }
    button.secondary { background: #475467; }
    button.chip {
      min-height: 34px;
      background: #eef2f4;
      color: var(--text);
      border: 1px solid var(--line);
      padding: 0 10px;
      font-size: 13px;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 7px 10px;
      border-radius: 999px;
      background: rgba(47, 125, 87, 0.14);
      color: #175c3d;
      font-size: 14px;
      font-weight: 700;
    }
    .status.bad { background: rgba(180, 35, 24, 0.12); color: var(--warn); }
    .result {
      min-height: 180px;
      margin-top: 18px;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
      background: #fbfcfd;
    }
    .match-title { font-size: 28px; font-weight: 800; margin: 6px 0; letter-spacing: 0; }
    .muted { color: var(--muted); }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 10px;
      margin-top: 14px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      background: white;
    }
    .metric strong { display: block; font-size: 20px; margin-top: 4px; }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }
    th, td {
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }
    th { color: var(--muted); font-weight: 700; }
    code {
      background: #eef2f4;
      border-radius: 4px;
      padding: 2px 4px;
      overflow-wrap: anywhere;
    }
    pre {
      overflow: auto;
      background: #111827;
      color: #e5e7eb;
      border-radius: 8px;
      padding: 12px;
      font-size: 13px;
      max-height: 260px;
    }
    @media (max-width: 860px) {
      header { align-items: flex-start; flex-direction: column; }
      main { grid-template-columns: 1fr; }
      .row { flex-direction: column; align-items: stretch; }
      .metric-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Audio Identification</h1>
    <div id="status" class="status">Loading</div>
  </header>
  <main>
    <section>
      <h2>Identify Query</h2>
      <label for="file">WAV query path</label>
      <div class="row">
        <input id="file" value="data/queries/bak_query.wav" placeholder="data/queries/bak_query.wav">
        <button id="identify">Identify</button>
        <button id="refresh" class="secondary">Refresh</button>
      </div>
      <div id="queries" class="query-list"></div>
      <label for="upload" style="margin-top: 16px;">Upload WAV query</label>
      <div class="row">
        <input id="upload" type="file" accept=".wav,audio/wav">
        <button id="uploadButton" class="secondary">Upload & Identify</button>
      </div>
      <div id="result" class="result">
        <div class="muted">Run an identification to see the matched song, confidence, latency, and candidates.</div>
      </div>
    </section>
    <aside>
      <h2>System</h2>
      <div class="metric-grid">
        <div class="metric"><span class="muted">Songs</span><strong id="songsCount">0</strong></div>
        <div class="metric"><span class="muted">Hashes</span><strong id="hashCount">0</strong></div>
        <div class="metric"><span class="muted">Indexed</span><strong id="indexedCount">0</strong></div>
      </div>
      <h2 style="margin-top: 22px;">Catalog</h2>
      <div id="songs"></div>
    </aside>
  </main>
  <script>
    const statusEl = document.getElementById("status");
    const songsEl = document.getElementById("songs");
    const queriesEl = document.getElementById("queries");
    const resultEl = document.getElementById("result");
    const fileEl = document.getElementById("file");
    const uploadEl = document.getElementById("upload");

    async function loadHealth() {
      const response = await fetch("/health");
      const health = await response.json();
      statusEl.textContent = health.status.toUpperCase();
      statusEl.className = health.status === "ok" ? "status" : "status bad";
      document.getElementById("songsCount").textContent = health.songs_loaded;
      document.getElementById("hashCount").textContent = health.hashes_indexed;
      document.getElementById("indexedCount").textContent = health.songs_indexed;
    }

    async function loadSongs() {
      const response = await fetch("/songs");
      const payload = await response.json();
      const rows = payload.songs.map(song => `
        <tr>
          <td><strong>${escapeHtml(song.title)}</strong><br><span class="muted">${escapeHtml(song.artist)}</span></td>
          <td>${escapeHtml(song.genre)}</td>
          <td><code>${escapeHtml(song.audio_path)}</code></td>
        </tr>
      `).join("");
      songsEl.innerHTML = `<table><thead><tr><th>Song</th><th>Genre</th><th>Path</th></tr></thead><tbody>${rows}</tbody></table>`;
    }

    async function loadQueries() {
      const response = await fetch("/queries");
      const payload = await response.json();
      queriesEl.innerHTML = payload.queries.map(query => `
        <button class="chip" type="button" data-path="${escapeHtml(query.path)}">${escapeHtml(query.name)}</button>
      `).join("");
      queriesEl.querySelectorAll("button").forEach(button => {
        button.addEventListener("click", () => {
          fileEl.value = button.dataset.path;
          identify();
        });
      });
    }

    async function identify() {
      const file = fileEl.value.trim();
      if (!file) {
        resultEl.innerHTML = `<div class="muted">Enter a WAV query path.</div>`;
        return;
      }
      resultEl.innerHTML = `<div class="muted">Identifying...</div>`;
      const response = await fetch(`/identify?file=${encodeURIComponent(file)}`);
      const result = await response.json();
      renderResult(result);
    }

    async function uploadAndIdentify() {
      const file = uploadEl.files[0];
      if (!file) {
        resultEl.innerHTML = `<div class="muted">Choose a WAV query file.</div>`;
        return;
      }
      resultEl.innerHTML = `<div class="muted">Uploading and identifying...</div>`;
      const response = await fetch("/identify-upload", {
        method: "POST",
        headers: {"Content-Type": "audio/wav"},
        body: file
      });
      const result = await response.json();
      renderResult(result);
    }

    function renderResult(result) {
      const song = result.song;
      const candidates = (result.candidates || []).map(item => `
        <tr>
          <td>${escapeHtml(item.song_id)}</td>
          <td>${item.confidence}</td>
          <td>${item.votes}</td>
        </tr>
      `).join("");
      resultEl.innerHTML = `
        <div class="muted">${escapeHtml(result.status)}</div>
        <div class="match-title">${song ? escapeHtml(song.title) : "Unknown"}</div>
        <div>${song ? `${escapeHtml(song.artist)} &middot; ${escapeHtml(song.genre)}` : escapeHtml(result.message || "No confident match")}</div>
        <div class="metric-grid">
          <div class="metric"><span class="muted">Confidence</span><strong>${result.confidence}</strong></div>
          <div class="metric"><span class="muted">Latency</span><strong>${result.latency_ms} ms</strong></div>
          <div class="metric"><span class="muted">Candidates</span><strong>${(result.candidates || []).length}</strong></div>
        </div>
        <h2 style="margin-top: 18px;">Candidates</h2>
        <table><thead><tr><th>Song ID</th><th>Confidence</th><th>Votes</th></tr></thead><tbody>${candidates}</tbody></table>
        <pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>
      `;
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
      }[char]));
    }

    document.getElementById("identify").addEventListener("click", identify);
    document.getElementById("uploadButton").addEventListener("click", uploadAndIdentify);
    document.getElementById("refresh").addEventListener("click", () => {
      loadHealth();
      loadSongs();
      loadQueries();
    });
    loadHealth();
    loadSongs();
    loadQueries();
  </script>
</body>
</html>"""
