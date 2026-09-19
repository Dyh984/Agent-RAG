import re
from dataclasses import dataclass
from pathlib import Path

import pymupdf


@dataclass(frozen=True)
class ParsedPage:
    page: int
    text: str


def normalize_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_pdf_pages(path: Path) -> list[ParsedPage]:
    with pymupdf.open(path) as document:
        if document.needs_pass:
            raise ValueError("暂不支持加密 PDF")
        pages = [
            ParsedPage(index + 1, normalize_text(page.get_text("text")))
            for index, page in enumerate(document)
        ]

    if not any(page.text for page in pages):
        raise ValueError("PDF 未提取到可用文本，扫描件需要后续 OCR 支持")
    return pages
