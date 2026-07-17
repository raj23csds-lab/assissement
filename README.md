# Tri9T PDF Parsing Pipeline

An end-to-end document processing pipeline developed for the **Tri9T AI Engineering Internship Assignment**.

The application ingests PDF documents, reconstructs their hierarchical structure, maintains document version history, generates QA test cases for selected sections, and detects stale test cases when document content changes. The pipeline is accessible through both a **FastAPI REST API** and a **Command-Line Interface (CLI)**.

---

## Features

* Extracts text from PDF documents using **pypdf**
* Reconstructs a hierarchical document tree consisting of headings, subheadings, paragraphs, bullet lists, numbered lists, and table-like rows
* Maintains version history for ingested documents
* Stores document metadata and hierarchy in **SQLite**
* Generates deterministic QA test-case drafts for selected document sections
* Stores generated test cases as **JSON** artifacts
* Detects stale test cases by comparing document revisions using content hashing
* Exposes all functionality through a FastAPI REST API and a Command-Line Interface (CLI)

---

## Tech Stack

| Technology | Purpose                         |
| ---------- | ------------------------------- |
| Python     | Core programming language       |
| FastAPI    | REST API framework              |
| Pydantic   | Request and response validation |
| SQLite     | Document and version storage    |
| pypdf      | PDF text extraction             |
| JSON       | Test-case artifact storage      |

---

## System Architecture

```text
                PDF Document
                      │
                      ▼
              PDF Parser (pypdf)
                      │
                      ▼
        Hierarchical Document Tree
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
   SQLite Database          JSON Artifact Store
(Document Structure,         (Generated QA
 Versions, Revisions)        Test Cases)
                      │
                      ▼
             FastAPI REST API / CLI
```

---

## Project Workflow

1. Ingest a PDF document.
2. Extract and normalize text using **pypdf**.
3. Reconstruct the document into a hierarchical tree.
4. Store document versions, logical nodes, and revisions in **SQLite**.
5. Generate QA test cases for selected nodes.
6. Store generated test cases as JSON artifacts.
7. Detect stale test cases whenever document content changes.



## Usage

### Ingest a Document

```bash
python -m tri9t_pipeline ingest "C:\Users\Rakshitha J\Downloads\AI Engineering Internship Assignment - Tri9T AI (1).pdf" --document-key tri9t-assignment --title "Tri9T Assignment"
```

### Start the API Server

```bash
python -m tri9t_pipeline serve
```

The server starts locally and exposes the REST API endpoints.

---

## API Endpoints

| Method | Endpoint                                               | Description                                        |
| ------ | ------------------------------------------------------ | -------------------------------------------------- |
| POST   | `/documents/ingest`                                    | Ingest a PDF document                              |
| GET    | `/documents/{document_key}/versions/{version_id}/tree` | Retrieve the parsed document hierarchy             |
| POST   | `/selections`                                          | Create a document selection                        |
| POST   | `/test-cases/generate`                                 | Generate QA test cases                             |
| GET    | `/test-cases/by-selection/{selection_id}`              | Retrieve test cases for a selection                |
| GET    | `/test-cases/by-node/{logical_node_id}`                | Retrieve test cases associated with a logical node |

---

## Storage Design

### SQLite

The relational database stores:

* Documents
* Document versions
* Logical nodes
* Node revisions
* User selections

### JSON Artifact Store

Generated QA test cases and their associated metadata are stored as JSON artifacts. JSON provides a lightweight, portable, and human-readable storage format suitable for downstream processing.

---

## Design Decisions

* **pypdf** was selected because the assignment PDF contains an extractable text layer, making OCR unnecessary.
* **SQLite** provides lightweight, reliable persistence for document structures, versions, and revisions.
* **JSON** serves as a portable artifact store for generated QA test cases.
* **Content hashing** enables efficient stale test-case detection without reprocessing unchanged document sections.

---

## Limitations

* Scanned or image-only PDFs are not currently supported.
* Heading detection is based primarily on textual patterns rather than font size or layout information.
* Cross-version node matching relies on structural identity instead of semantic similarity.

---

## Future Enhancements

* OCR support for scanned PDF documents
* Layout-aware parsing using font and positional metadata
* Semantic node matching across document versions
* Interactive document tree visualization
* Automated parser regression testing
* Enhanced test-case generation using LLM-based validation

---

## Assignment Scope

This implementation satisfies the primary requirements of the Tri9T AI Engineering Internship Assignment by providing:

* PDF text extraction
* Hierarchical document reconstruction
* Version-aware document storage
* Logical node management
* QA test-case generation
* JSON artifact persistence
* Stale test-case detection
* FastAPI-based REST services
* Command-Line Interface (CLI)


