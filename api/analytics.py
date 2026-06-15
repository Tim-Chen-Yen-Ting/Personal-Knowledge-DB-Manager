from http.server import BaseHTTPRequestHandler
import json, sys, os
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.lib import db


def _compute_stats(entries: list[dict]) -> dict:
    from collections import Counter, defaultdict

    tag_counts = Counter()
    tag_word_counts = defaultdict(list)
    tag_sources = defaultdict(set)
    tag_last_updated = {}
    co_occurrence = defaultdict(Counter)

    for e in entries:
        tags = e.get("tags") or []
        content = e.get("content") or ""
        source = e.get("source_file") or ""
        updated_raw = e.get("updated_at")

        word_count = len(content.split())
        updated_dt = None
        if updated_raw:
            try:
                updated_dt = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
            except Exception:
                pass

        for tag in tags:
            tag_counts[tag] += 1
            tag_word_counts[tag].append(word_count)
            if source:
                tag_sources[tag].add(source)
            if updated_dt:
                if tag not in tag_last_updated or updated_dt > tag_last_updated[tag]:
                    tag_last_updated[tag] = updated_dt

        for i, t1 in enumerate(tags):
            for t2 in tags[i + 1:]:
                co_occurrence[t1][t2] += 1
                co_occurrence[t2][t1] += 1

    now = datetime.now(timezone.utc)

    tag_stats = []
    for tag, count in tag_counts.most_common():
        wc = tag_word_counts[tag]
        last = tag_last_updated.get(tag)
        days_stale = (now - last).days if last else None
        tag_stats.append({
            "tag": tag,
            "entry_count": count,
            "avg_word_count": round(sum(wc) / len(wc)),
            "source_count": len(tag_sources[tag]),
            "days_since_update": days_stale,
        })

    # Top co-occurrence pairs
    pairs = []
    seen = set()
    for t1, neighbors in co_occurrence.items():
        for t2, cnt in neighbors.items():
            key = tuple(sorted([t1, t2]))
            if key not in seen:
                seen.add(key)
                pairs.append({"a": t1, "b": t2, "count": cnt})
    pairs.sort(key=lambda x: -x["count"])

    return {
        "total_entries": len(entries),
        "total_tags": len(tag_counts),
        "tag_stats": tag_stats,
        "co_occurrence": pairs[:40],
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        entries = db.get_all_wiki_entries()
        stats = _compute_stats(entries)
        self._respond(200, stats)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(payload))
        self.end_headers()
        self.wfile.write(payload)
