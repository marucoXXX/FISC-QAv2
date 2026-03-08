"""Agent 2: Router - 質問→Reader 割当マップ生成"""

from __future__ import annotations

import json
import logging

from .models import IndexEntry, Question, ReaderAssignment, RoutingResult

logger = logging.getLogger(__name__)

# 大分類→KBカテゴリ+キーワードの静的マッピング
_CATEGORY_HINTS: dict[str, list[str]] = {
    "セキュリティ管理": ["policies", "past_answers"],
    "アクセス管理": ["policies"],
    "ウイルス対策": ["policies", "system_docs"],
    "ネットワーク管理": ["system_docs", "policies"],
    "バックアップ管理": ["system_docs"],
    "インシデント対応": ["system_docs"],
    "変更管理": ["system_docs", "operations"],
    "物理セキュリティ": ["system_docs", "policies"],
    "教育・訓練": ["operations", "system_docs"],
    "外部委託管理": ["regulations", "system_docs"],
    "システム開発": ["regulations", "policies"],
    "ログ・監視": ["system_docs", "operations"],
}

# キーワードベースのファイルマッチング
_KEYWORD_MAP: dict[str, list[str]] = {
    "セキュリティ管理": ["security_policy", "past_answer"],
    "アクセス管理": ["access_control", "security_policy"],
    "ウイルス対策": ["security_policy", "operation_manual"],
    "ネットワーク管理": ["infra_overview", "encryption_standards"],
    "バックアップ管理": ["dr_bcp_plan", "infra_overview"],
    "インシデント対応": ["incident_response", "operation_manual"],
    "変更管理": ["operation_manual", "change_management_log"],
    "物理セキュリティ": ["infra_overview", "security_policy"],
    "教育・訓練": ["security_training_record", "audit_compliance"],
    "外部委託管理": ["outsourcing_management", "audit_compliance"],
    "システム開発": ["system_development_standards", "security_policy"],
    "ログ・監視": ["operation_manual", "vulnerability_assessment"],
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


def _static_route(
    questions: list[Question],
    index: list[IndexEntry],
) -> list[tuple[Question, list[IndexEntry]]]:
    """静的キーワードマッチによるルーティング。"""
    return [(q, _match_files_for_question(q, index)) for q in questions]


def _build_llm_routing_prompt(
    questions: list[Question],
    index: list[IndexEntry],
) -> str:
    """LLM ルーティング用のプロンプトを生成する。"""
    index_desc = "\n".join(
        f"- {e.file_name} (category: {e.category}, tokens: {e.estimated_tokens}): {e.summary[:200]}"
        for e in index
    )
    question_desc = "\n".join(
        f"- Q{q.no} [{q.major} > {q.minor}]: {q.question}"
        for q in questions
    )
    return (
        "あなたはFISC安全対策基準に関する質問票の回答支援システムのルーティングエージェントです。\n"
        "以下のナレッジベース（KB）ファイル一覧と質問リストを見て、"
        "各質問に回答するために参照すべきKBファイルを選んでください。\n\n"
        "## KBファイル一覧\n"
        f"{index_desc}\n\n"
        "## 質問リスト\n"
        f"{question_desc}\n\n"
        "## 出力形式\n"
        "以下のJSON形式で出力してください。他のテキストは不要です。\n"
        "```json\n"
        "{\n"
        '  "routing": [\n'
        '    {"question_no": 1, "files": ["file1.pdf", "file2.docx"]},\n'
        "    ...\n"
        "  ]\n"
        "}\n"
        "```\n"
        "各質問に最低1つ、最大3つのファイルを割り当ててください。\n"
        "質問文の内容を理解し、最も関連性の高いファイルを選んでください。"
    )


def _parse_llm_routing_response(
    text: str,
    questions: list[Question],
    index: list[IndexEntry],
) -> dict[int, list[str]]:
    """LLM レスポンスから質問→ファイル名リストのマッピングを解析する。"""
    # JSON 部分を抽出
    clean = text
    if "```" in clean:
        parts = clean.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{"):
                clean = stripped
                break

    data = json.loads(clean)
    routing_list = data.get("routing", [])

    valid_files = {e.file_name for e in index}
    result: dict[int, list[str]] = {}
    for item in routing_list:
        qno = item["question_no"]
        files = [f for f in item["files"] if f in valid_files]
        if files:
            result[qno] = files

    return result


def _llm_route(
    questions: list[Question],
    index: list[IndexEntry],
    api_key: str,
    model: str,
) -> list[tuple[Question, list[IndexEntry]]]:
    """LLM ベースの動的ルーティング。"""
    import litellm
    prompt = _build_llm_routing_prompt(questions, index)

    response = litellm.completion(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key or None,
    )
    response_text = response.choices[0].message.content

    qno_to_files = _parse_llm_routing_response(response_text, questions, index)
    index_by_name = {e.file_name: e for e in index}

    result: list[tuple[Question, list[IndexEntry]]] = []
    for q in questions:
        file_names = qno_to_files.get(q.no, [])
        matched = [index_by_name[f] for f in file_names if f in index_by_name]
        if not matched:
            # LLM が割り当てなかった質問は静的フォールバック
            matched = _match_files_for_question(q, index)
        result.append((q, matched))

    return result


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
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> RoutingResult:
    if api_key:
        try:
            question_files = _llm_route(questions, index, api_key, model)
        except Exception as e:
            logger.warning("LLM routing failed, falling back to static: %s", e)
            question_files = _static_route(questions, index)
    else:
        question_files = _static_route(questions, index)

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
