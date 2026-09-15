import aiosqlite
from pathlib import Path
from src.core.config import settings

DB_FILE = Path(settings.DATABASE_URL)


class DBConnection:
    """Connection manager supporting both `async with get_db_connection()` and `async with await get_db_connection()`."""

    def __init__(self, db_file=None):
        self.db_file = db_file
        self._conn = None

    def __await__(self):
        async def _connect():
            if self._conn is None:
                file_to_use = self.db_file or DB_FILE
                self._conn = await aiosqlite.connect(file_to_use)
                self._conn.row_factory = aiosqlite.Row
            return self
        return _connect().__await__()

    async def __aenter__(self):
        if self._conn is None:
            file_to_use = self.db_file or DB_FILE
            self._conn = await aiosqlite.connect(file_to_use)
            self._conn.row_factory = aiosqlite.Row
        return self._conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            await self._conn.close()
            self._conn = None

    def __getattr__(self, name):
        if self._conn is not None:
            return getattr(self._conn, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    async def close(self):
        if self._conn:
            await self._conn.close()
            self._conn = None


def get_db_connection(db_file=None):
    """Provides an aiosqlite database connection."""
    return DBConnection(db_file)


async def init_db() -> None:
    """Initializes the database schema if tables do not already exist."""
    async with await get_db_connection() as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS eval_history (
                run_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                total_attempts INTEGER NOT NULL,
                final_status TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS rejection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                attempt INTEGER NOT NULL,
                failed_criterion TEXT NOT NULL,
                failure_reason TEXT NOT NULL,
                corrections TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES eval_history (run_id)
            );
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS system_learnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_keyword TEXT NOT NULL,
                recurring_failure TEXT NOT NULL,
                successful_fix TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        # Seed sample learning if table is empty
        cursor = await db.execute("SELECT COUNT(*) FROM system_learnings;")
        row = await cursor.fetchone()
        if row and row[0] == 0:
            await db.execute(
                """
                INSERT INTO system_learnings (topic_keyword, recurring_failure, successful_fix)
                VALUES (?, ?, ?);
                """,
                (
                    "rag",
                    "Using terms like 'Vector' and 'Embedding' without immediate simplified definitions.",
                    "Define Vector as 'a list of numbers representing meaning' and Embedding as 'converting text to numbers' right in parentheses.",
                ),
            )
        await db.commit()
