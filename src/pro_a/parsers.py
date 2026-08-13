from __future__ import annotations

from pathlib import Path


class ParseError(RuntimeError):
    pass


def parse_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ParseError(f"Unable to decode text file: {path}")


def parse_pdf(path: Path) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            text = f"[PAGE_PARSE_ERROR: {e}]"
        parts.append(f"\n[[PAGE:{i}]]\n{text}")
    return "\n".join(parts)


def parse_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    parts = []
    for i, p in enumerate(doc.paragraphs, 1):
        if p.text.strip():
            parts.append(f"[[PARA:{i}]] {p.text}")
    for ti, table in enumerate(doc.tables, 1):
        parts.append(f"[[TABLE:{ti}]]")
        for ri, row in enumerate(table.rows, 1):
            vals = [cell.text.replace("\n", " ").strip() for cell in row.cells]
            parts.append(f"[[TABLE:{ti}:ROW:{ri}]] " + " | ".join(vals))
    return "\n".join(parts)


def parse_xlsx(path: Path) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"[[SHEET:{ws.title}]]")
        for ri, row in enumerate(ws.iter_rows(values_only=True), 1):
            vals = ["" if v is None else str(v) for v in row]
            if any(v.strip() for v in vals):
                parts.append(f"[[SHEET:{ws.title}:ROW:{ri}]] " + " | ".join(vals))
    return "\n".join(parts)


def parse_pptx(path: Path) -> str:
    from pptx import Presentation
    prs = Presentation(str(path))
    parts = []
    for si, slide in enumerate(prs.slides, 1):
        parts.append(f"[[SLIDE:{si}]]")
        for shape in slide.shapes:
            text = getattr(shape, "text", "")
            if text and text.strip():
                parts.append(text.strip())
    return "\n".join(parts)


def parse_source(path: Path) -> tuple[str, str]:
    ext = path.suffix.lower()
    if ext in {".txt", ".md", ".markdown", ".csv"}:
        return parse_text_file(path), ext.lstrip(".") or "text"
    if ext == ".pdf":
        return parse_pdf(path), "pdf"
    if ext in {".docx"}:
        return parse_docx(path), "docx"
    if ext in {".xlsx", ".xlsm"}:
        return parse_xlsx(path), "xlsx"
    if ext in {".pptx"}:
        return parse_pptx(path), "pptx"
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ParseError("Image OCR/multimodal parsing is intentionally deferred in v0.1; file can still be archived/uploaded.")
    raise ParseError(f"Unsupported parser for extension: {ext or '<none>'}")


def chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        if end < len(text):
            boundary = text.rfind("\n", start, end)
            if boundary > start + max_chars // 2:
                end = boundary
        chunks.append(text[start:end])
        start = end
    return chunks
