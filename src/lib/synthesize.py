import os, json
import httpx
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)


class WikiEntry(BaseModel):
    title: str
    content: str
    tags: list[str]


class QueryResult(BaseModel):
    answer: str
    sources: list[str]


def _call(prompt: str) -> str:
    key = os.environ["GEMINI_API_KEY"]
    response = httpx.post(
        GEMINI_URL,
        params={"key": key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=55,
    )
    response.raise_for_status()
    return response.json()["candidates"][0]["content"]["parts"][0]["text"]


def _parse(text: str, model):
    raw = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return model.model_validate(json.loads(raw))


def synthesize_to_wiki(raw_text: str, source_filename: str, existing_tags: list[str] | None = None) -> WikiEntry:
    tag_hint = (
        f"\nExisting tags in the knowledge base: {', '.join(existing_tags)}. "
        "Reuse these where appropriate. Only create new tags if the topic genuinely doesn't fit any existing ones."
        if existing_tags else ""
    )
    prompt = f"""You are a knowledge base curator.
Read the following document and produce a structured wiki entry as JSON.

Source file: {source_filename}{tag_hint}

---
{raw_text}
---

Respond with ONLY a JSON object matching this schema:
{{"title": "string", "content": "markdown summary", "tags": ["tag1", "tag2"]}}

Write a clear, dense summary as content in markdown. Choose a concise descriptive title. Add 3-6 lowercase tags."""

    return _parse(_call(prompt), WikiEntry)


def query_wiki(question: str, wiki_entries: list[dict]) -> QueryResult:
    context = "\n\n---\n\n".join(
        f"**{e['title']}**\n{e['content']}" for e in wiki_entries
    )
    prompt = f"""You are a personal knowledge assistant.
Answer the question using only the knowledge base entries below.

Knowledge base:
{context}

Question: {question}

Respond with ONLY a JSON object matching this schema:
{{"answer": "full answer in markdown", "sources": ["wiki title 1", "wiki title 2"]}}"""

    return _parse(_call(prompt), QueryResult)
