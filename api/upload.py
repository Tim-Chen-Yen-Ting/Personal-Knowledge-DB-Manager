from http.server import BaseHTTPRequestHandler
import json, cgi, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.lib import db


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_type, params = cgi.parse_header(self.headers.get("Content-Type", ""))

        if content_type != "multipart/form-data":
            self._respond(400, {"error": "Expected multipart/form-data"})
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers["Content-Type"]},
        )

        if "file" not in form:
            self._respond(400, {"error": "No file field in request"})
            return

        file_item = form["file"]
        filename = file_item.filename
        content = file_item.file.read()

        path = db.upload_raw_file(filename, content)
        self._respond(200, {"path": path, "filename": filename})

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
