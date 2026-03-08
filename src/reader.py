"""Agent 3: Reader - KBファイルを読み回答を生成"""

from __future__ import annotations

import json
from pathlib import Path

import litellm

from .models import Answer, Confidence, Question

SYSTEM_PROMPT = """\
あなたはFISC（金融情報システムセンター）のセキュリティアンケートに回答する専門家です。
提供されたナレッジベース（KB）ドキュメントの内容のみに基づいて、各質問に対して正確に回答してください。

回答ルール:
1. KBドキュメントに明確な根拠がある場合のみ回答する
2. 根拠が見つからない場合は confidence="low", status="回答不可候補" とする
3. 情報が曖昧・矛盾する場合は confidence="medium", status="要確認" とする
4. 回答は具体的かつ簡潔に記述する
5. 必ず根拠となるドキュメントのセクションを明記する

出力は以下のJSON配列形式で返してください:
[
  {
    "question_no": <int>,
    "answer": "<回答テキスト>",
    "status": "対応済" | "要確認" | "回答不可候補",
    "source_references": ["<ファイル名> / <セクション>"],
    "confidence": "high" | "medium" | "low",
    "key_excerpt": "<根拠となる文章の抜粋>"
  }
]
"""


def _read_file_content(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import fitz
            doc = fitz.open(str(path))
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text
        except ImportError:
            return f"[PDF file: {path.name} - PyMuPDF not installed]"
    elif suffix == ".docx":
        from docx import Document
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif suffix == ".xlsx":
        from openpyxl import load_workbook
        wb = load_workbook(str(path), read_only=True, data_only=True)
        lines = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                line = " | ".join(str(c) for c in row if c is not None)
                if line.strip():
                    lines.append(line)
        wb.close()
        return "\n".join(lines)
    else:
        return path.read_text(encoding="utf-8", errors="replace")


def _build_user_prompt(
    questions: list[Question],
    file_contents: dict[str, str],
) -> str:
    parts = ["## ナレッジベースドキュメント\n"]
    for fname, content in file_contents.items():
        parts.append(f"### {fname}\n```\n{content}\n```\n")

    parts.append("\n## 回答対象の質問\n")
    for q in questions:
        parts.append(f"- Q{q.no} [{q.major} > {q.minor}]: {q.question}")

    parts.append("\n上記の質問すべてにJSON配列形式で回答してください。")
    return "\n".join(parts)


def run_reader(
    reader_id: str,
    questions: list[Question],
    files: list[str],
    kb_base_dir: Path,
    api_key: str,
    model: str = "claude-sonnet-4-20250514",
) -> list[Answer]:
    file_contents: dict[str, str] = {}
    for fpath in files:
        full_path = kb_base_dir / fpath
        if full_path.exists():
            file_contents[fpath] = _read_file_content(full_path)
        else:
            file_contents[fpath] = f"[ファイルが見つかりません: {fpath}]"

    user_prompt = _build_user_prompt(questions, file_contents)

    response = litellm.completion(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        api_key=api_key or None,
    )

    response_text = response.choices[0].message.content
    return _parse_reader_response(response_text, questions)


def _parse_reader_response(text: str, questions: list[Question]) -> list[Answer]:
    # Extract JSON from response (handle markdown code blocks)
    json_text = text.strip()
    if "```" in json_text:
        # Extract content between first ``` and last ```
        parts = json_text.split("```")
        for part in parts[1::2]:  # odd-indexed parts are inside code blocks
            stripped = part.strip()
            if stripped.startswith("json"):
                stripped = stripped[4:].strip()
            if stripped.startswith("["):
                json_text = stripped
                break
    else:
        # No code blocks — try to find JSON array directly
        start = json_text.find("[")
        end = json_text.rfind("]") + 1
        if start >= 0 and end > start:
            json_text = json_text[start:end]

    try:
        data = json.loads(json_text)
    except json.JSONDecodeError:
        import sys
        print(f"[Reader] JSON parse failed. Raw response (first 500 chars):\n{text[:500]}", file=sys.stderr)
        # If parsing fails, return low-confidence answers for all questions
        return [
            Answer(
                question_no=q.no,
                answer="",
                status="回答不可候補",
                confidence=Confidence.LOW.value,
                flag="LLM応答のパースに失敗",
            )
            for q in questions
        ]

    answers: list[Answer] = []
    for item in data:
        answers.append(Answer(
            question_no=item["question_no"],
            answer=item.get("answer", ""),
            status=item.get("status", "要確認"),
            source_references=item.get("source_references", []),
            confidence=item.get("confidence", Confidence.MEDIUM.value),
            key_excerpt=item.get("key_excerpt", ""),
        ))

    # Ensure all questions have answers
    answered_nos = {a.question_no for a in answers}
    for q in questions:
        if q.no not in answered_nos:
            answers.append(Answer(
                question_no=q.no,
                answer="",
                status="回答不可候補",
                confidence=Confidence.LOW.value,
                flag="Readerから回答なし",
            ))

    return answers


def answers_to_dicts(answers: list[Answer]) -> list[dict]:
    return [
        {
            "question_no": a.question_no,
            "answer": a.answer,
            "status": a.status,
            "source_references": a.source_references,
            "confidence": a.confidence,
            "key_excerpt": a.key_excerpt,
        }
        for a in answers
    ]
