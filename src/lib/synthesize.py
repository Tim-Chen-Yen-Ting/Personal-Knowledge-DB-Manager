import os
import anthropic
import instructor
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

_client = instructor.from_anthropic(
    anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
)


class WikiEntry(BaseModel):
    title: str
    content: str        # synthesized markdown — key facts, context, structure
    tags: list[str]     # 3-6 lowercase topic tags


class QueryResult(BaseModel):
    answer: str         # full response in markdown
    sources: list[str]  # wiki entry titles used


def synthesize_to_wiki(raw_text: str, source_filename: str) -> WikiEntry:
    """Turn extracted raw text into a structured wiki entry."""
    return _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                f"You are a knowledge base curator. "
                f"Read the following document and produce a structured wiki entry.\n\n"
                f"Source file: {source_filename}\n\n"
                f"---\n{raw_text}\n---\n\n"
                f"Write a clear, dense summary as `content` in markdown. "
                f"Choose a concise descriptive `title`. "
                f"Add 3-6 lowercase `tags` that describe the topic."
            )
        }],
        response_model=WikiEntry,
    )


def query_wiki(question: str, wiki_entries: list[dict]) -> QueryResult:
    """Answer a question using the wiki entries as context."""
    context = "\n\n---\n\n".join(
        f"**{e['title']}**\n{e['content']}" for e in wiki_entries
    )
    return _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": (
                f"You are a personal knowledge assistant. "
                f"Answer the question using only the knowledge base entries below.\n\n"
                f"Knowledge base:\n{context}\n\n"
                f"Question: {question}"
            )
        }],
        response_model=QueryResult,
    )
