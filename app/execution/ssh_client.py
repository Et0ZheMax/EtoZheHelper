from __future__ import annotations

import socket
import time
from dataclasses import dataclass
from typing import Protocol

SSH_CLIENT_STDOUT_LIMIT = 64 * 1024 + 1
SSH_CLIENT_STDERR_LIMIT = 32 * 1024 + 1
SSH_POLL_INTERVAL_SECONDS = 0.05


@dataclass(frozen=True)
class SshCommandResult:
    exit_code: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False


class SshClientProtocol(Protocol):
    def run_command(
        self,
        hostname: str,
        port: int,
        username: str,
        command: str,
        connect_timeout: int,
        command_timeout: int,
    ) -> SshCommandResult:
        ...


class DefaultSshClient:
    """Tiny Paramiko wrapper for bounded, non-interactive SSH agent execution."""

    def run_command(
        self,
        hostname: str,
        port: int,
        username: str,
        command: str,
        connect_timeout: int,
        command_timeout: int,
    ) -> SshCommandResult:
        import paramiko

        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                timeout=connect_timeout,
                banner_timeout=connect_timeout,
                auth_timeout=connect_timeout,
                look_for_keys=True,
                allow_agent=True,
            )
            _stdin, stdout_file, _stderr_file = client.exec_command(command, timeout=command_timeout)
            channel = stdout_file.channel
            channel.settimeout(SSH_POLL_INTERVAL_SECONDS)
            stdout = bytearray()
            stderr = bytearray()
            deadline = time.monotonic() + command_timeout
            timed_out = False

            while True:
                if channel.recv_ready():
                    chunk = channel.recv(4096)
                    if chunk and len(stdout) < SSH_CLIENT_STDOUT_LIMIT:
                        remaining = SSH_CLIENT_STDOUT_LIMIT - len(stdout)
                        stdout.extend(chunk[:remaining])
                if channel.recv_stderr_ready():
                    chunk = channel.recv_stderr(4096)
                    if chunk and len(stderr) < SSH_CLIENT_STDERR_LIMIT:
                        remaining = SSH_CLIENT_STDERR_LIMIT - len(stderr)
                        stderr.extend(chunk[:remaining])
                if channel.exit_status_ready():
                    while channel.recv_ready():
                        chunk = channel.recv(4096)
                        if chunk and len(stdout) < SSH_CLIENT_STDOUT_LIMIT:
                            remaining = SSH_CLIENT_STDOUT_LIMIT - len(stdout)
                            stdout.extend(chunk[:remaining])
                    while channel.recv_stderr_ready():
                        chunk = channel.recv_stderr(4096)
                        if chunk and len(stderr) < SSH_CLIENT_STDERR_LIMIT:
                            remaining = SSH_CLIENT_STDERR_LIMIT - len(stderr)
                            stderr.extend(chunk[:remaining])
                    exit_code = channel.recv_exit_status()
                    return SshCommandResult(exit_code=exit_code, stdout=bytes(stdout), stderr=bytes(stderr))
                if time.monotonic() >= deadline:
                    timed_out = True
                    channel.close()
                    return SshCommandResult(exit_code=None, stdout=bytes(stdout), stderr=bytes(stderr), timed_out=timed_out)
                time.sleep(SSH_POLL_INTERVAL_SECONDS)
        except socket.timeout:
            return SshCommandResult(exit_code=None, stdout=b"", stderr=b"", timed_out=True)
        finally:
            client.close()


ParamikoSshClient = DefaultSshClient
