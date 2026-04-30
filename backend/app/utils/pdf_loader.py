import re
from pathlib import Path
from pypdf import PdfReader


def extract_faq_chunks(pdf_path: str) -> list[dict]:
    """
    Extract FAQ content from PDF and split into Q&A chunks.
    Each chunk: {"section": str, "question": str, "text": str}
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"FAQ PDF not found: {pdf_path}")

    reader = PdfReader(str(path))
    full_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    return _parse_chunks(full_text)


def _parse_chunks(text: str) -> list[dict]:
    chunks = []
    current_section = "General"
    current_question = ""
    current_lines: list[str] = []

    # Section headers like "1. ABOUT REID & TAYLOR" or "SECTION 1: ..."
    section_pattern = re.compile(
        r"^\s*(?:\d+[\.\)]\s+)?([A-Z][A-Z &/\-]{4,})\s*$"
    )
    # Question lines: start with Q: or numbered questions or end with ?
    question_pattern = re.compile(r"^\s*(?:Q\s*[:.]?\s*|Q\d+[\.\)]\s*)(.+)$", re.IGNORECASE)

    def flush():
        if current_lines:
            body = " ".join(current_lines).strip()
            if len(body) > 20:
                chunks.append({
                    "section": current_section,
                    "question": current_question,
                    "text": (
                        f"Q: {current_question}\nA: {body}"
                        if current_question
                        else f"{current_section}: {body}"
                    ),
                })

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        sec_match = section_pattern.match(line)
        q_match = question_pattern.match(line)

        if sec_match and len(line.split()) <= 8:
            flush()
            current_section = sec_match.group(1).title()
            current_question = ""
            current_lines = []
        elif q_match:
            flush()
            current_question = q_match.group(1).strip()
            current_lines = []
        elif line.endswith("?") and len(line) > 15 and not line.startswith("A"):
            flush()
            current_question = line
            current_lines = []
        else:
            # Skip answer prefix markers ("A:", "A.")
            answer_line = re.sub(r"^\s*A\s*[:\.]\s*", "", line)
            current_lines.append(answer_line)

    flush()

    # If parsing produced too few chunks, fall back to paragraph chunking
    if len(chunks) < 5:
        chunks = _paragraph_chunks(text)

    return chunks


def _paragraph_chunks(text: str, min_length: int = 80) -> list[dict]:
    """Fallback: split text into paragraph-sized chunks."""
    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    for i, para in enumerate(paragraphs):
        para = para.strip()
        if len(para) >= min_length:
            chunks.append({
                "section": "FAQ",
                "question": "",
                "text": para,
            })
    return chunks
