from http.server import BaseHTTPRequestHandler
import json, datetime
from src.lib import db, synthesize


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        question = body.get("question")
        tags = body.get("tags")          # optional: filter wiki by topic

        if not question:
            self._respond(400, {"error": "Missing 'question' field"})
            return

        # 1. Fetch relevant wiki entries from Supabase
        entries = db.get_wiki_entries(tags) if tags else db.get_all_wiki_entries()

        if not entries:
            self._respond(200, {"answer": "No knowledge base entries found.", "sources": []})
            return

        # 2. LLM reads wiki + answers
        result = synthesize.query_wiki(question, entries)

        # 3. Save output to Supabase outputs/ bucket
        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_filename = f"query_{timestamp}.md"
        output_content = f"# Query\n{question}\n\n# Answer\n{result.answer}\n\n# Sources\n" + \
                         "\n".join(f"- {s}" for s in result.sources)
        db.save_output(output_filename, output_content)

        self._respond(200, {
            "answer": result.answer,
            "sources": result.sources,
            "saved_as": f"outputs/{output_filename}",
        })

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
