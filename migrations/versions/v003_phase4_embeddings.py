"""
Migration Revision 003: Add vector embedding and metadata columns to document_chunks table.
Supports PostgreSQL (with pgvector extension if available, otherwise TEXT fallback) and SQLite (with JSON string compatibility).
"""

REVISION = "003_phase4_embeddings"
DESCRIPTION = "Add embedding, embedding_model, embedding_dimension, and embedded_at to document_chunks"

SQL_UPGRADE_SQLITE = [
    """
    ALTER TABLE document_chunks ADD COLUMN embedding TEXT;
    """,
    """
    ALTER TABLE document_chunks ADD COLUMN embedding_model TEXT;
    """,
    """
    ALTER TABLE document_chunks ADD COLUMN embedding_dimension INTEGER;
    """,
    """
    ALTER TABLE document_chunks ADD COLUMN embedded_at TIMESTAMP;
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_document_chunks_embedded ON document_chunks(document_id, embedding_model);
    """
]

SQL_DOWNGRADE_POSTGRES = [
    "DROP INDEX IF EXISTS ix_document_chunks_embedded;",
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedded_at;",
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_dimension;",
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_model;",
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding;"
]

SQL_DOWNGRADE_SQLITE = [
    "DROP INDEX IF EXISTS ix_document_chunks_embedded;",
    "ALTER TABLE document_chunks DROP COLUMN embedded_at;",
    "ALTER TABLE document_chunks DROP COLUMN embedding_dimension;",
    "ALTER TABLE document_chunks DROP COLUMN embedding_model;",
    "ALTER TABLE document_chunks DROP COLUMN embedding;"
]

def upgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    if "postgres" in dialect_name.lower():
        # Check if vector extension is available in PostgreSQL instance
        has_vector_ext = False
        try:
            connection_or_cursor.execute("SELECT name FROM pg_available_extensions WHERE name = 'vector';")
            rows = connection_or_cursor.fetchall()
            if rows and rows[0] and rows[0][0] == "vector":
                has_vector_ext = True
        except Exception:
            has_vector_ext = False

        if has_vector_ext:
            connection_or_cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            embed_sql = "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding vector(768);"
        else:
            embed_sql = "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding TEXT;"

        stmts = [
            embed_sql,
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(64);",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_dimension INTEGER;",
            "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMP WITH TIME ZONE;",
            "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedded ON document_chunks(document_id, embedding_model);"
        ]
        for sql in stmts:
            connection_or_cursor.execute(sql)
    else:
        for sql in SQL_UPGRADE_SQLITE:
            try:
                connection_or_cursor.execute(sql)
            except Exception as e:
                # If SQLite column already exists, skip gracefully
                if "duplicate column name" in str(e).lower():
                    continue
                raise e

def downgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    stmts = SQL_DOWNGRADE_POSTGRES if "postgres" in dialect_name.lower() else SQL_DOWNGRADE_SQLITE
    for sql in stmts:
        try:
            connection_or_cursor.execute(sql)
        except Exception:
            pass
