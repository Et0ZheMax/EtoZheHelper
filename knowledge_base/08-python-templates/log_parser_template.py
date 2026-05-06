#!/usr/bin/env python3
"""
Generic log parser template.
"""

from __future__ import annotations

import argparse
import logging
import re
from pathlib import Path


LINE_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*?\|(?P<id>[^|]+)\|(?P<payload>.+)$"
)


def parse_line(line: str) -> dict | None:
    match = LINE_RE.search(line)
    if not match:
        return None
    return match.groupdict()


def parse_file(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for number, line in enumerate(f, start=1):
            parsed = parse_line(line.strip())
            if parsed:
                parsed["line"] = number
                rows.append(parsed)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("logfile", type=Path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    rows = parse_file(args.logfile)
    for row in rows:
        print(row)

    logging.info("Parsed %s rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
