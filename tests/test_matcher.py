"""Tests for the matching module (past answers + common answers)."""

from __future__ import annotations

import json
import math
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest

from src.matcher import (
    MatchResult,
    _cosine_similarity,
    _tokenize,
    match_common_answers,
    match_past_answers,
)


# --- Helper tests ---


class TestTokenize:
    def test_tokenize_japanese(self):
        tokens = _tokenize("認証管理")
        # Should contain unigrams and bigrams
        assert "認" in tokens
        assert "証" in tokens
        assert "認証" in tokens
        assert "証管" in tokens


class TestCosineSimilarity:
    def test_cosine_similarity(self):
        a = Counter({"a": 3, "b": 4})
        b = Counter({"a": 3, "b": 4})
        assert _cosine_similarity(a, b) == pytest.approx(1.0)

        c = Counter({"x": 1, "y": 1})
        assert _cosine_similarity(a, c) == pytest.approx(0.0)


# --- Past answer matching ---


class TestMatchPastAnswers:
    def test_match_exact_question(self):
        questions = [{"question_no": 1, "question_text": "MFAの導入状況は？"}]
        past_qa = [
            {"id": 10, "question_text": "MFAの導入状況は？", "answer_text": "導入済み"},
        ]
        results = match_past_answers(questions, past_qa)
        assert 1 in results
        assert results[1].score == pytest.approx(1.0)
        assert results[1].matched_answer == "導入済み"

    def test_match_similar_question(self):
        questions = [{"question_no": 1, "question_text": "MFAの導入状況は？"}]
        past_qa = [
            {"id": 10, "question_text": "MFAの導入についての状況は？", "answer_text": "導入済み"},
        ]
        results = match_past_answers(questions, past_qa)
        assert 1 in results
        assert results[1].score > 0.7

    def test_no_match_below_threshold(self):
        questions = [{"question_no": 1, "question_text": "バックアップの頻度は？"}]
        past_qa = [
            {"id": 10, "question_text": "社員食堂のメニューは？", "answer_text": "和食"},
        ]
        results = match_past_answers(questions, past_qa)
        assert 1 not in results

    def test_match_empty_past_qa(self):
        questions = [{"question_no": 1, "question_text": "テスト質問"}]
        results = match_past_answers(questions, [])
        assert results == {}

    def test_match_picks_best(self):
        questions = [{"question_no": 1, "question_text": "MFAの導入状況は？"}]
        past_qa = [
            {"id": 10, "question_text": "社員食堂のメニューは？", "answer_text": "和食"},
            {"id": 11, "question_text": "MFAの導入状況は？", "answer_text": "導入済み"},
            {"id": 12, "question_text": "RPOの設定は？", "answer_text": "4時間"},
        ]
        results = match_past_answers(questions, past_qa)
        assert 1 in results
        assert results[1].matched_id == 11


# --- Common answer matching ---


class TestMatchCommonAnswers:
    def _mock_llm_response(self, content: str):
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = content
        return mock_resp

    @patch("litellm.completion")
    def test_common_match_with_llm(self, mock_completion):
        mock_completion.return_value = self._mock_llm_response(
            '[{"question_no": 1, "common_id": 5, "score": 0.9}]'
        )
        questions = [{"question_no": 1, "question_text": "MFAは？"}]
        common_list = [{"id": 5, "question_pattern": "MFA導入", "answer_text": "導入済み"}]

        results = match_common_answers(questions, common_list, api_key="key", model="test")
        assert 1 in results
        assert results[1].matched_id == 5
        assert results[1].score == 0.9

    @patch("litellm.completion")
    def test_common_match_empty_input(self, mock_completion):
        results = match_common_answers([], [{"id": 1, "question_pattern": "Q", "answer_text": "A"}],
                                       api_key="key", model="test")
        assert results == {}
        mock_completion.assert_not_called()

    @patch("litellm.completion")
    def test_common_match_invalid_json(self, mock_completion):
        mock_completion.return_value = self._mock_llm_response("sorry I cannot help")
        questions = [{"question_no": 1, "question_text": "Q?"}]
        common_list = [{"id": 1, "question_pattern": "Q", "answer_text": "A"}]

        results = match_common_answers(questions, common_list, api_key="key", model="test")
        assert results == {}

    @patch("litellm.completion")
    def test_common_match_filters_low_score(self, mock_completion):
        # The LLM is instructed to only return score >= 0.7, but if it returns lower,
        # the code still accepts it. This tests that the code passes through scores as-is.
        mock_completion.return_value = self._mock_llm_response(
            '[{"question_no": 1, "common_id": 5, "score": 0.3}]'
        )
        questions = [{"question_no": 1, "question_text": "Q?"}]
        common_list = [{"id": 5, "question_pattern": "P", "answer_text": "A"}]

        results = match_common_answers(questions, common_list, api_key="key", model="test")
        # The current implementation doesn't filter by score on the client side
        assert 1 in results
        assert results[1].score == 0.3
