"""Database connection and schema management."""

import logging
import sqlite3
from pathlib import Path

from gw2trading.config import settings

logger = logging.getLogger("gw2trading.db")

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database.

    Creates the data directory and database file if they don't exist.
    Applies the schema on first connection.
    """
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(settings.db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    _apply_schema(conn)
    return conn


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply schema.sql to the database (idempotent via IF NOT EXISTS)."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    logger.debug("Schema applied successfully")
