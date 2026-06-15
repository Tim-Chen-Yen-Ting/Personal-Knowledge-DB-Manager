import os, json
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key=os.environ["GEMINI_API_KEY"])
_model = genai.GenerativeModel("gemini-2.0-flash")


class WikiEntry(BaseModel):
    title: str
    content: str        # synthesized markdown — key facts, context, structure
    tags: list[str]     # 3-6 lowercase topic tags


class QueryResult(BaseModel):
    answer: str         # full response in markdown
    sources: list[str]  # wiki entry titles used


def _parse(response_text: str, model):
    raw = response_text.strip().removeprefix("```json").removesuffix("```").strip()
    return model.model_validate(json.loads(raw))


def synthesize_to_wiki(raw_text: str, source_filename: str) -> WikiEntry:
    prompt = f"""You are a knowledge base curator.
Read the following document and produce a structured wiki entry as JSON.

Source file: {source_filename}

---
{raw_text}
---

Respond with ONLY a JSON object matching this schema:
{{"title": "string", "content": "markdown summary", "tags": ["tag1", "tag2"]}}

Write a clear, dense summary as content in markdown. Choose a concise descriptive title. Add 3-6 lowercase tags."""

    response = _model.generate_content(prompt)
    return _parse(response.text, WikiEntry)


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

    response = _model.generate_content(prompt)
    return _parse(response.text, QueryResult)
