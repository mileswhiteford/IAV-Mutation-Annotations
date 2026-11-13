import json
import sqlite3
import threading
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

APP_ID = 0x49415641
TABLES = {"profiles", "settings", "papers", "sources", "observations", "revisions", "reviews"}


def now() -> str:
    return datetime.now(UTC).isoformat()


def uid() -> str:
    return str(uuid4())


def get(conn, table: str, key: str):
    if table not in TABLES:
        raise ValueError("Unknown table")
    row = conn.execute(f"SELECT data FROM {table} WHERE id = ?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def put(conn, table: str, key: str, data: dict):
    if table not in TABLES:
        raise ValueError("Unknown table")
    conn.execute(f"INSERT INTO {table}(id, data) VALUES (?, ?) "
                 "ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                 (key, json.dumps(data, ensure_ascii=False)))


def all_rows(conn, table: str) -> list[dict]:
    if table not in TABLES:
        raise ValueError("Unknown table")
    return [json.loads(row[0]) for row in conn.execute(f"SELECT data FROM {table} ORDER BY rowid")]


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connection() as conn:
            app_id = conn.execute("PRAGMA application_id").fetchone()[0]
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            existing_tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchone()
            if app_id not in (0, APP_ID) or version > 1 or (app_id == 0 and existing_tables):
                raise ValueError("Unsupported annotation database")
            for table in sorted(TABLES):
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table}(id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            conn.execute(f"PRAGMA application_id={APP_ID}")
            conn.execute("PRAGMA user_version=1")
            conn.execute("CREATE INDEX IF NOT EXISTS observation_pmid ON observations(json_extract(data, '$.pmid'))")
            conn.execute("CREATE INDEX IF NOT EXISTS source_pmid ON sources(json_extract(data, '$.pmid'))")

    @contextmanager
    def connection(self):
        with self.lock, closing(sqlite3.connect(self.path, timeout=10)) as conn, conn:
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn

    def backup(self) -> bytes:
        # https://docs.python.org/3/library/sqlite3.html#sqlite3.Connection.backup
        with self.connection() as conn, sqlite3.connect(":memory:") as target:
            conn.backup(target)
            return target.serialize()

    def restore(self, content: bytes):
        try:
            candidate = sqlite3.connect(":memory:")
            candidate.deserialize(content)
            if candidate.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
                raise ValueError("This is not an IAV Annotator backup")
            if candidate.execute("PRAGMA user_version").fetchone()[0] != 1:
                raise ValueError("Unsupported backup version")
            if candidate.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("The backup failed its integrity check")
            names = {row[0] for row in candidate.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if names != TABLES:
                raise ValueError("The backup has an unexpected structure")
            for table in TABLES:
                for row in candidate.execute(f"SELECT data FROM {table}"):
                    if not isinstance(json.loads(row[0]), dict):
                        raise TypeError("The backup contains an invalid record")
            with self.lock:
                previous = self.backup()
                recovery = self.path.with_suffix(".before-restore.sqlite3")
                recovery.write_bytes(previous)
                with self.connection() as conn:
                    candidate.backup(conn)
        except (sqlite3.Error, json.JSONDecodeError, TypeError) as exc:
            raise ValueError("Cannot read this annotation backup") from exc
        finally:
            if "candidate" in locals():
                candidate.close()
