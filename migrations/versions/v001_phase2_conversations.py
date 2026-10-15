"""
Migration Revision 001: Create conversations and chat_messages tables.
Supports both SQLite and PostgreSQL.
"""

REVISION = "001_phase2_conversations"
DESCRIPTION = "Create conversations and chat_messages tables with ON DELETE CASCADE and indexes"

SQL_UPGRADE_POSTGRES = [
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id VARCHAR(64) PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title VARCHAR(255) DEFAULT 'Cuộc trò chuyện mới',
        status VARCHAR(50) DEFAULT 'ACTIVE',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id VARCHAR(64) PRIMARY KEY,
        conversation_id VARCHAR(64) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
        role VARCHAR(20) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_chat_messages_conv_created ON chat_messages(conversation_id, created_at);
    """
]

SQL_UPGRADE_SQLITE = [
    """
    CREATE TABLE IF NOT EXISTS conversations (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        title TEXT DEFAULT 'Cuộc trò chuyện mới',
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_messages (
        id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_chat_messages_conv_created ON chat_messages(conversation_id, created_at);
    """
]

SQL_DOWNGRADE = [
    "DROP TABLE IF EXISTS chat_messages;",
    "DROP TABLE IF EXISTS conversations;"
]

def upgrade(connection, dialect_name: str = "sqlite"):
    stmts = SQL_UPGRADE_POSTGRES if "postgres" in dialect_name.lower() else SQL_UPGRADE_SQLITE
    for sql in stmts:
        connection.execute(sql)

def downgrade(connection, dialect_name: str = "sqlite"):
    for sql in SQL_DOWNGRADE:
        connection.execute(sql)
