#!/usr/bin/env python3
"""
Basic Python CLI template for sysadmin scripts.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Basic admin script template")
    parser.add_argument("--input", type=Path, required=True, help="Input file or directory")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without changing anything")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def process_path(path: Path, dry_run: bool) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")

    logging.info("Processing: %s", path)

    if dry_run:
        logging.info("[DRY-RUN] Would process %s", path)
        return

    # TODO: real work here
    logging.info("Done")


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    try:
        process_path(args.input, args.dry_run)
    except Exception as exc:
        logging.exception("Failed: %s", exc)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
