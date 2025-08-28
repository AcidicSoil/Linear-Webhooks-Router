-- SQLite schema for idempotent mapping and future DLQ support

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS mappings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  linear_issue_id TEXT NOT NULL UNIQUE,
  github_owner TEXT NOT NULL,
  github_repo TEXT NOT NULL,
  github_issue_number INTEGER NOT NULL,
  content_checksum TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mappings_linear_issue_id ON mappings(linear_issue_id);

-- Dead Letter Queue for failed events
CREATE TABLE IF NOT EXISTS failed_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  error TEXT NOT NULL,
  retries INTEGER NOT NULL DEFAULT 0,
  first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
);
