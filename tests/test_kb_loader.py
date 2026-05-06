from app.kb.loader import load_knowledge_base


def test_loader_reads_markdown_and_frontmatter(tmp_path):
    kb = tmp_path / "kb"
    kb.mkdir()
    (kb / "dns.md").write_text(
        """---
type: runbook
domain: linux
tags: [dns, resolved]
risk: low
requires_root: false
---

# DNS Runbook

## Check resolver

Use resolvectl status.
""",
        encoding="utf-8",
    )

    docs = load_knowledge_base(kb)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.title == "DNS Runbook"
    assert doc.headings == ["DNS Runbook", "Check resolver"]
    assert doc.metadata["type"] == "runbook"
    assert doc.tags == ["dns", "resolved"]
    assert doc.domain == "linux"
    assert doc.risk == "low"
    assert doc.requires_root is False
