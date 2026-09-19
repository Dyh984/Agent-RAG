import secrets
from pathlib import Path
from urllib.parse import quote_plus

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
ROLE = "agent_rag_app"
DATABASES = ("agent_rag", "agent_rag_test")


def load_admin_password(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"请在 {path} 中配置 POSTGRES_ADMIN_PASSWORD")

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = raw_line.partition("=")
        if separator and key.strip() == "POSTGRES_ADMIN_PASSWORD" and value.strip():
            return value.strip()

    raise RuntimeError(".env.bootstrap 缺少 POSTGRES_ADMIN_PASSWORD")


def build_database_url(user: str, password: str, database: str) -> str:
    return (
        f"postgresql+psycopg://{user}:{quote_plus(password)}"
        f"@127.0.0.1:5432/{database}"
    )


def write_runtime_env(password: str) -> None:
    content = (
        f"DATABASE_URL={build_database_url(ROLE, password, 'agent_rag')}\n"
        f"TEST_DATABASE_URL={build_database_url(ROLE, password, 'agent_rag_test')}\n"
    )
    (ROOT / ".env").write_text(content, encoding="utf-8")


def main() -> None:
    admin_password = load_admin_password(ROOT / ".env.bootstrap")
    app_password = secrets.token_urlsafe(32)

    with psycopg.connect(
        host="127.0.0.1",
        port=5432,
        dbname="postgres",
        user="postgres",
        password=admin_password,
        autocommit=True,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (ROLE,))
            role_exists = cursor.fetchone() is not None
            statement = (
                "ALTER ROLE {} WITH LOGIN PASSWORD {}"
                if role_exists
                else "CREATE ROLE {} WITH LOGIN PASSWORD {}"
            )
            cursor.execute(
                sql.SQL(statement).format(
                    sql.Identifier(ROLE),
                    sql.Literal(app_password),
                )
            )

            for database in DATABASES:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (database,),
                )
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8'").format(
                            sql.Identifier(database),
                            sql.Identifier(ROLE),
                        )
                    )
                else:
                    cursor.execute(
                        sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
                            sql.Identifier(database),
                            sql.Identifier(ROLE),
                        )
                    )

    write_runtime_env(app_password)
    print(
        "Created agent_rag databases and wrote application connection strings to .env"
    )


if __name__ == "__main__":
    main()
