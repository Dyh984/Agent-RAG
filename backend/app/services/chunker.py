from dataclasses import dataclass

from app.services.pdf_parser import ParsedPage


@dataclass(frozen=True)
class TextChunk:
    page: int
    text: str


def chunk_pages(
    pages: list[ParsedPage] | list[tuple[int, str]],
    size: int,
    overlap: int,
) -> list[TextChunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size and overlap are invalid")

    result: list[TextChunk] = []
    step = size - overlap
    for item in pages:
        page, text = (
            (item.page, item.text)
            if isinstance(item, ParsedPage)
            else item
        )
        for start in range(0, len(text), step):
            chunk = text[start : start + size].strip()
            if chunk:
                result.append(TextChunk(page=page, text=chunk))
            if start + size >= len(text):
                break
    return result
