from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .domain import ParsedDocument, ParsedNode


NUMBERED_HEADING_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\.?\s+(?P<title>\S.*)$")
LIST_ITEM_RE = re.compile(r"^(?:[\u2022\u25cf\u25e6\-*]|●)\s+(?P<body>.+)$")
NUMBERED_LIST_ITEM_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)*)[.)]\s+(?P<body>.+)$")
MULTI_COLUMN_RE = re.compile(r"\S(?:.*\S){2,}\s{2,}\S")
HEADING_CUES = {
    "about",
    "decision",
    "design",
    "document",
    "expected",
    "important",
    "ingestion",
    "key",
    "note",
    "other",
    "overview",
    "required",
    "retrieval",
    "submission",
    "what",
    "versioning",
}


def _collapse_spaces(text: str) -> str:
    return re.sub(r"[\t ]+", " ", text).strip()


def _is_probable_heading(line: str) -> bool:
    tokens = line.split()
    if not tokens or len(tokens) > 14:
        return False
    if line.endswith((".", ":", ";")):
        return False
    if line.count(" ") >= 5 and line.lower() == line:
        return False
    if not re.search(r"[A-Za-z]", line):
        return False
    if line.startswith(("●", "•", "-", "*")):
        return False

    def is_title_word(token: str) -> bool:
        stripped = token.strip("()[]{}:,.-")
        return bool(stripped) and (stripped[0].isupper() or stripped.isupper())

    if len(tokens) == 1:
        return is_title_word(tokens[0])

    if len(tokens) == 2:
        return all(is_title_word(token) for token in tokens)

    normalized_first = re.sub(r"[^a-z0-9]+", "", tokens[0].lower())
    if normalized_first in HEADING_CUES:
        return True

    if any(symbol in line for symbol in ("&", "(", ")", "/", "-")) and tokens[0][0].isupper():
        return True

    return False


def _heading_level(line: str, fallback_level: int) -> tuple[bool, int, str]:
    numbered = NUMBERED_HEADING_RE.match(line)
    if numbered:
        number = numbered.group("number")
        title = numbered.group("title").strip()
        return True, len(number.split(".")), title
    if _is_probable_heading(line):
        if fallback_level <= 1:
            return True, 1, line
        return True, 2 if fallback_level == 2 else fallback_level - 1, line
    return False, fallback_level, line


def _looks_like_table_row(line: str) -> bool:
    return " | " in line or MULTI_COLUMN_RE.search(line) is not None


class PdfHierarchyParser:
    def parse_pdf(self, pdf_path: str | Path, title: str | None = None) -> ParsedDocument:
        path = Path(pdf_path)
        reader = PdfReader(str(path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return self.parse_pages(pages=pages, source_path=path, title=title or path.stem)

    def parse_pages(self, pages: Iterable[str], source_path: Path, title: str) -> ParsedDocument:
        root = ParsedNode(kind="document", heading=title, body="", level=0, page_start=1, page_end=1)
        heading_stack: list[ParsedNode] = [root]
        active_block: ParsedNode | None = None

        for page_number, page_text in enumerate(pages, start=1):
            raw_lines = [_collapse_spaces(line) for line in page_text.splitlines()]
            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line:
                    active_block = None
                    continue

                is_heading, level, heading_text = _heading_level(line, heading_stack[-1].level + 1)
                bullet_match = LIST_ITEM_RE.match(line) or NUMBERED_LIST_ITEM_RE.match(line)
                if is_heading:
                    active_block = None
                    while len(heading_stack) > 1 and heading_stack[-1].level >= level:
                        heading_stack.pop()
                    heading_node = ParsedNode(
                        kind="heading",
                        heading=heading_text,
                        body="",
                        level=level,
                        page_start=page_number,
                        page_end=page_number,
                    )
                    heading_stack[-1].children.append(heading_node)
                    heading_stack.append(heading_node)
                    continue

                if bullet_match:
                    active_block = None
                    bullet_body = bullet_match.group("body").strip()
                    list_item = ParsedNode(
                        kind="list_item",
                        heading="",
                        body=bullet_body,
                        level=heading_stack[-1].level + 1,
                        page_start=page_number,
                        page_end=page_number,
                    )
                    heading_stack[-1].children.append(list_item)
                    active_block = list_item
                    continue

                if _looks_like_table_row(line):
                    active_block = None
                    table_row = ParsedNode(
                        kind="table_row",
                        heading="",
                        body=line,
                        level=heading_stack[-1].level + 1,
                        page_start=page_number,
                        page_end=page_number,
                    )
                    heading_stack[-1].children.append(table_row)
                    active_block = table_row
                    continue

                if active_block and active_block.kind in {"paragraph", "list_item", "table_row"}:
                    active_block.body = f"{active_block.body} {line}".strip()
                    active_block.page_end = page_number
                    continue

                paragraph = ParsedNode(
                    kind="paragraph",
                    heading="",
                    body=line,
                    level=heading_stack[-1].level + 1,
                    page_start=page_number,
                    page_end=page_number,
                )
                heading_stack[-1].children.append(paragraph)
                active_block = paragraph

        return ParsedDocument(source_path=source_path, title=title, pages=list(pages), roots=root.children)
