from pathlib import Path

from fastapi.testclient import TestClient

import tri9t_pipeline.api as api_module
from tri9t_pipeline.service import PipelineService


def test_api_round_trip(tmp_path: Path, monkeypatch):
    db_path = tmp_path / "api.db"
    artifacts_path = tmp_path / "api.json"
    artifacts_path.write_text('{"items": []}', encoding="utf-8")
    service = PipelineService(database_path=db_path, artifacts_path=artifacts_path)
    monkeypatch.setattr(api_module, "service", service)

    pdf_path = tmp_path / "sample.txt"
    pdf_path.write_text("Section\nBullet item", encoding="utf-8")
    parsed = service.parser.parse_pages([pdf_path.read_text(encoding="utf-8")], source_path=pdf_path, title="sample")
    ingest = service.repository.ingest("sample", parsed, "hash-1")

    tree = service.version_tree("sample", ingest["version_id"])
    node_id = tree[0]["id"]

    client = TestClient(api_module.app)
    selection = client.post(
        "/selections",
        json={
            "document_key": "sample",
            "version_id": ingest["version_id"],
            "logical_node_id": node_id,
            "note": "api selection",
        },
    )
    assert selection.status_code == 200

    generated = client.post("/test-cases/generate", json={"selection_id": selection.json()["selection_id"]})
    assert generated.status_code == 200
    assert generated.json()

    tree_response = client.get(f"/documents/sample/versions/{ingest['version_id']}/tree")
    assert tree_response.status_code == 200
    assert tree_response.json()
