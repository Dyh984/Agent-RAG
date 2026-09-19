from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.models.ingestion import (
    Document,
    DocumentChunk,
    IngestStatus,
)
from app.services.chunker import chunk_pages
from app.services.files import resolve_upload_path
from app.services.pdf_parser import extract_pdf_pages

SessionFactory = Callable[[], Session]


def safe_ingest_message(error: Exception) -> str:
    if isinstance(error, ValueError):
        return str(error)
    return "文档处理失败，请检查文件后重试"


def ingest_document(
    document_id: UUID,
    settings: Settings | None = None,
    session_factory: SessionFactory = SessionLocal,
) -> None:
    settings = settings or get_settings()
    with session_factory() as session:
        document = session.get(Document, document_id)
        if document is None:
            return

        document.status = IngestStatus.parsing
        document.job.status = IngestStatus.parsing
        document.job.started_at = datetime.now(UTC)
        document.job.progress = 10
        session.commit()

        try:
            pages = extract_pdf_pages(
                resolve_upload_path(document.file_path, settings)
            )

            document.status = IngestStatus.chunking
            document.job.status = IngestStatus.chunking
            document.job.progress = 55
            session.commit()

            chunks = chunk_pages(
                pages,
                settings.chunk_size,
                settings.chunk_overlap,
            )
            session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document.id
                )
            )
            session.add_all(
                DocumentChunk(
                    document_id=document.id,
                    kb_id=document.kb_id,
                    chunk_index=index,
                    content=chunk.text,
                    page=chunk.page,
                    chapter=None,
                    chunk_metadata={
                        "parser": "pymupdf",
                        "chunk_strategy_version": "char-v1",
                    },
                )
                for index, chunk in enumerate(chunks)
            )
            document.status = IngestStatus.completed
            document.chunk_count = len(chunks)
            document.error_message = None
            document.job.status = IngestStatus.completed
            document.job.progress = 100
            document.job.error_message = None
            document.job.finished_at = datetime.now(UTC)
            session.commit()
        except Exception as error:
            session.rollback()
            document = session.get(Document, document_id)
            if document is None:
                return
            message = safe_ingest_message(error)
            session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == document.id
                )
            )
            document.status = IngestStatus.failed
            document.chunk_count = 0
            document.error_message = message
            document.job.status = IngestStatus.failed
            document.job.progress = 100
            document.job.error_message = message
            document.job.finished_at = datetime.now(UTC)
            session.commit()


def get_ingest_runner():
    return ingest_document
