from __future__ import annotations

import hashlib
from dataclasses import asdict
from pathlib import Path

from .config import get_app_paths
from .domain import TestCaseArtifact
from .generator import JsonArtifactStore, TestCaseGenerator
from .parser import PdfHierarchyParser
from .repository import DocumentRepository


def _hash_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


class PipelineService:
    def __init__(self, database_path: str | Path | None = None, artifacts_path: str | Path | None = None):
        paths = get_app_paths()
        self.repository = DocumentRepository(database_path or paths.database_path)
        self.artifact_store = JsonArtifactStore(artifacts_path or paths.artifacts_path)
        self.parser = PdfHierarchyParser()
        self.generator = TestCaseGenerator()

    def ingest_pdf(self, pdf_path: str | Path, document_key: str | None = None, title: str | None = None) -> dict[str, object]:
        source_path = Path(pdf_path)
        parsed_document = self.parser.parse_pdf(source_path, title=title or source_path.stem)
        key = document_key or source_path.stem.lower().replace(" ", "-")
        source_hash = _hash_file(source_path)
        return self.repository.ingest(key, parsed_document, source_hash)

    def create_selection(self, document_key: str, version_id: str, logical_node_id: str, note: str = "") -> dict[str, object]:
        document = self.repository.get_document_by_key(document_key)
        if not document:
            raise ValueError(f"Unknown document key: {document_key}")
        selection_id = self.repository.create_selection(document["id"], version_id, logical_node_id, note)
        return {
            "selection_id": selection_id,
            "logical_node_id": logical_node_id,
            "version_id": version_id,
            "note": note,
        }

    def _build_case_set(self, selection_id: str) -> list[TestCaseArtifact]:
        selection = self.repository.get_selection(selection_id)
        if not selection:
            raise ValueError(f"Unknown selection id: {selection_id}")

        revision = self.repository.get_revision_for_version(selection.logical_node_id, selection.version_id)
        if revision is None:
            raise ValueError("Selection references a revision that no longer exists")

        latest_revision = self.repository.get_latest_revision(selection.logical_node_id)
        logical_node = self.repository.get_logical_node(selection.logical_node_id)
        block_type = logical_node["block_type"] if logical_node else "paragraph"
        title = logical_node["title"] if logical_node else revision["raw_text"]
        is_stale = latest_revision is not None and latest_revision["content_hash"] != revision["content_hash"]
        return self.generator.generate(
            selection_id=selection.selection_id,
            logical_node_id=selection.logical_node_id,
            version_id=selection.version_id,
            source_content_hash=revision["content_hash"],
            block_type=block_type,
            title=title,
            body=revision["body"],
            latest_content_hash=latest_revision["content_hash"] if latest_revision else None,
            is_stale=is_stale,
        )

    def generate_for_selection(self, selection_id: str) -> list[dict[str, object]]:
        cases = self._build_case_set(selection_id)
        self.artifact_store.append(cases)
        return [asdict(case) for case in cases]

    def refresh_case_views_by_selection(self, selection_id: str) -> list[dict[str, object]]:
        selection = self.repository.get_selection(selection_id)
        if not selection:
            return []
        revision = self.repository.get_revision_for_version(selection.logical_node_id, selection.version_id)
        latest_revision = self.repository.get_latest_revision(selection.logical_node_id)
        cases = self.artifact_store.list_by_selection(selection_id)
        refreshed: list[dict[str, object]] = []
        for case in cases:
            case["staleness_status"] = "stale" if latest_revision and revision and latest_revision["content_hash"] != revision["content_hash"] else "fresh"
            case["latest_content_hash"] = latest_revision["content_hash"] if latest_revision else None
            refreshed.append(case)
        return refreshed

    def refresh_case_views_by_node(self, logical_node_id: str) -> list[dict[str, object]]:
        selection_ids = self.repository.list_selection_ids(logical_node_id)
        refreshed: list[dict[str, object]] = []
        for selection_id in selection_ids:
            refreshed.extend(self.refresh_case_views_by_selection(selection_id))
        return refreshed

    def version_tree(self, document_key: str, version_id: str) -> list[dict[str, object]]:
        document = self.repository.get_document_by_key(document_key)
        if not document:
            return []
        return self.repository.fetch_tree_for_version(document["id"], version_id)
