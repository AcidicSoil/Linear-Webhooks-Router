from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Mapping:
    linear_issue_id: str
    github_owner: str
    github_repo: str
    github_issue_number: int
    content_checksum: str | None = None


class MappingRepository:
    """SQLite-backed repository for Linear↔GitHub issue mappings.

    Storage URL formats supported:
    - file path to a SQLite database file, e.g., `data/app.db`
    - `:memory:` for in-memory (tests)
    If the DB file does not exist, schema from `app/db/schema.sql` is applied.
    """

    def __init__(self, storage_url: Optional[str] = None) -> None:
        # Default to a local file if not provided
        self.storage_url = storage_url or "data/app.db"
        self._ensure_db_initialized()

    def _ensure_db_initialized(self) -> None:
        if self.storage_url != ":memory":
            db_path = Path(self.storage_url)
            db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            schema_path = Path(__file__).with_name("schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                conn.executescript(f.read())

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.storage_url)
        try:
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        finally:
            conn.close()

    def upsert_mapping(self, mapping: Mapping) -> Mapping:
        """Insert a new mapping or return existing if linear_issue_id exists.

        Ensures idempotency: same `linear_issue_id` will not create duplicates.
        """
        with self._connect() as conn:
            # Try insert; on conflict return existing stored row
            cur = conn.execute(
                """
                INSERT INTO mappings (linear_issue_id, github_owner, github_repo, github_issue_number, content_checksum)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(linear_issue_id) DO NOTHING;
                """,
                (
                    mapping.linear_issue_id,
                    mapping.github_owner,
                    mapping.github_repo,
                    mapping.github_issue_number,
                    mapping.content_checksum,
                ),
            )
            # Retrieve row to return canonical data
            row = conn.execute(
                "SELECT linear_issue_id, github_owner, github_repo, github_issue_number, content_checksum FROM mappings WHERE linear_issue_id = ?",
                (mapping.linear_issue_id,),
            ).fetchone()
            assert row is not None
            return Mapping(
                linear_issue_id=row["linear_issue_id"],
                github_owner=row["github_owner"],
                github_repo=row["github_repo"],
                github_issue_number=int(row["github_issue_number"]),
                content_checksum=row["content_checksum"],
            )

    def get_by_linear_issue_id(self, linear_issue_id: str) -> Optional[Mapping]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT linear_issue_id, github_owner, github_repo, github_issue_number, content_checksum FROM mappings WHERE linear_issue_id = ?",
                (linear_issue_id,),
            ).fetchone()
            if not row:
                return None
            return Mapping(
                linear_issue_id=row["linear_issue_id"],
                github_owner=row["github_owner"],
                github_repo=row["github_repo"],
                github_issue_number=int(row["github_issue_number"]),
                content_checksum=row["content_checksum"],
            )

    def update_checksum(self, linear_issue_id: str, checksum: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE mappings SET content_checksum = ? WHERE linear_issue_id = ?",
                (checksum, linear_issue_id),
            )

    # ---- DLQ operations ----
    def dlq_insert(self, event_type: str, payload: str, error: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO failed_events (event_type, payload, error) VALUES (?, ?, ?)",
                (event_type, payload, error),
            )
            return int(cur.lastrowid)

    def dlq_list(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, event_type, retries, last_seen FROM failed_events ORDER BY last_seen DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def dlq_get(self, id_: int):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, event_type, payload, error, retries, first_seen, last_seen FROM failed_events WHERE id = ?",
                (id_,),
            ).fetchone()
            return dict(row) if row else None

    def dlq_bump_retry(self, id_: int, error: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE failed_events SET retries = retries + 1, error = ?, last_seen = CURRENT_TIMESTAMP WHERE id = ?",
                (error, id_),
            )

    def dlq_delete(self, id_: int):
        with self._connect() as conn:
            conn.execute("DELETE FROM failed_events WHERE id = ?", (id_,))
