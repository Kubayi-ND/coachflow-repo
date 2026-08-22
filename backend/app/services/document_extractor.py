"""Extracts plain text from a Drive file by mime type — the shared read path
every backfill source in drive_backfill.py uses before writing to
context_library or transcripts. Not part of the ongoing ingestion pipeline:
the live transcript webhook only ever receives Plaud/Gemini Meet exports,
which transcript_normalizer.py already handles directly.
"""
import io
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.integrations.google.drive import download_file, export_google_doc_text

GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
PDF_MIME_TYPE = "application/pdf"
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def extract_text(tenant_id: str, file_id: str, mime_type: str) -> str:
    if mime_type == GOOGLE_DOC_MIME_TYPE:
        return await export_google_doc_text(tenant_id, file_id)

    raw_bytes = await download_file(tenant_id, file_id)
    if mime_type == PDF_MIME_TYPE:
        return _extract_pdf_text(raw_bytes)
    if mime_type == DOCX_MIME_TYPE:
        return _extract_docx_text(raw_bytes)
    return raw_bytes.decode("utf-8", errors="replace")


def _extract_pdf_text(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx_text(raw_bytes: bytes) -> str:
    document = Document(io.BytesIO(raw_bytes))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def extract_local_file_text(path: Path) -> str:
    """Extract text from a local context document without touching prompts."""
    raw_bytes = path.read_bytes()
    if path.suffix.lower() == ".pdf":
        return _extract_pdf_text(raw_bytes)
    if path.suffix.lower() == ".docx":
        return _extract_docx_text(raw_bytes)
    return raw_bytes.decode("utf-8", errors="replace")
