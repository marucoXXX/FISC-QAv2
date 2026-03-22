"""E2Eワークフローテスト — 5ステップ統合テスト（XLSX / DOCX両形式）

テストシナリオ:
  1. 過去回答が揃っている → Step2でマッチ・採用
  2. 新規質問 + 共通DB → Step3でマッチ・採用
  3. 新規質問 + KB → Step4でAI回答生成
"""
from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from src.config import Config
from src.web import db
from src.web.app import create_app

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "e2e_workflow"


# ---------------------------------------------------------------------------
# Test data (inline — matches generate_e2e_fixtures.py)
# ---------------------------------------------------------------------------

PAST_ANSWERS = json.loads((FIXTURES_DIR / "past_answers.json").read_text(encoding="utf-8"))
COMMON_ANSWERS = json.loads((FIXTURES_DIR / "common_answers.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_fixture(name: str) -> bytes:
    return (FIXTURES_DIR / name).read_bytes()


def _upload_session(client: TestClient, bank_id: int, filename: str,
                    qa_file_id: Optional[int] = None) -> int:
    """Create a session by uploading a questionnaire file, return session_id."""
    content = _read_fixture(filename)
    url = f"/api/sessions?bank_id={bank_id}"
    if qa_file_id:
        url += f"&qa_file_id={qa_file_id}"
    res = client.post(url, files={"file": (filename, content)})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["question_count"] == 10
    return data["session_id"]


def _run_step2(client: TestClient, sid: int) -> dict:
    """Run Step2 past-answer matching."""
    res = client.post(f"/api/sessions/{sid}/step2/match")
    assert res.status_code == 200
    return res.json()


def _confirm_step2(client: TestClient, sid: int, accept_nos: list[int],
                   reject_nos: Optional[list[int]] = None):
    """Confirm Step2 matches."""
    items = [{"question_no": n, "confirmed": True} for n in accept_nos]
    if reject_nos:
        items += [{"question_no": n, "confirmed": False} for n in reject_nos]
    res = client.put(f"/api/sessions/{sid}/step2/confirm", json=items)
    assert res.status_code == 200
    return res.json()


def _make_litellm_mock(common_ids: list[int]):
    """Create a mock for litellm.completion that returns Q6-Q8 matched to common answers."""
    matches = [
        {"question_no": 6, "common_id": common_ids[0], "score": 0.92},
        {"question_no": 7, "common_id": common_ids[1], "score": 0.89},
        {"question_no": 8, "common_id": common_ids[2], "score": 0.91},
    ]
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = json.dumps(matches)
    return mock_resp


def _make_pipeline_mock(db_path: Path, sid: int):
    """Mock pipeline that directly updates Q9-Q10 as 'generated'."""
    def fake_start(session_id, unresolved_questions, config, db_path):
        for q in unresolved_questions:
            db.update_session_question(
                db_path, session_id, q["question_no"],
                answer_source="generated",
                answer_text=f"AI生成回答: {q['question_text'][:20]}...",
                source_references=json.dumps(["kb/system_docs/test.pdf"]),
                confidence="medium",
                step_resolved=4,
            )
        db.update_session(db_path, session_id, current_step=5)
        return "fake-job-id"
    return fake_start


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path):
    db_path = tmp_path / "test.db"
    db.init_db(db_path)
    return db_path


@pytest.fixture
def client(tmp_db):
    config = Config(kb_dir="kb", api_key="test-key")
    app = create_app(tmp_db, config=config)
    return TestClient(app)


@pytest.fixture
def bank_xlsx(client):
    """Create a test bank with XLSX format config, return (bank_id, qa_file_id)."""
    res = client.post("/api/banks", json={"name": "E2Eテスト銀行XLSX", "code": "E2EX"})
    assert res.status_code == 200
    bank_id = res.json()["id"]
    res = client.post(f"/api/banks/{bank_id}/qa-files", json={
        "qa_file_name": "質問票XLSX",
        "file_format": "xlsx",
        "question_col": "D",
        "answer_col": "E",
        "header_row": 1,
        "data_start_row": 2,
    })
    assert res.status_code == 200
    qa_file_id = res.json()["id"]
    return bank_id, qa_file_id


@pytest.fixture
def bank_docx(client):
    """Create a test bank with DOCX format config, return (bank_id, qa_file_id)."""
    res = client.post("/api/banks", json={"name": "E2Eテスト銀行DOCX", "code": "E2ED"})
    assert res.status_code == 200
    bank_id = res.json()["id"]
    res = client.post(f"/api/banks/{bank_id}/qa-files", json={
        "qa_file_name": "質問票DOCX",
        "file_format": "docx",
        "question_col": "D",
        "answer_col": "E",
        "header_row": 1,
        "data_start_row": 2,
        "table_index": 0,
    })
    assert res.status_code == 200
    qa_file_id = res.json()["id"]
    return bank_id, qa_file_id


@pytest.fixture
def past_qa_ids(client, tmp_db):
    """Insert past answers for a given bank. Returns (bank_id -> [past_qa_id, ...]) mapping."""
    def _insert(bank_id: int) -> list[int]:
        ids = []
        for pa in PAST_ANSWERS:
            pid = db.add_past_qa(
                tmp_db, bank_id, pa["question_text"], pa["answer_text"],
            )
            ids.append(pid)
        return ids
    return _insert


@pytest.fixture
def common_ids(tmp_db):
    """Insert common answers, return list of IDs."""
    ids = []
    for ca in COMMON_ANSWERS:
        cid = db.create_common_answer(
            tmp_db, ca["question_pattern"], ca["answer_text"],
            category=ca["category"],
        )
        ids.append(cid)
    return ids


# =========================================================================
# TestWorkflowXlsx — XLSX形式でのフルワークフローテスト
# =========================================================================

class TestWorkflowXlsx:

    def test_step2_matches_past_answers(self, client, bank_xlsx, past_qa_ids, tmp_db):
        """シナリオ1: 過去回答が揃っている → Step2でマッチ・採用"""
        bank_id, qa_file_id = bank_xlsx
        past_qa_ids(bank_id)

        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        # Step2 match
        result = _run_step2(client, sid)
        assert result["total"] == 10
        assert result["matched"] >= 5, f"Expected >=5 matches, got {result['matched']}"

        # Verify match results
        res = client.get(f"/api/sessions/{sid}/step2/results")
        questions = res.json()
        matched = [q for q in questions if q["matched_past_qa_id"] is not None]
        assert len(matched) >= 5

        # Confirm Q1-Q5 as past_match
        matched_nos = [q["question_no"] for q in matched]
        _confirm_step2(client, sid, accept_nos=matched_nos[:5],
                       reject_nos=[n for n in range(1, 11) if n not in matched_nos[:5]])

        # Verify answer_source
        res = client.get(f"/api/sessions/{sid}/questions")
        for q in res.json():
            if q["question_no"] <= 5:
                assert q["answer_source"] == "past_match", \
                    f"Q{q['question_no']} should be past_match"
                assert q["answer_text"] != ""

    def test_step3_matches_common_answers(self, client, bank_xlsx, past_qa_ids,
                                          common_ids, tmp_db):
        """シナリオ2: 新規質問 + 共通DB → Step3でマッチ・採用"""
        bank_id, qa_file_id = bank_xlsx
        past_qa_ids(bank_id)

        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        # Step2: match and confirm Q1-Q5
        _run_step2(client, sid)
        _confirm_step2(client, sid,
                       accept_nos=list(range(1, 6)),
                       reject_nos=list(range(6, 11)))

        # Step3: match with mocked LLM
        with patch("litellm.completion", return_value=_make_litellm_mock(common_ids)):
            res = client.post(f"/api/sessions/{sid}/step3/match")
            assert res.status_code == 200
            data = res.json()
            assert data["matched"] == 3

        # Verify Step3 results (only unresolved questions)
        res = client.get(f"/api/sessions/{sid}/step3/results")
        pending = res.json()
        common_matched = [q for q in pending if q["matched_common_id"] is not None]
        assert len(common_matched) == 3

        # Confirm Q6-Q8
        items = [{"question_no": n, "confirmed": True} for n in [6, 7, 8]]
        items += [{"question_no": n, "confirmed": False} for n in [9, 10]]
        res = client.put(f"/api/sessions/{sid}/step3/confirm", json=items)
        assert res.status_code == 200
        assert res.json()["confirmed"] == 3

        # Verify
        res = client.get(f"/api/sessions/{sid}/questions")
        for q in res.json():
            if q["question_no"] in [6, 7, 8]:
                assert q["answer_source"] == "common_match"
                assert q["answer_text"] != ""

    def test_step4_generates_from_kb(self, client, bank_xlsx, past_qa_ids,
                                     common_ids, tmp_db):
        """シナリオ3: 新規質問 → Step4でAI回答生成"""
        bank_id, qa_file_id = bank_xlsx
        past_qa_ids(bank_id)

        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        # Step2
        _run_step2(client, sid)
        _confirm_step2(client, sid,
                       accept_nos=list(range(1, 6)),
                       reject_nos=list(range(6, 11)))

        # Step3
        with patch("litellm.completion", return_value=_make_litellm_mock(common_ids)):
            client.post(f"/api/sessions/{sid}/step3/match")
        items = [{"question_no": n, "confirmed": True} for n in [6, 7, 8]]
        items += [{"question_no": n, "confirmed": False} for n in [9, 10]]
        client.put(f"/api/sessions/{sid}/step3/confirm", json=items)

        # Step4: mock pipeline
        with patch("src.web.pipeline.start_session_pipeline_job",
                    side_effect=_make_pipeline_mock(tmp_db, sid)):
            res = client.post(f"/api/sessions/{sid}/step4/generate")
            assert res.status_code == 200

        # Verify Q9-Q10 generated
        res = client.get(f"/api/sessions/{sid}/questions")
        for q in res.json():
            if q["question_no"] in [9, 10]:
                assert q["answer_source"] == "generated"
                assert q["answer_text"] != ""

    def test_full_workflow_end_to_end(self, client, bank_xlsx, past_qa_ids,
                                     common_ids, tmp_db):
        """全体フロー: Step1→Step2→Step3→Step4→Step5（XLSX）"""
        bank_id, qa_file_id = bank_xlsx
        past_qa_ids(bank_id)

        # Step1
        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        # Step2
        _run_step2(client, sid)
        _confirm_step2(client, sid,
                       accept_nos=list(range(1, 6)),
                       reject_nos=list(range(6, 11)))

        # Step3
        with patch("litellm.completion", return_value=_make_litellm_mock(common_ids)):
            client.post(f"/api/sessions/{sid}/step3/match")
        items = [{"question_no": n, "confirmed": True} for n in [6, 7, 8]]
        items += [{"question_no": n, "confirmed": False} for n in [9, 10]]
        client.put(f"/api/sessions/{sid}/step3/confirm", json=items)

        # Step4
        with patch("src.web.pipeline.start_session_pipeline_job",
                    side_effect=_make_pipeline_mock(tmp_db, sid)):
            client.post(f"/api/sessions/{sid}/step4/generate")

        # Step5: summary
        res = client.get(f"/api/sessions/{sid}/step5/summary")
        assert res.status_code == 200
        stats = res.json()["stats"]
        assert stats["past_match"] == 5
        assert stats["common_match"] == 3
        assert stats["generated"] == 2
        assert stats["pending"] == 0

        # Step5: finalize
        res = client.put(f"/api/sessions/{sid}/step5/finalize")
        assert res.status_code == 200
        assert res.json()["accumulated"] == 10

        # Verify past_qa accumulated
        past = db.list_past_qa(tmp_db, bank_id)
        # Original 5 + 10 accumulated from session
        assert len(past) >= 15

        # Step5: export
        res = client.get(f"/api/sessions/{sid}/export")
        assert res.status_code == 200
        assert "spreadsheet" in res.headers["content-type"]


# =========================================================================
# TestWorkflowDocx — DOCX形式でのワークフローテスト
# =========================================================================

class TestWorkflowDocx:

    def test_step1_extracts_questions_from_docx(self, client, bank_docx):
        """DOCX質問票から正しく10問抽出される"""
        bank_id, qa_file_id = bank_docx
        sid = _upload_session(client, bank_id, "questionnaire_10q.docx", qa_file_id)

        res = client.get(f"/api/sessions/{sid}/questions")
        assert res.status_code == 200
        questions = res.json()
        assert len(questions) == 10
        assert questions[0]["question_text"] == "情報セキュリティポリシーの策定・承認状況を教えてください"
        assert questions[9]["question_text"] == "SIEMによるリアルタイム監視体制について説明してください"

    def test_full_workflow_docx(self, client, bank_docx, past_qa_ids,
                                common_ids, tmp_db):
        """全体フロー: Step1→Step2→Step3→Step4→Step5（DOCX）"""
        bank_id, qa_file_id = bank_docx
        past_qa_ids(bank_id)

        # Step1
        sid = _upload_session(client, bank_id, "questionnaire_10q.docx", qa_file_id)

        # Step2
        _run_step2(client, sid)
        _confirm_step2(client, sid,
                       accept_nos=list(range(1, 6)),
                       reject_nos=list(range(6, 11)))

        # Step3
        with patch("litellm.completion", return_value=_make_litellm_mock(common_ids)):
            client.post(f"/api/sessions/{sid}/step3/match")
        items = [{"question_no": n, "confirmed": True} for n in [6, 7, 8]]
        items += [{"question_no": n, "confirmed": False} for n in [9, 10]]
        client.put(f"/api/sessions/{sid}/step3/confirm", json=items)

        # Step4
        with patch("src.web.pipeline.start_session_pipeline_job",
                    side_effect=_make_pipeline_mock(tmp_db, sid)):
            client.post(f"/api/sessions/{sid}/step4/generate")

        # Step5: summary
        res = client.get(f"/api/sessions/{sid}/step5/summary")
        stats = res.json()["stats"]
        assert stats["past_match"] == 5
        assert stats["common_match"] == 3
        assert stats["generated"] == 2

        # Step5: export
        res = client.get(f"/api/sessions/{sid}/export")
        assert res.status_code == 200
        assert "wordprocessingml" in res.headers["content-type"]


# =========================================================================
# TestFormatParity — XLSX/DOCXで同一結果になることを検証
# =========================================================================

class TestFormatParity:

    def test_same_questions_extracted(self, client, bank_xlsx, bank_docx):
        """XLSX/DOCXで同一質問が抽出される"""
        bank_id_x, qf_x = bank_xlsx
        bank_id_d, qf_d = bank_docx

        sid_x = _upload_session(client, bank_id_x, "questionnaire_10q.xlsx", qf_x)
        sid_d = _upload_session(client, bank_id_d, "questionnaire_10q.docx", qf_d)

        q_xlsx = client.get(f"/api/sessions/{sid_x}/questions").json()
        q_docx = client.get(f"/api/sessions/{sid_d}/questions").json()

        assert len(q_xlsx) == len(q_docx) == 10

        for qx, qd in zip(q_xlsx, q_docx):
            assert qx["question_no"] == qd["question_no"]
            assert qx["question_text"] == qd["question_text"]
            assert qx["major"] == qd["major"]
            assert qx["minor"] == qd["minor"]

    def test_export_formats(self, client, bank_xlsx, bank_docx,
                            past_qa_ids, common_ids, tmp_db):
        """XLSX入力→XLSX出力、DOCX入力→DOCX出力"""
        for bank_fixture, filename, expected_mime in [
            (bank_xlsx, "questionnaire_10q.xlsx", "spreadsheet"),
            (bank_docx, "questionnaire_10q.docx", "wordprocessingml"),
        ]:
            bank_id, qa_file_id = bank_fixture
            past_qa_ids(bank_id)

            sid = _upload_session(client, bank_id, filename, qa_file_id)

            # Step2-4 (skip to just manually add answers for export test)
            _run_step2(client, sid)
            all_nos = list(range(1, 11))
            _confirm_step2(client, sid, accept_nos=all_nos[:5], reject_nos=all_nos[5:])

            # Manually set answers for remaining questions
            for n in range(6, 11):
                client.put(f"/api/sessions/{sid}/questions/{n}",
                           json={"answer_text": f"手動回答{n}", "add_to_common": False})

            # Export
            res = client.get(f"/api/sessions/{sid}/export")
            assert res.status_code == 200
            assert expected_mime in res.headers["content-type"], \
                f"Expected {expected_mime} in {res.headers['content-type']}"
            assert len(res.content) > 100  # Not empty


# =========================================================================
# TestWorkflowLlmMatching — LLM/hybrid戦略のテスト
# =========================================================================

class TestWorkflowLlmMatching:

    def _mock_llm_past_response(self, past_qa_ids_list: list[int]):
        """LLM past answer matching mock response."""
        matches = []
        for i, pid in enumerate(past_qa_ids_list, start=1):
            matches.append({
                "question_no": i,
                "past_qa_id": pid,
                "score": 0.95,
                "judgment": "reusable",
                "reason": "語尾の変更のみで趣旨は同一",
            })
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = json.dumps(matches)
        return mock_resp

    def test_step2_llm_strategy(self, client, bank_xlsx, past_qa_ids, tmp_db):
        """LLM戦略でStep2マッチング"""
        bank_id, qa_file_id = bank_xlsx
        pids = past_qa_ids(bank_id)

        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        with patch("litellm.completion",
                    return_value=self._mock_llm_past_response(pids)):
            res = client.post(
                f"/api/sessions/{sid}/step2/match?match_strategy=llm")
            assert res.status_code == 200
            data = res.json()
            assert data["matched"] == 5

        # Verify judgment/reason stored
        res = client.get(f"/api/sessions/{sid}/step2/results")
        questions = res.json()
        matched = [q for q in questions if q["matched_past_qa_id"] is not None]
        assert len(matched) == 5
        for q in matched:
            assert q["match_judgment"] == "reusable"
            assert q["match_reason"] != ""

    def test_step2_hybrid_strategy(self, client, bank_xlsx, past_qa_ids, tmp_db):
        """ハイブリッド戦略でStep2マッチング"""
        bank_id, qa_file_id = bank_xlsx
        pids = past_qa_ids(bank_id)

        sid = _upload_session(client, bank_id, "questionnaire_10q.xlsx", qa_file_id)

        with patch("litellm.completion",
                    return_value=self._mock_llm_past_response(pids)):
            res = client.post(
                f"/api/sessions/{sid}/step2/match?match_strategy=hybrid")
            assert res.status_code == 200
            data = res.json()
            assert data["matched"] >= 5

        # Verify judgment is set
        res = client.get(f"/api/sessions/{sid}/step2/results")
        questions = res.json()
        matched = [q for q in questions if q["matched_past_qa_id"] is not None]
        assert all(q["match_judgment"] != "" for q in matched)
