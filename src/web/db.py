"""SQLite database layer for FISC-QAv2."""

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

-- 銀行マスタ
CREATE TABLE IF NOT EXISTS banks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 銀行別QAファイル（フォーマット設定含む）
CREATE TABLE IF NOT EXISTS bank_qa_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    qa_file_name TEXT NOT NULL,
    file_format TEXT NOT NULL DEFAULT 'xlsx',
    question_col TEXT NOT NULL DEFAULT 'D',
    answer_col TEXT NOT NULL DEFAULT 'E',
    header_row INTEGER NOT NULL DEFAULT 1,
    data_start_row INTEGER NOT NULL DEFAULT 2,
    table_index INTEGER NOT NULL DEFAULT 0,
    format_type TEXT NOT NULL DEFAULT 'freetext',
    choices_col TEXT NOT NULL DEFAULT '',
    remarks_col TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(bank_id, qa_file_name)
);
CREATE INDEX IF NOT EXISTS idx_bqf_bank ON bank_qa_files(bank_id);

-- 銀行別の過去Q&Aペア
CREATE TABLE IF NOT EXISTS past_qa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    choices_text TEXT NOT NULL DEFAULT '',
    remarks_text TEXT NOT NULL DEFAULT '',
    source_file TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_past_qa_bank ON past_qa(bank_id);

-- 共通回答DB
CREATE TABLE IF NOT EXISTS common_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_pattern TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ワークフロー（5ステップワークフローの単位）
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER NOT NULL REFERENCES banks(id),
    qa_file_id INTEGER REFERENCES bank_qa_files(id),
    name TEXT NOT NULL,
    current_step INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'in_progress',
    source_file_name TEXT NOT NULL DEFAULT '',
    source_file_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- ワークフロー内の各質問
CREATE TABLE IF NOT EXISTS session_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    question_no INTEGER NOT NULL,
    major TEXT NOT NULL DEFAULT '',
    minor TEXT NOT NULL DEFAULT '',
    question_text TEXT NOT NULL DEFAULT '',
    choices_text TEXT NOT NULL DEFAULT '',
    remarks_text TEXT NOT NULL DEFAULT '',
    answer_source TEXT NOT NULL DEFAULT 'pending',
    answer_text TEXT NOT NULL DEFAULT '',
    source_references TEXT NOT NULL DEFAULT '[]',
    confidence TEXT NOT NULL DEFAULT '',
    matched_past_qa_id INTEGER REFERENCES past_qa(id),
    past_question_text TEXT NOT NULL DEFAULT '',
    past_answer_text TEXT NOT NULL DEFAULT '',
    matched_common_id INTEGER REFERENCES common_answers(id),
    common_answer_text TEXT NOT NULL DEFAULT '',
    match_judgment TEXT NOT NULL DEFAULT '',
    match_reason TEXT NOT NULL DEFAULT '',
    assessment_mark TEXT NOT NULL DEFAULT '',
    user_confirmed INTEGER NOT NULL DEFAULT 0,
    step_resolved INTEGER NOT NULL DEFAULT 0,
    add_to_common INTEGER NOT NULL DEFAULT 0,
    UNIQUE(session_id, question_no)
);
CREATE INDEX IF NOT EXISTS idx_sq_session ON session_questions(session_id);

-- アップロードファイル管理
CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_id INTEGER NOT NULL REFERENCES banks(id) ON DELETE CASCADE,
    file_type TEXT NOT NULL,
    original_name TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    uploaded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_uf_bank ON uploaded_files(bank_id);

-- KBフォルダ管理
CREATE TABLE IF NOT EXISTS kb_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """既存DBに新しい列を追加するマイグレーション"""
    migrations = [
        ("session_questions", "match_judgment", "TEXT NOT NULL DEFAULT ''"),
        ("session_questions", "match_reason", "TEXT NOT NULL DEFAULT ''"),
        ("session_questions", "assessment_mark", "TEXT NOT NULL DEFAULT ''"),
        ("bank_qa_files", "analysis_confirmed", "INTEGER NOT NULL DEFAULT 0"),
        ("bank_qa_files", "column_definitions", "TEXT NOT NULL DEFAULT '[]'"),
        ("bank_qa_files", "row_structure", "TEXT NOT NULL DEFAULT ''"),
        ("bank_qa_files", "heading_pattern", "TEXT NOT NULL DEFAULT ''"),
        ("session_questions", "extra_columns", "TEXT NOT NULL DEFAULT '{}'"),
        ("session_questions", "is_heading", "INTEGER NOT NULL DEFAULT 0"),
    ]
    for table, col, col_def in migrations:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
        except sqlite3.OperationalError:
            pass  # 列が既に存在する場合はスキップ


def init_db(db_path: Path = DEFAULT_DB_PATH) -> Path:
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
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


# ===== Bank CRUD =====


def create_bank(
    db_path: Path,
    name: str,
    code: str,
    notes: str = "",
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO banks (name, code, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, code, notes, now, now),
        )
        return cur.lastrowid


def list_banks(db_path: Path) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT b.*, COUNT(DISTINCT pq.id) as past_qa_count, "
            "COUNT(DISTINCT bqf.id) as qa_file_count "
            "FROM banks b "
            "LEFT JOIN past_qa pq ON b.id = pq.bank_id "
            "LEFT JOIN bank_qa_files bqf ON b.id = bqf.bank_id "
            "GROUP BY b.id ORDER BY b.name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_bank(db_path: Path, bank_id: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM banks WHERE id = ?", (bank_id,)).fetchone()
    return dict(row) if row else None


def update_bank(db_path: Path, bank_id: int, **fields) -> bool:
    allowed = {"name", "code", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [bank_id]
    with get_conn(db_path) as conn:
        cur = conn.execute(f"UPDATE banks SET {set_clause} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_bank(db_path: Path, bank_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM banks WHERE id = ?", (bank_id,))
        return cur.rowcount > 0


# ===== Bank QA Files CRUD =====


def create_bank_qa_file(
    db_path: Path,
    bank_id: int,
    qa_file_name: str,
    file_format: str = "xlsx",
    question_col: str = "D",
    answer_col: str = "E",
    header_row: int = 1,
    data_start_row: int = 2,
    table_index: int = 0,
    format_type: str = "freetext",
    choices_col: str = "",
    remarks_col: str = "",
    analysis_confirmed: int = 0,
    column_definitions: str = "[]",
    row_structure: str = "",
    heading_pattern: str = "",
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO bank_qa_files (bank_id, qa_file_name, file_format, "
            "question_col, answer_col, header_row, data_start_row, table_index, "
            "format_type, choices_col, remarks_col, analysis_confirmed, "
            "column_definitions, row_structure, heading_pattern, "
            "created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (bank_id, qa_file_name, file_format, question_col, answer_col,
             header_row, data_start_row, table_index,
             format_type, choices_col, remarks_col, analysis_confirmed,
             column_definitions, row_structure, heading_pattern, now, now),
        )
        return cur.lastrowid


def list_bank_qa_files(db_path: Path, bank_id: int) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM bank_qa_files WHERE bank_id = ? ORDER BY id",
            (bank_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_bank_qa_file(db_path: Path, qa_file_id: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM bank_qa_files WHERE id = ?", (qa_file_id,),
        ).fetchone()
    return dict(row) if row else None


def update_bank_qa_file(db_path: Path, qa_file_id: int, **fields) -> bool:
    allowed = {"qa_file_name", "file_format", "question_col", "answer_col",
               "header_row", "data_start_row", "table_index",
               "format_type", "choices_col", "remarks_col"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [qa_file_id]
    with get_conn(db_path) as conn:
        cur = conn.execute(f"UPDATE bank_qa_files SET {set_clause} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_bank_qa_file(db_path: Path, qa_file_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM bank_qa_files WHERE id = ?", (qa_file_id,))
        return cur.rowcount > 0


# ===== Past QA CRUD =====


def add_past_qa(
    db_path: Path, bank_id: int, question_text: str, answer_text: str,
    source_file: str = "", choices_text: str = "", remarks_text: str = "",
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO past_qa (bank_id, question_text, answer_text, "
            "choices_text, remarks_text, source_file, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (bank_id, question_text, answer_text, choices_text, remarks_text,
             source_file, now),
        )
        return cur.lastrowid


def bulk_add_past_qa(
    db_path: Path, bank_id: int, qa_pairs: list[dict], source_file: str = "",
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        conn.executemany(
            "INSERT INTO past_qa (bank_id, question_text, answer_text, "
            "choices_text, remarks_text, source_file, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(bank_id, qa["question_text"], qa["answer_text"],
              qa.get("choices_text", ""), qa.get("remarks_text", ""),
              source_file, now)
             for qa in qa_pairs],
        )
        return len(qa_pairs)


def list_past_qa(db_path: Path, bank_id: int) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM past_qa WHERE bank_id = ? ORDER BY id", (bank_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_past_qa(db_path: Path, past_qa_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM past_qa WHERE id = ?", (past_qa_id,))
        return cur.rowcount > 0


# ===== Common Answers CRUD =====


def create_common_answer(
    db_path: Path, question_pattern: str, answer_text: str,
    category: str = "", source: str = "",
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO common_answers (question_pattern, answer_text, category, source, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (question_pattern, answer_text, category, source, now, now),
        )
        return cur.lastrowid


def list_common_answers(
    db_path: Path, category: str | None = None, search: str | None = None,
) -> list[dict]:
    with get_conn(db_path) as conn:
        query = "SELECT * FROM common_answers"
        params: list[Any] = []
        conditions = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if search:
            conditions.append("(question_pattern LIKE ? OR answer_text LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id"
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_common_answer(db_path: Path, common_id: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM common_answers WHERE id = ?", (common_id,),
        ).fetchone()
    return dict(row) if row else None


def update_common_answer(db_path: Path, common_id: int, **fields) -> bool:
    allowed = {"question_pattern", "answer_text", "category", "source"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [common_id]
    with get_conn(db_path) as conn:
        cur = conn.execute(f"UPDATE common_answers SET {set_clause} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_common_answer(db_path: Path, common_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM common_answers WHERE id = ?", (common_id,))
        return cur.rowcount > 0


# ===== Session CRUD =====


def create_session(
    db_path: Path, bank_id: int, name: str,
    source_file_name: str = "", source_file_path: str = "",
    qa_file_id: int | None = None,
) -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO sessions (bank_id, qa_file_id, name, current_step, status, "
            "source_file_name, source_file_path, created_at, updated_at) "
            "VALUES (?, ?, ?, 1, 'in_progress', ?, ?, ?, ?)",
            (bank_id, qa_file_id, name, source_file_name, source_file_path, now, now),
        )
        return cur.lastrowid


def list_sessions(db_path: Path) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT s.*, b.name as bank_name "
            "FROM sessions s JOIN banks b ON s.bank_id = b.id "
            "ORDER BY s.created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_session(db_path: Path, session_id: int) -> dict | None:
    with get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT s.*, b.name as bank_name, b.code as bank_code, "
            "qf.qa_file_name, qf.file_format, qf.question_col, qf.answer_col, "
            "qf.header_row, qf.data_start_row, qf.table_index, "
            "qf.format_type, qf.choices_col, qf.remarks_col, "
            "qf.column_definitions, qf.row_structure, qf.heading_pattern "
            "FROM sessions s "
            "JOIN banks b ON s.bank_id = b.id "
            "LEFT JOIN bank_qa_files qf ON s.qa_file_id = qf.id "
            "WHERE s.id = ?",
            (session_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_session(db_path: Path, session_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0


def update_session(db_path: Path, session_id: int, **fields) -> bool:
    allowed = {"current_step", "status", "name"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [session_id]
    with get_conn(db_path) as conn:
        cur = conn.execute(f"UPDATE sessions SET {set_clause} WHERE id = ?", values)
        return cur.rowcount > 0


# ===== Session Questions CRUD =====


def bulk_add_session_questions(
    db_path: Path, session_id: int, questions: list[dict],
) -> int:
    with get_conn(db_path) as conn:
        conn.executemany(
            "INSERT INTO session_questions "
            "(session_id, question_no, major, minor, question_text, "
            "choices_text, remarks_text, extra_columns, is_heading) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(session_id, q["question_no"], q.get("major", ""),
              q.get("minor", ""), q.get("question_text", ""),
              q.get("choices_text", ""), q.get("remarks_text", ""),
              q.get("extra_columns", "{}"), q.get("is_heading", 0))
             for q in questions],
        )
        return len(questions)


def get_session_questions(
    db_path: Path, session_id: int, answer_source: str | None = None,
) -> list[dict]:
    with get_conn(db_path) as conn:
        query = "SELECT * FROM session_questions WHERE session_id = ?"
        params: list[Any] = [session_id]
        if answer_source:
            query += " AND answer_source = ?"
            params.append(answer_source)
        query += " ORDER BY question_no"
        rows = conn.execute(query, params).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        d["source_references"] = json.loads(d["source_references"])
        results.append(d)
    return results


def update_session_question(db_path: Path, session_id: int, question_no: int, **fields) -> bool:
    allowed = {
        "answer_source", "answer_text", "source_references", "confidence",
        "matched_past_qa_id", "past_question_text", "past_answer_text",
        "match_judgment", "match_reason", "assessment_mark",
        "matched_common_id", "common_answer_text",
        "user_confirmed", "step_resolved", "add_to_common",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    if "source_references" in updates and isinstance(updates["source_references"], list):
        updates["source_references"] = json.dumps(updates["source_references"], ensure_ascii=False)
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [session_id, question_no]
    with get_conn(db_path) as conn:
        cur = conn.execute(
            f"UPDATE session_questions SET {set_clause} "
            f"WHERE session_id = ? AND question_no = ?", values,
        )
        return cur.rowcount > 0


def get_unresolved_questions(db_path: Path, session_id: int) -> list[dict]:
    return get_session_questions(db_path, session_id, answer_source="pending")


# ===== Legacy run helpers =====


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


# ===== KB Folders CRUD =====


def create_kb_folder(db_path: Path, path: str, label: str = "") -> int:
    now = datetime.now().isoformat()
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "INSERT INTO kb_folders (path, label, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (path, label, now, now),
        )
        return cur.lastrowid


def list_kb_folders(db_path: Path) -> list[dict]:
    with get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM kb_folders ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def update_kb_folder(db_path: Path, folder_id: int, **fields) -> bool:
    allowed = {"path", "label"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    updates["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [folder_id]
    with get_conn(db_path) as conn:
        cur = conn.execute(f"UPDATE kb_folders SET {set_clause} WHERE id = ?", values)
        return cur.rowcount > 0


def delete_kb_folder(db_path: Path, folder_id: int) -> bool:
    with get_conn(db_path) as conn:
        cur = conn.execute("DELETE FROM kb_folders WHERE id = ?", (folder_id,))
        return cur.rowcount > 0
