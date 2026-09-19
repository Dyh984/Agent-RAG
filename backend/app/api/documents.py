import uuid
from collections.abc import Callable
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.ingestion import (
    Document,
    DocumentChunk,
    IngestJob,
    IngestStatus,
    KnowledgeBase,
)
from app.services.files import (
    UploadValidationError,
    resolve_upload_path,
    save_pdf_stream,
)
from app.workers.ingest import get_ingest_runner

router = APIRouter(tags=["documents"])


def serialize_document(document: Document) -> dict:
    return {
        "id": str(document.id),
        "kb_id": str(document.kb_id),
        "name": document.original_filename,
        "status": document.status.value,
        "chunk_count": document.chunk_count,
        "error_message": document.error_message,
    }


@router.post("/kbs/{kb_id}/documents", status_code=202)
def upload_document(
    kb_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    ingest_runner: Callable = Depends(get_ingest_runner),
) -> dict:
    if db.get(KnowledgeBase, kb_id) is None:
        return api_error(404, "knowledge_base_not_found", "知识库不存在")

    document_id = uuid.uuid4()
    try:
        stored = save_pdf_stream(file, kb_id, document_id, settings)
    except UploadValidationError as error:
        return api_error(422, error.code, str(error))

    duplicate = db.scalar(
        select(Document).where(
            Document.kb_id == kb_id,
            Document.file_hash == stored.sha256,
        )
    )
    if duplicate is not None:
        resolve_upload_path(stored.relative_path, settings).unlink(missing_ok=True)
        return api_error(409, "duplicate_document", "该知识库已存在相同文件")

    document = Document(
        id=document_id,
        kb_id=kb_id,
        original_filename=file.filename or "document.pdf",
        stored_filename=stored.stored_filename,
        file_path=stored.relative_path,
        file_hash=stored.sha256,
        mime_type=file.content_type or "application/pdf",
        file_size=stored.size,
        status=IngestStatus.pending,
        chunk_count=0,
    )
    document.job = IngestJob(
        status=IngestStatus.pending,
        progress=0,
    )
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        resolve_upload_path(stored.relative_path, settings).unlink(missing_ok=True)
        raise
    db.refresh(document)

    background_tasks.add_task(ingest_runner, document.id, settings)
    return serialize_document(document)


@router.get("/documents/{document_id}")
def get_document(
    document_id: UUID,
    db: Session = Depends(get_db),
) -> dict:
    document = db.get(Document, document_id)
    if document is None:
        return api_error(404, "document_not_found", "文档不存在")
    return serialize_document(document)


@router.get("/documents/{document_id}/chunks")
def list_chunks(
    document_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    if db.get(Document, document_id) is None:
        return api_error(404, "document_not_found", "文档不存在")
    query = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(limit)
    )
    items = [
        {
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "page": chunk.page,
            "chapter": chunk.chapter,
            "metadata": chunk.chunk_metadata,
        }
        for chunk in db.scalars(query).all()
    ]
    return {"items": items, "offset": offset, "limit": limit}


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    document = db.get(Document, document_id)
    if document is None:
        return api_error(404, "document_not_found", "文档不存在")

    try:
        stored_path = resolve_upload_path(document.file_path, settings)
    except ValueError:
        return api_error(409, "cleanup_blocked", "文档存储路径不安全，已阻止删除")

    db.delete(document)
    db.commit()
    try:
        stored_path.unlink(missing_ok=True)
    except OSError:
        return api_error(500, "file_cleanup_failed", "数据已删除，但文件清理失败")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
