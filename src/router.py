"""Agent 2: Router - 質問→Reader 割当マップ生成"""

from __future__ import annotations

from .models import IndexEntry, Question, ReaderAssignment, RoutingResult

# 大分類→KBカテゴリ+キーワードの静的マッピング
_CATEGORY_HINTS: dict[str, list[str]] = {
    "セキュリティ管理": ["policies", "past_answers"],
    "アクセス管理": ["policies"],
    "ウイルス対策": ["policies", "system_docs"],
    "ネットワーク管理": ["system_docs", "policies"],
    "バックアップ管理": ["system_docs"],
    "インシデント対応": ["system_docs"],
    "変更管理": ["system_docs"],
    "物理セキュリティ": ["system_docs", "policies"],
    "教育・訓練": ["system_docs", "policies"],
}

# キーワードベースのファイルマッチング
_KEYWORD_MAP: dict[str, list[str]] = {
    "セキュリティ管理": ["security_policy", "past_answer"],
    "アクセス管理": ["access_control", "security_policy"],
    "ウイルス対策": ["security_policy", "operation_manual"],
    "ネットワーク管理": ["infra_overview", "encryption_standards"],
    "バックアップ管理": ["dr_bcp_plan", "infra_overview"],
    "インシデント対応": ["incident_response", "operation_manual"],
    "変更管理": ["operation_manual", "audit_compliance"],
    "物理セキュリティ": ["infra_overview", "security_policy"],
    "教育・訓練": ["audit_compliance", "security_policy"],
}


def _match_files_for_question(
    question: Question,
    index: list[IndexEntry],
) -> list[IndexEntry]:
    keywords = _KEYWORD_MAP.get(question.major, [])
    categories = _CATEGORY_HINTS.get(question.major, [])

    matched: list[IndexEntry] = []
    for entry in index:
        stem = entry.file_name.rsplit(".", 1)[0]
        if any(kw in stem for kw in keywords):
            matched.append(entry)
        elif entry.category in categories and entry not in matched:
            matched.append(entry)

    if not matched:
        matched = [e for e in index if e.category in ("policies", "system_docs")][:2]

    return matched


def _pack_readers(
    question_files: list[tuple[Question, list[IndexEntry]]],
    token_budget: int,
) -> list[ReaderAssignment]:
    readers: list[ReaderAssignment] = []
    current_questions: list[int] = []
    current_files: set[str] = set()
    current_tokens = 0

    for question, files in question_files:
        needed_tokens = sum(
            f.estimated_tokens for f in files if f.path not in current_files
        )
        if current_questions and (current_tokens + needed_tokens) > token_budget:
            readers.append(ReaderAssignment(
                reader_id=chr(ord("A") + len(readers)),
                questions=current_questions,
                files=sorted(current_files),
                estimated_tokens=current_tokens,
            ))
            current_questions = []
            current_files = set()
            current_tokens = 0

        current_questions.append(question.no)
        for f in files:
            if f.path not in current_files:
                current_files.add(f.path)
                current_tokens += f.estimated_tokens

    if current_questions:
        readers.append(ReaderAssignment(
            reader_id=chr(ord("A") + len(readers)),
            questions=current_questions,
            files=sorted(current_files),
            estimated_tokens=current_tokens,
        ))

    return readers


def run_router(
    questions: list[Question],
    index: list[IndexEntry],
    token_budget_per_reader: int = 80000,
) -> RoutingResult:
    question_files: list[tuple[Question, list[IndexEntry]]] = []
    for q in questions:
        matched = _match_files_for_question(q, index)
        question_files.append((q, matched))

    readers = _pack_readers(question_files, token_budget_per_reader)
    return RoutingResult(readers=readers)


def routing_to_dict(result: RoutingResult) -> dict:
    return {
        "readers": [
            {
                "reader_id": r.reader_id,
                "questions": r.questions,
                "files": r.files,
                "estimated_tokens": r.estimated_tokens,
            }
            for r in result.readers
        ]
    }
