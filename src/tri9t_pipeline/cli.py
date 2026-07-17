from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from .service import PipelineService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tri9T PDF parsing and QA pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Ingest a PDF and persist the parsed hierarchy")
    ingest.add_argument("pdf_path")
    ingest.add_argument("--document-key")
    ingest.add_argument("--title")

    tree = subparsers.add_parser("tree", help="Print a stored version tree")
    tree.add_argument("document_key")
    tree.add_argument("version_id")

    generate = subparsers.add_parser("generate", help="Generate test cases for a stored selection")
    generate.add_argument("selection_id")

    serve = subparsers.add_parser("serve", help="Start the FastAPI app")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", default=8000, type=int)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    service = PipelineService()

    if args.command == "ingest":
        result = service.ingest_pdf(args.pdf_path, document_key=args.document_key, title=args.title)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "tree":
        result = service.version_tree(args.document_key, args.version_id)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "generate":
        result = service.generate_for_selection(args.selection_id)
        print(json.dumps(result, indent=2))
        return 0

    uvicorn.run("tri9t_pipeline.api:app", host=args.host, port=args.port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
