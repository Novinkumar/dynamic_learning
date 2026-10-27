"""Small, idempotent upgrades for databases created before AI practice existed.

The project intentionally has no migration framework. ``db.create_all()`` still
creates a complete fresh schema; this module only adds nullable/defaulted
columns to an existing development database. It never changes learner data.
"""

from sqlalchemy import inspect, text

from .. import db


# Column name -> portable DDL. Every added column is nullable or has a
# non-destructive default so existing rows remain valid.
QUIZ_COLUMNS = {
    "source": "VARCHAR(30) DEFAULT 'catalog' NOT NULL",
    "owner_id": "INTEGER NULL",
    "generation_provider": "VARCHAR(80) NULL",
    "generation_model": "VARCHAR(120) NULL",
    "generation_seed": "VARCHAR(80) NULL",
    "generation_mode": "VARCHAR(30) NULL",
    "difficulty": "VARCHAR(30) NULL",
    # SQLite cannot add a column with a non-constant default; backfill below.
    "created_at": "DATETIME NULL",
    "completed_at": "DATETIME NULL",
}

QUESTION_COLUMNS = {
    "explanation": "TEXT DEFAULT '' NOT NULL",
    "skill": "VARCHAR(80) DEFAULT '' NOT NULL",
    "difficulty": "VARCHAR(20) DEFAULT 'core' NOT NULL",
}


def _add_missing_columns(connection, inspector, table, definitions):
    existing = {column["name"] for column in inspector.get_columns(table)}
    for name, definition in definitions.items():
        if name not in existing:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {definition}"))


def ensure_schema():
    """Add AI-practice columns and indexes to an already-created database."""
    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "quiz" not in tables or "question" not in tables:
        return
    with db.engine.begin() as connection:
        _add_missing_columns(connection, inspector, "quiz", QUIZ_COLUMNS)
        _add_missing_columns(connection, inspector, "question", QUESTION_COLUMNS)
        # Give existing shared quizzes a real creation date without relying on
        # a non-constant DEFAULT in ALTER TABLE.
        connection.execute(text("UPDATE quiz SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_quiz_owner_id ON quiz (owner_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_quiz_source ON quiz (source)"))
