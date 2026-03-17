import io
from pathlib import Path


def extract_text(content: bytes, filename: str) -> str | None:
    """
    ファイル内容からテキストを抽出する。
    対応形式: PDF, Word (.docx)
    """
    suffix = Path(filename).suffix.lower()

    try:
        if suffix == ".pdf":
            return _extract_from_pdf(content)
        elif suffix == ".docx":
            return _extract_from_docx(content)
        elif suffix == ".doc":
            # .doc形式は非対応（python-docxは.docxのみ）
            return None
        else:
            return None
    except Exception:
        return None


def _extract_from_pdf(content: bytes) -> str | None:
    """PDFからテキストを抽出"""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return "\n\n".join(text_parts) if text_parts else None


def _extract_from_docx(content: bytes) -> str | None:
    """Word(.docx)からテキストを抽出"""
    from docx import Document

    doc = Document(io.BytesIO(content))
    text_parts = []

    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text)

    return "\n\n".join(text_parts) if text_parts else None
