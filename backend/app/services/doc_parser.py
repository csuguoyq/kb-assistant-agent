"""文档解析：从 PDF / Word / TXT / Markdown 文件提取纯文本。"""
import io

ALLOWED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md", ".markdown")


def _read_text(raw: bytes) -> str:
    for encoding in ("utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_text(filename: str, raw: bytes) -> str:
    """按扩展名分发到对应解析器；不支持的格式抛 ValueError。"""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if lower.endswith(".docx"):
        import docx
        document = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip())
    if lower.endswith((".txt", ".md", ".markdown")):
        return _read_text(raw)
    raise ValueError(f"仅支持 {' / '.join(ALLOWED_EXTENSIONS)} 文件")
