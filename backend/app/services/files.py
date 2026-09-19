from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.core.config import Settings, get_settings

BLOCK_SIZE = 1024 * 1024
ALLOWED_MIME_TYPES = {"application/pdf", "application/octet-stream"}


class UploadValidationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class StoredUpload:
    relative_path: str
    stored_filename: str
    sha256: str
    size: int


def resolve_upload_path(
    relative_path: str,
    settings: Settings | None = None,
) -> Path:
    root = (settings or get_settings()).upload_root.resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("path is outside upload root") from error
    return candidate


def save_pdf_stream(
    upload: UploadFile,
    kb_id: UUID,
    document_id: UUID,
    settings: Settings,
) -> StoredUpload:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix != ".pdf" or upload.content_type not in ALLOWED_MIME_TYPES:
        raise UploadValidationError(
            "unsupported_file_type",
            "首版仅支持 PDF 文件",
        )

    relative = Path(str(kb_id)) / f"{document_id}.pdf"
    target = resolve_upload_path(relative.as_posix(), settings)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".pdf.part")
    digest = sha256()
    total = 0
    header = b""

    try:
        with temporary.open("xb") as output:
            while block := upload.file.read(BLOCK_SIZE):
                if not header:
                    header = block[:5]
                total += len(block)
                if total > settings.max_upload_bytes:
                    raise UploadValidationError(
                        "file_too_large",
                        "文件超过上传大小限制",
                    )
                digest.update(block)
                output.write(block)

        if total == 0:
            raise UploadValidationError("empty_file", "不能上传空文件")
        if header != b"%PDF-":
            raise UploadValidationError("invalid_pdf", "文件内容不是有效 PDF")
        temporary.replace(target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return StoredUpload(
        relative_path=relative.as_posix(),
        stored_filename=target.name,
        sha256=digest.hexdigest(),
        size=total,
    )
