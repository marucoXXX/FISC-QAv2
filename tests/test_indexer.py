"""Agent 1: Indexer 単体テスト"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.indexer import index_to_dicts, run_indexer


class TestIndexer:
    """Indexer がKBファイルを読み取り、インデックスを生成できることを検証する。"""

    def test_kb_files_exist(self, kb_dir: Path):
        """KBディレクトリにファイルが存在すること。"""
        all_files = list(kb_dir.rglob("*"))
        files = [f for f in all_files if f.is_file()]
        assert len(files) == 12, f"KB には12ファイル期待、実際は {len(files)}"

    def test_expected_index_structure(self, expected_index: list[dict]):
        """期待出力のインデックスが正しい構造を持つこと。"""
        assert len(expected_index) > 0
        required_keys = {"file_name", "path", "category", "summary", "estimated_tokens"}
        for entry in expected_index:
            assert required_keys.issubset(entry.keys()), f"Missing keys in {entry}"

    def test_index_covers_all_kb_files(self, expected_index: list[dict], kb_dir: Path):
        """インデックスがすべてのKBファイルをカバーすること。"""
        kb_files = {f.name for f in kb_dir.rglob("*") if f.is_file()}
        indexed_files = {entry["file_name"] for entry in expected_index}
        assert kb_files == indexed_files

    def test_indexer_run(self, kb_dir: Path):
        """Indexer を実行してインデックスを生成する。"""
        result = run_indexer(kb_dir)
        assert len(result) == 12
        dicts = index_to_dicts(result)
        required_keys = {"file_name", "path", "category", "summary", "estimated_tokens"}
        for entry in dicts:
            assert required_keys.issubset(entry.keys())
            assert entry["estimated_tokens"] > 0

    def test_indexer_update_detection(self, kb_dir: Path):
        """前回インデックスと比較して更新検知できること。"""
        first_run = run_indexer(kb_dir)
        prev = index_to_dicts(first_run)
        second_run = run_indexer(kb_dir, previous_index=prev)
        # 同じファイルなので全て未更新
        assert all(not e.updated for e in second_run)
