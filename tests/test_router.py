"""Agent 2: Router 単体テスト"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_io import read_questionnaire
from src.indexer import run_indexer
from src.router import routing_to_dict, run_router


class TestRouter:
    """Router が質問をカテゴリに基づき適切なソースに割り当てることを検証する。"""

    def test_routing_map_structure(self, expected_routing_map: dict):
        """ルーティングマップが正しい構造を持つこと。"""
        assert len(expected_routing_map) == 20
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
        }
        assert majors == expected

    def test_sources_are_valid_paths(self, expected_routing_map: dict):
        """割り当てソースが妥当なパスであること。"""
        valid_prefixes = ("policies/", "past_answers/", "system_docs/")
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
        budget = 20000
        result = run_router(questions, index, token_budget_per_reader=budget)
        # 小さい予算なので複数Readerに分割されるはず
        assert len(result.readers) > 1
