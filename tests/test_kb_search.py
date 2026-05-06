from app.kb.models import KnowledgeDocument
from app.kb.search import search_documents


def test_search_finds_document_by_title_content_and_tags():
    docs = [
        KnowledgeDocument(
            path="linux/dns.md",
            title="Linux DNS quick check",
            content="Use resolvectl status when name resolution fails.",
            headings=["Linux DNS quick check"],
            metadata={"domain": "linux", "tags": ["dns"]},
            tags=["dns"],
            domain="linux",
        )
    ]

    results = search_documents("dns resolvectl", docs, limit=5)

    assert len(results) == 1
    assert results[0].score > 0
    assert results[0].snippet
    assert results[0].path == "linux/dns.md"
