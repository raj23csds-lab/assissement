from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import uuid

from .domain import TestCaseArtifact


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _split_candidate_sentences(text: str) -> list[str]:
    parts: list[str] = []
    for fragment in re.split(r"(?<=[.;:])\s+|\n+", text):
        candidate = fragment.strip(" \t\u2022●-")
        if candidate:
            parts.append(candidate)
    return parts or [text.strip()]


class TestCaseGenerator:
    def generate(
        self,
        *,
        selection_id: str,
        logical_node_id: str,
        version_id: str,
        source_content_hash: str,
        block_type: str,
        title: str,
        body: str,
        latest_content_hash: str | None,
        is_stale: bool,
    ) -> list[TestCaseArtifact]:
        title_text = title.strip() or body[:80].strip() or block_type.replace("_", " ")
        body_text = body.strip()
        candidates = _split_candidate_sentences(body_text) if body_text else [title_text]
        cases: list[TestCaseArtifact] = []
        freshness_status = "stale" if is_stale else "fresh"
        freshness_reason = (
            "Latest revision content hash differs from the snapshot used to generate this case."
            if is_stale
            else "Latest revision content hash matches the snapshot used to generate this case."
        )

        for index, candidate in enumerate(candidates[:3], start=1):
            case_id = str(uuid.uuid4())
            if block_type == "heading":
                description = (
                    f"Verify the parser preserves the section '{title_text}' and its hierarchy."
                    if index == 1
                    else f"Verify the child element derived from '{candidate}' is retained under '{title_text}'."
                )
                expected = f"Section '{title_text}' remains traceable and structurally intact."
            elif block_type == "list_item":
                description = f"Verify the bullet requirement '{candidate}' is captured without losing its list relationship."
                expected = "The list item is present in the same order and remains linked to its parent section."
            elif block_type == "table_row":
                description = f"Verify table row preservation for '{candidate}'."
                expected = "The row is retained with its cell boundaries and ordering intact."
            else:
                description = f"Verify the paragraph '{candidate}' remains attached to the correct section."
                expected = "The paragraph remains searchable, attributable, and structurally nested."

            cases.append(
                TestCaseArtifact(
                    case_id=case_id,
                    selection_id=selection_id,
                    logical_node_id=logical_node_id,
                    version_id=version_id,
                    source_content_hash=source_content_hash,
                    title=f"{title_text} [{index}]",
                    description=description,
                    expected_result=expected,
                    staleness_status=freshness_status,
                    staleness_reason=freshness_reason,
                    latest_content_hash=latest_content_hash,
                )
            )
        return cases


class JsonArtifactStore:
    def __init__(self, store_path: str | Path):
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.store_path.exists():
            self._write({"items": []})

    def _read(self) -> dict[str, object]:
        with self.store_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, object]) -> None:
        temporary = self.store_path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        temporary.replace(self.store_path)

    def append(self, cases: list[TestCaseArtifact]) -> None:
        payload = self._read()
        items = payload.setdefault("items", [])
        items.extend({**asdict(case), "created_at": _utc_now()} for case in cases)
        self._write(payload)

    def list_by_selection(self, selection_id: str) -> list[dict[str, object]]:
        payload = self._read()
        items = payload.get("items", [])
        return [item for item in items if item.get("selection_id") == selection_id]

    def list_by_node(self, logical_node_id: str) -> list[dict[str, object]]:
        payload = self._read()
        items = payload.get("items", [])
        return [item for item in items if item.get("logical_node_id") == logical_node_id]
