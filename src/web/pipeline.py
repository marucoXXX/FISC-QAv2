"""Pipeline execution for Web UI — runs orchestrator in background thread."""

from __future__ import annotations

import io
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from ..config import Config

_semaphore = threading.Semaphore(1)
_jobs: Dict[str, "JobState"] = {}


@dataclass
class JobState:
    job_id: str
    status: str = "queued"  # queued | running | done | error
    progress: List[str] = field(default_factory=list)
    result_run_id: Optional[int] = None
    error: Optional[str] = None


class _ProgressCapture(io.TextIOBase):
    """Captures stderr writes from orchestrator's _log() and stores them in job state."""

    def __init__(self, job: JobState) -> None:
        self._job = job

    def write(self, s: str) -> int:
        text = s.strip()
        if text:
            self._job.progress.append(text)
        return len(s)

    def flush(self) -> None:
        pass


def start_pipeline_job(
    questionnaire_path: Path,
    kb_dir: Path,
    config: Config,
    db_path: Path,
) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = JobState(job_id=job_id)
    _jobs[job_id] = job

    thread = threading.Thread(
        target=_run_pipeline_thread,
        args=(job, questionnaire_path, kb_dir, config, db_path),
        daemon=True,
    )
    thread.start()
    return job_id


def _run_pipeline_thread(
    job: JobState,
    questionnaire_path: Path,
    kb_dir: Path,
    config: Config,
    db_path: Path,
) -> None:
    acquired = _semaphore.acquire(timeout=0)
    if not acquired:
        job.status = "error"
        job.error = "別のパイプラインが実行中です。完了までお待ちください。"
        return

    try:
        job.status = "running"
        job.progress.append("パイプライン開始...")

        from ..orchestrator import run_pipeline

        capture = _ProgressCapture(job)
        old_stderr = sys.stderr
        sys.stderr = capture  # type: ignore[assignment]
        try:
            output_path = run_pipeline(questionnaire_path, kb_dir, config)
        finally:
            sys.stderr = old_stderr

        job.progress.append(f"Excel出力完了: {output_path}")
        job.progress.append("DB へインポート中...")

        # Import results into review DB
        from ..web.app import _parse_excel
        from ..web import db

        content = output_path.read_bytes()
        questions, answers, notes = _parse_excel(content)
        run_id = db.import_run(
            db_path,
            output_path.name,
            questions,
            answers,
            notes,
            source_file=str(output_path),
        )

        job.result_run_id = run_id
        job.status = "done"
        job.progress.append(f"完了: run_id={run_id}")

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.progress.append(f"エラー: {e}")
    finally:
        _semaphore.release()


def start_session_pipeline_job(
    session_id: int,
    unresolved_questions: list,
    config: Config,
    db_path: Path,
) -> str:
    job_id = uuid.uuid4().hex[:12]
    job = JobState(job_id=job_id)
    _jobs[job_id] = job

    thread = threading.Thread(
        target=_run_session_pipeline_thread,
        args=(job, session_id, unresolved_questions, config, db_path),
        daemon=True,
    )
    thread.start()
    return job_id


def _run_session_pipeline_thread(
    job: JobState,
    session_id: int,
    unresolved_questions: list,
    config: Config,
    db_path: Path,
) -> None:
    acquired = _semaphore.acquire(timeout=0)
    if not acquired:
        job.status = "error"
        job.error = "別のパイプラインが実行中です。完了までお待ちください。"
        return

    try:
        job.status = "running"
        job.progress.append(f"セッション #{session_id}: {len(unresolved_questions)}件の質問を生成中...")

        from ..orchestrator import run_pipeline
        from ..excel_io import read_questionnaire
        from ..web import db as web_db

        session = web_db.get_session(db_path, session_id)
        if not session:
            raise ValueError("Session not found")

        capture = _ProgressCapture(job)
        old_stderr = sys.stderr
        sys.stderr = capture  # type: ignore[assignment]

        try:
            # Use existing pipeline for generation
            kb_dir = Path(config.kb_dir)
            source_path = Path(session.get("source_file_path", ""))

            if source_path.exists() and kb_dir.exists():
                output_path = run_pipeline(source_path, kb_dir, config)

                # Parse results and update session questions
                from ..web.app import _parse_excel
                content = output_path.read_bytes()
                _, answers, _ = _parse_excel(content)

                answer_map = {a["question_no"]: a for a in answers}
                unresolved_nos = {q["question_no"] for q in unresolved_questions}

                for q_no in unresolved_nos:
                    ans = answer_map.get(q_no)
                    if ans and ans.get("answer"):
                        refs = ans.get("source_references", [])
                        web_db.update_session_question(db_path, session_id, q_no,
                            answer_source="generated",
                            answer_text=ans["answer"],
                            source_references=refs,
                            confidence=ans.get("confidence", ""),
                            step_resolved=4,
                        )
            else:
                job.progress.append("ソースファイルまたはKBが見つかりません")
        finally:
            sys.stderr = old_stderr

        web_db.update_session(db_path, session_id, current_step=5)
        job.status = "done"
        job.progress.append("生成完了")

    except Exception as e:
        job.status = "error"
        job.error = str(e)
        job.progress.append(f"エラー: {e}")
    finally:
        _semaphore.release()


def get_job(job_id: str) -> Optional[JobState]:
    return _jobs.get(job_id)


def get_job_progress_sse(job_id: str) -> Iterator[str]:
    """SSE generator that yields progress events until job completes."""
    job = _jobs.get(job_id)
    if not job:
        yield f"event: error\ndata: Job not found\n\n"
        return

    sent = 0
    while True:
        # Send any new progress messages
        while sent < len(job.progress):
            msg = job.progress[sent]
            yield f"event: progress\ndata: {msg}\n\n"
            sent += 1

        if job.status == "done":
            yield f"event: done\ndata: {job.result_run_id}\n\n"
            return
        if job.status == "error":
            yield f"event: error\ndata: {job.error or 'Unknown error'}\n\n"
            return

        time.sleep(0.5)
