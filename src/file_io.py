"""File I/O module for reading/writing questionnaires in bank-specific formats."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any


@dataclass
class FormatConfig:
    file_format: str  # 'xlsx' or 'docx'
    question_col: str
    answer_col: str
    header_row: int
    data_start_row: int
    table_index: int = 0
    format_type: str = "freetext"  # 'choices' | 'assessment' | 'freetext'
    choices_col: str = ""
    remarks_col: str = ""


@dataclass
class Question:
    question_no: int
    question_text: str
    major: str = ""
    minor: str = ""
    choices_text: str = ""
    remarks_text: str = ""


def _col_letter_to_index(col: str) -> int:
    result = 0
    for c in col.upper():
        result = result * 26 + (ord(c) - ord('A') + 1)
    return result - 1


def read_questionnaire(path: Path, config: FormatConfig) -> list[Question]:
    if config.file_format == "docx":
        return _read_docx_questionnaire(path, config)
    return _read_xlsx_questionnaire(path, config)


def _read_xlsx_questionnaire(path: Path, config: FormatConfig) -> list[Question]:
    from openpyxl import load_workbook

    wb = load_workbook(str(path), read_only=True, data_only=True)
    ws = wb.active
    q_idx = _col_letter_to_index(config.question_col)
    c_idx = _col_letter_to_index(config.choices_col) if config.choices_col else -1
    r_idx = _col_letter_to_index(config.remarks_col) if config.remarks_col else -1

    questions = []
    for i, row in enumerate(ws.iter_rows(min_row=config.data_start_row, values_only=True), start=1):
        if len(row) <= q_idx:
            continue
        q_text = str(row[q_idx] or "").strip()
        if not q_text:
            continue
        major = str(row[1] or "").strip() if len(row) > 1 else ""
        minor = str(row[2] or "").strip() if len(row) > 2 else ""
        choices = str(row[c_idx] or "").strip() if 0 <= c_idx < len(row) else ""
        remarks = str(row[r_idx] or "").strip() if 0 <= r_idx < len(row) else ""
        questions.append(Question(
            question_no=i,
            question_text=q_text,
            major=major,
            minor=minor,
            choices_text=choices,
            remarks_text=remarks,
        ))

    wb.close()
    return questions


def _read_docx_questionnaire(path: Path, config: FormatConfig) -> list[Question]:
    from docx import Document

    doc = Document(str(path))
    if config.table_index >= len(doc.tables):
        return []

    table = doc.tables[config.table_index]
    q_idx = _col_letter_to_index(config.question_col)
    c_idx = _col_letter_to_index(config.choices_col) if config.choices_col else -1
    r_idx = _col_letter_to_index(config.remarks_col) if config.remarks_col else -1

    questions = []
    no = 0
    for i, row in enumerate(table.rows):
        if i < config.data_start_row - 1:
            continue
        cells = row.cells
        if len(cells) <= q_idx:
            continue
        q_text = cells[q_idx].text.strip()
        if not q_text:
            continue
        no += 1
        major = cells[1].text.strip() if len(cells) > 1 else ""
        minor = cells[2].text.strip() if len(cells) > 2 else ""
        choices = cells[c_idx].text.strip() if 0 <= c_idx < len(cells) else ""
        remarks = cells[r_idx].text.strip() if 0 <= r_idx < len(cells) else ""
        questions.append(Question(
            question_no=no,
            question_text=q_text,
            major=major,
            minor=minor,
            choices_text=choices,
            remarks_text=remarks,
        ))

    return questions


def write_answers_to_original(
    original_path: Path,
    answers: dict[int, str],
    config: FormatConfig,
    output_path: Path,
) -> Path:
    """元ファイルの回答列に書き込み、フォーマットを維持して出力"""
    if config.file_format == "docx":
        return _write_docx_answers(original_path, answers, config, output_path)
    return _write_xlsx_answers(original_path, answers, config, output_path)


def _write_xlsx_answers(
    original_path: Path,
    answers: dict[int, str],
    config: FormatConfig,
    output_path: Path,
) -> Path:
    from openpyxl import load_workbook

    wb = load_workbook(str(original_path))
    ws = wb.active
    a_col = config.answer_col.upper()

    no = 0
    for row_idx in range(config.data_start_row, ws.max_row + 1):
        q_idx = _col_letter_to_index(config.question_col)
        q_cell = ws.cell(row=row_idx, column=q_idx + 1).value
        if not q_cell or not str(q_cell).strip():
            continue
        no += 1
        if no in answers:
            ws[f"{a_col}{row_idx}"] = answers[no]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(output_path))
    wb.close()
    return output_path


def _write_docx_answers(
    original_path: Path,
    answers: dict[int, str],
    config: FormatConfig,
    output_path: Path,
) -> Path:
    from docx import Document

    doc = Document(str(original_path))
    if config.table_index >= len(doc.tables):
        return output_path

    table = doc.tables[config.table_index]
    a_idx = _col_letter_to_index(config.answer_col)
    q_idx = _col_letter_to_index(config.question_col)

    no = 0
    for i, row in enumerate(table.rows):
        if i < config.data_start_row - 1:
            continue
        cells = row.cells
        if len(cells) <= max(q_idx, a_idx):
            continue
        q_text = cells[q_idx].text.strip()
        if not q_text:
            continue
        no += 1
        if no in answers:
            cells[a_idx].text = answers[no]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(output_path))
    return output_path
