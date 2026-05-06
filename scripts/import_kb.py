#!/usr/bin/env python3
"""Safely import Markdown knowledge base files from a folder or zip archive."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

IGNORED_SUFFIXES = {
    ".env",
    ".key",
    ".pem",
    ".p12",
    ".sqlite",
    ".db",
    ".zip",
}


@dataclass
class ImportSummary:
    copied: int = 0
    updated: int = 0
    skipped: int = 0
    ignored: int = 0
    errors: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "copied": self.copied,
            "updated": self.updated,
            "skipped": self.skipped,
            "ignored": self.ignored,
            "errors": self.errors,
        }


def _has_hidden_part(path: Path | PurePosixPath) -> bool:
    return any(part.startswith(".") for part in path.parts if part not in {".", ""})


def _is_allowed_markdown(path: Path | PurePosixPath) -> bool:
    suffix = path.suffix.lower()
    if _has_hidden_part(path):
        return False
    if suffix != ".md":
        return False
    if suffix in IGNORED_SUFFIXES:
        return False
    return True


def _normalize_prefix(prefix: str | None) -> PurePosixPath:
    if not prefix:
        return PurePosixPath("")
    normalized = PurePosixPath(prefix.replace("\\", "/"))
    if normalized.is_absolute() or ".." in normalized.parts or _has_hidden_part(normalized):
        raise ValueError("--prefix must be a safe relative path without hidden or parent-traversal parts")
    return normalized


def _safe_target_path(target_root: Path, relative: PurePosixPath) -> Path:
    destination = (target_root / Path(*relative.parts)).resolve()
    root = target_root.resolve()
    if destination != root and root not in destination.parents:
        raise ValueError(f"Refusing to write outside target: {relative.as_posix()}")
    return destination


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _copy_bytes(data: bytes, destination: Path, summary: ImportSummary, *, dry_run: bool) -> None:
    if destination.exists():
        existing_hash = _sha256_file(destination)
        new_hash = _sha256_bytes(data)
        if existing_hash == new_hash:
            summary.skipped += 1
            return
        summary.updated += 1
    else:
        summary.copied += 1

    if dry_run:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)


def _copy_file(source: Path, destination: Path, summary: ImportSummary, *, dry_run: bool) -> None:
    if destination.exists():
        try:
            if _sha256_file(source) == _sha256_file(destination):
                summary.skipped += 1
                return
            summary.updated += 1
        except OSError:
            summary.errors += 1
            return
    else:
        summary.copied += 1

    if dry_run:
        return
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    except OSError:
        summary.errors += 1


def import_from_folder(source: str | Path, target: str | Path, *, prefix: str | None = None, dry_run: bool = False) -> ImportSummary:
    source_root = Path(source).expanduser().resolve()
    target_root = Path(target).expanduser().resolve()
    safe_prefix = _normalize_prefix(prefix)
    summary = ImportSummary()

    if not source_root.exists() or not source_root.is_dir():
        raise ValueError(f"Source directory not found: {source_root}")

    for path in sorted(source_root.rglob("*")):
        try:
            relative_path = path.relative_to(source_root)
        except ValueError:
            summary.errors += 1
            continue
        relative = PurePosixPath(relative_path.as_posix())
        if path.is_dir():
            if _has_hidden_part(relative):
                summary.ignored += 1
            continue
        if not _is_allowed_markdown(relative):
            summary.ignored += 1
            continue
        try:
            destination = _safe_target_path(target_root, safe_prefix / relative)
            _copy_file(path, destination, summary, dry_run=dry_run)
        except (OSError, ValueError):
            summary.errors += 1
    return summary


def _safe_zip_relative(name: str) -> PurePosixPath | None:
    normalized_name = name.replace("\\", "/")
    relative = PurePosixPath(normalized_name)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    return relative


def import_from_zip(zip_path: str | Path, target: str | Path, *, prefix: str | None = None, dry_run: bool = False) -> ImportSummary:
    archive_path = Path(zip_path).expanduser().resolve()
    target_root = Path(target).expanduser().resolve()
    safe_prefix = _normalize_prefix(prefix)
    summary = ImportSummary()

    if not archive_path.exists() or not archive_path.is_file():
        raise ValueError(f"Zip archive not found: {archive_path}")

    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            relative = _safe_zip_relative(info.filename)
            if relative is None:
                summary.errors += 1
                continue
            if info.is_dir():
                if _has_hidden_part(relative):
                    summary.ignored += 1
                continue
            if not _is_allowed_markdown(relative):
                summary.ignored += 1
                continue
            try:
                destination = _safe_target_path(target_root, safe_prefix / relative)
                data = archive.read(info)
                _copy_bytes(data, destination, summary, dry_run=dry_run)
            except (OSError, ValueError, zipfile.BadZipFile):
                summary.errors += 1
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely import Markdown files into the local knowledge_base.")
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--source", help="Source directory with Markdown files")
    source_group.add_argument("--zip", dest="zip_path", help="Source zip archive with Markdown files")
    parser.add_argument("--target", required=True, help="Target knowledge base directory")
    parser.add_argument("--prefix", help="Safe relative target prefix, for example imported/IT-Playbook-Max")
    parser.add_argument("--dry-run", action="store_true", help="Report planned changes without writing files")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.source:
            summary = import_from_folder(args.source, args.target, prefix=args.prefix, dry_run=args.dry_run)
        else:
            summary = import_from_zip(args.zip_path, args.target, prefix=args.prefix, dry_run=args.dry_run)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))

    for key, value in summary.as_dict().items():
        print(f"{key}: {value}")
    return 1 if summary.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
