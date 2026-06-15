from http.server import BaseHTTPRequestHandler
import json
from src.lib import db, extract, synthesize


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        path = body.get("path")          # e.g. "raw/report.pdf"
        if not path:
            self._respond(400, {"error": "Missing 'path' field"})
            return

        filename = path.split("/")[-1]

        # 1. Pull raw file from Supabase storage
        raw_bytes = db.download_raw_file(path)

        # 2. Extract plain text
        try:
            text = extract.extract_text(filename, raw_bytes)
        except ValueError as e:
            self._respond(400, {"error": str(e)})
            return

        # 3. LLM synthesizes → structured WikiEntry
        entry = synthesize.synthesize_to_wiki(text, filename)

        # 4. Upsert into wiki table
        db.upsert_wiki_entry(
            title=entry.title,
            content=entry.content,
            tags=entry.tags,
            source_file=path,
        )

        self._respond(200, {
            "title": entry.title,
            "tags": entry.tags,
            "source_file": path,
        })

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
