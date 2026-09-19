def test_create_and_list_knowledge_base(client):
    created = client.post(
        "/api/kbs",
        json={"name": "制度库", "description": "公司制度"},
    )

    assert created.status_code == 201
    kb_id = created.json()["id"]

    listed = client.get("/api/kbs")
    assert listed.status_code == 200
    assert listed.json() == [
        {
            "id": kb_id,
            "name": "制度库",
            "description": "公司制度",
            "total_chunks": 0,
            "documents": [],
        }
    ]


def test_reject_blank_name(client):
    response = client.post(
        "/api/kbs",
        json={"name": "   ", "description": ""},
    )

    assert response.status_code == 422


def test_delete_missing_knowledge_base(client):
    response = client.delete(
        "/api/kbs/00000000-0000-0000-0000-000000000000"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "knowledge_base_not_found"
