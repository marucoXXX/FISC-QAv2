"""Agent 3: Reader 単体テスト"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models import Answer, Confidence, Question
from src.reader import (
    _extract_json_array,
    _find_matching_bracket,
    _is_openai_model,
    _parse_reader_response,
    _read_file_content,
    _try_parse_truncated,
    run_reader,
)


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
        assert len(docx_files) == 6
        for docx in docx_files:
            assert docx.stat().st_size > 0, f"{docx.name} is empty"

    def test_past_answers_dir_present(self, kb_dir: Path):
        """過去回答ディレクトリに過去回答ファイルが存在すること。"""
        past_dir = kb_dir / "past_answers"
        xlsx_files = list(past_dir.glob("*.xlsx"))
        assert len(xlsx_files) == 2

    def test_read_docx_content(self, kb_dir: Path):
        """DOCXファイルの内容を読み取れること。"""
        docx_path = kb_dir / "policies" / "data_protection_policy.docx"
        content = _read_file_content(docx_path)
        assert len(content) > 0
        assert "データ" in content or "data" in content.lower()

    def test_read_xlsx_content(self, kb_dir: Path):
        """Excelファイルの内容を読み取れること。"""
        xlsx_path = kb_dir / "operations" / "change_management_log.xlsx"
        content = _read_file_content(xlsx_path)
        assert len(content) > 0

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
    def mock_llm_response(self):
        """正常な LLM 応答を返す mock を構築するヘルパー。"""
        def _make(text: str, finish_reason: str = "stop"):
            mock_choice = MagicMock()
            mock_choice.message.content = text
            mock_choice.finish_reason = finish_reason
            response = MagicMock()
            response.choices = [mock_choice]
            return response
        return _make

    @patch("src.reader.litellm.completion")
    def test_run_reader_normal(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
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
        mock_completion.return_value = mock_llm_response(response_json)

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
        mock_completion.assert_called_once()

    @patch("src.reader.litellm.completion")
    def test_run_reader_api_error(self, mock_completion, sample_questions, kb_dir):
        """API エラー時に例外が伝播すること（Orchestrator がリトライを担当）。"""
        mock_completion.side_effect = Exception("API rate limit exceeded")

        with pytest.raises(Exception, match="API rate limit"):
            run_reader(
                reader_id="test",
                questions=sample_questions,
                files=["policies/security_policy.pdf"],
                kb_base_dir=kb_dir,
                api_key="fake-key",
            )

    @patch("src.reader.litellm.completion")
    def test_run_reader_invalid_json(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
        """API が不正 JSON を返した場合、全質問に LOW confidence の回答を返すこと。"""
        mock_completion.return_value = mock_llm_response("これはJSONではありません")

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

    @patch("src.reader.litellm.completion")
    def test_run_reader_truncated_recoverable(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
        """finish_reason=length で切断されたが部分復旧できる場合。"""
        # Q1のみ含む切断されたJSON（閉じ括弧なし）
        truncated = '[{"question_no": 1, "answer": "MFA導入済み", "status": "対応済", "confidence": "high"'
        mock_completion.return_value = mock_llm_response(truncated, finish_reason="length")

        answers = run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
        )

        assert len(answers) == 2
        # Q1は復旧されている
        q1 = [a for a in answers if a.question_no == 1][0]
        assert q1.answer == "MFA導入済み"
        # Q2は切断フラグ付き
        q2 = [a for a in answers if a.question_no == 2][0]
        assert q2.flag == "LLM応答がトークン上限で切断"

    @patch("src.reader.litellm.completion")
    def test_run_reader_truncated_unrecoverable(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
        """finish_reason=length で復旧不能な場合、全質問に切断フラグを付与する。"""
        mock_completion.return_value = mock_llm_response("これは完全に壊れた", finish_reason="length")

        answers = run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
        )

        assert len(answers) == 2
        assert all(a.flag == "LLM応答がトークン上限で切断" for a in answers)
        assert all(a.confidence == Confidence.LOW.value for a in answers)

    @patch("src.reader.litellm.completion")
    def test_run_reader_openai_response_format(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
        """OpenAIモデル使用時にresponse_formatが付加されること。"""
        response_json = json.dumps([
            {"question_no": 1, "answer": "回答1", "status": "対応済", "confidence": "high"},
            {"question_no": 2, "answer": "回答2", "status": "対応済", "confidence": "high"},
        ])
        mock_completion.return_value = mock_llm_response(response_json)

        run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
            model="gpt-4o",
        )

        call_kwargs = mock_completion.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["max_tokens"] == 16384

    @patch("src.reader.litellm.completion")
    def test_run_reader_anthropic_no_response_format(self, mock_completion, sample_questions, mock_llm_response, kb_dir):
        """Anthropicモデル使用時にresponse_formatが付加されないこと。"""
        response_json = json.dumps([
            {"question_no": 1, "answer": "回答1", "status": "対応済", "confidence": "high"},
            {"question_no": 2, "answer": "回答2", "status": "対応済", "confidence": "high"},
        ])
        mock_completion.return_value = mock_llm_response(response_json)

        run_reader(
            reader_id="test",
            questions=sample_questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
            model="claude-sonnet-4-20250514",
        )

        call_kwargs = mock_completion.call_args[1]
        assert "response_format" not in call_kwargs


class TestOpenAIModelDetection:
    """_is_openai_model のテスト。"""

    def test_gpt_models(self):
        assert _is_openai_model("gpt-4o") is True
        assert _is_openai_model("gpt-4o-mini") is True
        assert _is_openai_model("gpt-3.5-turbo") is True

    def test_openai_prefixed(self):
        assert _is_openai_model("openai/gpt-4o") is True

    def test_o1_o3_models(self):
        assert _is_openai_model("o1-preview") is True
        assert _is_openai_model("o3-mini") is True

    def test_anthropic_models(self):
        assert _is_openai_model("claude-sonnet-4-20250514") is False
        assert _is_openai_model("claude-3-haiku-20240307") is False

    def test_other_models(self):
        assert _is_openai_model("gemini-pro") is False


class TestTryParseTruncated:
    """切断JSON復旧のテスト。"""

    @pytest.fixture
    def questions(self):
        return [
            Question(no=1, major="テスト", minor="テスト", question="Q1"),
            Question(no=2, major="テスト", minor="テスト", question="Q2"),
        ]

    def test_recover_missing_closing_bracket(self, questions):
        """閉じ括弧が欠けたJSON配列を復旧できること。"""
        truncated = json.dumps([
            {"question_no": 1, "answer": "回答1", "status": "対応済", "confidence": "high"}
        ])[:-1]  # remove ]
        result = _try_parse_truncated(truncated, questions)
        assert result is not None
        assert len(result) == 2
        assert result[0].answer == "回答1"

    def test_completely_broken_returns_none(self, questions):
        """完全に壊れたテキストではNoneを返すこと。"""
        result = _try_parse_truncated("これは壊れた応答", questions)
        assert result is None


class TestFindMatchingBracket:
    """_find_matching_bracket のテスト。"""

    def test_simple_array(self):
        start, end = _find_matching_bracket('[1, 2, 3]', '[', ']')
        assert start == 0
        assert end == 9

    def test_nested_arrays(self):
        text = '{"answers": [{"q": 1}], "tags": ["a"]}'
        start, end = _find_matching_bracket(text, '[', ']')
        # Should match [{"q": 1}], not extend to ["a"]
        assert text[start:end] == '[{"q": 1}]'

    def test_nested_objects(self):
        text = '{"a": {"b": 1}, "c": 2}'
        start, end = _find_matching_bracket(text, '{', '}')
        assert text[start:end] == text

    def test_strings_with_brackets(self):
        text = '{"key": "value with ] bracket", "arr": [1]}'
        start, end = _find_matching_bracket(text, '[', ']')
        assert text[start:end] == '[1]'

    def test_no_match(self):
        start, end = _find_matching_bracket('no brackets here', '[', ']')
        assert start == -1
        assert end == -1

    def test_unclosed_bracket(self):
        start, end = _find_matching_bracket('[1, 2, 3', '[', ']')
        assert start == -1
        assert end == -1


class TestExtractJsonArray:
    """_extract_json_array のテスト。"""

    def test_object_wrapped_response(self):
        """OpenAI response_format で返る object ラップを正しく抽出。"""
        text = '{"answers": [{"question_no": 1}], "tags": ["security"]}'
        result = _extract_json_array(text)
        # Should extract full object since no top-level array
        # Actually, it should find [ first - the answers array
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["question_no"] == 1

    def test_plain_array(self):
        """プレーンなJSON配列をそのまま抽出。"""
        text = '[{"question_no": 1, "answer": "test"}]'
        result = _extract_json_array(text)
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    def test_code_block_array(self):
        """コードブロック内のJSON配列を抽出。"""
        text = '```json\n[{"question_no": 1}]\n```'
        result = _extract_json_array(text)
        parsed = json.loads(result)
        assert isinstance(parsed, list)


class TestParseReaderResponseOpenAI:
    """OpenAI形式レスポンスのパーステスト。"""

    @pytest.fixture
    def questions(self):
        return [
            Question(no=1, major="テスト", minor="テスト", question="Q1"),
            Question(no=2, major="テスト", minor="テスト", question="Q2"),
        ]

    def test_object_wrapped_answers(self, questions):
        """OpenAI response_format で返る {"answers": [...]} 形式のパース。"""
        text = json.dumps({
            "answers": [
                {"question_no": 1, "answer": "回答1", "status": "対応済", "confidence": "high"},
                {"question_no": 2, "answer": "回答2", "status": "対応済", "confidence": "medium"},
            ]
        })
        answers = _parse_reader_response(text, questions)
        assert len(answers) == 2
        assert answers[0].answer == "回答1"
        assert answers[1].confidence == "medium"

    def test_object_with_multiple_arrays(self, questions):
        """複数配列を含むobjectレスポンスのパース。"""
        text = json.dumps({
            "answers": [
                {"question_no": 1, "answer": "回答1", "status": "対応済", "confidence": "high"},
                {"question_no": 2, "answer": "回答2", "status": "対応済", "confidence": "high"},
            ],
            "metadata": {"total": 2},
            "tags": ["security", "compliance"],
        })
        answers = _parse_reader_response(text, questions)
        assert len(answers) == 2
        assert answers[0].answer == "回答1"

    def test_none_input(self, questions):
        """None入力でエラーにならずフラグ付き回答を返す。"""
        answers = _parse_reader_response(None, questions)
        assert len(answers) == 2
        assert all(a.flag == "LLM応答のパースに失敗" for a in answers)

    def test_empty_string_input(self, questions):
        """空文字入力でエラーにならずフラグ付き回答を返す。"""
        answers = _parse_reader_response("", questions)
        assert len(answers) == 2
        assert all(a.flag == "LLM応答のパースに失敗" for a in answers)

    def test_whitespace_only_input(self, questions):
        """空白のみ入力でエラーにならずフラグ付き回答を返す。"""
        answers = _parse_reader_response("   \n  ", questions)
        assert len(answers) == 2
        assert all(a.flag == "LLM応答のパースに失敗" for a in answers)


class TestRunReaderNoneContent:
    """run_reader で content が None の場合のテスト。"""

    @pytest.fixture
    def questions(self):
        return [
            Question(no=1, major="テスト", minor="テスト", question="Q1"),
        ]

    @patch("src.reader.litellm.completion")
    def test_none_content_returns_empty_flag(self, mock_completion, questions, kb_dir):
        """content が None の場合、LLM応答が空フラグを返す。"""
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_choice.finish_reason = "stop"
        response = MagicMock()
        response.choices = [mock_choice]
        mock_completion.return_value = response

        answers = run_reader(
            reader_id="test",
            questions=questions,
            files=["policies/security_policy.pdf"],
            kb_base_dir=kb_dir,
            api_key="fake-key",
        )

        assert len(answers) == 1
        assert answers[0].flag == "LLM応答が空"
        assert answers[0].confidence == Confidence.LOW.value
