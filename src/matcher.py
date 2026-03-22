"""Question matching module for past answers and common answers."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any


@dataclass
class MatchResult:
    question_no: int
    matched_id: int
    matched_question: str
    matched_answer: str
    score: float
    judgment: str = ""   # reusable / caution / different
    reason: str = ""     # LLM判定理由


def _tokenize(text: str) -> list[str]:
    """日本語テキストを文字n-gramでトークン化"""
    text = re.sub(r"\s+", "", text.lower())
    tokens = []
    # unigram + bigram
    for c in text:
        tokens.append(c)
    for i in range(len(text) - 1):
        tokens.append(text[i:i+2])
    return tokens


def _cosine_similarity(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common_keys = set(a.keys()) & set(b.keys())
    dot = sum(a[k] * b[k] for k in common_keys)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def match_past_answers(
    questions: list[dict],
    past_qa_list: list[dict],
    threshold: float = 0.7,
) -> dict[int, MatchResult]:
    """TF-IDF類似度で過去回答をマッチング"""
    if not past_qa_list:
        return {}

    past_vectors = [
        (qa, Counter(_tokenize(qa["question_text"])))
        for qa in past_qa_list
    ]

    results: dict[int, MatchResult] = {}
    for q in questions:
        q_no = q["question_no"]
        q_text = q.get("question_text", "")
        q_vec = Counter(_tokenize(q_text))

        best_score = 0.0
        best_qa = None
        for qa, pv in past_vectors:
            score = _cosine_similarity(q_vec, pv)
            if score > best_score:
                best_score = score
                best_qa = qa

        if best_qa and best_score >= threshold:
            results[q_no] = MatchResult(
                question_no=q_no,
                matched_id=best_qa["id"],
                matched_question=best_qa["question_text"],
                matched_answer=best_qa["answer_text"],
                score=best_score,
            )

    return results


def match_common_answers(
    questions: list[dict],
    common_list: list[dict],
    api_key: str,
    model: str,
) -> dict[int, MatchResult]:
    """LLMで意味的に共通回答をマッチング"""
    if not questions or not common_list:
        return {}

    import litellm

    q_texts = []
    for q in questions:
        q_texts.append(f"Q{q['question_no']}: {q.get('question_text', '')}")

    c_texts = []
    for c in common_list:
        c_texts.append(f"C{c['id']}: {c['question_pattern']}")

    prompt = (
        "以下の質問リストと共通回答リストを比較し、意味的に同じ内容を聞いている質問と共通回答のペアを特定してください。\n"
        "表現が違っても同じ趣旨であればマッチとしてください。\n\n"
        "【質問リスト】\n" + "\n".join(q_texts) + "\n\n"
        "【共通回答リスト】\n" + "\n".join(c_texts) + "\n\n"
        "結果をJSON配列で返してください。マッチがない質問は含めないでください。\n"
        'フォーマット: [{"question_no": 1, "common_id": 5, "score": 0.9}]\n'
        "scoreは0-1の確信度です。0.7以上のみ返してください。"
    )

    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        temperature=0,
    )

    text = response.choices[0].message.content or ""
    # JSONを抽出
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return {}

    try:
        matches = json.loads(match.group())
    except json.JSONDecodeError:
        return {}

    common_map = {c["id"]: c for c in common_list}
    results: dict[int, MatchResult] = {}
    for m in matches:
        q_no = m.get("question_no")
        c_id = m.get("common_id")
        score = m.get("score", 0)
        if q_no is None or c_id is None or c_id not in common_map:
            continue
        c = common_map[c_id]
        results[q_no] = MatchResult(
            question_no=q_no,
            matched_id=c_id,
            matched_question=c["question_pattern"],
            matched_answer=c["answer_text"],
            score=score,
        )

    return results


def match_past_answers_llm(
    questions: list[dict],
    past_qa_list: list[dict],
    api_key: str,
    model: str,
) -> dict[int, MatchResult]:
    """LLMで意味的に過去回答をマッチング（判定理由付き）"""
    if not questions or not past_qa_list:
        return {}

    import litellm

    q_texts = []
    for q in questions:
        q_texts.append(f"Q{q['question_no']}: {q.get('question_text', '')}")

    p_texts = []
    for p in past_qa_list:
        p_texts.append(f"P{p['id']}: {p['question_text']}")

    prompt = (
        "以下の【今回の質問リスト】と【過去の質問リスト】を比較してください。\n"
        "意味的に同じ内容を聞いている質問ペアを特定し、過去の回答を再利用できるか判定してください。\n\n"
        "【今回の質問リスト】\n" + "\n".join(q_texts) + "\n\n"
        "【過去の質問リスト】\n" + "\n".join(p_texts) + "\n\n"
        "判定基準:\n"
        "- reusable: 質問の趣旨が同じで、過去の回答をそのまま再利用可能\n"
        "- caution: 趣旨は近いが、表現や範囲に差異があり回答の修正が必要な可能性あり\n"
        "- different: 質問の趣旨が異なり、過去の回答は使えない\n\n"
        "結果をJSON配列で返してください。マッチがない質問は含めないでください。\n"
        "判定がdifferentのものも含めないでください。\n"
        'フォーマット: [{"question_no": 1, "past_qa_id": 5, "score": 0.95, '
        '"judgment": "reusable", "reason": "語尾の変更のみで趣旨は同一"}]\n'
        "scoreは0-1の確信度です。"
    )

    response = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        api_key=api_key,
        temperature=0,
    )

    text = response.choices[0].message.content or ""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return {}

    try:
        matches = json.loads(match.group())
    except json.JSONDecodeError:
        return {}

    past_map = {p["id"]: p for p in past_qa_list}
    results: dict[int, MatchResult] = {}
    for m in matches:
        q_no = m.get("question_no")
        p_id = m.get("past_qa_id")
        score = m.get("score", 0)
        judgment = m.get("judgment", "")
        reason = m.get("reason", "")
        if q_no is None or p_id is None or p_id not in past_map:
            continue
        p = past_map[p_id]
        results[q_no] = MatchResult(
            question_no=q_no,
            matched_id=p_id,
            matched_question=p["question_text"],
            matched_answer=p["answer_text"],
            score=score,
            judgment=judgment,
            reason=reason,
        )

    return results


def match_past_answers_hybrid(
    questions: list[dict],
    past_qa_list: list[dict],
    api_key: str,
    model: str,
    cosine_threshold: float = 0.5,
) -> dict[int, MatchResult]:
    """ハイブリッド: cosineで候補抽出 → LLMで精密判定"""
    if not questions or not past_qa_list:
        return {}

    # Phase 1: cosineで緩い閾値で候補抽出
    cosine_results = match_past_answers(questions, past_qa_list, threshold=cosine_threshold)

    if not cosine_results:
        return {}

    # Phase 2: cosineで候補になった質問のみLLM判定
    candidate_questions = [
        q for q in questions if q["question_no"] in cosine_results
    ]
    candidate_past_ids = {r.matched_id for r in cosine_results.values()}
    candidate_past = [p for p in past_qa_list if p["id"] in candidate_past_ids]

    llm_results = match_past_answers_llm(
        candidate_questions, candidate_past, api_key, model,
    )

    # LLM結果をcosine結果にマージ
    merged: dict[int, MatchResult] = {}
    for q_no, cosine_r in cosine_results.items():
        if q_no in llm_results:
            merged[q_no] = llm_results[q_no]
        else:
            cosine_r.judgment = "caution"
            cosine_r.reason = "コサイン類似度のみ（LLM判定なし）"
            merged[q_no] = cosine_r

    return merged
