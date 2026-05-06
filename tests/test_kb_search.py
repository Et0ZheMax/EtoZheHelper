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


def test_synonym_search_finds_dns_doc_for_russian_resolution_issue():
    docs = [
        KnowledgeDocument(
            path="linux/dns.md",
            title="DNS deep dive",
            content="Use resolvectl status and getent hosts when name resolution fails.",
            headings=["DNS deep dive"],
            metadata={"domain": "linux", "tags": ["dns"]},
            tags=["dns"],
            domain="linux",
            doc_type="runbook",
            risk="low",
        )
    ]

    results = search_documents("не резолвится", docs, limit=5)

    assert results
    assert results[0].path == "linux/dns.md"


def test_search_snippet_is_not_empty_or_huge():
    docs = [
        KnowledgeDocument(
            path="linux/dns.md",
            title="DNS deep dive",
            content=("Intro text. " * 80) + "\n## resolvectl checks\nUse resolvectl status safely." + (" tail" * 80),
            headings=["DNS deep dive", "resolvectl checks"],
        )
    ]

    results = search_documents("resolvectl", docs, limit=5)

    assert results[0].snippet
    assert len(results[0].snippet) <= 402
    assert "resolvectl checks" in results[0].snippet


def test_search_returns_matched_terms_metadata():
    docs = [
        KnowledgeDocument(
            path="linux/dns.md",
            title="DNS deep dive",
            content="Use dig for DNS checks.",
            headings=["DNS deep dive"],
            tags=["dns"],
        )
    ]

    results = search_documents("dns", docs, limit=5)

    assert "matched_terms" in results[0].metadata
    assert "dns" in results[0].metadata["matched_terms"]


def test_document_summary_mapping_deduplicates_search_results():
    from app.api.chat import _document_summaries

    docs = [
        KnowledgeDocument(path="linux/dns.md", title="DNS", content="Use resolvectl.", headings=["DNS"]),
        KnowledgeDocument(path="linux/dns.md", title="DNS copy", content="Use resolvectl too.", headings=["DNS copy"]),
    ]

    summaries = _document_summaries(docs, "resolvectl")

    assert [summary.path for summary in summaries] == ["linux/dns.md"]
