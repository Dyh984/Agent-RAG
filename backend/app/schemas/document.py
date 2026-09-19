from uuid import UUID

from pydantic import BaseModel


class DocumentRead(BaseModel):
    id: UUID
    kb_id: UUID
    name: str
    status: str
    chunk_count: int
    error_message: str | None
