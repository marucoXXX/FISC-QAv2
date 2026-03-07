"""SQLite database layer for review workflow."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB_PATH = Path("fisc_review.db")

SCHEMA = """\
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    source_file TEXT,
    total_questions INTEGER NOT NULL DEFAULT 0,
    approved_count INTEGER NOT NULL DEFAULT 0,
    rejected_count INTEGER NOT NULL DEFAULT 0,
    pending_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    question_no INTEGER NOT NULL,
    major TEXT NOT NULL DEFAULT '',
    minor TEXT NOT NULL DEFAULT '',
    question TEXT NOT NULL DEFAULT '',
    answer TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT '',
    source_references TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT 'low',
    key_excerpt TEXT NOT NULL DEFAULT '',
    flag TEXT,
    review_status TEXT NOT NULL DEFAULT 'pending',
    review_comment TEXT NOT NULL DEFAULT '',
    reviewed_at TEXT,
    UNIQUE(run_id, question_no)
);

CREATE TABLE IF NOT EXISTS review_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    question_no INTEGER NOT NULL,
    issue_type TEXT NOT NULL DEFAULT 'other',
    severity TEXT NOT NULL DEFAULT 'medium',
    description TEXT NOT NULL DEFAULT '',
    suggestion TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_answers_run ON answers(run_id);
CREATE INDEX IF NOT EXISTS idx_answers_review ON answers(run_id, review_status);
CREATE INDEX IF NOT EXISTS idx_notes_run ON review_notes(run_id);
"""


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(SCHEMA)
    return db_path


@contextmanager
def get_conn(db_path: Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def import_run(
    db_path: Path,
    name: str,
    questions: list[dict],
    answers: list[dict],
    review_notes: list[dict],
    source_file: str = "",
) -> int:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO runs (name, imported_at, source_file, total_questions, pending_count) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, datetime.now().isoformat(), source_file, len(questions), len(questions)),
        )
        run_id = cur.lastrowid

        q_map = {q["no"]: q for q in questions}

        for ans in answers:
            q = q_map.get(ans["question_no"], {})
            refs = ans.get("source_references", [])
            conn.execute(
                "INSERT INTO answers "
                "(run_id, question_no, major, minor, question, answer, status, "
                " source_references, confidence, key_excerpt, flag) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    ans["question_no"],
                    q.get("major", ""),
                    q.get("minor", ""),
                    q.get("question", ""),
                    ans.get("answer", ""),
                    ans.get("status", ""),
                    json.dumps(refs, ensure_ascii=False),
                    ans.get("confidence", "low"),
                    ans.get("key_excerpt", ""),
                    ans.get("flag"),
                ),
            )

        for note in review_notes:
            conn.execute(
                "INSERT INTO review_notes "
                "(run_id, question_no, issue_type, severity, description, suggestion) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    note["question_no"],
                    note.get("issue_type", "other"),
                    note.get("severity", "medium"),
                    note.get("description", ""),
                    note.get("suggestion", ""),
                ),
            )

    return run_id


def list_runs(db_path: Path) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY imported_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(db_path: Path, run_id: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return dict(row) if row else None


def get_answers(db_path: Path, run_id: int, review_status: str | None = None) -> list[dict]:
    with get_conn(db_path) as conn:
        if review_status:
            rows = conn.execute(
                "SELECT * FROM answers WHERE run_id = ? AND review_status = ? ORDER BY question_no",
                (run_id, review_status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM answers WHERE run_id = ? ORDER BY question_no",
                (run_id,),
            ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["source_references"] = json.loads(d["source_references"])
        results.append(d)
    return results


def get_answer(db_path: Path, run_id: int, question_no: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM answers WHERE run_id = ? AND question_no = ?",
            (run_id, question_no),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["source_references"] = json.loads(d["source_references"])
    return d


def set_review(
    db_path: Path, run_id: int, question_no: int, status: str, comment: str = "",
) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "UPDATE answers SET review_status = ?, review_comment = ?, reviewed_at = ? "
            "WHERE run_id = ? AND question_no = ?",
            (status, comment, datetime.now().isoformat(), run_id, question_no),
        )
        if cur.rowcount == 0:
            return False
        _update_run_counts(conn, run_id)
    return True


def bulk_set_review(
    db_path: Path, run_id: int, status: str, question_nos: list[int] | None = None,
) -> int:
    with get_conn(db_path) as conn:
        now = datetime.now().isoformat()
        if question_nos:
            placeholders = ",".join("?" for _ in question_nos)
            cur = conn.execute(
                f"UPDATE answers SET review_status = ?, review_comment = '', reviewed_at = ? "
                f"WHERE run_id = ? AND question_no IN ({placeholders})",
                [status, now, run_id] + question_nos,
            )
        else:
            cur = conn.execute(
                "UPDATE answers SET review_status = ?, review_comment = '', reviewed_at = ? "
                "WHERE run_id = ?",
                (status, now, run_id),
            )
        count = cur.rowcount
        _update_run_counts(conn, run_id)
    return count


def get_review_notes(db_path: Path, run_id: int) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM review_notes WHERE run_id = ? "
            "ORDER BY CASE severity WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END, "
            "question_no",
            (run_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_run_stats(db_path: Path, run_id: int) -> dict:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT "
            "  COUNT(*) as total, "
            "  SUM(CASE WHEN review_status='approved' THEN 1 ELSE 0 END) as approved, "
            "  SUM(CASE WHEN review_status='rejected' THEN 1 ELSE 0 END) as rejected, "
            "  SUM(CASE WHEN review_status='needs_revision' THEN 1 ELSE 0 END) as needs_revision, "
            "  SUM(CASE WHEN review_status='pending' THEN 1 ELSE 0 END) as pending, "
            "  SUM(CASE WHEN confidence='high' THEN 1 ELSE 0 END) as conf_high, "
            "  SUM(CASE WHEN confidence='medium' THEN 1 ELSE 0 END) as conf_medium, "
            "  SUM(CASE WHEN confidence='low' THEN 1 ELSE 0 END) as conf_low, "
            "  SUM(CASE WHEN confidence='past_answer' THEN 1 ELSE 0 END) as conf_past "
            "FROM answers WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        note_count = conn.execute(
            "SELECT COUNT(*) FROM review_notes WHERE run_id = ?", (run_id,),
        ).fetchone()[0]
    stats = dict(row)
    stats["review_notes_count"] = note_count
    return stats


def _update_run_counts(conn: sqlite3.Connection, run_id: int) -> None:
    row = conn.execute(
        "SELECT "
        "  SUM(CASE WHEN review_status='approved' THEN 1 ELSE 0 END), "
        "  SUM(CASE WHEN review_status='rejected' THEN 1 ELSE 0 END), "
        "  SUM(CASE WHEN review_status='pending' OR review_status='needs_revision' "
        "       THEN 1 ELSE 0 END) "
        "FROM answers WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    conn.execute(
        "UPDATE runs SET approved_count=?, rejected_count=?, pending_count=? WHERE id=?",
        (row[0] or 0, row[1] or 0, row[2] or 0, run_id),
    )
