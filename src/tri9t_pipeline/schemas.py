from __future__ import annotations

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    pdf_path: str = Field(..., description="Local PDF path on the server machine")
    document_key: str | None = None
    title: str | None = None


class SelectionCreateRequest(BaseModel):
    document_key: str
    version_id: str
    logical_node_id: str
    note: str = ""


class GenerateRequest(BaseModel):
    selection_id: str


class CaseResponse(BaseModel):
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
