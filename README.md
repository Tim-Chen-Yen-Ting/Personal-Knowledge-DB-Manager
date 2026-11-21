# Personal Knowledge DB Manager

A small full-stack knowledge base: drop in documents, get back a tagged wiki of LLM-written summaries, then ask questions against it, view analytics on what you know, and run a per-topic "knowledge audit" that points out gaps.

Built for a non-technical end user, so the whole thing is one web page and a handful of serverless functions. There's nothing to install on the user's side.

## What it does

- **Ingest** PDF, DOCX, TXT, MD and CSV files. Each file is stored raw, its text is extracted, and an LLM condenses it into a wiki entry with a title, a markdown summary, and 3 to 6 lowercase tags.
- **Ask** questions in a chat box, optionally scoped to selected tags. Answers come only from the knowledge base and cite the wiki entries they used. Every answer is saved as a Markdown file, which gives a simple audit trail.
- **Analytics dashboard** (`/analytics.html`): entries per tag, average entry length per tag, and which tags tend to appear together.
- **Knowledge audit:** pick a tag and get a structured assessment: a summary of what you currently understand, strengths, gaps, concrete suggestions, and a shallow / moderate / deep rating. The audit is saved too.

## Design decisions

**Tag reuse to prevent taxonomy sprawl.** On ingest, the existing tag list is passed to the model with an instruction to reuse tags unless a topic genuinely doesn't fit. Without that, LLM tagging tends to produce near-duplicates ("ml", "machine-learning", "machine learning"), which makes tag-scoped questions and the analytics useless.

**Tag-scoped context injection instead of vector retrieval.** A question is answered by loading the entries for the selected tags (or all entries) into the prompt. There's no embedding store or retriever to tune. At this scale (a personal collection of summaries, not millions of chunks) that is simpler, cheaper, and easier to debug, and the answer's sources are exactly the entries the model was shown. The trade-off is that it stops working once the summaries no longer fit in one context window. That's the point at which retrieval would be worth adding.

**Summaries, not chunks.** The wiki stores one dense summary per source file. Questions run against the summaries, and the raw file stays in storage for reference.

**Few dependencies.** The Gemini API is called over plain HTTP with `httpx` rather than through an SDK, to keep the serverless bundle small. Model output is parsed and validated with Pydantic.

## Architecture

```
public/               static front end (vanilla HTML/JS, Chart.js for the dashboard)
  index.html          chat + file upload
  analytics.html      dashboard + knowledge audit
api/                  Vercel Python serverless functions
  upload.py           POST multipart file  -> raw/ in storage
  ingest.py           POST {path}          -> extract, summarize, upsert wiki entry
  query.py            POST {question,tags} -> answer + sources, saved to outputs/
  audit.py            POST {tag}           -> structured gap analysis, saved to outputs/
  analytics.py        GET                  -> aggregate stats over the wiki table
src/lib/
  db.py               Supabase storage + Postgres access
  extract.py          PDF / DOCX / text extraction
  synthesize.py       Gemini calls, prompt templates, Pydantic output models
```

Flow for a new document: `upload` stores it, then `ingest` downloads it, extracts the text, loads the existing tags, asks Gemini for a wiki entry, and upserts it keyed on title.

## Stack

- **Hosting:** Vercel (Python serverless functions + static files)
- **Database and storage:** Supabase (Postgres for the wiki table, a storage bucket for raw files and saved outputs)
- **LLM:** Google Gemini (`gemini-2.0-flash`) over the REST API
- **Extraction:** `pdfplumber`, `python-docx`
- **Charts:** Chart.js

## Setup

1. Create a Supabase project with:
   - a storage bucket named `files`
   - a `wiki` table with columns `title` (unique), `content`, `tags` (`text[]`), `source_file`, and `updated_at`
2. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com).
3. Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY`, `SUPABASE_URL` and `SUPABASE_KEY`.
4. Deploy to Vercel (set the same three variables in the project settings), or run locally with the Vercel CLI: `vercel dev`.

```bash
pip install -r requirements.txt
cp .env.example .env
vercel dev
```

## Limitations

This is a personal tool, not a multi-user product.

- No authentication. Anyone who can reach a deployment can use it, so don't expose it publicly with sensitive material in it.
- One knowledge base per deployment. There are no accounts or per-user separation.
- Context-injection retrieval has a ceiling (see above), and entries are keyed on title, so two documents that produce the same title will overwrite each other.
- Only text-based files are supported. Scanned PDFs without a text layer won't extract.
