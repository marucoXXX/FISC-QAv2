"""Agent 2: Router 単体テスト"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.excel_io import read_questionnaire
from src.indexer import run_indexer
from src.router import (
    _build_llm_routing_prompt,
    _parse_llm_routing_response,
    routing_to_dict,
    run_router,
)


class TestRouter:
    """Router が質問をカテゴリに基づき適切なソースに割り当てることを検証する。"""

    def test_routing_map_structure(self, expected_routing_map: dict):
        """ルーティングマップが正しい構造を持つこと。"""
        assert len(expected_routing_map) == 30
        for qno, mapping in expected_routing_map.items():
            assert "major" in mapping
            assert "minor" in mapping
            assert "assigned_sources" in mapping
            assert len(mapping["assigned_sources"]) > 0

    def test_all_major_categories_covered(self, expected_routing_map: dict):
        """全大分類がルーティングに含まれること。"""
        majors = {m["major"] for m in expected_routing_map.values()}
        expected = {
            "セキュリティ管理", "アクセス管理", "ウイルス対策", "ネットワーク管理",
            "バックアップ管理", "インシデント対応", "変更管理", "物理セキュリティ", "教育・訓練",
            "外部委託管理", "システム開発", "ログ・監視",
        }
        assert majors == expected

    def test_sources_are_valid_paths(self, expected_routing_map: dict):
        """割り当てソースが妥当なパスであること。"""
        valid_prefixes = ("policies/", "past_answers/", "system_docs/", "operations/", "regulations/")
        for mapping in expected_routing_map.values():
            for src in mapping["assigned_sources"]:
                assert any(src.startswith(p) for p in valid_prefixes), f"Invalid source: {src}"

    def test_router_run(self, questionnaire_path: Path, kb_dir: Path):
        """Router を実行してルーティングマップを生成する。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)
        result = run_router(questions, index)
        result_dict = routing_to_dict(result)

        # All questions should be assigned
        all_assigned = set()
        for reader in result_dict["readers"]:
            all_assigned.update(reader["questions"])
            assert len(reader["files"]) > 0
            assert reader["estimated_tokens"] > 0
        assert all_assigned == {q.no for q in questions}

    def test_router_respects_token_budget(self, questionnaire_path: Path, kb_dir: Path):
        """小さいトークン予算で複数Readerに分割されること。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)
        budget = 5000
        result = run_router(questions, index, token_budget_per_reader=budget)
        # 小さい予算なので複数Readerに分割されるはず
        assert len(result.readers) > 1


class TestLlmRouter:
    """LLM ベース動的ルーティングの検証（mock）。"""

    def test_build_llm_routing_prompt(self, questionnaire_path: Path, kb_dir: Path):
        """LLM ルーティングプロンプトが正しく構築されること。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)
        prompt = _build_llm_routing_prompt(questions, index)
        assert "KBファイル一覧" in prompt
        assert "質問リスト" in prompt
        assert "Q1" in prompt
        assert "security_policy.pdf" in prompt

    def test_parse_llm_routing_response(self, kb_dir: Path):
        """LLM レスポンスの JSON を正しくパースすること。"""
        from src.models import Question
        questions = [
            Question(no=1, major="セキュリティ管理", minor="ポリシー管理", question="テスト"),
            Question(no=2, major="アクセス管理", minor="権限管理", question="テスト"),
        ]
        index = run_indexer(kb_dir)
        response_text = json.dumps({
            "routing": [
                {"question_no": 1, "files": ["security_policy.pdf", "access_control_policy.pdf"]},
                {"question_no": 2, "files": ["access_control_policy.pdf"]},
            ]
        })
        result = _parse_llm_routing_response(response_text, questions, index)
        assert result[1] == ["security_policy.pdf", "access_control_policy.pdf"]
        assert result[2] == ["access_control_policy.pdf"]

    def test_parse_llm_routing_response_markdown(self, kb_dir: Path):
        """マークダウンコードブロックで囲まれた JSON もパースできること。"""
        from src.models import Question
        questions = [Question(no=1, major="テスト", minor="テスト", question="テスト")]
        index = run_indexer(kb_dir)
        response_text = '```json\n{"routing": [{"question_no": 1, "files": ["security_policy.pdf"]}]}\n```'
        result = _parse_llm_routing_response(response_text, questions, index)
        assert result[1] == ["security_policy.pdf"]

    def test_parse_llm_routing_filters_invalid_files(self, kb_dir: Path):
        """存在しないファイル名が除外されること。"""
        from src.models import Question
        questions = [Question(no=1, major="テスト", minor="テスト", question="テスト")]
        index = run_indexer(kb_dir)
        response_text = json.dumps({
            "routing": [
                {"question_no": 1, "files": ["security_policy.pdf", "nonexistent.pdf"]},
            ]
        })
        result = _parse_llm_routing_response(response_text, questions, index)
        assert result[1] == ["security_policy.pdf"]

    def test_run_router_with_llm(self, questionnaire_path: Path, kb_dir: Path):
        """LLM ルーティングが正しく動作すること（mock）。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)

        # 全質問に security_policy.pdf を割り当てるLLMレスポンス
        routing_data = {
            "routing": [
                {"question_no": q.no, "files": ["security_policy.pdf"]}
                for q in questions
            ]
        }
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps(routing_data)
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        with patch("litellm.completion") as mock_completion:
            mock_completion.return_value = mock_response
            result = run_router(questions, index, api_key="fake-key")

        result_dict = routing_to_dict(result)
        all_assigned = set()
        for reader in result_dict["readers"]:
            all_assigned.update(reader["questions"])
        assert all_assigned == {q.no for q in questions}
        mock_completion.assert_called_once()

    def test_run_router_llm_failure_fallback(self, questionnaire_path: Path, kb_dir: Path):
        """LLM 失敗時に静的ルーティングにフォールバックすること。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)

        with patch("litellm.completion") as mock_completion:
            mock_completion.side_effect = Exception("API error")
            result = run_router(questions, index, api_key="fake-key")

        # フォールバック: 全質問が割り当てられていること
        result_dict = routing_to_dict(result)
        all_assigned = set()
        for reader in result_dict["readers"]:
            all_assigned.update(reader["questions"])
        assert all_assigned == {q.no for q in questions}

    def test_run_router_no_api_key_uses_static(self, questionnaire_path: Path, kb_dir: Path):
        """api_key なしの場合は静的ルーティングが使われること。"""
        questions = read_questionnaire(questionnaire_path)
        index = run_indexer(kb_dir)

        # api_key なしで呼び出し — LLM は呼ばれないはず
        with patch("litellm.completion") as mock_completion:
            result = run_router(questions, index)
            mock_completion.assert_not_called()

        result_dict = routing_to_dict(result)
        all_assigned = set()
        for reader in result_dict["readers"]:
            all_assigned.update(reader["questions"])
        assert all_assigned == {q.no for q in questions}
