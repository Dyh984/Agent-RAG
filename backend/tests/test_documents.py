def test_upload_pdf_processes_and_persists_chunks(client, created_kb, sample_pdf):
    with sample_pdf.open("rb") as stream:
        response = client.post(
            f"/api/kbs/{created_kb}/documents",
            files={"file": ("policy.pdf", stream, "application/pdf")},
        )

    assert response.status_code == 202
    document = client.get(f"/api/documents/{response.json()['id']}").json()
    assert document["status"] == "completed"
    assert document["chunk_count"] > 0

    chunks_response = client.get(f"/api/documents/{document['id']}/chunks")
    assert chunks_response.status_code == 200
    chunks = chunks_response.json()["items"]
    assert chunks[0]["page"] == 1
    assert chunks[0]["content"]


def test_duplicate_pdf_in_same_kb_returns_409(client, created_kb, sample_pdf):
    payload = sample_pdf.read_bytes()

    first = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("a.pdf", payload, "application/pdf")},
    )
    second = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("b.pdf", payload, "application/pdf")},
    )

    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["code"] == "duplicate_document"


def test_non_pdf_is_rejected(client, created_kb):
    response = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_file_type"


def test_invalid_pdf_bytes_are_rejected(client, created_kb):
    response = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "invalid_pdf"


def test_missing_document_returns_404(client):
    response = client.get(
        "/api/documents/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "document_not_found"


def test_upload_to_missing_knowledge_base_returns_404(client, sample_pdf):
    with sample_pdf.open("rb") as stream:
        response = client.post(
            "/api/kbs/00000000-0000-0000-0000-000000000000/documents",
            files={"file": ("policy.pdf", stream, "application/pdf")},
        )

    assert response.status_code == 404
    assert response.json()["code"] == "knowledge_base_not_found"


def test_empty_pdf_is_rejected(client, created_kb):
    response = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "empty_file"


def test_oversized_pdf_is_rejected_and_temporary_file_is_removed(
    client,
    created_kb,
    test_settings,
):
    payload = b"%PDF-" + (b"x" * test_settings.max_upload_bytes)

    response = client.post(
        f"/api/kbs/{created_kb}/documents",
        files={"file": ("large.pdf", payload, "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "file_too_large"
    assert not list(test_settings.upload_root.rglob("*.part"))


def test_image_only_pdf_finishes_failed_without_chunks(
    client,
    created_kb,
    tmp_path,
):
    import pymupdf

    path = tmp_path / "scan.pdf"
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(path)
    pdf.close()

    with path.open("rb") as stream:
        response = client.post(
            f"/api/kbs/{created_kb}/documents",
            files={"file": ("scan.pdf", stream, "application/pdf")},
        )

    document = client.get(f"/api/documents/{response.json()['id']}").json()
    assert document["status"] == "failed"
    assert document["chunk_count"] == 0
    assert "OCR" in document["error_message"]
    chunks = client.get(f"/api/documents/{document['id']}/chunks").json()
    assert chunks["items"] == []


def test_chunk_list_is_paginated_in_document_order(
    client,
    created_kb,
    sample_pdf,
):
    with sample_pdf.open("rb") as stream:
        response = client.post(
            f"/api/kbs/{created_kb}/documents",
            files={"file": ("policy.pdf", stream, "application/pdf")},
        )
    document_id = response.json()["id"]

    first = client.get(
        f"/api/documents/{document_id}/chunks?offset=0&limit=1"
    ).json()
    second = client.get(
        f"/api/documents/{document_id}/chunks?offset=1&limit=1"
    ).json()

    assert first["items"][0]["chunk_index"] == 0
    assert second["items"][0]["chunk_index"] == 1
