"""
Migration Revision 004: Add embedding_version column to document_chunks table.
Supports PostgreSQL and SQLite.
"""

REVISION = "004_phase4_1_metadata"
DESCRIPTION = "Add embedding_version to document_chunks"

SQL_UPGRADE_POSTGRES = [
    "ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS embedding_version VARCHAR(32);"
]

SQL_UPGRADE_SQLITE = [
    "ALTER TABLE document_chunks ADD COLUMN embedding_version TEXT;"
]

SQL_DOWNGRADE_POSTGRES = [
    "ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding_version;"
]

SQL_DOWNGRADE_SQLITE = [
    "ALTER TABLE document_chunks DROP COLUMN embedding_version;"
]

def upgrade(connection_or_cursor, dialect_name: str = "sqlite"):
    stmts = SQL_UPGRADE_POSTGRES if "postgres" in dialect_name.lower() else SQL_UPGRADE_SQLITE
    for sql in stmts:
        try:
            connection_or_cursor.execute(sql)
        except Exception as e:
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
