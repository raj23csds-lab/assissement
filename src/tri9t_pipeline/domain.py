from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ParsedNode:
    kind: str
    heading: str = ""
    body: str = ""
    level: int = 0
    page_start: int = 0
    page_end: int = 0
    children: list["ParsedNode"] = field(default_factory=list)


@dataclass(slots=True)
class ParsedDocument:
    source_path: Path
    title: str
    pages: list[str]
    roots: list[ParsedNode]


@dataclass(slots=True)
class SelectionView:
    selection_id: str
    logical_node_id: str
    version_id: str
    note: str


@dataclass(slots=True)
class TestCaseArtifact:
    case_id: str
    selection_id: str
    logical_node_id: str
    version_id: str
    source_content_hash: str
    title: str
    description: str
    expected_result: str
    staleness_status: str
    staleness_reason: str
    latest_content_hash: str | None = None
