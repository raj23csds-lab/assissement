from __future__ import annotations

import hashlib
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .domain import ParsedDocument, ParsedNode, SelectionView


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "node"


def _hash_text(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


def _stable_uuid(namespace: str, stable_key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tri9t:{namespace}:{stable_key}"))


class DocumentRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    document_key TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS versions (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    source_path TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(document_id, version_number),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS logical_nodes (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    stable_key TEXT NOT NULL,
                    block_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    level INTEGER NOT NULL,
                    parent_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(document_id, stable_key),
                    FOREIGN KEY(document_id) REFERENCES documents(id)
                );

                CREATE TABLE IF NOT EXISTS node_revisions (
                    id TEXT PRIMARY KEY,
                    logical_node_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    order_index INTEGER NOT NULL,
                    raw_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(logical_node_id, version_id),
                    FOREIGN KEY(logical_node_id) REFERENCES logical_nodes(id),
                    FOREIGN KEY(version_id) REFERENCES versions(id)
                );

                CREATE TABLE IF NOT EXISTS selections (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    logical_node_id TEXT NOT NULL,
                    note TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(document_id) REFERENCES documents(id),
                    FOREIGN KEY(version_id) REFERENCES versions(id),
                    FOREIGN KEY(logical_node_id) REFERENCES logical_nodes(id)
                );
                """
            )

    def get_or_create_document(self, document_key: str, title: str, source_path: str) -> str:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id FROM documents WHERE document_key = ?",
                (document_key,),
            ).fetchone()
            if row:
                connection.execute(
                    "UPDATE documents SET title = ?, source_path = ? WHERE id = ?",
                    (title, source_path, row["id"]),
                )
                return row["id"]

            document_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO documents (id, document_key, title, source_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (document_id, document_key, title, source_path, now),
            )
            return document_id

    def create_version(self, document_id: str, source_path: str, source_hash: str) -> tuple[str, int]:
        now = _utc_now()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(version_number), 0) AS version_number FROM versions WHERE document_id = ?",
                (document_id,),
            ).fetchone()
            version_number = int(row["version_number"]) + 1
            version_id = str(uuid.uuid4())
            connection.execute(
                "INSERT INTO versions (id, document_id, version_number, source_path, source_hash, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (version_id, document_id, version_number, source_path, source_hash, now),
            )
            return version_id, version_number

    def ingest(self, document_key: str, parsed_document: ParsedDocument, source_hash: str) -> dict[str, object]:
        document_id = self.get_or_create_document(document_key, parsed_document.title, str(parsed_document.source_path))
        version_id, version_number = self.create_version(document_id, str(parsed_document.source_path), source_hash)

        node_count = 0
        with self._connect() as connection:
            for _logical_node, _revision, _stable_key in self._persist_tree(
                connection=connection,
                document_id=document_id,
                version_id=version_id,
                nodes=parsed_document.roots,
                parent_id=None,
                parent_stable_key=document_key,
            ):
                node_count += 1

        return {
            "document_id": document_id,
            "document_key": document_key,
            "version_id": version_id,
            "version_number": version_number,
            "node_count": node_count,
        }

    def _persist_tree(
        self,
        connection: sqlite3.Connection,
        document_id: str,
        version_id: str,
        nodes: Iterable[ParsedNode],
        parent_id: str | None,
        parent_stable_key: str,
    ) -> Iterable[tuple[str, str, str]]:
        sibling_counts: dict[str, int] = {}
        for order_index, node in enumerate(nodes, start=1):
            signature_source = node.heading if node.heading else node.kind
            signature = _slugify(signature_source)
            occurrence = sibling_counts.get(signature, 0) + 1
            sibling_counts[signature] = occurrence
            stable_key = f"{parent_stable_key}/{signature}-{occurrence}"
            logical_node_id = _stable_uuid(document_id, stable_key)
            now = _utc_now()
            existing = connection.execute(
                "SELECT id FROM logical_nodes WHERE document_id = ? AND stable_key = ?",
                (document_id, stable_key),
            ).fetchone()
            title = node.heading or node.body[:120]
            if existing:
                logical_node_id = existing["id"]
                connection.execute(
                    "UPDATE logical_nodes SET block_type = ?, title = ?, level = ?, parent_id = ?, updated_at = ? WHERE id = ?",
                    (node.kind, title, node.level, parent_id, now, logical_node_id),
                )
            else:
                connection.execute(
                    "INSERT INTO logical_nodes (id, document_id, stable_key, block_type, title, level, parent_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (logical_node_id, document_id, stable_key, node.kind, title, node.level, parent_id, now, now),
                )

            raw_text = node.heading if node.heading else node.body
            content_hash = _hash_text(node.kind, node.heading, node.body, str(node.level))
            revision_id = str(uuid.uuid4())
            connection.execute(
                "INSERT OR REPLACE INTO node_revisions (id, logical_node_id, version_id, body, content_hash, page_start, page_end, order_index, raw_text, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    revision_id,
                    logical_node_id,
                    version_id,
                    node.body,
                    content_hash,
                    node.page_start,
                    node.page_end,
                    order_index,
                    raw_text,
                    now,
                ),
            )

            yield logical_node_id, revision_id, stable_key
            if node.children:
                yield from self._persist_tree(
                    connection=connection,
                    document_id=document_id,
                    version_id=version_id,
                    nodes=node.children,
                    parent_id=logical_node_id,
                    parent_stable_key=stable_key,
                )

    def create_selection(self, document_id: str, version_id: str, logical_node_id: str, note: str) -> str:
        selection_id = str(uuid.uuid4())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO selections (id, document_id, version_id, logical_node_id, note, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (selection_id, document_id, version_id, logical_node_id, note, _utc_now()),
            )
        return selection_id

    def get_selection(self, selection_id: str) -> SelectionView | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, logical_node_id, version_id, note FROM selections WHERE id = ?",
                (selection_id,),
            ).fetchone()
        if not row:
            return None
        return SelectionView(
            selection_id=row["id"],
            logical_node_id=row["logical_node_id"],
            version_id=row["version_id"],
            note=row["note"],
        )

    def get_latest_revision(self, logical_node_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT nr.*, v.version_number
                FROM node_revisions nr
                JOIN versions v ON v.id = nr.version_id
                WHERE nr.logical_node_id = ?
                ORDER BY v.version_number DESC
                LIMIT 1
                """,
                (logical_node_id,),
            ).fetchone()
        return row

    def get_revision_for_version(self, logical_node_id: str, version_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM node_revisions WHERE logical_node_id = ? AND version_id = ?",
                (logical_node_id, version_id),
            ).fetchone()

    def get_logical_node(self, logical_node_id: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute(
                "SELECT * FROM logical_nodes WHERE id = ?",
                (logical_node_id,),
            ).fetchone()

    def fetch_tree_for_version(self, document_id: str, version_id: str) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ln.id, ln.parent_id, ln.block_type, ln.title, ln.level,
                       nr.body, nr.content_hash, nr.order_index, nr.page_start, nr.page_end
                FROM logical_nodes ln
                JOIN node_revisions nr ON nr.logical_node_id = ln.id
                WHERE ln.document_id = ? AND nr.version_id = ?
                ORDER BY COALESCE(ln.parent_id, ln.id), nr.order_index, ln.level
                """,
                (document_id, version_id),
            ).fetchall()

        nodes = {
            row["id"]: {
                "id": row["id"],
                "parent_id": row["parent_id"],
                "kind": row["block_type"],
                "title": row["title"],
                "level": row["level"],
                "body": row["body"],
                "content_hash": row["content_hash"],
                "order_index": row["order_index"],
                "page_start": row["page_start"],
                "page_end": row["page_end"],
                "children": [],
            }
            for row in rows
        }
        roots: list[dict[str, object]] = []
        for node in nodes.values():
            parent_id = node["parent_id"]
            if parent_id and parent_id in nodes:
                nodes[parent_id]["children"].append(node)
            else:
                roots.append(node)
        return roots

    def get_document_by_key(self, document_key: str) -> sqlite3.Row | None:
        with self._connect() as connection:
            return connection.execute("SELECT * FROM documents WHERE document_key = ?", (document_key,)).fetchone()

    def list_selection_ids(self, logical_node_id: str) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id FROM selections WHERE logical_node_id = ? ORDER BY created_at ASC",
                (logical_node_id,),
            ).fetchall()
        return [row["id"] for row in rows]
