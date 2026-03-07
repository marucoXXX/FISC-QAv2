"""Agent 1: Indexer 単体テスト"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.indexer import (
    _extract_summary_docx,
    _extract_summary_text,
    _llm_summarize,
    index_to_dicts,
    run_indexer,
)


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


class TestDocxHeadingExtraction:
    """DOCX の見出し優先抽出を検証する。"""

    def test_headings_appear_first_in_summary(self, kb_dir: Path):
        """DOCX の要約が見出しを優先して含むこと。"""
        docx_path = kb_dir / "policies" / "data_protection_policy.docx"
        summary, tokens = _extract_summary_docx(docx_path)
        assert tokens > 0
        # 見出しテキストが要約の先頭付近に現れること
        assert "データ分類" in summary or "保持期間" in summary or "廃棄方法" in summary

    def test_docx_summary_not_empty(self, kb_dir: Path):
        """すべてのDOCXファイルが空でない要約を持つこと。"""
        for docx in kb_dir.rglob("*.docx"):
            summary, tokens = _extract_summary_docx(docx)
            assert summary, f"{docx.name} の要約が空"
            assert tokens > 0


class TestTextExtraction:
    """テキストファイル要約の行数制限を検証する。"""

    def test_text_summary_limited(self, tmp_path: Path):
        """テキスト要約が max_lines で制限されること。"""
        long_text = "\n".join(f"Line {i}" for i in range(200))
        txt_file = tmp_path / "test.txt"
        txt_file.write_text(long_text, encoding="utf-8")
        summary, tokens = _extract_summary_text(txt_file, max_lines=5)
        assert summary.count("\n") <= 4  # 5行なので改行は最大4つ
        assert tokens > 0  # 全文からトークン推定


class TestLlmSummary:
    """LLM 要約オプションの検証（mock）。"""

    def test_llm_summarize_called(self):
        """LLM 要約が正しくAPIを呼び出すこと。"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="LLMによる要約テキスト")]
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.messages.create.return_value = mock_response
            result = _llm_summarize("テスト本文", "test.pdf", "fake-key", "claude-sonnet-4-20250514")
        assert result == "LLMによる要約テキスト"
        mock_client.messages.create.assert_called_once()

    def test_run_indexer_with_llm_summary(self, kb_dir: Path):
        """use_llm_summary=True でLLM要約が適用されること。"""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="LLM生成サマリ")]
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.messages.create.return_value = mock_response
            result = run_indexer(kb_dir, api_key="fake-key", use_llm_summary=True)
        # 全ファイルの要約がLLM生成に置き換わっていること
        for entry in result:
            assert entry.summary == "LLM生成サマリ"
        assert mock_client.messages.create.call_count == 12

    def test_run_indexer_llm_failure_fallback(self, kb_dir: Path):
        """LLM呼び出し失敗時にローカル要約にフォールバックすること。"""
        with patch("anthropic.Anthropic") as mock_cls:
            mock_client = mock_cls.return_value
            mock_client.messages.create.side_effect = Exception("API error")
            result = run_indexer(kb_dir, api_key="fake-key", use_llm_summary=True)
        # フォールバック: 全ファイルがローカル要約を持つこと
        for entry in result:
            assert entry.summary  # 空でないこと
            assert entry.summary != "LLM生成サマリ"
