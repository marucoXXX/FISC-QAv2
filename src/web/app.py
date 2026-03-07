"""FastAPI application for FISC-QAv2 Review UI."""

import json
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import Config
from . import db
from . import pipeline

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    db_path: Path = db.DEFAULT_DB_PATH,
    config: Optional[Config] = None,
) -> FastAPI:
    config = config or Config()
    db.init_db(db_path)

    app = FastAPI(title="FISC-QAv2 Review UI", version="0.1.0")

    # --- Models ---

    class ReviewRequest(BaseModel):
        status: str  # "approved" | "rejected" | "needs_revision"
        comment: str = ""

    class BulkReviewRequest(BaseModel):
        status: str
        question_nos: Optional[List[int]] = None

    # --- API Routes ---

    @app.post("/api/runs/import")
    async def import_run(file: UploadFile) -> dict:
        if not file.filename:
            raise HTTPException(400, "ファイル名がありません")

        content = await file.read()

        if file.filename.endswith(".xlsx"):
            questions, answers, notes = _parse_excel(content)
        elif file.filename.endswith(".json"):
            questions, answers, notes = _parse_json(content)
        else:
            raise HTTPException(400, "Excel (.xlsx) または JSON (.json) ファイルのみ対応")

        run_id = db.import_run(
            db_path, file.filename, questions, answers, notes, source_file=file.filename,
        )
        return {"run_id": run_id, "message": f"インポート完了: {len(answers)}件の回答"}

    @app.get("/api/runs")
    def list_runs() -> list[dict]:
        return db.list_runs(db_path)

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: int) -> dict:
        run = db.get_run(db_path, run_id)
        if not run:
            raise HTTPException(404, "実行結果が見つかりません")
        return run

    @app.get("/api/runs/{run_id}/stats")
    def get_stats(run_id: int) -> dict:
        run = db.get_run(db_path, run_id)
        if not run:
            raise HTTPException(404)
        return db.get_run_stats(db_path, run_id)

    @app.get("/api/runs/{run_id}/answers")
    def get_answers(
        run_id: int,
        review_status: Optional[str] = Query(None),
    ) -> list[dict]:
        return db.get_answers(db_path, run_id, review_status=review_status)

    @app.get("/api/runs/{run_id}/answers/{question_no}")
    def get_answer(run_id: int, question_no: int) -> dict:
        ans = db.get_answer(db_path, run_id, question_no)
        if not ans:
            raise HTTPException(404, "回答が見つかりません")
        notes = [
            n for n in db.get_review_notes(db_path, run_id)
            if n["question_no"] == question_no
        ]
        ans["review_notes"] = notes
        return ans

    @app.put("/api/runs/{run_id}/answers/{question_no}/review")
    def set_review(run_id: int, question_no: int, req: ReviewRequest) -> dict:
        if req.status not in ("approved", "rejected", "needs_revision", "pending"):
            raise HTTPException(400, "無効なステータス")
        ok = db.set_review(db_path, run_id, question_no, req.status, req.comment)
        if not ok:
            raise HTTPException(404)
        return {"ok": True}

    @app.put("/api/runs/{run_id}/bulk-review")
    def bulk_review(run_id: int, req: BulkReviewRequest) -> dict:
        if req.status not in ("approved", "rejected", "needs_revision", "pending"):
            raise HTTPException(400, "無効なステータス")
        count = db.bulk_set_review(db_path, run_id, req.status, req.question_nos)
        return {"ok": True, "updated": count}

    @app.get("/api/runs/{run_id}/review-notes")
    def get_review_notes(run_id: int) -> list[dict]:
        return db.get_review_notes(db_path, run_id)

    @app.get("/api/runs/{run_id}/export")
    def export_approved(run_id: int) -> StreamingResponse:
        run = db.get_run(db_path, run_id)
        if not run:
            raise HTTPException(404)
        answers = db.get_answers(db_path, run_id, review_status="approved")
        all_answers = db.get_answers(db_path, run_id)

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "FISC回答結果（確定）"
        ws.append(["No.", "大分類", "小分類", "質問内容", "回答", "対応状況",
                    "根拠ソース", "確信度", "レビュー", "備考"])

        approved_nos = {a["question_no"] for a in answers}
        for a in all_answers:
            ws.append([
                a["question_no"],
                a["major"],
                a["minor"],
                a["question"],
                a["answer"] if a["question_no"] in approved_nos else "",
                a["status"] if a["question_no"] in approved_nos else "未承認",
                ", ".join(a["source_references"]),
                a["confidence"],
                a["review_status"],
                a["flag"] or "",
            ])

        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="FISC_approved_{run_id}.xlsx"'},
        )

    @app.delete("/api/runs/{run_id}")
    def delete_run(run_id: int) -> dict:
        with db.get_conn(db_path) as conn:
            conn.execute("DELETE FROM review_notes WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM answers WHERE run_id = ?", (run_id,))
            cur = conn.execute("DELETE FROM runs WHERE id = ?", (run_id,))
            if cur.rowcount == 0:
                raise HTTPException(404)
        return {"ok": True}

    # --- Pipeline API ---

    @app.post("/api/pipeline/start")
    async def start_pipeline(file: UploadFile) -> dict:
        if not file.filename or not file.filename.endswith(".xlsx"):
            raise HTTPException(400, "質問票 Excel (.xlsx) ファイルが必要です")

        content = await file.read()
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        tmp.write(content)
        tmp.close()

        kb_dir = Path(config.kb_dir)
        if not kb_dir.exists():
            raise HTTPException(400, f"KB ディレクトリが見つかりません: {kb_dir}")

        job_id = pipeline.start_pipeline_job(
            questionnaire_path=Path(tmp.name),
            kb_dir=kb_dir,
            config=config,
            db_path=db_path,
        )
        return {"job_id": job_id}

    @app.get("/api/pipeline/{job_id}/progress")
    def pipeline_progress(job_id: str) -> StreamingResponse:
        job = pipeline.get_job(job_id)
        if not job:
            raise HTTPException(404, "ジョブが見つかりません")
        return StreamingResponse(
            pipeline.get_job_progress_sse(job_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/pipeline/{job_id}/status")
    def pipeline_status(job_id: str) -> dict:
        job = pipeline.get_job(job_id)
        if not job:
            raise HTTPException(404, "ジョブが見つかりません")
        return {
            "job_id": job.job_id,
            "status": job.status,
            "progress": job.progress,
            "result_run_id": job.result_run_id,
            "error": job.error,
        }

    # --- Config API ---

    @app.get("/api/config")
    def get_config() -> dict:
        return {
            "kb_dir": config.kb_dir,
            "model": config.model,
            "token_budget": config.token_budget_per_reader,
            "output_dir": config.output_dir,
            "api_key_set": bool(config.api_key),
        }

    class ConfigUpdate(BaseModel):
        kb_dir: Optional[str] = None
        model: Optional[str] = None
        token_budget: Optional[int] = None
        output_dir: Optional[str] = None

    @app.put("/api/config")
    def update_config(req: ConfigUpdate) -> dict:
        if req.kb_dir is not None:
            config.kb_dir = req.kb_dir
        if req.model is not None:
            config.model = req.model
        if req.token_budget is not None:
            config.token_budget_per_reader = req.token_budget
        if req.output_dir is not None:
            config.output_dir = req.output_dir
        return {"ok": True}

    # --- Static files (frontend) ---
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return app


def _parse_excel(content: bytes) -> tuple[list[dict], list[dict], list[dict]]:
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    questions = []
    answers = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            continue
        no = int(row[0])
        questions.append({
            "no": no,
            "major": str(row[1] or ""),
            "minor": str(row[2] or ""),
            "question": str(row[3] or ""),
        })
        answers.append({
            "question_no": no,
            "answer": str(row[4] or ""),
            "status": str(row[5] or ""),
            "source_references": [s.strip() for s in str(row[6] or "").split(",") if s.strip()],
            "confidence": str(row[7] or "low"),
            "key_excerpt": "",
            "flag": str(row[8] or "") or None,
        })

    notes = []
    if "レビュー指摘" in wb.sheetnames:
        ws2 = wb["レビュー指摘"]
        for row in ws2.iter_rows(min_row=2, values_only=True):
            if row[0] is None:
                continue
            notes.append({
                "question_no": int(row[0]),
                "issue_type": str(row[1] or "other"),
                "severity": str(row[2] or "medium"),
                "description": str(row[3] or ""),
                "suggestion": str(row[4] or "") if len(row) > 4 else "",
            })

    wb.close()
    return questions, answers, notes


def _parse_json(content: bytes) -> tuple[list[dict], list[dict], list[dict]]:
    data = json.loads(content.decode("utf-8"))

    questions = data.get("questions", [])
    answers = data.get("answers", [])
    notes = data.get("review_notes", [])

    return questions, answers, notes
