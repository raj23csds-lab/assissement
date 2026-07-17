# Approach

## Parsing Strategy

The PDF is text-extractable, so the pipeline starts with `pypdf` instead of OCR. The parser normalizes extracted lines, recognizes numbered headings, short title-case headings, bullets, numbered list items, and simple table-like rows, then builds a nested tree.

## Versioning Strategy

Each ingest creates a new version row. Logical nodes are keyed structurally so a node can keep the same identity across versions while its body changes. A new revision row is written for every version, which makes staleness checks possible by comparing the saved content hash with the latest one.

## Artifact Store

Generated QA output is stored as JSON because the assignment allows a justified JSON store as the NoSQL layer. SQLite is used for the document tree, version history, and selections.

## Decision Log

1. What is most likely to silently give wrong results without erroring?

   Heading inference is the weakest part. A short sentence can look like a heading, and a real heading can look like prose. I would catch this by maintaining parser fixtures from real PDFs and snapshotting the resulting tree shape, then diffing node counts, heading paths, and parent/child relationships on every change.

2. Where did you choose simplicity over correctness, and what would break first in production?

   I used structural identity rather than a semantic diff model for version matching. That keeps the system runnable and the staleness check visible, but if a section is rewritten and moved, the matcher may split one logical concept into multiple nodes. The first thing to break would be cross-version traceability for heavily edited documents.

3. Name one input you did not handle, and what happens when the system sees it.

   Scanned-image PDFs without an extractable text layer are not handled here. The parser will return weak or empty structure, and the pipeline should surface that as a low-confidence ingest rather than pretending the hierarchy is reliable.

## What I Would Do With More Time

- Add font-size and layout-aware parsing using a PDF library with richer geometry support.
- Add OCR fallback for image-only PDFs.
- Add similarity-based cross-version node matching.
- Add a UI for browsing the tree and reviewing stale test cases.
