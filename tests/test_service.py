from pathlib import Path

from tri9t_pipeline.service import PipelineService


def _seed_service(tmp_path: Path) -> PipelineService:
    db_path = tmp_path / "tri9t.db"
    artifacts_path = tmp_path / "cases.json"
    artifacts_path.write_text('{"items": []}', encoding="utf-8")
    return PipelineService(database_path=db_path, artifacts_path=artifacts_path)


def test_versioning_and_staleness_are_visible(tmp_path: Path):
    service = _seed_service(tmp_path)

    pdf_v1 = tmp_path / "manual_v1.txt"
    pdf_v1.write_text("Section\nOne requirement", encoding="utf-8")
    parsed_v1 = service.parser.parse_pages([pdf_v1.read_text(encoding="utf-8")], source_path=pdf_v1, title="manual")
    ingest_v1 = service.repository.ingest("manual", parsed_v1, "hash-v1")

    tree_v1 = service.version_tree("manual", ingest_v1["version_id"])
    logical_node_id = next(child["id"] for child in tree_v1[0]["children"] if child["kind"] == "paragraph")
    selection = service.create_selection("manual", ingest_v1["version_id"], logical_node_id, note="baseline")
    generated = service.generate_for_selection(selection["selection_id"])
    assert generated
    assert generated[0]["staleness_status"] == "fresh"

    pdf_v2 = tmp_path / "manual_v2.txt"
    pdf_v2.write_text("Section\nOne requirement updated", encoding="utf-8")
    parsed_v2 = service.parser.parse_pages([pdf_v2.read_text(encoding="utf-8")], source_path=pdf_v2, title="manual")
    service.repository.ingest("manual", parsed_v2, "hash-v2")

    refreshed = service.refresh_case_views_by_selection(selection["selection_id"])
    assert refreshed[0]["staleness_status"] == "stale"
