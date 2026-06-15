import io
from pathlib import Path


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from a file based on its extension."""
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return _from_pdf(content)
    elif ext in (".docx", ".doc"):
        return _from_docx(content)
    elif ext in (".txt", ".md", ".csv"):
        return content.decode("utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _from_pdf(content: bytes) -> str:
    import pdfplumber
    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts)


def _from_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
