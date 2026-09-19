import pytest

from app.services.files import resolve_upload_path


def upload_completed_document(client, kb_id, sample_pdf):
    with sample_pdf.open("rb") as stream:
        response = client.post(
            f"/api/kbs/{kb_id}/documents",
            files={"file": ("policy.pdf", stream, "application/pdf")},
        )
    assert response.status_code == 202
    document_id = response.json()["id"]
    assert client.get(f"/api/documents/{document_id}").json()["status"] == "completed"
    return document_id


def test_delete_document_removes_rows_and_exact_file(
    client,
    created_kb,
    sample_pdf,
    test_settings,
):
    document_id = upload_completed_document(client, created_kb, sample_pdf)
    stored_files = list(test_settings.upload_root.rglob("*.pdf"))
    assert len(stored_files) == 1

    response = client.delete(f"/api/documents/{document_id}")

    assert response.status_code == 204
    assert not stored_files[0].exists()
    assert client.get(f"/api/documents/{document_id}").status_code == 404


def test_resolve_upload_path_rejects_escape(test_settings):
    with pytest.raises(ValueError, match="outside upload root"):
        resolve_upload_path("../secret.txt", test_settings)


def test_delete_kb_cascades_documents_chunks_and_files(
    client,
    created_kb,
    sample_pdf,
    test_settings,
):
    document_id = upload_completed_document(client, created_kb, sample_pdf)
    stored_files = list(test_settings.upload_root.rglob("*.pdf"))
    assert len(stored_files) == 1

    response = client.delete(f"/api/kbs/{created_kb}")

    assert response.status_code == 204
    assert not stored_files[0].exists()
    assert client.get(f"/api/documents/{document_id}").status_code == 404
    assert client.get("/api/kbs").json() == []
