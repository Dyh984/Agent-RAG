from pathlib import Path

import pymupdf
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.main import app
from app.workers.ingest import get_ingest_runner, ingest_document


@pytest.fixture(scope="session")
def migrated_engine():
    test_url = get_settings().test_database_url
    if not test_url:
        raise RuntimeError("TEST_DATABASE_URL is required for integration tests")

    config = Config(str(Path("backend/alembic.ini")))
    config.set_main_option("sqlalchemy.url", test_url.replace("%", "%%"))
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(test_url)
    yield engine
    engine.dispose()


def clear_test_tables(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE document_chunks, ingest_jobs, documents, "
                "knowledge_bases CASCADE"
            )
        )


@pytest.fixture
def test_settings(migrated_engine, tmp_path):
    settings = get_settings()
    return Settings(
        database_url=str(migrated_engine.url),
        test_database_url=settings.test_database_url,
        upload_root=tmp_path / "uploads",
        max_upload_bytes=2 * 1024 * 1024,
        chunk_size=800,
        chunk_overlap=100,
    )


@pytest.fixture
def client(migrated_engine, test_settings):
    clear_test_tables(migrated_engine)
    test_session_factory = sessionmaker(bind=migrated_engine, expire_on_commit=False)

    def override_get_db():
        with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_ingest_runner] = lambda: (
        lambda document_id, settings: ingest_document(
            document_id,
            settings,
            test_session_factory,
        )
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        clear_test_tables(migrated_engine)


@pytest.fixture
def created_kb(client):
    response = client.post(
        "/api/kbs",
        json={"name": "测试知识库", "description": "测试上传"},
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def sample_pdf(tmp_path):
    path = tmp_path / "policy.pdf"
    document = pymupdf.open()
    for text_value in ("Page one policy text " * 40, "Page two travel text " * 40):
        page = document.new_page()
        page.insert_textbox(
            page.rect + (36, 36, -36, -36),
            text_value,
            fontsize=10,
        )
    document.save(path)
    document.close()
    return path
