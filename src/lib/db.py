import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)


# --- Storage ---

def upload_raw_file(filename: str, content: bytes) -> str:
    """Upload a file to the raw/ bucket. Returns the storage path."""
    db = get_client()
    path = f"raw/{filename}"
    db.storage.from_("files").upload(path, content, {"upsert": "true"})
    return path

def download_raw_file(path: str) -> bytes:
    db = get_client()
    return db.storage.from_("files").download(path)

def save_output(filename: str, content: str) -> str:
    """Save a query result to the outputs/ bucket."""
    db = get_client()
    path = f"outputs/{filename}"
    db.storage.from_("files").upload(path, content.encode(), {"upsert": "true"})
    return path


# --- Wiki table ---

def upsert_wiki_entry(title: str, content: str, tags: list[str], source_file: str):
    db = get_client()
    db.table("wiki").upsert({
        "title": title,
        "content": content,
        "tags": tags,
        "source_file": source_file,
    }, on_conflict="title").execute()

def get_wiki_entries(tags: list[str] | None = None) -> list[dict]:
    db = get_client()
    query = db.table("wiki").select("title, content, tags")
    if tags:
        query = query.overlaps("tags", tags)
    return query.execute().data

def get_all_wiki_entries() -> list[dict]:
    db = get_client()
    return db.table("wiki").select("title, content, tags").execute().data
