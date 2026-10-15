"""
Migration Revision 002: Create documents and document_chunks tables.
Supports both SQLite and PostgreSQL.
"""

REVISION = "002_phase3_documents"
DESCRIPTION = "Create documents and document_chunks tables with indexes, cascade delete and access scope"

SQL_UPGRADE_POSTGRES = [
    """
    CREATE TABLE IF NOT EXISTS documents (
        id VARCHAR(64) PRIMARY KEY,
        title VARCHAR(255) NOT NULL,
        filename VARCHAR(255) NOT NULL,
        source_type VARCHAR(50) DEFAULT 'policy' NOT NULL,
        mime_type VARCHAR(100) DEFAULT 'text/plain' NOT NULL,
        storage_path VARCHAR(500),
        checksum VARCHAR(64) NOT NULL,
        version INTEGER DEFAULT 1,
        status VARCHAR(32) DEFAULT 'PENDING',
        error_message TEXT,
        total_chunks INTEGER DEFAULT 0,
        access_scope VARCHAR(50) DEFAULT 'public',
        owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_checksum ON documents(checksum);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_status ON documents(status);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents(owner_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id VARCHAR(64) PRIMARY KEY,
        document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        page_number INTEGER,
        section VARCHAR(255),
        meta_info TEXT,
        token_estimate INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_document_chunks_doc_idx ON document_chunks(document_id, chunk_index);
    """
]

SQL_UPGRADE_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        filename TEXT NOT NULL,
        source_type TEXT DEFAULT 'policy' NOT NULL,
        mime_type TEXT DEFAULT 'text/plain' NOT NULL,
        storage_path TEXT,
        checksum TEXT NOT NULL,
        version INTEGER DEFAULT 1,
        status TEXT DEFAULT 'PENDING',
        error_message TEXT,
        total_chunks INTEGER DEFAULT 0,
        access_scope TEXT DEFAULT 'public',
        owner_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_checksum ON documents(checksum);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_status ON documents(status);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_documents_owner_id ON documents(owner_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS document_chunks (
        id TEXT PRIMARY KEY,
        document_id TEXT NOT NULL,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        page_number INTEGER,
        section TEXT,
        meta_info TEXT,
        token_estimate INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_document_chunks_document_id ON document_chunks(document_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_document_chunks_doc_idx ON document_chunks(document_id, chunk_index);
    """
]

SQL_DOWNGRADE = [
    "DROP TABLE IF EXISTS document_chunks;",
    "DROP TABLE IF EXISTS documents;"
]

def upgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    stmts = SQL_UPGRADE_POSTGRES if "postgres" in dialect_name.lower() else SQL_UPGRADE_SQLITE
    for sql in stmts:
        connection_or_cursor.execute(sql)

def downgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    for sql in SQL_DOWNGRADE:
        connection_or_cursor.execute(sql)
