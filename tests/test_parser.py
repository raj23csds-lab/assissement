from pathlib import Path

from tri9t_pipeline.parser import PdfHierarchyParser


def test_duplicate_headings_get_distinct_nodes_and_correct_parent(tmp_path: Path):
    parser = PdfHierarchyParser()
    pages = [
        "Overview\nIntro line\nDetails\nFirst details line\nDetails\nSecond details line",
    ]
    document = parser.parse_pages(pages, source_path=tmp_path / "sample.pdf", title="sample")

    overview = document.roots[0]
    assert overview.kind == "heading"
    detail_headings = [node for node in overview.children if node.kind == "heading"]
    assert len(detail_headings) == 2
    assert detail_headings[0].heading == "Details"
    assert detail_headings[1].heading == "Details"
    assert detail_headings[0] is not detail_headings[1]
    assert all(node.level == 2 for node in detail_headings)


def test_numbered_headings_and_bullets_preserve_hierarchy(tmp_path: Path):
    parser = PdfHierarchyParser()
    pages = [
        "1. Parent\n● first requirement\n● second requirement\n1.1 Child\nNested body",
    ]
    document = parser.parse_pages(pages, source_path=tmp_path / "sample.pdf", title="sample")

    parent = document.roots[0]
    assert parent.kind == "heading"
    assert [child.kind for child in parent.children[:2]] == ["list_item", "list_item"]
    child = parent.children[2]
    assert child.kind == "heading"
    assert child.level == 2
    assert child.children[0].body == "Nested body"


def test_wrapped_paragraph_lines_attach_to_the_same_block(tmp_path: Path):
    parser = PdfHierarchyParser()
    pages = [
        "Key Terms\nThis sentence is long and\ncontinues on the next line\n\nAnother block",
    ]
    document = parser.parse_pages(pages, source_path=tmp_path / "sample.pdf", title="sample")

    heading = document.roots[0]
    paragraph = next(child for child in heading.children if child.kind == "paragraph")
    assert paragraph.body == "This sentence is long and continues on the next line"
