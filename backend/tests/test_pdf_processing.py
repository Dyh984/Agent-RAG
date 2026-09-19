from pathlib import Path

import pymupdf

from app.services.chunker import chunk_pages
from app.services.pdf_parser import extract_pdf_pages


def make_pdf(path: Path) -> None:
    document = pymupdf.open()
    for text in ("Page one policy text", "Page two travel text"):
        page = document.new_page()
        page.insert_text((72, 72), text, fontsize=12)
    document.save(path)
    document.close()


def test_parser_preserves_one_based_page_numbers(tmp_path):
    path = tmp_path / "sample.pdf"
    make_pdf(path)

    pages = extract_pdf_pages(path)

    assert [page.page for page in pages] == [1, 2]
    assert "Page one policy" in pages[0].text


def test_chunks_never_cross_page_boundaries():
    chunks = chunk_pages(
        [(1, "A" * 1000), (2, "B" * 900)],
        size=800,
        overlap=100,
    )

    assert [chunk.page for chunk in chunks] == [1, 1, 2, 2]
    assert all(set(chunk.text) <= {"A"} for chunk in chunks if chunk.page == 1)
    assert all(set(chunk.text) <= {"B"} for chunk in chunks if chunk.page == 2)
    assert chunks[1].text.startswith("A" * 100)


def test_chunker_rejects_invalid_overlap():
    try:
        chunk_pages([(1, "text")], size=100, overlap=100)
    except ValueError as error:
        assert "invalid" in str(error)
    else:
        raise AssertionError("invalid overlap must raise ValueError")
