"""FISC-QAv2 CLI エントリポイント

使用例:
  python -m src qa   --questionnaire input/q.xlsx --kb-dir kb/
  python -m src index --kb-dir kb/
  python -m src route --questionnaire input/q.xlsx --index index.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model", default=None, help="Claude モデル名")
    parser.add_argument("--token-budget", type=int, default=None,
                        help="Reader あたりのトークン上限")


def cmd_qa(args: argparse.Namespace) -> None:
    from .config import Config
    from .orchestrator import run_pipeline

    config = Config()
    if args.model:
        config.model = args.model
    if args.token_budget:
        config.token_budget_per_reader = args.token_budget
    if args.output_dir:
        config.output_dir = args.output_dir

    output = run_pipeline(args.questionnaire, args.kb_dir, config)
    print(f"出力: {output}")


def cmd_index(args: argparse.Namespace) -> None:
    from .indexer import index_to_dicts, load_index, run_indexer, save_index

    kb_dir = Path(args.kb_dir)
    previous = load_index(Path(args.previous)) if args.previous else None
    entries = run_indexer(kb_dir, previous_index=previous)

    output_path = Path(args.output)
    save_index(entries, output_path)

    updated = sum(1 for e in entries if e.updated)
    print(f"インデックス生成完了: {len(entries)}ファイル（更新あり: {updated}）")
    print(f"出力: {output_path}")


def cmd_route(args: argparse.Namespace) -> None:
    from .excel_io import read_questionnaire
    from .indexer import run_indexer
    from .models import IndexEntry
    from .router import routing_to_dict, run_router

    questions = read_questionnaire(Path(args.questionnaire))

    if args.index:
        raw = json.loads(Path(args.index).read_text(encoding="utf-8"))
        index = [IndexEntry(**e) for e in raw]
    else:
        if not args.kb_dir:
            print("--index または --kb-dir のいずれかが必要です", file=sys.stderr)
            sys.exit(1)
        index = run_indexer(Path(args.kb_dir))

    budget = args.token_budget or 80000
    result = run_router(questions, index, token_budget_per_reader=budget)
    output = routing_to_dict(result)

    if args.output:
        Path(args.output).write_text(
            json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"ルーティングマップ出力: {args.output}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_read(args: argparse.Namespace) -> None:
    from .excel_io import read_questionnaire
    from .models import Question
    from .reader import answers_to_dicts, run_reader

    questions = read_questionnaire(Path(args.questionnaire))
    if args.questions:
        nos = {int(n) for n in args.questions.split(",")}
        questions = [q for q in questions if q.no in nos]

    files = args.files.split(",")
    answers = run_reader(
        reader_id=args.reader_id or "CLI",
        questions=questions,
        files=files,
        kb_base_dir=Path(args.kb_dir),
        api_key="",  # Config から取得
        model=args.model or "claude-sonnet-4-20250514",
    )
    print(json.dumps(answers_to_dicts(answers), ensure_ascii=False, indent=2))


def cmd_serve(args: argparse.Namespace) -> None:
    import uvicorn
    from .config import Config
    from .web.app import create_app
    from .web.db import DEFAULT_DB_PATH

    config = Config()
    if args.kb_dir:
        config.kb_dir = args.kb_dir
    if args.model:
        config.model = args.model
    if args.token_budget:
        config.token_budget_per_reader = args.token_budget

    db_path = Path(args.db) if args.db else DEFAULT_DB_PATH
    app = create_app(db_path, config=config)
    print(f"Review UI: http://localhost:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port)


def cmd_review(args: argparse.Namespace) -> None:
    from .excel_io import read_questionnaire
    from .models import Answer
    from .reviewer import run_reviewer

    questions = read_questionnaire(Path(args.questionnaire))
    raw_answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))

    answers: dict[int, Answer] = {}
    for item in raw_answers:
        answers[item["question_no"]] = Answer(
            question_no=item["question_no"],
            answer=item.get("answer", ""),
            status=item.get("status", ""),
            source_references=item.get("source_references", []),
            confidence=item.get("confidence", "medium"),
            key_excerpt=item.get("key_excerpt", ""),
        )

    final, notes = run_reviewer(
        questions=questions,
        answers=answers,
        api_key="",
        model=args.model or "claude-sonnet-4-20250514",
    )
    result = {
        "final_answers": {
            str(k): {"answer": v.answer, "status": v.status, "confidence": v.confidence}
            for k, v in final.items()
        },
        "review_notes": [
            {"question_no": n.question_no, "issue_type": n.issue_type,
             "severity": n.severity, "description": n.description}
            for n in notes
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="fisc-qav2",
        description="FISC アンケート自動回答マルチエージェントシステム v2",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- qa ---
    p_qa = sub.add_parser("qa", help="全パイプライン実行 (/fisc-qa)")
    p_qa.add_argument("--questionnaire", required=True, help="質問票 Excel パス")
    p_qa.add_argument("--kb-dir", required=True, help="KB ディレクトリパス")
    p_qa.add_argument("--output-dir", default="output", help="出力ディレクトリ")
    _add_common_args(p_qa)

    # --- index ---
    p_idx = sub.add_parser("index", help="インデックス生成 (/fisc-index)")
    p_idx.add_argument("--kb-dir", required=True, help="KB ディレクトリパス")
    p_idx.add_argument("--previous", default=None, help="前回インデックス JSON パス")
    p_idx.add_argument("--output", default="index.json", help="出力先 JSON パス")

    # --- route ---
    p_rt = sub.add_parser("route", help="ルーティングマップ生成 (/fisc-route)")
    p_rt.add_argument("--questionnaire", required=True, help="質問票 Excel パス")
    p_rt.add_argument("--index", default=None, help="インデックス JSON パス")
    p_rt.add_argument("--kb-dir", default=None, help="KB ディレクトリパス（--index 省略時）")
    p_rt.add_argument("--output", default=None, help="出力先 JSON パス（省略時は stdout）")
    _add_common_args(p_rt)

    # --- read ---
    p_rd = sub.add_parser("read", help="Reader 回答生成 (/fisc-read)")
    p_rd.add_argument("--questionnaire", required=True, help="質問票 Excel パス")
    p_rd.add_argument("--kb-dir", required=True, help="KB ディレクトリパス")
    p_rd.add_argument("--files", required=True, help="読み込みファイル（カンマ区切り）")
    p_rd.add_argument("--questions", default=None, help="対象質問No（カンマ区切り、省略時は全問）")
    p_rd.add_argument("--reader-id", default=None, help="Reader ID")
    _add_common_args(p_rd)

    # --- review ---
    p_rv = sub.add_parser("review", help="レビュー実行 (/fisc-review)")
    p_rv.add_argument("--questionnaire", required=True, help="質問票 Excel パス")
    p_rv.add_argument("--answers", required=True, help="回答 JSON パス")
    _add_common_args(p_rv)

    # --- serve ---
    p_sv = sub.add_parser("serve", help="レビュー Web UI 起動")
    p_sv.add_argument("--host", default="127.0.0.1", help="バインドホスト")
    p_sv.add_argument("--port", type=int, default=8000, help="ポート番号")
    p_sv.add_argument("--db", default=None, help="SQLite DB パス")
    p_sv.add_argument("--kb-dir", default=None, help="KB ディレクトリパス")
    _add_common_args(p_sv)

    args = parser.parse_args()

    cmds = {
        "qa": cmd_qa,
        "index": cmd_index,
        "route": cmd_route,
        "read": cmd_read,
        "review": cmd_review,
        "serve": cmd_serve,
    }
    cmds[args.command](args)


if __name__ == "__main__":
    main()
