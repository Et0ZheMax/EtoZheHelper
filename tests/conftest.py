import os
import tempfile
from pathlib import Path


def pytest_configure(config):
    test_root = Path(tempfile.mkdtemp(prefix="etozhehelper-tests-"))
    data_dir = test_root / "data"
    kb_dir = test_root / "knowledge_base"
    data_dir.mkdir(parents=True, exist_ok=True)
    kb_dir.mkdir(parents=True, exist_ok=True)
    (kb_dir / "dns.md").write_text(
        """---
type: runbook
domain: linux
tags: [dns, ubuntu]
risk: low
requires_root: false
---

# Ubuntu DNS troubleshooting

Use resolvectl status and getent hosts for safe local diagnostics.
""",
        encoding="utf-8",
    )

    os.environ["DATABASE_URL"] = f"sqlite:///{(data_dir / 'test.db').as_posix()}"
    os.environ["KNOWLEDGE_BASE_DIR"] = str(kb_dir)
