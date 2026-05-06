#!/usr/bin/env python3
"""
Safe subprocess wrapper.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def run_command(command: list[str], timeout: int = 30) -> CommandResult:
    proc = subprocess.run(
        command,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return CommandResult(
        command=command,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


if __name__ == "__main__":
    result = run_command(["hostname"])
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr)
