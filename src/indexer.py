"""Agent 1: Indexer - KBファイルの軽量インデックス生成と更新検知"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import IndexEntry

# 1トークン ≈ 4文字（日本語は約2文字）として推定
_CHARS_PER_TOKEN_EN = 4
_CHARS_PER_TOKEN_JA = 2


def _estimate_tokens(text: str) -> int:
    ja_count = sum(1 for c in text if ord(c) > 0x3000)
    en_count = len(text) - ja_count
    return int(ja_count / _CHARS_PER_TOKEN_JA + en_count / _CHARS_PER_TOKEN_EN)


def _extract_summary_pdf(path: Path, max_pages: int = 2) -> tuple[str, int]:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(path))
        text = ""
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            text += page.get_text()
        full_text = "".join(page.get_text() for page in doc)
        tokens = _estimate_tokens(full_text)
        doc.close()
        summary = text[:500].strip()
        return summary, tokens
    except ImportError:
        # PyMuPDF not available - estimate from file size
        size = path.stat().st_size
        tokens = size // 3  # rough estimate
        return f"[PDF] {path.stem}", tokens


def _extract_summary_docx(path: Path) -> tuple[str, int]:
    from docx import Document
    doc = Document(str(path))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    tokens = _estimate_tokens(full_text)
    summary = full_text[:500].strip()
    return summary, tokens


def _extract_summary_xlsx(path: Path) -> tuple[str, int]:
    from openpyxl import load_workbook
    wb = load_workbook(str(path), read_only=True, data_only=True)
    texts = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            row_text = " ".join(str(c) for c in row if c is not None)
            if row_text.strip():
                texts.append(row_text)
    wb.close()
    full_text = "\n".join(texts)
    tokens = _estimate_tokens(full_text)
    summary = full_text[:500].strip()
    return summary, tokens


def _extract_summary(path: Path) -> tuple[str, int]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _extract_summary_pdf(path)
    elif suffix == ".docx":
        return _extract_summary_docx(path)
    elif suffix == ".xlsx":
        return _extract_summary_xlsx(path)
    else:
        text = path.read_text(encoding="utf-8", errors="replace")
        tokens = _estimate_tokens(text)
        return text[:500].strip(), tokens


def _file_modified_iso(path: Path) -> str:
    mtime = path.stat().st_mtime
    return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()


def _category_from_path(path: Path, kb_dir: Path) -> str:
    try:
        rel = path.relative_to(kb_dir)
        return rel.parts[0] if len(rel.parts) > 1 else "other"
    except ValueError:
        return "other"


def run_indexer(
    kb_dir: Path,
    previous_index: list[dict] | None = None,
) -> list[IndexEntry]:
    kb_dir = Path(kb_dir)
    prev_map: dict[str, str] = {}
    if previous_index:
        for entry in previous_index:
            prev_map[entry["file_name"]] = entry.get("last_modified", "")

    entries: list[IndexEntry] = []
    for f in sorted(kb_dir.rglob("*")):
        if not f.is_file():
            continue
        summary, tokens = _extract_summary(f)
        last_modified = _file_modified_iso(f)
        updated = True
        if f.name in prev_map and prev_map[f.name] == last_modified:
            updated = False

        category = _category_from_path(f, kb_dir)
        entries.append(IndexEntry(
            file_name=f.name,
            path=str(f.relative_to(kb_dir.parent.parent) if "fixtures" in str(kb_dir) else f),
            category=category,
            summary=summary,
            estimated_tokens=tokens,
            last_modified=last_modified,
            updated=updated,
        ))

    return entries


def index_to_dicts(entries: list[IndexEntry]) -> list[dict]:
    return [
        {
            "file_name": e.file_name,
            "path": e.path,
            "category": e.category,
            "summary": e.summary,
            "estimated_tokens": e.estimated_tokens,
            "last_modified": e.last_modified,
            "updated": e.updated,
        }
        for e in entries
    ]


def save_index(entries: list[IndexEntry], path: Path) -> None:
    path.write_text(
        json.dumps(index_to_dicts(entries), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_index(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))
