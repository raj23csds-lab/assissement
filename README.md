# Tri9T PDF Pipeline

This repository builds an end-to-end PDF parsing pipeline for the Tri9T AI assignment update.

It ingests a PDF, reconstructs a hierarchical tree, persists versioned nodes in SQLite, stores generated QA artifacts in JSON, and exposes retrieval and staleness checks through FastAPI and a CLI.

## What It Does

- Parses PDF text with `pypdf`.
- Reconstructs headings, subsections, paragraphs, bullets, and table-like rows into a tree.
- Stores documents, versions, logical nodes, revisions, and selections in SQLite.
- Generates deterministic QA test-case drafts from selected nodes.
- Stores generated artifacts in a JSON file to satisfy the NoSQL requirement.
- Returns a fresh/stale status for previously generated test cases.

## Run It

Install dependencies, then use one of these commands:

```bash
python -m tri9t_pipeline ingest "C:\Users\Rakshitha J\Downloads\AI Engineering Internship Assignment - Tri9T AI (1).pdf" --document-key tri9t-assignment --title "Tri9T Assignment"
python -m tri9t_pipeline serve
```

The API exposes:

- `POST /documents/ingest`
- `GET /documents/{document_key}/versions/{version_id}/tree`
- `POST /selections`
- `POST /test-cases/generate`
- `GET /test-cases/by-selection/{selection_id}`
- `GET /test-cases/by-node/{logical_node_id}`

## Notes

The assignment asked for FastAPI, Pydantic, SQLAlchemy, and SQLite. This implementation keeps the FastAPI and SQLite parts, but uses the standard library `sqlite3` module instead of SQLAlchemy because the current Windows 32-bit Python environment could not build the `greenlet` dependency required by SQLAlchemy on this machine.
