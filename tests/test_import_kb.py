import zipfile

from scripts.import_kb import import_from_folder, import_from_zip


def test_import_from_folder_copies_markdown(tmp_path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    (source / "a" ).mkdir(parents=True)
    (source / "a" / "doc.md").write_text("# Doc\n", encoding="utf-8")

    summary = import_from_folder(source, target)

    assert summary.copied == 1
    assert (target / "a" / "doc.md").read_text(encoding="utf-8") == "# Doc\n"


def test_import_ignores_hidden_files_and_folders(tmp_path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    (source / ".hidden").mkdir(parents=True)
    (source / ".hidden" / "doc.md").write_text("# Secret\n", encoding="utf-8")
    (source / ".secret.md").write_text("# Secret\n", encoding="utf-8")

    summary = import_from_folder(source, target)

    assert summary.copied == 0
    assert summary.ignored >= 1
    assert not target.exists()


def test_import_ignores_non_markdown_files(tmp_path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    source.mkdir()
    (source / "notes.txt").write_text("text", encoding="utf-8")
    (source / "archive.zip").write_bytes(b"not a real zip")

    summary = import_from_folder(source, target)

    assert summary.copied == 0
    assert summary.ignored == 2


def test_dry_run_does_not_write(tmp_path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    source.mkdir()
    (source / "doc.md").write_text("# Doc\n", encoding="utf-8")

    summary = import_from_folder(source, target, dry_run=True)

    assert summary.copied == 1
    assert not (target / "doc.md").exists()


def test_zip_import_blocks_path_traversal(tmp_path):
    archive = tmp_path / "kb.zip"
    target = tmp_path / "target"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../evil.md", "# Evil\n")
        zf.writestr("good.md", "# Good\n")

    summary = import_from_zip(archive, target)

    assert summary.errors == 1
    assert (target / "good.md").exists()
    assert not (tmp_path / "evil.md").exists()


def test_prefix_import_writes_under_prefix(tmp_path):
    source = tmp_path / "src"
    target = tmp_path / "target"
    source.mkdir()
    (source / "doc.md").write_text("# Doc\n", encoding="utf-8")

    summary = import_from_folder(source, target, prefix="imported/IT-Playbook-Max")

    assert summary.copied == 1
    assert (target / "imported" / "IT-Playbook-Max" / "doc.md").exists()
    assert not (target / "doc.md").exists()
