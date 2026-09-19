from sqlalchemy import inspect


def test_ingestion_tables_exist(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())

    assert {
        "knowledge_bases",
        "documents",
        "document_chunks",
        "ingest_jobs",
    } <= tables


def test_document_hash_is_unique_per_knowledge_base(migrated_engine):
    constraints = inspect(migrated_engine).get_unique_constraints("documents")

    assert {"kb_id", "file_hash"} in [
        set(item["column_names"]) for item in constraints
    ]
