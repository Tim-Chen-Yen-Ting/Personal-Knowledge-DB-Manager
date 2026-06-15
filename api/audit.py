from http.server import BaseHTTPRequestHandler
import json, sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.lib import db, synthesize


def _audit_prompt(tag: str, entries: list[dict]) -> str:
    context = "\n\n---\n\n".join(
        f"**{e['title']}**\n{e['content']}" for e in entries
    )
    return f"""You are an expert learning advisor reviewing someone's personal knowledge base.

The user has {len(entries)} knowledge base entries tagged "{tag}".

Here they are:
{context}

Produce a structured analysis of this knowledge area as JSON:
{{
  "summary": "2-3 sentence synthesis of what the user currently understands about {tag}",
  "strengths": ["specific topic they have good coverage on", ...],
  "gaps": ["important topic in {tag} that is missing or shallow", ...],
  "suggestions": ["concrete thing to learn or read next", ...],
  "depth_assessment": "shallow | moderate | deep"
}}

Be specific and honest. Gaps should name real topics, not generic advice. Suggestions should be actionable.
Respond with ONLY the JSON object."""


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))

        tag = body.get("tag", "").strip()
        if not tag:
            self._respond(400, {"error": "Missing 'tag' field"})
            return

        all_entries = db.get_all_wiki_entries()
        tag_entries = [e for e in all_entries if tag in (e.get("tags") or [])]

        if not tag_entries:
            self._respond(404, {"error": f"No entries found for tag '{tag}'"})
            return

        prompt = _audit_prompt(tag, tag_entries)
        raw = synthesize._call(prompt)
        result = json.loads(
            raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        )
        result["tag"] = tag
        result["entry_count"] = len(tag_entries)

        # Save to outputs/
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"audit_{tag}_{date_str}.json"
        db.save_output(filename, json.dumps(result, indent=2).encode())

        self._respond(200, result)

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
