from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .schemas import CaseResponse, GenerateRequest, IngestRequest, SelectionCreateRequest
from .service import PipelineService


app = FastAPI(title="Tri9T PDF Pipeline", version="0.1.0")
service = PipelineService()


@app.post("/documents/ingest")
def ingest_document(request: IngestRequest):
    return service.ingest_pdf(request.pdf_path, document_key=request.document_key, title=request.title)


@app.get("/documents/{document_key}/versions/{version_id}/tree")
def get_tree(document_key: str, version_id: str):
    return service.version_tree(document_key, version_id)


@app.post("/selections")
def create_selection(request: SelectionCreateRequest):
    try:
        return service.create_selection(request.document_key, request.version_id, request.logical_node_id, request.note)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/test-cases/generate", response_model=list[CaseResponse])
def generate_cases(request: GenerateRequest):
    return service.generate_for_selection(request.selection_id)


@app.get("/test-cases/by-selection/{selection_id}")
def cases_by_selection(selection_id: str):
    return service.refresh_case_views_by_selection(selection_id)


@app.get("/test-cases/by-node/{logical_node_id}")
def cases_by_node(logical_node_id: str):
    return service.refresh_case_views_by_node(logical_node_id)
