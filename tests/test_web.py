"""Tests for FISC-QAv2 Review Web UI (db + API)."""

from __future__ import annotations

import json
import tempfile
from io import BytesIO
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config import Config
from src.web import db


# --- DB Layer Tests ---


@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    return db_path


@pytest.fixture
def sample_data():
    questions = [
        {"no": 1, "major": "セキュリティ管理", "minor": "認証", "question": "MFAの導入状況は？"},
        {"no": 2, "major": "バックアップ管理", "minor": "RPO", "question": "RPOの設定は？"},
        {"no": 3, "major": "アクセス管理", "minor": "権限", "question": "最小権限の原則は？"},
    ]
    answers = [
        {
            "question_no": 1, "answer": "MFA導入済み", "status": "対応済み",
            "source_references": ["security_policy.pdf"], "confidence": "high",
            "key_excerpt": "MFAを全ユーザに適用", "flag": None,
        },
        {
            "question_no": 2, "answer": "RPO=4時間", "status": "対応済み",
            "source_references": ["backup_policy.docx"], "confidence": "medium",
            "key_excerpt": "", "flag": None,
        },
        {
            "question_no": 3, "answer": "", "status": "回答不可",
            "source_references": [], "confidence": "low",
            "key_excerpt": "", "flag": "KB に該当情報なし",
        },
    ]
    review_notes = [
        {
            "question_no": 2, "issue_type": "weak_reference", "severity": "medium",
            "description": "根拠ソースの記述が曖昧", "suggestion": "具体的なセクション番号を追記",
        },
        {
            "question_no": 3, "issue_type": "missing_evidence", "severity": "high",
            "description": "KBに関連情報がない", "suggestion": "アクセス管理規程の追加を検討",
        },
    ]
    return questions, answers, review_notes


def test_init_db(tmp_db):
    assert tmp_db.exists()


def test_import_and_list_runs(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)
    assert run_id == 1

    runs = db.list_runs(tmp_db)
    assert len(runs) == 1
    assert runs[0]["name"] == "test_run"
    assert runs[0]["total_questions"] == 3
    assert runs[0]["pending_count"] == 3


def test_get_run(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)
    run = db.get_run(tmp_db, run_id)
    assert run is not None
    assert run["name"] == "test_run"

    assert db.get_run(tmp_db, 999) is None


def test_get_answers(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    all_answers = db.get_answers(tmp_db, run_id)
    assert len(all_answers) == 3
    assert all_answers[0]["question_no"] == 1
    assert all_answers[0]["answer"] == "MFA導入済み"
    assert all_answers[0]["source_references"] == ["security_policy.pdf"]
    assert all_answers[0]["review_status"] == "pending"


def test_get_single_answer(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    ans = db.get_answer(tmp_db, run_id, 1)
    assert ans is not None
    assert ans["confidence"] == "high"

    assert db.get_answer(tmp_db, run_id, 99) is None


def test_set_review(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    ok = db.set_review(tmp_db, run_id, 1, "approved", "LGTM")
    assert ok is True

    ans = db.get_answer(tmp_db, run_id, 1)
    assert ans["review_status"] == "approved"
    assert ans["review_comment"] == "LGTM"
    assert ans["reviewed_at"] is not None

    # Run counts updated
    run = db.get_run(tmp_db, run_id)
    assert run["approved_count"] == 1
    assert run["pending_count"] == 2


def test_bulk_set_review(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    count = db.bulk_set_review(tmp_db, run_id, "approved", [1, 2])
    assert count == 2

    run = db.get_run(tmp_db, run_id)
    assert run["approved_count"] == 2
    assert run["pending_count"] == 1


def test_bulk_set_review_all(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    count = db.bulk_set_review(tmp_db, run_id, "approved")
    assert count == 3

    run = db.get_run(tmp_db, run_id)
    assert run["approved_count"] == 3
    assert run["pending_count"] == 0


def test_get_review_notes(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    result = db.get_review_notes(tmp_db, run_id)
    assert len(result) == 2
    # Sorted by severity DESC → high first
    assert result[0]["severity"] == "high"
    assert result[0]["question_no"] == 3


def test_get_run_stats(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    db.set_review(tmp_db, run_id, 1, "approved")
    db.set_review(tmp_db, run_id, 3, "rejected")

    stats = db.get_run_stats(tmp_db, run_id)
    assert stats["total"] == 3
    assert stats["approved"] == 1
    assert stats["rejected"] == 1
    assert stats["pending"] == 1
    assert stats["conf_high"] == 1
    assert stats["conf_medium"] == 1
    assert stats["conf_low"] == 1
    assert stats["review_notes_count"] == 2


def test_filter_by_review_status(tmp_db, sample_data):
    questions, answers, notes = sample_data
    run_id = db.import_run(tmp_db, "test_run", questions, answers, notes)

    db.set_review(tmp_db, run_id, 1, "approved")

    approved = db.get_answers(tmp_db, run_id, review_status="approved")
    assert len(approved) == 1
    assert approved[0]["question_no"] == 1

    pending = db.get_answers(tmp_db, run_id, review_status="pending")
    assert len(pending) == 2


# --- API Tests ---


@pytest.fixture
def client(tmp_db):
    from starlette.testclient import TestClient
    from src.web.app import create_app

    config = Config(kb_dir="kb", api_key="test-key")
    app = create_app(tmp_db, config=config)
    return TestClient(app)


@pytest.fixture
def populated_client(client, sample_data, tmp_db):
    questions, answers, notes = sample_data
    db.import_run(tmp_db, "test_run", questions, answers, notes)
    return client


def _make_test_excel():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["No.", "大分類", "小分類", "質問内容", "回答", "対応状況", "根拠ソース", "確信度", "備考"])
    ws.append([1, "セキュリティ管理", "認証", "MFAは？", "導入済み", "対応済み", "sec.pdf", "high", ""])
    ws.append([2, "バックアップ", "RPO", "RPOは？", "4時間", "対応済み", "backup.docx", "medium", ""])

    ws2 = wb.create_sheet("レビュー指摘")
    ws2.append(["質問No.", "指摘種別", "重大度", "説明", "提案"])
    ws2.append([2, "weak_reference", "medium", "曖昧", "詳細化"])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def test_api_import_excel(client):
    content = _make_test_excel()
    res = client.post("/api/runs/import", files={"file": ("test.xlsx", content)})
    assert res.status_code == 200
    data = res.json()
    assert data["run_id"] == 1
    assert "2件" in data["message"]


def test_api_import_json(client):
    payload = {
        "questions": [{"no": 1, "major": "A", "minor": "B", "question": "Q?"}],
        "answers": [{"question_no": 1, "answer": "A!", "status": "ok", "confidence": "high"}],
        "review_notes": [],
    }
    content = json.dumps(payload).encode()
    res = client.post("/api/runs/import", files={"file": ("test.json", content)})
    assert res.status_code == 200


def test_api_list_runs(populated_client):
    res = populated_client.get("/api/runs")
    assert res.status_code == 200
    runs = res.json()
    assert len(runs) == 1


def test_api_get_run(populated_client):
    res = populated_client.get("/api/runs/1")
    assert res.status_code == 200
    assert res.json()["name"] == "test_run"


def test_api_get_run_404(client):
    res = client.get("/api/runs/999")
    assert res.status_code == 404


def test_api_get_answers(populated_client):
    res = populated_client.get("/api/runs/1/answers")
    assert res.status_code == 200
    answers = res.json()
    assert len(answers) == 3


def test_api_get_answers_filtered(populated_client):
    res = populated_client.get("/api/runs/1/answers?review_status=pending")
    assert len(res.json()) == 3


def test_api_get_answer_detail(populated_client):
    res = populated_client.get("/api/runs/1/answers/1")
    assert res.status_code == 200
    data = res.json()
    assert data["answer"] == "MFA導入済み"
    assert "review_notes" in data


def test_api_set_review(populated_client):
    res = populated_client.put(
        "/api/runs/1/answers/1/review",
        json={"status": "approved", "comment": "OK"},
    )
    assert res.status_code == 200

    ans = populated_client.get("/api/runs/1/answers/1").json()
    assert ans["review_status"] == "approved"
    assert ans["review_comment"] == "OK"


def test_api_set_review_invalid_status(populated_client):
    res = populated_client.put(
        "/api/runs/1/answers/1/review",
        json={"status": "invalid"},
    )
    assert res.status_code == 400


def test_api_bulk_review(populated_client):
    res = populated_client.put(
        "/api/runs/1/bulk-review",
        json={"status": "approved", "question_nos": [1, 2]},
    )
    assert res.status_code == 200
    assert res.json()["updated"] == 2


def test_api_get_review_notes(populated_client):
    res = populated_client.get("/api/runs/1/review-notes")
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_api_get_stats(populated_client):
    res = populated_client.get("/api/runs/1/stats")
    assert res.status_code == 200
    stats = res.json()
    assert stats["total"] == 3
    assert stats["pending"] == 3


def test_api_export(populated_client):
    # Approve one first
    populated_client.put("/api/runs/1/answers/1/review", json={"status": "approved"})
    res = populated_client.get("/api/runs/1/export")
    assert res.status_code == 200
    assert "spreadsheet" in res.headers["content-type"]


def test_api_delete_run(populated_client):
    res = populated_client.delete("/api/runs/1")
    assert res.status_code == 200

    res = populated_client.get("/api/runs/1")
    assert res.status_code == 404


def test_api_static_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "FISC-QAv2" in res.text


# --- Config API Tests ---


def test_api_get_config(client):
    res = client.get("/api/config")
    assert res.status_code == 200
    data = res.json()
    assert data["kb_dir"] == "kb"
    assert data["api_key_set"] is True
    assert "model" in data
    assert "token_budget" in data


def test_api_update_config(client):
    res = client.put("/api/config", json={"kb_dir": "/new/kb", "model": "claude-haiku-4-5-20251001"})
    assert res.status_code == 200

    res = client.get("/api/config")
    data = res.json()
    assert data["kb_dir"] == "/new/kb"
    assert data["model"] == "claude-haiku-4-5-20251001"


def test_api_update_config_partial(client):
    res = client.put("/api/config", json={"token_budget": 50000})
    assert res.status_code == 200

    res = client.get("/api/config")
    assert res.json()["token_budget"] == 50000


# --- Pipeline API Tests ---


def test_api_pipeline_start(client, tmp_path):
    content = _make_test_excel()

    # Create a fake kb directory
    kb_dir = tmp_path / "kb"
    kb_dir.mkdir()

    # Update config to point to our temp kb dir
    client.put("/api/config", json={"kb_dir": str(kb_dir)})

    with patch("src.web.pipeline.start_pipeline_job", return_value="abc123") as mock_start:
        res = client.post("/api/pipeline/start", files={"file": ("test.xlsx", content)})
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == "abc123"
        mock_start.assert_called_once()


def test_api_pipeline_start_rejects_non_xlsx(client):
    res = client.post("/api/pipeline/start", files={"file": ("test.json", b"{}")})
    assert res.status_code == 400


def test_api_pipeline_status(client):
    from src.web.pipeline import JobState, _jobs

    job = JobState(job_id="test123", status="running", progress=["step1", "step2"])
    _jobs["test123"] = job

    res = client.get("/api/pipeline/test123/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "running"
    assert len(data["progress"]) == 2
    assert data["progress"][0] == "step1"

    # Cleanup
    del _jobs["test123"]


def test_api_pipeline_status_404(client):
    res = client.get("/api/pipeline/nonexistent/status")
    assert res.status_code == 404


def test_api_pipeline_progress_404(client):
    res = client.get("/api/pipeline/nonexistent/progress")
    assert res.status_code == 404
