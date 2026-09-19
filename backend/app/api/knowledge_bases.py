from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.errors import api_error
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.ingestion import KnowledgeBase
from app.schemas.knowledge_base import KnowledgeBaseCreate
from app.services.files import resolve_upload_path

router = APIRouter(tags=["knowledge-bases"])


def serialize_kb(kb: KnowledgeBase) -> dict:
    documents = [
        {
            "id": str(document.id),
            "name": document.original_filename,
            "status": document.status.value,
            "chunks": document.chunk_count,
            "error_message": document.error_message,
        }
        for document in sorted(
            kb.documents,
            key=lambda item: item.created_at,
            reverse=True,
        )
    ]
    return {
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "total_chunks": sum(document.chunk_count for document in kb.documents),
        "documents": documents,
    }


@router.get("/kbs")
def list_knowledge_bases(db: Session = Depends(get_db)) -> list[dict]:
    query = (
        select(KnowledgeBase)
        .options(selectinload(KnowledgeBase.documents))
        .order_by(KnowledgeBase.created_at)
    )
    return [serialize_kb(kb) for kb in db.scalars(query).unique().all()]


@router.post("/kbs", status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
) -> dict:
    kb = KnowledgeBase(name=payload.name, description=payload.description)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return serialize_kb(kb)


@router.delete("/kbs/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_base(
    kb_id: UUID,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Response:
    kb = db.get(KnowledgeBase, kb_id)
    if kb is None:
        return api_error(404, "knowledge_base_not_found", "知识库不存在")

    try:
        stored_paths = [
            resolve_upload_path(document.file_path, settings)
            for document in kb.documents
        ]
    except ValueError:
        return api_error(409, "cleanup_blocked", "文档存储路径不安全，已阻止删除")

    db.delete(kb)
    db.commit()
    try:
        for stored_path in stored_paths:
            stored_path.unlink(missing_ok=True)
    except OSError:
        return api_error(500, "file_cleanup_failed", "数据已删除，但文件清理失败")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
