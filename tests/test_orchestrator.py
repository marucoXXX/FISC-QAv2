"""Agent 0: Orchestrator テスト（並列実行 + CLI）"""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.config import Config
from src.models import Answer, Confidence, Question, ReaderAssignment
from src.orchestrator import _run_readers_parallel, _run_single_reader


class TestReaderParallel:
    """Reader の並列実行を検証する。"""

    @staticmethod
    def _fake_run_reader(reader_id, questions, files, kb_base_dir, api_key, model):
        """0.3秒スリープ後に回答を返すスタブ。"""
        time.sleep(0.3)
        return [
            Answer(
                question_no=q.no,
                answer=f"Reader {reader_id} の回答",
                status="対応済",
                confidence=Confidence.HIGH.value,
            )
            for q in questions
        ]

    def test_parallel_faster_than_sequential(self):
        """並列実行が逐次実行より速いことを検証。"""
        questions = [
            Question(no=i, major="テスト", minor="テスト", question=f"Q{i}")
            for i in range(1, 7)
        ]
        readers = [
            ReaderAssignment(reader_id="A", questions=[1, 2, 3], files=["a.pdf"],
                             estimated_tokens=1000),
            ReaderAssignment(reader_id="B", questions=[4, 5, 6], files=["b.pdf"],
                             estimated_tokens=1000),
        ]
        config = Config(max_reader_retries=1, api_key="dummy")

        with patch("src.orchestrator.run_reader", side_effect=self._fake_run_reader):
            start = time.monotonic()
            results = _run_readers_parallel(readers, questions, Path("/tmp"), config)
            elapsed = time.monotonic() - start

        assert len(results) == 6
        # 並列なら ~0.3秒、逐次なら ~0.6秒。0.5秒未満であること
        assert elapsed < 0.5, f"並列実行が遅い: {elapsed:.2f}秒"

    def test_all_questions_get_answers(self):
        """全質問に回答が返ること。"""
        questions = [
            Question(no=i, major="テスト", minor="テスト", question=f"Q{i}")
            for i in range(1, 5)
        ]
        readers = [
            ReaderAssignment(reader_id="A", questions=[1, 2], files=["a.pdf"],
                             estimated_tokens=1000),
            ReaderAssignment(reader_id="B", questions=[3, 4], files=["b.pdf"],
                             estimated_tokens=1000),
        ]
        config = Config(max_reader_retries=1, api_key="dummy")

        with patch("src.orchestrator.run_reader", side_effect=self._fake_run_reader):
            results = _run_readers_parallel(readers, questions, Path("/tmp"), config)

        answered_nos = {a.question_no for a in results}
        assert answered_nos == {1, 2, 3, 4}

    def test_single_reader_retry_on_failure(self):
        """リトライで復旧するケースを検証。"""
        call_count = 0

        def flaky_reader(reader_id, questions, files, kb_base_dir, api_key, model):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("API error")
            return [
                Answer(question_no=q.no, answer="OK", status="対応済",
                       confidence=Confidence.HIGH.value)
                for q in questions
            ]

        questions = [Question(no=1, major="テスト", minor="テスト", question="Q1")]
        assignment = ReaderAssignment(
            reader_id="A", questions=[1], files=["a.pdf"], estimated_tokens=1000,
        )
        config = Config(max_reader_retries=3, api_key="dummy")

        with patch("src.orchestrator.run_reader", side_effect=flaky_reader):
            results = _run_single_reader(assignment, questions, Path("/tmp"), config)

        assert len(results) == 1
        assert results[0].answer == "OK"
        assert call_count == 3

    def test_single_reader_all_retries_fail(self):
        """全リトライ失敗時に未回答が返ること。"""

        def always_fail(reader_id, questions, files, kb_base_dir, api_key, model):
            raise RuntimeError("permanent failure")

        questions = [Question(no=1, major="テスト", minor="テスト", question="Q1")]
        assignment = ReaderAssignment(
            reader_id="A", questions=[1], files=["a.pdf"], estimated_tokens=1000,
        )
        config = Config(max_reader_retries=2, api_key="dummy")

        with patch("src.orchestrator.run_reader", side_effect=always_fail):
            results = _run_single_reader(assignment, questions, Path("/tmp"), config)

        assert len(results) == 1
        assert results[0].status == "未回答"
        assert results[0].confidence == Confidence.LOW.value
