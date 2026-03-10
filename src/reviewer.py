"""Agent 4: Reviewer - 全回答の品質チェック・矛盾検出・最終判定"""

from __future__ import annotations

import json
import logging

import litellm

from .models import Answer, Confidence, Question, ReviewNote
from .reader import _is_openai_model

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたはFISCアンケート回答の品質レビュー担当者です。
全回答のサマリーを確認し、以下の観点でチェックしてください:

1. 回答間の矛盾（例: ある質問で「MFA必須」と回答し、別の質問で「MFA未導入」と回答）
2. 根拠の妥当性（根拠ソースが質問内容と整合しているか）
3. 「回答不可候補」の最終判定（confidence="low"を最終的に「回答不可」確定 or 格上げ）
4. 信頼度の最終スコアリング

出力は以下のJSON形式で返してください:
{
  "final_judgments": [
    {
      "question_no": <int>,
      "confidence_override": "high" | "medium" | "low" | null,
      "status_override": "<新ステータス>" | null,
      "flag": "<フラグ>" | null
    }
  ],
  "review_notes": [
    {
      "question_no": <int>,
      "issue_type": "contradiction" | "weak_reference" | "missing_evidence" | "other",
      "severity": "high" | "medium" | "low",
      "description": "<説明>",
      "suggestion": "<提案>"
    }
  ]
}
"""


def _extract_json_object(text: str) -> str:
    """LLM応答テキストからJSONオブジェクト部分を抽出する。"""
    from .reader import _find_matching_bracket

    raw = text.strip()
    # 1) コードブロック内を探す
    if "```" in raw:
        parts = raw.split("```")
        for part in parts[1::2]:
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("{") or stripped.startswith("["):
                return stripped
    # 2) フォールバック: 生テキストから { ... } を括弧深度マッチングで探す
    start, end = _find_matching_bracket(raw, "{", "}")
    if start >= 0:
        return raw[start:end]
    return raw


def _build_review_prompt(
    questions: list[Question],
    answers: dict[int, Answer],
) -> str:
    parts = ["## 回答サマリー\n"]
    for q in questions:
        ans = answers.get(q.no)
        if ans:
            parts.append(
                f"### Q{q.no} [{q.major} > {q.minor}]\n"
                f"質問: {q.question}\n"
                f"回答: {ans.answer}\n"
                f"ステータス: {ans.status}\n"
                f"根拠: {', '.join(ans.source_references) if ans.source_references else 'なし'}\n"
                f"確信度: {ans.confidence}\n"
                f"抜粋: {ans.key_excerpt}\n"
            )
        else:
            parts.append(
                f"### Q{q.no} [{q.major} > {q.minor}]\n"
                f"質問: {q.question}\n"
                f"回答: (未回答)\n"
            )

    parts.append("\n上記の全回答をレビューし、JSON形式で結果を返してください。")
    return "\n".join(parts)


def run_reviewer(
    questions: list[Question],
    answers: dict[int, Answer],
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> tuple[dict[int, Answer], list[ReviewNote]]:
    user_prompt = _build_review_prompt(questions, answers)

    kwargs: dict = dict(
        model=model,
        max_tokens=8192,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        api_key=api_key or None,
    )
    if _is_openai_model(model):
        kwargs["response_format"] = {"type": "json_object"}

    response = litellm.completion(**kwargs)

    choice = response.choices[0]
    finish_reason = getattr(choice, "finish_reason", None)
    response_text = choice.message.content

    if not response_text:
        logger.warning("[Reviewer] Empty response, using rule-based fallback")
        return _rule_based_review(answers), []

    if finish_reason == "length":
        logger.warning("[Reviewer] Response truncated (finish_reason=length), using rule-based fallback")
        return _rule_based_review(answers), []

    return _apply_review(answers, response_text)


def _apply_review(
    answers: dict[int, Answer],
    review_text: str,
) -> tuple[dict[int, Answer], list[ReviewNote]]:
    # Parse review response
    review_notes: list[ReviewNote] = []

    # Step 1: 直接 json.loads を試行（response_format 対応）
    data = None
    try:
        data = json.loads(review_text.strip())
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 2: 失敗時のみ _extract_json_object でフォールバック
    if data is None:
        json_text = _extract_json_object(review_text)
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # If parsing fails, apply rule-based review only
            return _rule_based_review(answers), review_notes

    # Apply overrides from LLM review
    for judgment in data.get("final_judgments", []):
        qno = judgment["question_no"]
        if qno in answers:
            ans = answers[qno]
            if judgment.get("confidence_override"):
                ans.confidence = judgment["confidence_override"]
            if judgment.get("status_override"):
                ans.status = judgment["status_override"]
            if judgment.get("flag"):
                ans.flag = judgment["flag"]

    # Parse review notes
    for note_data in data.get("review_notes", []):
        review_notes.append(ReviewNote(
            question_no=note_data["question_no"],
            issue_type=note_data.get("issue_type", "other"),
            severity=note_data.get("severity", "medium"),
            description=note_data.get("description", ""),
            suggestion=note_data.get("suggestion", ""),
        ))

    # Apply rule-based overrides on top
    answers = _rule_based_review(answers)
    return answers, review_notes


def _rule_based_review(answers: dict[int, Answer]) -> dict[int, Answer]:
    for qno, ans in answers.items():
        # Low confidence → force "回答不可"
        if ans.confidence == Confidence.LOW.value and ans.status not in ("回答不可", "過去回答採用"):
            ans.status = "回答不可"
            ans.flag = ans.flag or "KB に該当情報なし"
        # No answer text with high/medium confidence → downgrade
        if not ans.answer.strip() and ans.confidence != Confidence.LOW.value:
            ans.confidence = Confidence.LOW.value
            ans.status = "回答不可"
    return answers
