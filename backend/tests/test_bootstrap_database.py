from pathlib import Path

import pytest

from scripts.bootstrap_database import build_database_url, load_admin_password


def test_database_url_percent_encodes_password():
    url = build_database_url("agent_rag_app", "a:b/@ c", "agent_rag")

    assert (
        url
        == "postgresql+psycopg://agent_rag_app:a%3Ab%2F%40+c@127.0.0.1:5432/agent_rag"
    )


def test_missing_admin_password_is_rejected(tmp_path: Path):
    with pytest.raises(RuntimeError, match="POSTGRES_ADMIN_PASSWORD"):
        load_admin_password(tmp_path / ".env.bootstrap")
