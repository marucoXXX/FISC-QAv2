"""Agent 3: Reader 単体テスト"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models import Answer, Confidence, Question
from src.reader import _parse_reader_response, _read_file_content, run_reader


class TestReader:
    """Reader がソースドキュメントを読み取り回答を生成できることを検証する。"""

    def test_policy_pdfs_readable(self, kb_dir: Path):
        """ポリシーPDFが存在し、空でないこと。"""
        policies = list((kb_dir / "policies").glob("*.pdf"))
        assert len(policies) == 3
        for pdf in policies:
            assert pdf.stat().st_size > 0, f"{pdf.name} is empty"

    def test_system_docs_readable(self, kb_dir: Path):
        """システム文書が存在し、空でないこと。"""
        docs = list((kb_dir / "system_docs").rglob("*"))
        files = [f for f in docs if f.is_file()]
        assert len(files) == 5

    def test_docx_files_readable(self, kb_dir: Path):
        """DOCXファイルが存在し、空でないこと。"""
        docx_files = list(kb_dir.rglob("*.docx"))
        assert len(docx_files) == 4
        for docx in docx_files:
            assert docx.stat().st_size > 0, f"{docx.name} is empty"

    def test_past_answers_readable(self, kb_dir: Path):
        """過去回答Excelが存在すること。"""
        past = list((kb_dir / "past_answers").glob("*.xlsx"))
        assert len(past) == 2

    def test_read_docx_content(self, kb_dir: Path):
        """DOCXファイルの内容を読み取れること。"""
        docx_path = kb_dir / "policies" / "data_protection_policy.docx"
        content = _read_file_content(docx_path)
        assert len(content) > 0
        assert "データ" in content or "data" in content.lower()

    def test_read_xlsx_content(self, kb_dir: Path):
        """Excelファイルの内容を読み取れること。"""
        xlsx_path = kb_dir / "past_answers" / "past_answer_2024.xlsx"
        content = _read_file_content(xlsx_path)
        assert len(content) > 0
        assert "Q001" in content or "実施" in content

    def test_parse_reader_response_valid(self):
        """正常なJSON応答をパースできること。"""
        questions = [Question(no=1, major="テスト", minor="テスト", question="質問1")]
        response = '''[
            {
                "question_no": 1,
                "answer": "対応済みです",
                "status": "対応済",
                "source_references": ["test.pdf / 1章"],
                "confidence": "high",
                "key_excerpt": "テスト抜粋"
            }
        ]'''
        answers = _parse_reader_response(response, questions)
        assert len(answers) == 1
        assert answers[0].answer == "対応済みです"
        assert answers[0].confidence == "high"

    def test_parse_reader_response_invalid(self):
        """不正なJSON応答でも全質問に回答を返すこと。"""
        questions = [
            Question(no=1, major="テスト", minor="テスト", question="質問1"),
            Question(no=2, major="テスト", minor="テスト", question="質問2"),
        ]
        answers = _parse_reader_response("invalid json", questions)
        assert len(answers) == 2
        assert all(a.confidence == Confidence.LOW.value for a in answers)


class TestReaderMock:
    """API をモックした Reader テスト。"""

    @pytest.fixture
    def sample_questions(self):
        return [
            Question(no=1, major="セキュリティ", minor="認証", question="MFA を導入していますか"),
            Question(no=2, major="セキュリティ", minor="暗号化", question="通信の暗号化方式は何ですか"),
        ]

    @pytest.fixture
    def mock_api_response(self):
        """正常な API 応答を返す mock を構築するヘルパー。"""
        def _make(text: str):
            content_block = MagicMock()
            content_block.text = text
            response = MagicMock()
            response.content = [content_block]
            return response
        return _make

    @patch("src.reader.anthropic.Anthropic")
    def test_run_reader_normal(self, mock_cls, sample_questions, mock_api_response, kb_dir):
        """正常な API 応答で回答が生成されること。"""
        response_json = json.dumps([
            {
                "question_no": 1,
                "answer": "はい、全社的に MFA を導入済みです",
                "status": "対応済",
                "source_references": ["security_policy.pdf / 3章"],
                "confidence": "high",
                "key_excerpt": "全従業員に MFA を義務付け",
            },
            {
                "question_no": 2,
                "answer": "TLS 1.3 を使用しています",
                "status": "対応済",
                "source_references": ["security_policy.pdf / 5章"],
                "confidence": "high",
                "key_excerpt": "TLS 1.3 による暗号化通信",
            },
        ])
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = mock_api_response(response_json)

        answers = run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
        )

        assert len(answers) == 2
        assert answers[0].answer == "はい、全社的に MFA を導入済みです"
        assert answers[0].confidence == "high"
        assert answers[1].question_no == 2
        mock_client.messages.create.assert_called_once()

    @patch("src.reader.anthropic.Anthropic")
    def test_run_reader_api_error(self, mock_cls, sample_questions, kb_dir):
        """API エラー時に例外が伝播すること（Orchestrator がリトライを担当）。"""
        mock_client = mock_cls.return_value
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(Exception, match="API rate limit"):
            run_reader(
                reader_id="test",
                questions=sample_questions,
                files=["policies/security_policy.pdf"],
                kb_base_dir=kb_dir,
                api_key="fake-key",
            )

    @patch("src.reader.anthropic.Anthropic")
    def test_run_reader_invalid_json(self, mock_cls, sample_questions, mock_api_response, kb_dir):
        """API が不正 JSON を返した場合、全質問に LOW confidence の回答を返すこと。"""
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = mock_api_response("これはJSONではありません")

        answers = run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
        )

        assert len(answers) == 2
        assert all(a.confidence == Confidence.LOW.value for a in answers)
        assert all(a.flag == "LLM応答のパースに失敗" for a in answers)
