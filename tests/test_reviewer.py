"""Agent 4: Reviewer 単体テスト"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.models import Answer, Confidence, Question
from src.reviewer import _rule_based_review, run_reviewer


class TestReviewer:
    """Reviewer が回答を集約し品質判定を行えることを検証する。"""

    def test_final_answers_structure(self, expected_final_answers: dict):
        """最終回答が正しい構造を持つこと。"""
        assert len(expected_final_answers) == 20
        required_keys = {"question", "answer", "status", "evidence", "confidence", "needs_review"}
        for qno, ans in expected_final_answers.items():
            assert required_keys.issubset(ans.keys()), f"Missing keys in Q{qno}"

    def test_needs_review_flag(self, expected_final_answers: dict):
        """未回答状態では needs_review が True であること。"""
        for qno, ans in expected_final_answers.items():
            assert ans["needs_review"] is True, f"Q{qno}: needs_review should be True"

    def test_all_questions_answered(self, expected_final_answers: dict, expected_routing_map: dict):
        """ルーティングされた全質問に回答があること。"""
        assert set(expected_final_answers.keys()) == set(expected_routing_map.keys())

    def test_rule_based_review_low_confidence(self):
        """confidence=low の回答が「回答不可」に格下げされること。"""
        answers = {
            1: Answer(question_no=1, answer="テスト回答", status="要確認",
                      confidence=Confidence.LOW.value),
        }
        result = _rule_based_review(answers)
        assert result[1].status == "回答不可"
        assert result[1].flag == "KB に該当情報なし"

    def test_rule_based_review_empty_answer(self):
        """空回答でhigh confidence の場合、low に格下げされること。"""
        answers = {
            1: Answer(question_no=1, answer="", status="対応済",
                      confidence=Confidence.HIGH.value),
        }
        result = _rule_based_review(answers)
        assert result[1].confidence == Confidence.LOW.value
        assert result[1].status == "回答不可"

    def test_rule_based_review_past_answer_preserved(self):
        """過去回答採用のステータスが維持されること。"""
        answers = {
            1: Answer(question_no=1, answer="過去の回答", status="過去回答採用",
                      confidence=Confidence.LOW.value, flag="過去回答採用"),
        }
        result = _rule_based_review(answers)
        assert result[1].status == "過去回答採用"


class TestReviewerMock:
    """API をモックした Reviewer テスト。"""

    @pytest.fixture
    def sample_qa(self):
        questions = [
            Question(no=1, major="セキュリティ", minor="認証", question="MFA を導入していますか"),
            Question(no=2, major="運用", minor="監視", question="ログ監視の体制は"),
        ]
        answers = {
            1: Answer(question_no=1, answer="MFA導入済み", status="対応済",
                      confidence=Confidence.HIGH.value,
                      source_references=["security_policy.pdf / 3章"]),
            2: Answer(question_no=2, answer="24時間監視", status="対応済",
                      confidence=Confidence.MEDIUM.value,
                      source_references=["operation_manual.pdf / 2章"]),
        }
        return questions, answers

    @patch("src.reviewer.anthropic.Anthropic")
    def test_run_reviewer_normal(self, mock_cls, sample_qa):
        """正常なレビュー応答で判定が適用されること。"""
        questions, answers = sample_qa

        review_json = json.dumps({
            "final_judgments": [
                {"question_no": 1, "confidence_override": "high", "status_override": None, "flag": None},
                {"question_no": 2, "confidence_override": "high", "status_override": "対応済", "flag": None},
            ],
            "review_notes": [
                {
                    "question_no": 2,
                    "issue_type": "weak_reference",
                    "severity": "low",
                    "description": "根拠がやや弱い",
                    "suggestion": "追加資料を確認",
                },
            ],
        })

        content_block = MagicMock()
        content_block.text = review_json
        response = MagicMock()
        response.content = [content_block]
        mock_cls.return_value.messages.create.return_value = response

        final, notes = run_reviewer(questions, answers, api_key="fake-key")

        assert final[2].confidence == Confidence.HIGH.value
        assert len(notes) == 1
        assert notes[0].issue_type == "weak_reference"

    @patch("src.reviewer.anthropic.Anthropic")
    def test_run_reviewer_parse_failure_fallback(self, mock_cls, sample_qa):
        """API が不正 JSON を返した場合、ルールベースレビューにフォールバックすること。"""
        questions, answers = sample_qa

        content_block = MagicMock()
        content_block.text = "これはJSONではありません"
        response = MagicMock()
        response.content = [content_block]
        mock_cls.return_value.messages.create.return_value = response

        final, notes = run_reviewer(questions, answers, api_key="fake-key")

        # ルールベースレビューが適用され、結果が返ること
        assert 1 in final
        assert 2 in final
        assert len(notes) == 0  # パース失敗時は review_notes は空
